from __future__ import annotations

import hashlib
import json
import random
import time
from uuid import uuid4
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from hive_connectome.connectomes.installer import ConnectomeInstaller
from hive_connectome.db import HiveDB
from hive_connectome.evals import EvalRequest, canonical_task_set_hash, score_task_result, summarize_eval
from hive_connectome.exports import build_experiment_export
from hive_connectome.experiment_view import build_experiment_plan
from hive_connectome.environment import EnvironmentModeError, EnvironmentNotImplemented, WorkerEnvironmentRunner
from hive_connectome.pipeline import HivePipeline
from hive_connectome.provider_config import ProviderConfigUpdate, ProviderRegistry, ProviderTestRequest
from hive_connectome.scheduler import HeartbeatDaemon, validate_cron
from hive_connectome.schemas import CronTaskSpec, DataSourceSpec, DecisionType, EventEnvelope, HiveRunRequest, JevQuestion, PipelineRequest, SimulationSpec
from hive_connectome.settings import Settings
from hive_connectome.sources import poll_source
from hive_connectome.workers import WorkerSpec, WorkerStore


def create_app(settings_override: Settings | None = None, *, start_heartbeat: bool = True) -> FastAPI:
    settings = settings_override or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "inbox").mkdir(parents=True, exist_ok=True)

    db = HiveDB(settings.data_dir / "hive.sqlite3")
    worker_store = WorkerStore(settings.data_dir / "workers.json", settings.config_dir / "workers.default.json")
    provider_registry = ProviderRegistry(settings.data_dir, settings)
    venice, venice_chat, lmstudio = provider_registry.clients()
    pipeline = HivePipeline(
        db,
        worker_store,
        venice=venice,
        venice_chat=venice_chat,
        lmstudio=lmstudio,
        default_llm_model=provider_registry.config.get("default_llm_model"),
        data_dir=settings.data_dir,
        experiment_contract_path=settings.config_dir / "experiment_contract.json",
    )
    installer = ConnectomeInstaller(settings.config_dir / "connectomes.json", settings.data_dir)
    environment_runner = WorkerEnvironmentRunner(db, worker_store, pipeline, settings.data_dir / "inbox")
    heartbeat = HeartbeatDaemon(db, pipeline, settings.data_dir / "inbox", worker_store=worker_store, environment_runner=environment_runner)
    install_jobs: dict[str, dict] = {}

    def templates_data() -> dict:
        return json.loads((settings.config_dir / "experiment_templates.json").read_text(encoding="utf-8"))

    def seed_sources() -> None:
        example = settings.config_dir / "sources.example.json"
        if not db.list_sources() and example.exists():
            for item in json.loads(example.read_text(encoding="utf-8"))["sources"]:
                item = dict(item)
                if item.get("kind") == "file_drop" and item.get("path") == "/data/inbox":
                    item["path"] = str(settings.data_dir / "inbox")
                db.upsert_source(DataSourceSpec.model_validate(item).model_dump())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        seed_sources()
        if start_heartbeat:
            heartbeat.start()
        yield
        if start_heartbeat:
            await heartbeat.stop()
        db.close()

    app = FastAPI(title="HIVE Connectome", version="0.7.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.db = db
    app.state.worker_store = worker_store
    app.state.pipeline = pipeline
    app.state.installer = installer
    app.state.heartbeat = heartbeat
    app.state.environment_runner = environment_runner
    app.state.provider_registry = provider_registry

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def root():
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    async def health():
        return {
            "ok": True,
            "version": "0.7.0",
            "neural_runtime": pipeline.runtime_status(),
            "venice_configured": pipeline.venice is not None,
            "lmstudio_model": pipeline.default_llm_model,
            "workers": [w.id for w in worker_store.list()],
        }

    @app.get("/api/experiment-templates")
    async def experiment_templates():
        return templates_data()

    @app.get("/api/workers")
    async def list_workers():
        return worker_store.list()

    @app.get("/api/workers/{worker_id}")
    async def get_worker(worker_id: str):
        try:
            return worker_store.get(worker_id)
        except KeyError:
            raise HTTPException(404, "worker not found")

    @app.get("/api/experiments/{worker_id}/plan")
    async def experiment_plan(worker_id: str):
        try:
            worker = worker_store.get(worker_id)
        except KeyError:
            raise HTTPException(404, "core not found")
        return build_experiment_plan(
            worker,
            connectomes=installer.list_status(),
            runtime_status=pipeline.runtime_status(),
            provider_config=provider_registry.public(),
        )

    @app.put("/api/workers/{worker_id}")
    async def save_worker(worker_id: str, spec: WorkerSpec):
        if spec.id != worker_id:
            raise HTTPException(400, "worker id in path and body must match")
        saved = worker_store.save(spec)
        pipeline.reset(worker_id)
        return saved

    @app.post("/api/workers/from-template/{template_id}")
    async def create_worker_from_template(template_id: str, worker_id: str, name: str | None = None):
        template = next((t for t in templates_data()["templates"] if t["id"] == template_id), None)
        if not template:
            raise HTTPException(404, "template not found")
        if any(w.id == worker_id for w in worker_store.list()):
            raise HTTPException(409, "worker id already exists")
        raw = json.loads(json.dumps(template["worker"]))
        raw["id"] = worker_id
        raw["name"] = name or template["name"]
        raw["description"] = "CONTROL / DEVELOPMENT: " + raw.get("description", "")
        raw["experiment"]["notes"] = ("CONTROL ONLY: uses the 1,045-neuron MaleCNS locomotor subgraph; " + raw["experiment"].get("notes", "")).strip()
        raw["larva"] = {
            "engine": "cook2019_connectome",
            "state_size": 300,
            "substrate": "c_elegans_cook_2019_corrected_2020",
            "config": {"pack_id": "worm-cook-2020", "file": "cook_2020_adjacency.xlsx", "substeps": 8},
        }
        raw["bee"] = {
            "engine": "malecns_locomotor",
            "state_size": 1045,
            "substrate": "drosophila_malecns_v1_locomotor",
            "config": {"pack_id": "fly-malecns-locomotor", "file": "locomotor_circuit.json", "ms_per_event": 10},
        }
        raw["jev"]["questions"] = {
            "meaningful_signal": {"type": "noul", "instructions": "Is this event materially meaningful to this experiment?"},
            "novelty": {"type": "score", "instructions": "How novel is this event relative to recurrent state?", "criteria": ["routine", "notable", "highly novel"]},
            "route": {"type": "choice", "instructions": "What should this worker do next?", "criteria": {"store": "store evidence", "inspect": "inspect deeper", "escalate": "requires open-ended reasoning", "ignore": "no useful change"}},
            "llm_needed": {"type": "noul", "instructions": "Does this event require open-ended language reasoning?"},
        }
        return worker_store.save(WorkerSpec.model_validate(raw))

    @app.post("/api/workers/{worker_id}/clone")
    async def clone_worker(worker_id: str, new_id: str, name: str | None = None):
        try:
            source = worker_store.get(worker_id)
        except KeyError:
            raise HTTPException(404, "worker not found")
        if any(w.id == new_id for w in worker_store.list()):
            raise HTTPException(409, "new worker id already exists")
        raw = source.model_dump(mode="json")
        raw["id"] = new_id
        raw["name"] = name or f"{source.name} copy"
        return worker_store.save(WorkerSpec.model_validate(raw))

    @app.delete("/api/workers/{worker_id}")
    async def delete_worker(worker_id: str):
        try:
            worker_store.get(worker_id)
        except KeyError:
            raise HTTPException(404, "worker not found")
        worker_store.delete(worker_id)
        return {"ok": True}

    @app.get("/api/providers/config")
    async def provider_config():
        return provider_registry.public()

    @app.put("/api/providers/config")
    async def save_provider_config(update: ProviderConfigUpdate):
        try:
            public = provider_registry.update(update)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        provider_registry.apply(pipeline)
        return public

    @app.post("/api/providers/test")
    async def provider_test(req: ProviderTestRequest):
        try:
            if req.capability == "venice_jev":
                if pipeline.venice is None:
                    raise HTTPException(400, "Venice API key is not configured")
                result = await pipeline.venice.decide(
                    {"hive_provider_test": True, "purpose": "prove a live Venice Decisions transaction"},
                    {"reachable": JevQuestion(type=DecisionType.NOUL, instructions="Is this provider-test state present?")},
                    model=req.model or provider_registry.config.get("venice_decision_model"),
                )
                db.insert_provider_call(result.transport, stage_id="provider-test:venice-jev")
                return {"ok": True, "capability": req.capability, "model": result.model, "transport": result.transport, "answers": result.answers}
            if req.capability == "venice_chat":
                if pipeline.venice_chat is None:
                    raise HTTPException(400, "Venice API key is not configured")
                model = req.model
                if not model:
                    raise HTTPException(400, "Venice chat test requires a model")
                result = await pipeline.venice_chat.chat(
                    model,
                    "Return exactly the short token HIVE_PROVIDER_OK.",
                    {"hive_provider_test": True},
                    temperature=0.0,
                )
                db.insert_provider_call(result.transport, stage_id="provider-test:venice-chat")
                return {"ok": True, "capability": req.capability, "model": result.model, "transport": result.transport, "text": result.text}
            model = req.model or pipeline.default_llm_model
            if not model:
                raise HTTPException(400, "LM Studio chat test requires a model")
            result = await pipeline.lmstudio.chat(
                model,
                "Return exactly the short token HIVE_PROVIDER_OK.",
                {"hive_provider_test": True},
                temperature=0.0,
            )
            db.insert_provider_call(result.transport, stage_id="provider-test:lmstudio-chat")
            return {"ok": True, "capability": req.capability, "model": result.model, "transport": result.transport, "text": result.text}
        except HTTPException:
            raise
        except Exception as exc:
            receipt = getattr(exc, "receipt", None)
            if receipt:
                db.insert_provider_call(receipt, stage_id=f"provider-test:{req.capability}")
            raise HTTPException(502, str(exc))

    @app.get("/api/providers/status")
    async def provider_status():
        public = provider_registry.public()
        venice_client = pipeline.venice
        lmstudio_client = pipeline.lmstudio
        result = {
            "venice": {
                "configured": venice_client is not None,
                "ok": False,
                "base_url": public["venice_base_url"],
                "model": public["venice_decision_model"],
                "models": [],
            },
            "lmstudio": {
                "configured": True,
                "ok": False,
                "base_url": public["lmstudio_base_url"],
                "models": [],
            },
        }
        if venice_client:
            try:
                result["venice"]["models"] = await venice_client.list_models()
                result["venice"]["ok"] = True
            except Exception as exc:
                result["venice"]["error"] = str(exc)
        try:
            models = await lmstudio_client.list_models()
            result["lmstudio"]["ok"] = True
            result["lmstudio"]["models"] = models.get("data", models)
        except Exception as exc:
            result["lmstudio"]["error"] = str(exc)
        return result

    @app.get("/api/connectomes")
    async def connectomes():
        return installer.list_status()

    async def _install(pack_id: str):
        install_jobs[pack_id] = {"status": "running"}
        try:
            receipt = await installer.install(pack_id)
            install_jobs[pack_id] = {"status": "complete", "receipt": receipt}
        except Exception as exc:
            install_jobs[pack_id] = {"status": "error", "error": str(exc)}

    @app.post("/api/connectomes/{pack_id}/install")
    async def install_connectome(pack_id: str, background_tasks: BackgroundTasks, confirm: bool = Query(False)):
        try:
            pack = installer.get_pack(pack_id)
        except KeyError:
            raise HTTPException(404, "unknown connectome pack")
        if not pack.get("installable"):
            raise HTTPException(400, pack.get("reason", "not installable"))
        total = sum(int(f.get("bytes") or 0) for f in pack.get("files", []))
        if total > 100 * 1024 * 1024 and not confirm:
            raise HTTPException(409, f"large download ({total} bytes); resend with confirm=true")
        if install_jobs.get(pack_id, {}).get("status") == "running":
            return install_jobs[pack_id]
        background_tasks.add_task(_install, pack_id)
        return {"status": "queued", "pack_id": pack_id}

    @app.get("/api/connectomes/{pack_id}/job")
    async def connectome_job(pack_id: str):
        return install_jobs.get(pack_id, {"status": "idle"})

    @app.post("/api/pipeline/run")
    async def run_pipeline(req: PipelineRequest):
        try:
            return await pipeline.run(req)
        except KeyError as exc:
            raise HTTPException(404, f"worker not found: {exc}")
        except Exception as exc:
            raise HTTPException(502, str(exc))

    @app.post("/api/hive/run")
    async def run_hive(req: HiveRunRequest):
        results = []
        current_event = req.event
        for index, core_id in enumerate(req.core_ids):
            try:
                result = await pipeline.run(PipelineRequest(
                    worker_id=core_id,
                    event=current_event,
                    mode=req.mode,
                    jev_enabled=req.jev_enabled,
                    llm_enabled=req.llm_enabled,
                ))
            except KeyError:
                raise HTTPException(404, f"core not found: {core_id}")
            results.append(result)
            if index < len(req.core_ids) - 1:
                stage_metrics = {
                    stage_id: obs.metrics
                    for stage_id, obs in result.stages.items()
                }
                current_event = EventEnvelope(
                    source_id=f"hive:{core_id}",
                    kind="core_handoff",
                    payload={
                        "origin_event_id": req.event.id,
                        "previous_core": core_id,
                        "previous_run_id": result.run_id,
                        "decisions": result.decisions.answers,
                        "modulation": result.modulation,
                        "labels": result.labels,
                        "stage_metrics": stage_metrics,
                        "llm_text": result.llm.text if result.llm else None,
                    },
                    provenance={
                        "parent_run_id": result.run_id,
                        "parent_core_id": core_id,
                        "hive_chain": list(req.core_ids),
                    },
                )
        return {
            "core_ids": req.core_ids,
            "count": len(results),
            "results": [result.model_dump(mode="json") for result in results],
        }

    @app.get("/api/runs")
    async def runs(limit: int = Query(100, ge=1, le=5000), worker_id: str | None = None):
        return db.list_runs(limit=limit, worker_id=worker_id)

    @app.get("/api/runs/{run_id}")
    async def run_detail(run_id: str):
        run = db.get_run(run_id)
        if run is None:
            raise HTTPException(404, "run not found")
        return run

    @app.get("/api/provider-calls")
    async def provider_calls(limit: int = Query(200, ge=1, le=10000), run_id: str | None = None):
        return db.list_provider_calls(limit=limit, run_id=run_id)

    @app.get("/api/exports/experiment")
    async def export_experiment(worker_id: str | None = None, limit: int = Query(5000, ge=1, le=50000)):
        payload = build_experiment_export(
            db,
            worker_store,
            settings.data_dir,
            worker_id=worker_id,
            limit=limit,
        )
        suffix = worker_id or "all"
        return StreamingResponse(
            iter([payload]),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="hive-experiment-{suffix}.zip"'},
        )

    @app.post("/api/pipeline/reset")
    async def reset_pipeline(worker_id: str | None = None):
        try:
            pipeline.reset(worker_id)
        except KeyError:
            raise HTTPException(404, "worker not found")
        return {"ok": True, "worker_id": worker_id}

    @app.post("/api/workers/{worker_id}/run-environment")
    async def run_worker_environment(worker_id: str):
        try:
            return await environment_runner.run(worker_id)
        except KeyError:
            raise HTTPException(404, "worker not found")
        except EnvironmentModeError as exc:
            raise HTTPException(400, str(exc))
        except EnvironmentNotImplemented as exc:
            raise HTTPException(501, str(exc))

    @app.post("/api/evals/run")
    async def run_eval(req: EvalRequest):
        try:
            eval_worker = worker_store.get(req.worker_id)
        except KeyError:
            raise HTTPException(404, "worker not found")

        worker_hash = hashlib.sha256(
            json.dumps(
                eval_worker.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest()
        experiment_run_id = str(uuid4())
        task_set_hash = canonical_task_set_hash(req.cases)
        variants = req.resolved_variants()
        rows: list[dict] = []
        manifest_variants: list[dict] = []
        variant_records = []

        for variant in variants:
            variant_payload = variant.model_dump(mode="json")
            variant_hash = hashlib.sha256(
                json.dumps(
                    {"worker_hash": worker_hash, "variant": variant_payload},
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                ).encode("utf-8")
            ).hexdigest()
            variant_records.append((variant, variant_hash))
            manifest_variants.append({
                **variant_payload,
                "variant_hash": variant_hash,
            })

        if req.reset_policy == "persistent_sequence":
            pipeline.reset(req.worker_id)

        condition_orders: list[list[str]] = []
        for repetition in range(req.repetitions):
            ordered = list(variant_records)
            if req.condition_order_seed is not None:
                random.Random(req.condition_order_seed + repetition).shuffle(ordered)
            condition_orders.append([variant.id for variant, _ in ordered])

            for variant, variant_hash in ordered:
                if req.reset_policy == "reset_per_variant":
                    pipeline.reset(req.worker_id)

                for case in req.cases:
                    if req.reset_policy == "reset_per_case":
                        pipeline.reset(req.worker_id)

                    started = time.perf_counter()
                    try:
                        result = await pipeline.run(PipelineRequest(
                            worker_id=req.worker_id,
                            event=case.event,
                            mode="auto",
                            jev_enabled=variant.jev,
                            llm_enabled=variant.llm,
                            architecture=variant.architecture,
                            harness_passes=variant.harness_passes,
                            feedback_enabled=variant.feedback_enabled,
                            bridge_engines=variant.bridge_engines,
                            input_encoders=variant.input_encoders,
                        ))
                        route = result.decisions.answers.get("route", {}).get("choice")
                        task_score = score_task_result(case, result.task_result, route)
                        trace = result.execution.get("integration", {}).get("trace", [])
                        neural_stage_calls = sum(
                            1
                            for pass_trace in trace
                            for component in pass_trace.get("components", [])
                            if component.get("type") == "neural_stage"
                            and component.get("called")
                        )
                        rows.append({
                            "experiment_run_id": experiment_run_id,
                            "run_id": result.run_id,
                            "case_id": case.id,
                            "repetition": repetition,
                            "variant_id": variant.id,
                            "variant_hash": variant_hash,
                            # legacy key retained for old clients
                            "toggle_case": variant.id,
                            "jev": variant.jev,
                            "llm": variant.llm,
                            "architecture": result.execution.get("architecture"),
                            "harness_passes": result.execution.get(
                                "integration", {}
                            ).get("harness_passes", 1),
                            "feedback_enabled": variant.feedback_enabled,
                            "bridge_engines": dict(variant.bridge_engines),
                            "input_encoders": dict(variant.input_encoders),
                            "route": route,
                            "route_correct": (
                                None
                                if case.expected_route is None
                                else route == case.expected_route
                            ),
                            "task_result": result.task_result.model_dump(mode="json"),
                            "task_score": task_score,
                            "latency_ms": (time.perf_counter() - started) * 1000,
                            "jev_called": result.execution.get("jev", {}).get("called", False),
                            "jev_calls": result.execution.get("jev", {}).get("calls", 0),
                            "llm_called": result.execution.get("llm", {}).get("called", False),
                            "llm_calls": result.execution.get("llm", {}).get("calls", 0),
                            "neural_stage_calls": neural_stage_calls,
                            "unresolved": result.task_result.unresolved,
                            "error": None,
                        })
                    except Exception as exc:
                        rows.append({
                            "experiment_run_id": experiment_run_id,
                            "run_id": None,
                            "case_id": case.id,
                            "repetition": repetition,
                            "variant_id": variant.id,
                            "variant_hash": variant_hash,
                            "toggle_case": variant.id,
                            "jev": variant.jev,
                            "llm": variant.llm,
                            "architecture": variant.architecture,
                            "harness_passes": (
                                variant.harness_passes
                                or eval_worker.runtime.resolved_harness_passes
                            ),
                            "feedback_enabled": variant.feedback_enabled,
                            "bridge_engines": dict(variant.bridge_engines),
                            "input_encoders": dict(variant.input_encoders),
                            "route": None,
                            "route_correct": (
                                False if case.expected_route is not None else None
                            ),
                            "task_result": None,
                            "task_score": (
                                0.0
                                if case.expected_answer is not None
                                or case.expected_route is not None
                                else None
                            ),
                            "latency_ms": (time.perf_counter() - started) * 1000,
                            "jev_called": False,
                            "jev_calls": 0,
                            "llm_called": False,
                            "llm_calls": 0,
                            "neural_stage_calls": 0,
                            "unresolved": [],
                            "error": str(exc),
                        })

        summary = summarize_eval(rows)
        compute_signatures = {
            variant_id: {
                "jev_calls_per_case": values.get("jev_calls_per_case"),
                "llm_calls_per_case": values.get("llm_calls_per_case"),
                "neural_stage_calls_per_case": values.get("neural_stage_calls_per_case"),
                "harness_passes_per_case": values.get("harness_passes_per_case"),
            }
            for variant_id, values in summary.items()
        }
        normalized_signatures = {
            json.dumps(value, sort_keys=True, separators=(",", ":"))
            for value in compute_signatures.values()
        }
        compute_matched = len(normalized_signatures) <= 1

        experiment_record = {
            "experiment_run_id": experiment_run_id,
            "worker_id": req.worker_id,
            "worker_hash": worker_hash,
            "task_set_hash": task_set_hash,
            "scorer_version": req.scorer_version,
            "reset_policy": req.reset_policy,
            "repetitions": req.repetitions,
            "condition_order_seed": req.condition_order_seed,
            "condition_orders": condition_orders,
            "variants": manifest_variants,
            "case_ids": [case.id for case in req.cases],
            "run_ids": [row["run_id"] for row in rows if row.get("run_id")],
            "compute_signatures": compute_signatures,
            "compute_matched": compute_matched,
            "summary": summary,
            "rows": rows,
        }
        db.insert_experiment_run(experiment_record)
        return experiment_record

    @app.get("/api/evals/runs")
    async def eval_runs(limit: int = Query(100, ge=1, le=5000), worker_id: str | None = None):
        return db.list_experiment_runs(limit=limit, worker_id=worker_id)

    @app.get("/api/evals/runs/{experiment_run_id}")
    async def eval_run_detail(experiment_run_id: str):
        record = db.get_experiment_run(experiment_run_id)
        if record is None:
            raise HTTPException(404, "experiment run not found")
        return record

    @app.get("/api/events")
    async def events(limit: int = Query(50, ge=1, le=500)):
        return db.list_events(limit)

    @app.get("/api/sources")
    async def list_sources():
        return db.list_sources()

    @app.post("/api/sources")
    async def add_source(spec: DataSourceSpec):
        db.upsert_source(spec.model_dump())
        return {"ok": True, "source": spec}

    @app.post("/api/sources/{source_id}/poll")
    async def poll_one(source_id: str):
        raw = next((x for x in db.list_sources() if x["id"] == source_id), None)
        if not raw:
            raise HTTPException(404, "source not found")
        spec = DataSourceSpec.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})
        try:
            return await poll_source(spec, settings.data_dir / "inbox")
        except Exception as exc:
            raise HTTPException(400, str(exc))

    @app.get("/api/tasks")
    async def list_tasks():
        return db.list_tasks()

    @app.post("/api/tasks")
    async def add_task(spec: CronTaskSpec):
        try:
            valid = validate_cron(spec.cron)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc))
        if not valid:
            raise HTTPException(400, "invalid cron expression")
        db.upsert_task(spec.model_dump())
        return {"ok": True, "task": spec}

    @app.post("/api/simulate")
    async def simulate(spec: SimulationSpec, worker_id: str = "scout"):
        if spec.reset_brains:
            try:
                pipeline.reset(worker_id)
            except KeyError:
                raise HTTPException(404, "worker not found")
        results = []
        for event in spec.events:
            results.append(await pipeline.run(PipelineRequest(worker_id=worker_id, event=event, mode=spec.mode)))
        return {"name": spec.name, "worker_id": worker_id, "count": len(results), "results": results}

    return app
