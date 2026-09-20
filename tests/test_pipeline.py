import pytest
from pathlib import Path
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.workers import WorkerStore
from hive_connectome.schemas import EventEnvelope, PipelineRequest
from connectome_fixtures import install_runtime_fixtures

@pytest.mark.asyncio
async def test_offline_pipeline_runs(tmp_path:Path):
    install_runtime_fixtures(tmp_path)
    db=HiveDB(tmp_path/"hive.db")
    workers=WorkerStore(tmp_path/"workers.json",Path(__file__).parents[1]/"config"/"workers.default.json")
    p=HivePipeline(db,workers)
    out=await p.run(PipelineRequest(mode="offline",event=EventEnvelope(payload={"signal":"honey","value":4})))
    assert out.worm.engine.startswith("cook2019")
    assert out.fly.engine.startswith("malecns")
    assert out.execution["larva"]["real_connectome_topology"] is True
    assert out.execution["bee"]["real_connectome_topology"] is True
    assert out.fly.step==1
    assert out.decisions.provider=="brain-readout"
    assert db.list_events(1)[0]["payload"]["signal"]=="honey"
    db.close()
