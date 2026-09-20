from pathlib import Path
from hive_connectome.runtime_status import neural_runtime_status


def test_runtime_status_static_helper_defers_to_live_health():
    runtime = neural_runtime_status()
    assert runtime["backend"] == "connectome-runtime-v0.5"
    assert runtime["real_connectome_runtime_ready"] is None
    assert "biological_connectome_executing" not in runtime


def test_home_page_is_human_first_not_raw_json_first():
    text=(Path(__file__).parents[1]/"src/hive_connectome/static/index.html").read_text()
    assert "What do you want HIVE to do?" in text
    assert "Your result will appear here in normal language." in text
    assert "Raw JSON is available underneath the result" in text
    assert "Real connectome runtime" in text
    assert "Cook C. elegans" in text
    assert "Advanced experiment controls" in text


def test_front_door_has_plain_language_jobs_and_examples():
    js=(Path(__file__).parents[1]/"src/hive_connectome/static/app.js").read_text()
    for phrase in ["Understand new information","Sort / route an event","Decide what is worth remembering","Check a claim against evidence","Load example"]:
        assert phrase in js or phrase in (Path(__file__).parents[1]/"src/hive_connectome/static/index.html").read_text()
