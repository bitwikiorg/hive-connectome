from __future__ import annotations

import json
from typing import Any

from hive_connectome.brains.synthetic import DeterministicMiniBrain
from hive_connectome.brains.connectome import CookConnectomeBrain, MaleCNSLocomotorBrain
from hive_connectome.db import HiveDB
from hive_connectome.providers.lmstudio import LMStudio
from hive_connectome.providers.venice import VeniceChat, VeniceJev
from hive_connectome.schemas import (
    BrainKind,
    DecisionBundle,
    DecisionType,
    JevQuestion,
    PipelineRequest,
    PipelineResult,
)
from hive_connectome.workers import WorkerSpec, WorkerStore
from hive_connectome.brains.base import MiniBrain


def brain_readout(state: dict[str, Any]) -> DecisionBundle:
    novelty = min(2.0, float(state["bee"]["metrics"]["novelty"]) * 20.0)
    meaningful = min(0.98, 0.35 + float(state["bee"]["metrics"]["energy"]) * 2.5)
    route = "inspect" if novelty > 0.5 else "store"
    return DecisionBundle(
        provider="brain-readout",
        model="fixed-readout-v1",
        confidence=0.45,
        answers={
            "meaningful_signal": {"type":"noul","noul":meaningful},
            "novelty": {"type":"score","score":novelty,"confidence":0.45},
            "route": {"type":"choice","choice":route,"confidence":0.45},
            "llm_needed": {"type":"noul","noul":0.5},
        },
    )


class HivePipeline:
    def __init__(
        self,
        db: HiveDB,
        workers: WorkerStore,
        venice: VeniceJev | None = None,
        venice_chat: VeniceChat | None = None,
        lmstudio: LMStudio | None = None,
        default_llm_model: str | None = None,
        data_dir=None,
    ):
        self.db = db
        self.workers = workers
        self.venice = venice
        self.venice_chat = venice_chat
        self.lmstudio = lmstudio
        self.default_llm_model = default_llm_model
        from pathlib import Path
        self.data_dir = Path(data_dir or db.path.parent).resolve()
        self._brains: dict[str, tuple[MiniBrain, MiniBrain, tuple]] = {}

    def _engine(self, worker: WorkerSpec, stage: str, spec):
        brain_id = f"{worker.id}:{stage}"
        if spec.engine == "synthetic":
            kind = BrainKind.WORM_LINK if stage == "larva" else BrainKind.FLY_CORE
            return DeterministicMiniBrain(brain_id, kind, spec.state_size)
        pack_id = spec.config.get("pack_id")
        filename = spec.config.get("file")
        if not pack_id or not filename:
            raise ValueError(f"{stage} connectome engine requires config.pack_id and config.file")
        path = self.data_dir / "connectomes" / pack_id / filename
        if spec.engine == "cook2019_connectome":
            return CookConnectomeBrain(brain_id, path, substeps=int(spec.config.get("substeps", 8)))
        if spec.engine == "malecns_locomotor":
            return MaleCNSLocomotorBrain(brain_id, path, ms_per_event=int(spec.config.get("ms_per_event", 10)))
        raise NotImplementedError(f"unknown neural engine: {spec.engine}")

    def _pair(self, worker: WorkerSpec):
        signature = (
            worker.larva.engine,
            worker.larva.state_size,
            worker.larva.substrate,
            json.dumps(worker.larva.config, sort_keys=True, default=str),
            worker.bee.engine,
            worker.bee.state_size,
            worker.bee.substrate,
            json.dumps(worker.bee.config, sort_keys=True, default=str),
        )
        existing = self._brains.get(worker.id)
        if existing and existing[2] == signature:
            return existing[0], existing[1]
        larva = self._engine(worker, "larva", worker.larva)
        bee = self._engine(worker, "bee", worker.bee)
        self._brains[worker.id] = (larva, bee, signature)
        return larva, bee

    def runtime_status(self) -> dict[str, Any]:
        workers = self.workers.list()
        worker = next((w for w in workers if w.id == "scout"), workers[0] if workers else None)
        if worker is None:
            return {"ready": False, "backend": "none", "note": "no workers configured"}
        def stage_status(stage: str, spec):
            if spec.engine == "synthetic":
                return {"engine": spec.engine, "real_connectome_topology": False, "installed": True}
            pack_id, filename = spec.config.get("pack_id"), spec.config.get("file")
            path = self.data_dir / "connectomes" / str(pack_id) / str(filename)
            return {
                "engine": spec.engine,
                "real_connectome_topology": True,
                "installed": path.exists(),
                "pack_id": pack_id,
                "file": filename,
            }
        larva = stage_status("larva", worker.larva)
        bee = stage_status("bee", worker.bee)
        ready = bool(larva["installed"] and bee["installed"] and larva["real_connectome_topology"] and bee["real_connectome_topology"])
        return {
            "ready": ready,
            "backend": f"{larva['engine']} → {bee['engine']}",
            "real_connectome_runtime_ready": ready,
            "larva": larva,
            "bee": bee,
            "note": "Measured connectome topology is executed on each run when ready; input encoding and compact dynamics are engineered experimental layers.",
        }

    def reset(self, worker_id: str | None = None):
        if worker_id is None:
            for larva, bee, _ in self._brains.values():
                larva.reset()
                bee.reset()
            return
        worker = self.workers.get(worker_id)
        existing = self._brains.get(worker.id)
        if existing:
            existing[0].reset()
            existing[1].reset()

    @staticmethod
    def _noul(bundle: DecisionBundle, key: str) -> float:
        try:
            return float(bundle.answers[key]["noul"])
        except Exception:
            return 0.5

    async def run(self, req: PipelineRequest) -> PipelineResult:
        worker = self.workers.get(req.worker_id)
        jev_enabled = worker.jev.enabled if req.jev_enabled is None else req.jev_enabled
        llm_enabled = worker.llm.enabled if req.llm_enabled is None else req.llm_enabled

        if worker.outputs.save_event:
            self.db.insert_event(req.event.model_dump(mode="json"))

        larva_engine, bee_engine = self._pair(worker)
        larva = larva_engine.step({
            "event": req.event.payload,
            "experiment": worker.experiment.kind,
            "objective": worker.experiment.objective,
        })
        bee = bee_engine.step({
            "event": req.event.payload,
            "larva_metrics": larva.metrics,
            "larva_state_excerpt": larva.state_vector[:8],
            "experiment": worker.experiment.kind,
            "objective": worker.experiment.objective,
        })

        decision_state = {
            "worker": {
                "id": worker.id,
                "name": worker.name,
                "role": worker.role,
                "experiment": worker.experiment.model_dump(mode="json"),
                "data_environment": worker.data_environment.model_dump(mode="json"),
                "jev_enabled": jev_enabled,
                "llm_enabled": llm_enabled,
            },
            "event": req.event.model_dump(mode="json"),
            "larva": {"metrics": larva.metrics, "state_excerpt": larva.state_vector[:8]},
            "bee": {"metrics": bee.metrics, "state_excerpt": bee.state_vector[:12]},
        }

        decisions = brain_readout(decision_state)
        live_jev = jev_enabled and req.mode != "offline" and self.venice is not None
        unresolved: list[str] = []

        if jev_enabled:
            if live_jev:
                decisions = await self.venice.decide(
                    decision_state,
                    worker.jev.questions,
                    model=worker.jev.model,
                )
            elif req.mode != "offline":
                raise RuntimeError("JEV was requested, but Venice/JEV is not configured. HIVE will not silently substitute the fixed readout.")

        novelty = float(decisions.answers.get("novelty", {}).get("score", 1.0))
        meaningful = self._noul(decisions, "meaningful_signal")
        route = decisions.answers.get("route", {}).get("choice", "store")
        llm_needed = self._noul(decisions, "llm_needed")

        modulation = max(-1.0, min(1.0, (meaningful - 0.5) * 0.8 + (novelty - 1.0) * 0.2))
        if worker.jev.feedback_to_brain and jev_enabled:
            larva_engine.feedback(modulation)
            bee_engine.feedback(modulation)

        should_llm = False
        if llm_enabled:
            activation = worker.llm.activation
            if activation == "always":
                should_llm = True
            elif activation == "manual":
                should_llm = req.force_llm
            else:
                if jev_enabled:
                    should_llm = req.force_llm or llm_needed >= worker.jev.llm_gate_threshold or route == "escalate"
                else:
                    should_llm = True
        elif req.force_llm:
            should_llm = True

        llm = None
        if should_llm:
            if worker.llm.provider == "lmstudio":
                model = worker.llm.model or self.default_llm_model
                if self.lmstudio is not None and model:
                    llm = await self.lmstudio.chat(
                        model,
                        worker.llm.prompt or worker.experiment.task_prompt,
                        json.dumps(decision_state, default=str),
                        temperature=worker.llm.temperature,
                    )
                else:
                    unresolved.append("LLM required but LM Studio/model is not configured.")
            else:
                if self.venice_chat is not None and worker.llm.model:
                    llm = await self.venice_chat.chat(
                        worker.llm.model,
                        worker.llm.prompt or worker.experiment.task_prompt,
                        json.dumps(decision_state, default=str),
                        temperature=worker.llm.temperature,
                    )
                elif self.venice_chat is None:
                    unresolved.append("Venice LLM required but no Venice API key is configured.")
                else:
                    unresolved.append("Venice LLM required but this worker has no Venice chat model configured.")

        verification = None
        if llm is not None and live_jev and worker.llm.verify_with_jev:
            verification = await self.venice.decide(
                {"evidence": decision_state, "llm_output": llm.text},
                {
                    "supported": JevQuestion(
                        type=DecisionType.NOUL,
                        instructions="Is the LLM output supported by the supplied evidence without unsupported claims?",
                    )
                },
                model=worker.jev.model,
            )

        labels = [
            f"worker:{worker.id}",
            f"experiment:{worker.experiment.kind}",
            f"route:{route}",
            f"jev:{'on' if jev_enabled else 'off'}",
            f"llm:{'on' if llm_enabled else 'off'}",
        ]
        if meaningful >= 0.7:
            labels.append("meaningful")
        if novelty >= 1.4:
            labels.append("novel")

        result = PipelineResult(
            event=req.event,
            worm=larva,
            fly=bee,
            decisions=decisions,
            llm=llm,
            verification=verification,
            modulation=modulation,
            labels=labels if worker.outputs.write_labels else [],
            unresolved=unresolved,
            execution={
                "larva": {"engine": larva.engine, "real_connectome_topology": bool(larva.metadata.get("real_connectome_topology")), "metadata": larva.metadata},
                "bee": {"engine": bee.engine, "real_connectome_topology": bool(bee.metadata.get("real_connectome_topology")), "metadata": bee.metadata},
                "jev": {"requested": jev_enabled, "called": decisions.provider == "venice", "provider": decisions.provider, "model": decisions.model},
                "llm": {"requested": llm_enabled, "called": llm is not None, "provider": llm.provider if llm else None, "model": llm.model if llm else None},
            },
        )
        if worker.outputs.save_run:
            self.db.insert_run(result.model_dump(mode="json"))
        if not worker.runtime.persist_brain_state:
            larva_engine.reset()
            bee_engine.reset()
        return result
