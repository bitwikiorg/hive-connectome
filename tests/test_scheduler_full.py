from pathlib import Path
import pytest
import hive_connectome.scheduler as scheduler
from hive_connectome.db import HiveDB
from hive_connectome.schemas import EventEnvelope

class FakePipeline:
    def __init__(self): self.requests=[]
    async def run(self,req): self.requests.append(req); return {"ok":True}

@pytest.mark.asyncio
async def test_heartbeat_processes_file_once_and_survives_bad_source(tmp_path,monkeypatch):
    inbox=tmp_path/"inbox";inbox.mkdir();note=inbox/"note.md";note.write_text("x")
    db=HiveDB(tmp_path/"db.sqlite")
    db.upsert_source({"id":"good","name":"good","kind":"file_drop","path":str(inbox),"interval_seconds":5,"enabled":True,"auto_process":True})
    db.upsert_source({"id":"bad","name":"bad","kind":"http_json","url":"https://bad.test","method":"GET","body":None,"interval_seconds":5,"enabled":True,"auto_process":True})
    pipe=FakePipeline()
    async def fake_poll(spec,inbox_root):
        if spec.id=="bad": raise RuntimeError("boom")
        return [EventEnvelope(source_id=spec.id,kind="file",subject="note.md",payload="x",provenance={"path":str(note)})]
    monkeypatch.setattr(scheduler,"poll_source",fake_poll)
    hb=scheduler.HeartbeatDaemon(db,pipe,inbox); await hb.tick(); assert len(pipe.requests)==1
    for source in db.list_sources(): db.set_source_polled(source["id"],0)
    await hb.tick(); assert len(pipe.requests)==1; db.close()

@pytest.mark.asyncio
async def test_heartbeat_auto_process_false_stores_event(tmp_path,monkeypatch):
    inbox=tmp_path/"inbox";inbox.mkdir();db=HiveDB(tmp_path/"db.sqlite")
    db.upsert_source({"id":"manual","name":"manual","kind":"file_drop","path":str(inbox),"interval_seconds":5,"enabled":True,"auto_process":False})
    pipe=FakePipeline()
    async def fake_poll(spec,inbox_root): return [EventEnvelope(source_id="manual",kind="observation",payload={"x":1})]
    monkeypatch.setattr(scheduler,"poll_source",fake_poll); hb=scheduler.HeartbeatDaemon(db,pipe,inbox); await hb.tick()
    assert pipe.requests==[] and db.list_events(1)[0]["payload"]=={"x":1}; db.close()

@pytest.mark.asyncio
async def test_heartbeat_cron_emit(monkeypatch,tmp_path):
    inbox=tmp_path/"inbox";inbox.mkdir();db=HiveDB(tmp_path/"db.sqlite")
    db.upsert_task({"id":"t","name":"T","cron":"* * * * *","action":"emit_event","target_id":None,"payload":{"tick":1},"enabled":True})
    pipe=FakePipeline();monkeypatch.setattr(scheduler,"cron_due",lambda expr,stamp:True);hb=scheduler.HeartbeatDaemon(db,pipe,inbox);await hb.tick()
    assert len(pipe.requests)==1 and db.list_tasks()[0]["_last_run"] is not None;db.close()

class FakeEnvironmentRunner:
    def __init__(self): self.calls=[]
    async def run(self,worker_id): self.calls.append(worker_id); return {"worker_id":worker_id}

@pytest.mark.asyncio
async def test_heartbeat_poll_source_task_and_worker_runtime(tmp_path,monkeypatch):
    inbox=tmp_path/"inbox";inbox.mkdir();db=HiveDB(tmp_path/"db.sqlite")
    db.upsert_source({"id":"feed","name":"Feed","kind":"http_json","url":"https://example.test","method":"GET","body":None,"interval_seconds":60,"enabled":False,"auto_process":True})
    db.upsert_task({"id":"poll","name":"Poll","cron":"* * * * *","action":"poll_source","target_id":"feed","payload":None,"enabled":True})
    pipe=FakePipeline();called=[]
    async def fake_poll(spec,inbox_root): called.append(spec.id);return [EventEnvelope(source_id=spec.id,kind="observation",payload={"x":1})]
    monkeypatch.setattr(scheduler,"poll_source",fake_poll);monkeypatch.setattr(scheduler,"cron_due",lambda expr,stamp:True)
    from hive_connectome.workers import WorkerStore
    workers=WorkerStore(tmp_path/"workers.json",Path(__file__).parents[1]/"config"/"workers.default.json")
    scout=workers.get("scout");scout.runtime.enabled=True;scout.runtime.mode="daemon";scout.runtime.interval_seconds=5;workers.save(scout)
    env=FakeEnvironmentRunner();hb=scheduler.HeartbeatDaemon(db,pipe,inbox,worker_store=workers,environment_runner=env);await hb.tick()
    assert called==["feed"] and len(pipe.requests)==1 and env.calls==["scout"]
    await hb.tick(); assert env.calls==["scout"];db.close()

def test_poll_source_task_requires_target():
    from hive_connectome.schemas import CronTaskSpec
    with pytest.raises(ValueError,match="target_id"): CronTaskSpec(id="x",name="x",cron="* * * * *",action="poll_source")
