from __future__ import annotations

import hashlib
import json
import math
from typing import Any
from uuid import uuid4

from hive_connectome.brains.base import MiniBrain
from hive_connectome.brains.connectome import CookConnectomeBrain, MaleCNSLocomotorBrain
from hive_connectome.brains.malecns_full import MaleCNSFullBrain
from hive_connectome.brains.synthetic import DeterministicMiniBrain
from hive_connectome.db import HiveDB
from hive_connectome.experiment_contract import experiment_readiness, load_experiment_contract
from hive_connectome.providers.lmstudio import LMStudio
from hive_connectome.providers.venice import ProviderRequestError, VeniceChat, VeniceJev
from hive_connectome.schemas import (
    BrainKind,
    BrainStageSpec,
    BridgeSpec,
    DecisionBundle,
    DecisionType,
    JevQuestion,
    NeuralObservation,
    PipelineRequest,
    PipelineResult,
)
from hive_connectome.workers import WorkerSpec, WorkerStore


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8")


def brain_readout(observations: dict[str, NeuralObservation]) -> DecisionBundle:
    if not observations:
        return DecisionBundle(
            provider="brain-readout",
            model="fixed-readout-v2-no-brain",
            confidence=0.25,
            answers={
                "meaningful_signal": {"type": "noul", "noul": 0.5},
                "novelty": {"type": "score", "score": 0.0, "confidence": 0.25},
                "route": {"type": "choice", "choice": "store", "confidence": 0.25},
                "llm_needed": {"type": "noul", "noul": 0.5},
            },
        )
    last = list(observations.values())[-1]
    novelty = min(2.0, float(last.metrics.get("novelty", 0.0)) * 20.0)
    meaningful = min(0.98, 0.35 + float(last.metrics.get("energy", 0.0)) * 2.5)
    route = "inspect" if novelty > 0.5 else "store"
    return DecisionBundle(
        provider="brain-readout",
        model="fixed-readout-v2",
        confidence=0.45,
        answers={
            "meaningful_signal": {"type": "noul", "noul": meaningful},
            "novelty": {"type": "score", "score": novelty, "confidence": 0.45},
            "route": {"type": "choice", "choice": route, "confidence": 0.45},
            "llm_needed": {"type": "noul", "noul": 0.5},
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
        experiment_contract_path=None,
    ):
        self.db = db
        self.workers = workers
        self.venice = venice
        self.venice_chat = venice_chat
        self.lmstudio = lmstudio
        self.default_llm_model = default_llm_model
        from pathlib import Path
        self.data_dir = Path(data_dir or db.path.parent).resolve()
        self.experiment_contract_path = Path(experiment_contract_path).resolve() if experiment_contract_path else None
        self._brains: dict[str, dict[str, tuple[MiniBrain, tuple[Any, ...]]]] = {}

    def _engine(self, worker: WorkerSpec, stage: BrainStageSpec) -> MiniBrain:
        brain_id = f"{worker.id}:{stage.id}"
        if stage.engine == "synthetic":
            size = int(stage.state_size or 16)
            return DeterministicMiniBrain(brain_id, stage.kind, size)

        pack_id = stage.config.get("pack_id") or stage.connectome_pack
        if not pack_id:
            raise ValueError(f"{stage.id} connectome engine requires config.pack_id or connectome_pack")

        if stage.engine == "malecns_full_v1":
            raw_root = self.data_dir / "connectomes" / str(pack_id)
            compiled_root = self.data_dir / "compiled" / str(pack_id)
            return MaleCNSFullBrain(
                brain_id,
                raw_root,
                compiled_root,
                expected_neurons=int(stage.config.get("expected_neurons", 166700)),
                expected_directed_edges=int(stage.config.get("expected_directed_connections", 25582938)),
                expected_synaptic_contacts=int(stage.config.get("expected_synapses", 124177617)),
                dt=float(stage.config.get("dt", 0.020)),
                tau=float(stage.config.get("tau", 0.100)),
                gain=float(stage.config.get("gain", 3.0)),
                tonic=float(stage.config.get("tonic", 0.14)),
                threshold=float(stage.config.get("threshold", 1.0)),
                substeps=int(stage.config.get("substeps", 5)),
                sample_size=int(stage.config.get("sample_size", 2048)),
            )

        filename = stage.config.get("file")
        if not filename:
            raise ValueError(f"{stage.id} connectome engine requires config.file")
        path = self.data_dir / "connectomes" / str(pack_id) / str(filename)

        if stage.engine == "cook2019_connectome":
            return CookConnectomeBrain(brain_id, path, substeps=int(stage.config.get("substeps", 8)))
        if stage.engine == "malecns_locomotor":
            return MaleCNSLocomotorBrain(brain_id, path, ms_per_event=int(stage.config.get("ms_per_event", 10)))
        raise NotImplementedError(f"unknown neural engine: {stage.engine}")

    @staticmethod
    def _stage_signature(stage: BrainStageSpec) -> tuple[Any, ...]:
        return (
            stage.kind.value,
            stage.engine,
            stage.enabled,
            stage.state_size,
            stage.connectome_pack,
            tuple(stage.input_from),
            json.dumps(stage.config, sort_keys=True, default=str),
        )

    def _engines(self, worker: WorkerSpec) -> dict[str, MiniBrain]:
        bucket = self._brains.setdefault(worker.id, {})
        active_ids = {stage.id for stage in worker.brain_chain if stage.enabled}
        for stale in list(bucket):
            if stale not in active_ids:
                del bucket[stale]

        result: dict[str, MiniBrain] = {}
        for stage in worker.brain_chain:
            if not stage.enabled:
                continue
            signature = self._stage_signature(stage)
            existing = bucket.get(stage.id)
            if existing is None or existing[1] != signature:
                bucket[stage.id] = (self._engine(worker, stage), signature)
            result[stage.id] = bucket[stage.id][0]
        return result

    @staticmethod
    def _target_candidates(engine: MiniBrain) -> list[int]:
        candidates = getattr(engine, "input_candidates", None)
        if candidates is not None:
            return [int(value) for value in candidates]
        size = getattr(engine, "n", None) or getattr(engine, "size", None)
        return list(range(int(size or 0)))

    @staticmethod
    def _bridge_for(worker: WorkerSpec, source: str, target: str) -> BridgeSpec:
        for bridge in worker.bridges:
            if bridge.enabled and bridge.source == source and bridge.target == target:
                return bridge
        return BridgeSpec(
            id=f"{source}-to-{target}",
            source=source,
            target=target,
            engine="state_projection_v1",
            config={"source_excerpt": 32, "target_count": 24, "gain": 1.0},
        )

    def _bridge_payload(
        self,
        bridge: BridgeSpec,
        source: NeuralObservation,
        target_engine: MiniBrain,
        *,
        event: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        excerpt_n = max(1, int(bridge.config.get("source_excerpt", 32)))
        target_count = max(1, int(bridge.config.get("target_count", 24)))
        gain = float(bridge.config.get("gain", 1.0))
        candidates = self._target_candidates(target_engine)
        source_values = source.state_vector[:excerpt_n]
        trace: dict[str, Any] = {
            "id": bridge.id,
            "source": bridge.source,
            "target": bridge.target,
            "engine": bridge.engine,
            "source_step": source.step,
            "source_engine": source.engine,
            "source_excerpt": source_values[:16],
            "source_metrics": source.metrics,
        }

        if bridge.engine == "identity_payload_v1":
            payload = {
                "event": event,
                "upstream": {
                    "stage": bridge.source,
                    "metrics": source.metrics,
                    "state_excerpt": source_values,
                },
            }
            trace["stimulus_count"] = 0
            trace["payload_hash"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
            return payload, trace

        if not candidates or not source_values:
            trace["stimulus_count"] = 0
            return {"event": event, "__hive_stimulus__": []}, trace

        drives: dict[int, float] = {}
        if bridge.engine == "state_projection_v1":
            for i, value in enumerate(source_values[:target_count]):
                digest = hashlib.sha256(f"{bridge.id}:{i}".encode("utf-8")).digest()
                idx = candidates[int.from_bytes(digest[:4], "big") % len(candidates)]
                amplitude = max(-4.0, min(4.0, float(value) * gain))
                drives[idx] = max(-4.0, min(4.0, drives.get(idx, 0.0) + amplitude))
        elif bridge.engine == "hash_projection_v1":
            seed = {
                "bridge": bridge.id,
                "event": event,
                "metrics": source.metrics,
                "state_excerpt": source_values,
            }
            digest = hashlib.sha256(_canonical_bytes(seed)).digest()
            used: set[int] = set()
            for i in range(min(target_count, len(candidates))):
                block = hashlib.sha256(digest + i.to_bytes(2, "big")).digest()
                idx = candidates[int.from_bytes(block[:4], "big") % len(candidates)]
                if idx in used:
                    continue
                used.add(idx)
                drives[idx] = (0.55 + (block[4] / 255.0) * 0.45) * gain
        else:
            raise NotImplementedError(f"unknown bridge engine: {bridge.engine}")

        stimulus = [[idx, amp] for idx, amp in sorted(drives.items()) if abs(amp) > 1e-9]
        trace["stimulus_count"] = len(stimulus)
        trace["stimulus_excerpt"] = stimulus[:16]
        trace["stimulus_hash"] = hashlib.sha256(_canonical_bytes(stimulus)).hexdigest()
        return {
            "event": event,
            "upstream_stage": bridge.source,
            "__hive_stimulus__": stimulus,
        }, trace

    def runtime_status(self) -> dict[str, Any]:
        workers = self.workers.list()
        worker = next((w for w in workers if w.id == "scout"), workers[0] if workers else None)

        def stage_status(stage: BrainStageSpec):
            if stage.engine == "synthetic":
                return {"id": stage.id, "engine": stage.engine, "real_connectome_topology": False, "installed": True}
            pack_id = stage.config.get("pack_id") or stage.connectome_pack
            if stage.engine == "malecns_full_v1":
                root = self.data_dir / "connectomes" / str(pack_id)
                required = ["annotations.feather", "neurotransmitters.feather", "edges.feather"]
                present = {name: (root / name).exists() for name in required}
                return {
                    "id": stage.id,
                    "engine": stage.engine,
                    "real_connectome_topology": True,
                    "full_connectome": True,
                    "installed": all(present.values()),
                    "pack_id": pack_id,
                    "files": present,
                }
            filename = stage.config.get("file")
            path = self.data_dir / "connectomes" / str(pack_id) / str(filename)
            return {
                "id": stage.id,
                "engine": stage.engine,
                "real_connectome_topology": True,
                "installed": path.exists(),
                "pack_id": pack_id,
                "file": filename,
            }

        control = {"ready": False, "stages": []}
        if worker is not None:
            statuses = [stage_status(stage) for stage in worker.brain_chain if stage.enabled]
            control_ready = bool(statuses) and all(item["installed"] for item in statuses)
            control = {
                "ready": control_ready,
                "backend": " → ".join(item["engine"] for item in statuses) or "no-neural-stage",
                "stages": statuses,
                "larva": next((x for x in statuses if x["id"] == "worm"), statuses[0] if statuses else None),
                "bee": next((x for x in statuses if x["id"] == "fly"), statuses[-1] if statuses else None),
                "classification": "control_only",
                "note": "The runnable reduced MaleCNS path remains a control. v0.7 core graphs may remove or reorder neural stages explicitly.",
            }

        if self.experiment_contract_path and self.experiment_contract_path.exists():
            contract = load_experiment_contract(self.experiment_contract_path)
            primary = experiment_readiness(
                contract,
                data_dir=self.data_dir,
                supported_engines={"synthetic", "cook2019_connectome", "malecns_locomotor", "malecns_full_v1"},
            )
        else:
            primary = {
                "status": "blocked",
                "primary_experiment_ready": False,
                "blockers": ["experiment contract is unavailable"],
            }

        return {
            "ready": bool(primary.get("primary_experiment_ready")),
            "backend": control.get("backend", "none"),
            "primary_experiment_ready": bool(primary.get("primary_experiment_ready")),
            "real_connectome_runtime_ready": False,
            "study_mode": "PRIMARY" if primary.get("primary_experiment_ready") else "CONTROL_ONLY",
            "primary": primary,
            "control_runtime": control,
            "core_graph_runtime": True,
            "note": "Full MaleCNS execution is the primary study requirement. Core composition is independently configurable.",
        }

    def reset(self, worker_id: str | None = None):
        if worker_id is None:
            for bucket in self._brains.values():
                for engine, _ in bucket.values():
                    engine.reset()
            return
        self.workers.get(worker_id)
        for engine, _ in self._brains.get(worker_id, {}).values():
            engine.reset()

    @staticmethod
    def _noul(bundle: DecisionBundle, key: str) -> float:
        try:
            return float(bundle.answers[key]["noul"])
        except Exception:
            return 0.5

    def _store_transport(self, run_id: str, stage_id: str, transport: dict[str, Any] | None) -> None:
        if transport and transport.get("call_id"):
            self.db.insert_provider_call(transport, run_id=run_id, stage_id=stage_id)

    def _store_provider_error(self, run_id: str, stage_id: str, exc: Exception) -> None:
        receipt = getattr(exc, "receipt", None)
        if receipt:
            self._store_transport(run_id, stage_id, receipt)

    def _record_stage_execution(self, run_id: str, worker: WorkerSpec, stage: BrainStageSpec, observation: NeuralObservation) -> None:
        if not observation.metadata.get("real_connectome_topology"):
            return
        pack_id = stage.config.get("pack_id") or stage.connectome_pack
        receipt_dir = self.data_dir / "execution_receipts"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        receipt = {
            "receipt_version": 1,
            "run_id": run_id,
            "core_id": worker.id,
            "stage_id": stage.id,
            "requested_engine": stage.engine,
            "observed_engine": observation.engine,
            "pack_id": pack_id,
            "step": observation.step,
            "node_count": observation.metadata.get("node_count"),
            "edge_count": observation.metadata.get("edge_count"),
            "synaptic_contacts": observation.metadata.get("synaptic_contacts"),
            "full_connectome": bool(observation.metadata.get("full_connectome")),
            "state_hash": observation.metadata.get("state_hash"),
            "metadata": observation.metadata,
        }
        target = receipt_dir / f"{stage.engine}--{pack_id}.json"
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
        tmp.replace(target)

    def _record_full_state(self, run_id: str, stage: BrainStageSpec, engine: MiniBrain, observation: NeuralObservation) -> None:
        exporter = getattr(engine, "export_state", None)
        if not callable(exporter):
            return
        import numpy as np
        root = self.data_dir / "recordings" / run_id
        root.mkdir(parents=True, exist_ok=True)
        target = root / f"{stage.id}.npz"
        arrays = exporter()
        np.savez_compressed(target, **arrays)
        observation.metadata["recording_artifact"] = str(target.relative_to(self.data_dir))
        observation.metadata["recording_bytes"] = target.stat().st_size

    async def run(self, req: PipelineRequest) -> PipelineResult:
        run_id = str(uuid4())
        worker = self.workers.get(req.worker_id)
        jev_enabled = worker.jev.enabled if req.jev_enabled is None else req.jev_enabled
        llm_enabled = worker.llm.enabled if req.llm_enabled is None else req.llm_enabled

        if worker.outputs.save_event:
            self.db.insert_event(req.event.model_dump(mode="json"))

        engines = self._engines(worker)
        observations: dict[str, NeuralObservation] = {}
        bridge_trace: list[dict[str, Any]] = []

        for stage in worker.brain_chain:
            if not stage.enabled:
                continue
            engine = engines[stage.id]
            active_sources = [source for source in stage.input_from if source in observations]
            if not active_sources:
                payload: Any = {
                    "event": req.event.payload,
                    "experiment": worker.experiment.kind,
                    "objective": worker.experiment.objective,
                }
            else:
                merged_drives: dict[int, float] = {}
                identity_payloads: list[dict[str, Any]] = []
                explicit_bridge_seen = False
                for source_id in active_sources:
                    bridge = self._bridge_for(worker, source_id, stage.id)
                    bridged, trace = self._bridge_payload(
                        bridge,
                        observations[source_id],
                        engine,
                        event=req.event.payload,
                    )
                    bridge_trace.append(trace)
                    if "__hive_stimulus__" in bridged:
                        explicit_bridge_seen = True
                    for pair in bridged.get("__hive_stimulus__", []):
                        idx, amplitude = int(pair[0]), float(pair[1])
                        merged_drives[idx] = max(-4.0, min(4.0, merged_drives.get(idx, 0.0) + amplitude))
                    if "upstream" in bridged:
                        identity_payloads.append(bridged["upstream"])
                payload = {
                    "event": req.event.payload,
                    "experiment": worker.experiment.kind,
                    "objective": worker.experiment.objective,
                    "upstream": identity_payloads,
                }
                if explicit_bridge_seen:
                    payload["__hive_stimulus__"] = [[idx, amp] for idx, amp in sorted(merged_drives.items())]
            observation = engine.step(payload)
            if worker.outputs.recording_level == "full":
                self._record_full_state(run_id, stage, engine, observation)
            self._record_stage_execution(run_id, worker, stage, observation)
            observations[stage.id] = observation

        worm = next((obs for obs in observations.values() if obs.brain_kind == BrainKind.WORM_LINK), None)
        fly = next((obs for obs in observations.values() if obs.brain_kind == BrainKind.FLY_CORE), None)

        stage_state = {
            stage_id: {
                "kind": obs.brain_kind.value,
                "engine": obs.engine,
                "metrics": obs.metrics,
                "state_excerpt": obs.state_vector[:16],
                "metadata": obs.metadata,
            }
            for stage_id, obs in observations.items()
        }
        decision_state: dict[str, Any] = {
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
            "stages": stage_state,
            "bridges": bridge_trace,
        }
        if worm is not None:
            decision_state["larva"] = {"metrics": worm.metrics, "state_excerpt": worm.state_vector[:8]}
        if fly is not None:
            decision_state["bee"] = {"metrics": fly.metrics, "state_excerpt": fly.state_vector[:12]}

        decisions = brain_readout(observations)
        live_jev = jev_enabled and req.mode != "offline" and self.venice is not None
        unresolved: list[str] = []

        if jev_enabled:
            if live_jev:
                try:
                    decisions = await self.venice.decide(decision_state, worker.jev.questions, model=worker.jev.model)
                    self._store_transport(run_id, "jev", decisions.transport)
                except Exception as exc:
                    self._store_provider_error(run_id, "jev", exc)
                    raise
            elif req.mode != "offline":
                raise RuntimeError("JEV was requested, but Venice/JEV is not configured. HIVE will not silently substitute the fixed readout.")

        novelty = float(decisions.answers.get("novelty", {}).get("score", 1.0))
        meaningful = self._noul(decisions, "meaningful_signal")
        route = decisions.answers.get("route", {}).get("choice", "store")
        llm_needed = self._noul(decisions, "llm_needed")
        modulation = max(-1.0, min(1.0, (meaningful - 0.5) * 0.8 + (novelty - 1.0) * 0.2))

        if worker.jev.feedback_to_brain and jev_enabled:
            targets = set(worker.jev.feedback_targets)
            for stage_id, engine in engines.items():
                if not targets or stage_id in targets:
                    engine.feedback(modulation)

        should_llm = False
        if llm_enabled:
            activation = worker.llm.activation
            if activation == "always":
                should_llm = True
            elif activation == "manual":
                should_llm = req.force_llm
            else:
                should_llm = True if not jev_enabled else (
                    req.force_llm or llm_needed >= worker.jev.llm_gate_threshold or route == "escalate"
                )
        elif req.force_llm:
            should_llm = True

        llm = None
        if should_llm:
            if worker.llm.provider == "lmstudio":
                model = worker.llm.model or self.default_llm_model
                if self.lmstudio is not None and model:
                    try:
                        llm = await self.lmstudio.chat(
                            model,
                            worker.llm.prompt or worker.experiment.task_prompt,
                            json.dumps(decision_state, default=str),
                            temperature=worker.llm.temperature,
                        )
                        self._store_transport(run_id, "llm", llm.transport)
                    except Exception as exc:
                        self._store_provider_error(run_id, "llm", exc)
                        raise
                else:
                    unresolved.append("LLM required but LM Studio/model is not configured.")
            else:
                if self.venice_chat is not None and worker.llm.model:
                    try:
                        llm = await self.venice_chat.chat(
                            worker.llm.model,
                            worker.llm.prompt or worker.experiment.task_prompt,
                            json.dumps(decision_state, default=str),
                            temperature=worker.llm.temperature,
                        )
                        self._store_transport(run_id, "llm", llm.transport)
                    except Exception as exc:
                        self._store_provider_error(run_id, "llm", exc)
                        raise
                elif self.venice_chat is None:
                    unresolved.append("Venice LLM required but no Venice API key is configured.")
                else:
                    unresolved.append("Venice LLM required but this core has no Venice chat model configured.")

        verification = None
        if llm is not None and live_jev and worker.llm.verify_with_jev:
            try:
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
                self._store_transport(run_id, "jev-verification", verification.transport)
            except Exception as exc:
                self._store_provider_error(run_id, "jev-verification", exc)
                raise

        labels = [
            f"worker:{worker.id}",
            f"core:{worker.id}",
            f"experiment:{worker.experiment.kind}",
            f"route:{route}",
            f"jev:{'on' if jev_enabled else 'off'}",
            f"llm:{'on' if llm_enabled else 'off'}",
        ]
        if meaningful >= 0.7:
            labels.append("meaningful")
        if novelty >= 1.4:
            labels.append("novel")

        stage_execution = {
            stage.id: {
                "requested_engine": stage.engine,
                "kind": stage.kind.value,
                "input_from": list(stage.input_from),
                "engine": observations[stage.id].engine,
                "real_connectome_topology": bool(observations[stage.id].metadata.get("real_connectome_topology")),
                "metadata": observations[stage.id].metadata,
                "metrics": observations[stage.id].metrics,
            }
            for stage in worker.brain_chain if stage.enabled and stage.id in observations
        }
        provider_calls = [
            receipt.get("call_id")
            for receipt in [
                decisions.transport,
                llm.transport if llm else {},
                verification.transport if verification else {},
            ]
            if receipt.get("call_id")
        ]
        uses_control_fly = any(stage.engine == "malecns_locomotor" for stage in worker.brain_chain if stage.enabled)
        uses_full_fly = any(stage.engine == "malecns_full_v1" for stage in worker.brain_chain if stage.enabled)
        uses_full_worm = any(stage.engine == "cook2019_connectome" for stage in worker.brain_chain if stage.enabled)

        execution: dict[str, Any] = {
            "study_role": "primary_candidate" if uses_full_fly and uses_full_worm else ("control_only" if uses_control_fly else "experimental"),
            "primary_experiment": bool(uses_full_fly and uses_full_worm),
            "core_id": worker.id,
            "stages": stage_execution,
            "bridges": bridge_trace,
            "provider_call_ids": provider_calls,
            "resolved_worker": worker.model_dump(mode="json"),
            "recording_level": worker.outputs.recording_level,
            "jev": {
                "requested": jev_enabled,
                "called": decisions.provider == "venice",
                "provider": decisions.provider,
                "model": decisions.model,
                "call_id": decisions.transport.get("call_id"),
            },
            "llm": {
                "requested": llm_enabled,
                "called": llm is not None,
                "provider": llm.provider if llm else None,
                "model": llm.model if llm else None,
                "call_id": llm.transport.get("call_id") if llm else None,
            },
        }
        if worm is not None:
            execution["larva"] = {
                "engine": worm.engine,
                "real_connectome_topology": bool(worm.metadata.get("real_connectome_topology")),
                "metadata": worm.metadata,
            }
        if fly is not None:
            execution["bee"] = {
                "engine": fly.engine,
                "real_connectome_topology": bool(fly.metadata.get("real_connectome_topology")),
                "metadata": fly.metadata,
            }

        result = PipelineResult(
            run_id=run_id,
            event=req.event,
            stages=observations,
            worm=worm,
            fly=fly,
            decisions=decisions,
            llm=llm,
            verification=verification,
            modulation=modulation,
            labels=labels if worker.outputs.write_labels else [],
            unresolved=unresolved,
            execution=execution,
        )
        if worker.outputs.save_run:
            self.db.insert_run(result.model_dump(mode="json"))
        if not worker.runtime.persist_brain_state:
            for engine in engines.values():
                engine.reset()
        return result
