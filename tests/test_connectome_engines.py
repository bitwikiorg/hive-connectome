from pathlib import Path

from connectome_fixtures import install_runtime_fixtures
from hive_connectome.brains.connectome import CookConnectomeBrain, MaleCNSLocomotorBrain


def test_cook_engine_executes_measured_graph(tmp_path: Path):
    install_runtime_fixtures(tmp_path)
    path=tmp_path/'connectomes'/'worm-cook-2020'/'cook_2020_adjacency.xlsx'
    brain=CookConnectomeBrain('worm',path,substeps=3)
    obs=brain.step({'text':'hello'})
    assert obs.engine.startswith('cook2019')
    assert obs.metadata['real_connectome_topology'] is True
    assert obs.metrics['nodes'] == 3
    assert obs.metrics['edges'] > 0
    assert obs.step == 1
    brain.feedback(0.5)
    second=brain.step({'text':'hello again'})
    assert second.step == 2
    brain.reset()
    assert brain.step({'text':'hello'}).step == 1


def test_malecns_engine_executes_measured_graph(tmp_path: Path):
    install_runtime_fixtures(tmp_path)
    path=tmp_path/'connectomes'/'fly-malecns-locomotor'/'locomotor_circuit.json'
    brain=MaleCNSLocomotorBrain('fly',path,ms_per_event=5)
    obs=brain.step({'text':'stimulus'})
    assert obs.engine.startswith('malecns')
    assert obs.metadata['real_connectome_topology'] is True
    assert obs.metrics['nodes'] == 4
    assert obs.metrics['edges'] == 4
    brain.feedback(-0.25)
    assert brain.step({'text':'next'}).step == 2
    brain.reset()
    assert brain.step({'text':'stimulus'}).step == 1
