import pytest
from pathlib import Path
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import EventEnvelope,PipelineRequest
@pytest.mark.asyncio
async def test_offline_pipeline_runs(tmp_path:Path):
    db=HiveDB(tmp_path/"hive.db");p=HivePipeline(db)
    out=await p.run(PipelineRequest(mode="offline",event=EventEnvelope(payload={"signal":"honey","value":4})))
    assert out.worm.engine.startswith("synthetic") and out.fly.step==1 and out.decisions.provider=="local-heuristic"
    assert db.list_events(1)[0]["payload"]["signal"]=="honey"
