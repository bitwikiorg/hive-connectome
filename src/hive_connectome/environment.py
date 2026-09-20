from __future__ import annotations

from pathlib import Path
from typing import Any

from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import DataSourceSpec, PipelineRequest
from hive_connectome.sources import poll_source
from hive_connectome.workers import WorkerStore


class EnvironmentModeError(ValueError):
    pass


class EnvironmentNotImplemented(NotImplementedError):
    pass


class WorkerEnvironmentRunner:
    def __init__(self, db: HiveDB, workers: WorkerStore, pipeline: HivePipeline, inbox_root: Path):
        self.db = db
        self.workers = workers
        self.pipeline = pipeline
        self.inbox_root = inbox_root

    async def run(self, worker_id: str) -> dict[str, Any]:
        worker = self.workers.get(worker_id)
        env = worker.data_environment

        if env.mode == "manual":
            raise EnvironmentModeError("manual environment requires an event submitted through /api/pipeline/run")

        if env.mode == "source_ids":
            all_sources = {item["id"]: item for item in self.db.list_sources()}
            results: list[dict[str, Any]] = []
            for source_id in env.source_ids:
                raw = all_sources.get(source_id)
                if not raw:
                    results.append({"source_id": source_id, "error": "configured source not found"})
                    continue
                spec = DataSourceSpec.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})
                try:
                    polled = await poll_source(spec, self.inbox_root)
                    for event in polled[: worker.runtime.max_events_per_tick]:
                        result = await self.pipeline.run(PipelineRequest(worker_id=worker.id, event=event, mode="auto"))
                        results.append(result.model_dump(mode="json"))
                except Exception as exc:
                    results.append({"source_id": source_id, "error": str(exc)})
            return {"worker_id": worker.id, "environment": env.model_dump(mode="json"), "results": results}

        if env.mode == "file_drop":
            spec = DataSourceSpec(
                id=f"worker:{worker.id}:files",
                name=f"{worker.name} files",
                kind="file_drop",
                path=env.file_path,
                interval_seconds=env.poll_interval_seconds,
                enabled=True,
                auto_process=True,
            )
            polled = await poll_source(spec, self.inbox_root)
            results = []
            for event in polled[: worker.runtime.max_events_per_tick]:
                result = await self.pipeline.run(PipelineRequest(worker_id=worker.id, event=event, mode="auto"))
                results.append(result.model_dump(mode="json"))
            return {"worker_id": worker.id, "environment": env.model_dump(mode="json"), "results": results}

        if env.mode in {"browser_dom", "browser_visual"}:
            raise EnvironmentNotImplemented("browser environment adapter is not implemented yet")
        if env.mode == "worker_output":
            raise EnvironmentNotImplemented("worker-output chaining is not implemented yet")
        if env.mode == "simulation":
            raise EnvironmentNotImplemented("simulation environments run through /api/simulate, not run-environment")
        raise EnvironmentNotImplemented(f"environment mode {env.mode} is not implemented")
