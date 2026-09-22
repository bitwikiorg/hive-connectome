from pathlib import Path
from hive_connectome.workers import WorkerStore

def test_worker_store_persists_full_settings(tmp_path:Path):
    defaults=Path(__file__).parents[1]/"config"/"workers.default.json"
    store=WorkerStore(tmp_path/"workers.json",defaults)
    scout=store.get("scout")
    scout.experiment.task_prompt="changed task"
    scout.jev.enabled=False
    scout.llm.enabled=True
    scout.data_environment.mode="manual"
    store.save(scout)
    loaded=WorkerStore(tmp_path/"workers.json",defaults).get("scout")
    assert loaded.experiment.task_prompt=="changed task"
    assert loaded.jev.enabled is False
    assert loaded.llm.enabled is True
    assert loaded.data_environment.mode=="manual"


def test_legacy_jev_gating_fields_are_ignored(tmp_path:Path):
    from hive_connectome.workers import WorkerSpec
    import json
    defaults=Path(__file__).parents[1]/"config"/"workers.default.json"
    raw=json.loads(defaults.read_text())["workers"][0]
    raw["jev"]["llm_gate_threshold"] = 0.7
    raw["jev"]["confidence_threshold"] = 0.6
    worker=WorkerSpec.model_validate(raw)
    dumped=worker.model_dump(mode="json")
    assert "llm_gate_threshold" not in dumped["jev"]
    assert "confidence_threshold" not in dumped["jev"]
