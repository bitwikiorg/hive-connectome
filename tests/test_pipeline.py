import pytest
from pathlib import Path
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.workers import WorkerStore
from hive_connectome.schemas import EventEnvelope, PipelineRequest
from connectome_fixtures import install_runtime_fixtures, write_malecns_full_fixture

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
    assert out.fly.step==2
    assert out.decisions.provider=="brain-readout"
    assert db.list_events(1)[0]["payload"]["signal"]=="honey"
    db.close()


@pytest.mark.asyncio
async def test_primary_full_core_runs_fixture_and_records_full_state(tmp_path:Path):
    install_runtime_fixtures(tmp_path)
    write_malecns_full_fixture(tmp_path)
    db=HiveDB(tmp_path/"hive.db")
    workers=WorkerStore(tmp_path/"workers.json",Path(__file__).parents[1]/"config"/"workers.default.json")
    primary=workers.get("primary-full")
    primary.outputs.recording_level="full"
    primary.jev.enabled=False
    primary.llm.enabled=False
    fly_stage=next(stage for stage in primary.brain_chain if stage.id=="fly")
    fly_stage.config.update({
        "expected_neurons":4,
        "expected_directed_connections":4,
        "expected_synapses":26,
        "substeps":3,
        "sample_size":4,
    })
    workers.save(primary)
    p=HivePipeline(
        db,workers,data_dir=tmp_path,
        experiment_contract_path=Path(__file__).parents[1]/"config"/"experiment_contract.json",
    )
    out=await p.run(PipelineRequest(
        worker_id="primary-full",jev_enabled=False,llm_enabled=False,mode="offline",
        event=EventEnvelope(payload={"signal":"fixture"}),
    ))
    assert out.execution["study_role"]=="primary_candidate"
    assert out.execution["primary_experiment"] is True
    assert out.stages["fly"].metadata["full_connectome"] is True
    artifact=tmp_path/out.stages["fly"].metadata["recording_artifact"]
    assert artifact.exists() and artifact.suffix==".npz"
    receipt=tmp_path/"execution_receipts"/"malecns_full_v1--fly-malecns-v1.json"
    assert receipt.exists()
    import json
    saved=json.loads(receipt.read_text())
    assert saved["node_count"]==4 and saved["edge_count"]==4
    status=p.runtime_status()
    assert status["primary_experiment_ready"] is False
    assert any("valid execution receipt" in item or "full MaleCNS" in item for item in status["primary"]["blockers"])
    db.close()
