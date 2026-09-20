import json
from pathlib import Path
from hive_connectome.workers import WorkerSpec

def test_default_workers_validate_and_have_complete_settings():
    root=Path(__file__).parents[1]
    data=json.loads((root/"config"/"workers.default.json").read_text())
    assert data["workers"]
    for raw in data["workers"]:
        worker=WorkerSpec.model_validate(raw)
        assert worker.experiment.task_prompt
        assert worker.experiment.objective
        assert worker.larva.substrate
        assert worker.bee.substrate
        assert worker.jev.questions
        assert worker.runtime.mode
        assert worker.outputs is not None

def test_browser_templates_match_browser_environment():
    root=Path(__file__).parents[1]
    data=json.loads((root/"config"/"experiment_templates.json").read_text())
    by_id={x["id"]:x for x in data["templates"]}
    assert by_id["browser_dom_reader"]["worker"]["experiment"]["kind"]=="browser_dom"
    assert by_id["browser_dom_reader"]["worker"]["data_environment"]["mode"]=="browser_dom"
    assert by_id["browser_dom_reader"]["worker"]["data_environment"]["ocr_enabled"] is False
    assert by_id["browser_visual_reader"]["worker"]["experiment"]["kind"]=="browser_visual"
    assert by_id["browser_visual_reader"]["worker"]["data_environment"]["mode"]=="browser_visual"
    assert by_id["browser_visual_reader"]["worker"]["data_environment"]["ocr_enabled"] is True
