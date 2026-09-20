from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import CronTaskSpec, DataSourceSpec, EventEnvelope, PipelineRequest
from hive_connectome.sources import poll_source
from hive_connectome.workers import WorkerStore


def validate_cron(expression: str) -> bool:
    try:
        from croniter import croniter
    except ImportError as exc:
        raise RuntimeError("cron support requires the declared 'croniter' dependency") from exc
    return bool(croniter.is_valid(expression))


def cron_due(expression: str, minute_stamp: datetime) -> bool:
    try:
        from croniter import croniter
    except ImportError as exc:
        raise RuntimeError("cron support requires the declared 'croniter' dependency") from exc
    base = minute_stamp.timestamp() - 60
    return croniter(expression, base).get_next(float) <= minute_stamp.timestamp()


class HeartbeatDaemon:
    def __init__(
        self,
        db: HiveDB,
        pipeline: HivePipeline,
        inbox_root: Path,
        *,
        worker_store: WorkerStore | None = None,
        environment_runner=None,
    ):
        self.db = db
        self.pipeline = pipeline
        self.inbox_root = inbox_root
        self.worker_store = worker_store
        self.environment_runner = environment_runner
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._worker_last_run: dict[str, float | str] = {}

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _loop(self) -> None:
        while not self._stop.is_set():
            await self.tick()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=2)
            except TimeoutError:
                pass

    async def _handle_source(self, spec: DataSourceSpec) -> None:
        events = await poll_source(spec, self.inbox_root)
        for event in events:
            if spec.kind == "file_drop":
                source_path = str(event.provenance.get("path", ""))
                path = Path(source_path)
                if self.db.file_seen(source_path, path.stat().st_mtime):
                    continue
                self.db.mark_file_seen(source_path, path.stat().st_mtime)
            if spec.auto_process:
                await self.pipeline.run(PipelineRequest(worker_id="scout", event=event, mode="auto"))
            else:
                self.db.insert_event(event.model_dump(mode="json"))

    async def tick(self) -> None:
        now = time.time()
        source_map = {raw["id"]: raw for raw in self.db.list_sources()}
        for raw in source_map.values():
            spec = DataSourceSpec.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})
            if not spec.enabled:
                continue
            last = raw.get("_last_polled") or 0
            if now - float(last) < spec.interval_seconds:
                continue
            try:
                await self._handle_source(spec)
            except Exception:
                pass
            finally:
                self.db.set_source_polled(spec.id, now)

        minute_stamp = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        for raw in self.db.list_tasks():
            spec = CronTaskSpec.model_validate({k: v for k, v in raw.items() if not k.startswith("_")})
            if not spec.enabled or raw.get("_last_run") == minute_stamp.isoformat():
                continue
            try:
                if not cron_due(spec.cron, minute_stamp):
                    continue
                if spec.action == "emit_event":
                    event = EventEnvelope(source_id=f"cron:{spec.id}", kind="cron", payload=spec.payload or {})
                    await self.pipeline.run(PipelineRequest(worker_id="scout", event=event, mode="auto"))
                elif spec.action == "poll_source" and spec.target_id:
                    source_raw = source_map.get(spec.target_id)
                    if source_raw:
                        source_spec = DataSourceSpec.model_validate({k: v for k, v in source_raw.items() if not k.startswith("_")})
                        await self._handle_source(source_spec)
            except Exception:
                pass
            finally:
                self.db.set_task_run(spec.id, minute_stamp.isoformat())

        if self.worker_store is None or self.environment_runner is None:
            return
        for worker in self.worker_store.list():
            runtime = worker.runtime
            if not runtime.enabled or runtime.mode == "on_demand":
                continue
            due = False
            if runtime.mode == "daemon":
                last = float(self._worker_last_run.get(worker.id, 0) or 0)
                due = now - last >= runtime.interval_seconds
            elif runtime.mode == "cron" and runtime.cron:
                stamp = minute_stamp.isoformat()
                due = self._worker_last_run.get(worker.id) != stamp and cron_due(runtime.cron, minute_stamp)
            if not due:
                continue
            try:
                await self.environment_runner.run(worker.id)
            except Exception:
                pass
            finally:
                self._worker_last_run[worker.id] = minute_stamp.isoformat() if runtime.mode == "cron" else now
