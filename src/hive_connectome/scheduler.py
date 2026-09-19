from __future__ import annotations
import asyncio,time
from datetime import datetime,timezone
from pathlib import Path
from croniter import croniter
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import CronTaskSpec,DataSourceSpec,EventEnvelope,PipelineRequest
from hive_connectome.sources import poll_source

class HeartbeatDaemon:
    def __init__(self,db:HiveDB,pipeline:HivePipeline,inbox_root:Path):
        self.db=db;self.pipeline=pipeline;self.inbox_root=inbox_root;self._stop=asyncio.Event();self._task:asyncio.Task|None=None
    def start(self):
        if self._task is None:self._task=asyncio.create_task(self._loop())
    async def stop(self):
        self._stop.set()
        if self._task:await self._task
    async def _loop(self):
        while not self._stop.is_set():
            await self.tick()
            try:await asyncio.wait_for(self._stop.wait(),timeout=2)
            except TimeoutError:pass
    async def tick(self):
        now=time.time()
        for raw in self.db.list_sources():
            spec=DataSourceSpec.model_validate({k:v for k,v in raw.items() if not k.startswith("_")})
            if not spec.enabled:continue
            last=raw.get("_last_polled") or 0
            if now-float(last)<spec.interval_seconds:continue
            try:
                events=await poll_source(spec,self.inbox_root)
                for event in events:
                    if spec.kind=="file_drop":
                        source_path=str(event.provenance.get("path",""));p=Path(source_path)
                        if self.db.file_seen(source_path,p.stat().st_mtime):continue
                        self.db.mark_file_seen(source_path,p.stat().st_mtime)
                    if spec.auto_process:await self.pipeline.run(PipelineRequest(event=event,mode="auto"))
                    else:self.db.insert_event(event.model_dump(mode="json"))
            finally:self.db.set_source_polled(spec.id,now)
        minute_stamp=datetime.now(timezone.utc).replace(second=0,microsecond=0)
        for raw in self.db.list_tasks():
            spec=CronTaskSpec.model_validate({k:v for k,v in raw.items() if not k.startswith("_")})
            if not spec.enabled or raw.get("_last_run")==minute_stamp.isoformat():continue
            if croniter(spec.cron,minute_stamp.timestamp()-60).get_next(float)>minute_stamp.timestamp():continue
            if spec.action=="emit_event":
                await self.pipeline.run(PipelineRequest(event=EventEnvelope(source_id=f"cron:{spec.id}",kind="cron",payload=spec.payload or {}),mode="auto"))
            self.db.set_task_run(spec.id,minute_stamp.isoformat())
