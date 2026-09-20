import pytest
from pathlib import Path
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.workers import WorkerStore
from hive_connectome.schemas import EventEnvelope, PipelineRequest

@pytest.mark.asyncio
async def test_offline_pipeline_runs(tmp_path:Path):
    db=HiveDB(tmp_path/"hive.db")
    workers=WorkerStore(tmp_path/"workers.json",Path(__file__).parents[1]/"config"/"workers.default.json")
    p=HivePipeline(db,workers)
    out=await p.run(PipelineRequest(mode="offline",event=EventEnvelope(payload={"signal":"honey","value":4})))
    assert out.worm.engine.startswith("synthetic")
    assert out.fly.step==1
    assert out.decisions.provider=="brain-readout"
    assert db.list_events(1)[0]["payload"]["signal"]=="honey"
    db.close()
