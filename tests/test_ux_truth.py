from pathlib import Path
from hive_connectome.runtime_status import neural_runtime_status

ROOT = Path(__file__).parents[1]
HTML = (ROOT / "src/hive_connectome/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "src/hive_connectome/static/app.js").read_text(encoding="utf-8")


def test_runtime_status_static_helper_defers_to_live_health():
    runtime = neural_runtime_status()
    assert runtime["backend"] == "connectome-runtime-v0.7-core-graph"
    assert runtime["primary_experiment_ready"] is False
    assert runtime["real_connectome_runtime_ready"] is False
    assert runtime["study_mode"] == "CONTROL_ONLY"
    assert runtime["core_graph_runtime"] is True
    assert "biological_connectome_executing" not in runtime


def test_home_page_is_experiment_first_not_fake_assistant_first():
    for phrase in [
        "Choose the experiment Core",
        "RESOLVED EXECUTION PATH",
        "Give this Core an input",
        "See exactly what happened",
        "Ablation comparison",
        "Experiment records",
        "Debugging: raw run JSON",
    ]:
        assert phrase in HTML
    assert "What do you want HIVE to do?" not in HTML
    assert "Understand new information" not in JS
    assert "Sort / route an event" not in JS
    assert "Load example" not in HTML


def test_gui_explains_semantic_boundaries():
    assert "No hidden task preset is added" in HTML
    assert "Every box below corresponds to a stage that actually executed" in HTML
    assert "not part of the biological connectome" in JS
    assert "not labels discovered by the connectome itself" in JS
    assert "deterministic engineering readout" in JS
    assert "installed versus merely available" in HTML
