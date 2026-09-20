from pathlib import Path

from connectome_fixtures import install_runtime_fixtures, write_malecns_full_fixture
from hive_connectome.brains.connectome import CookConnectomeBrain, MaleCNSLocomotorBrain
from hive_connectome.brains.malecns_full import MaleCNSFullBrain, compile_full_malecns


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


def test_full_malecns_compiler_and_engine_executes_complete_fixture(tmp_path: Path):
    raw=write_malecns_full_fixture(tmp_path)
    compiled=tmp_path/'compiled'/'fly-malecns-v1'
    manifest=compile_full_malecns(
        raw,compiled,
        expected_neurons=4,
        expected_directed_edges=4,
        expected_synaptic_contacts=26,
    )
    assert manifest['neurons']==4
    assert manifest['directed_edges']==4
    assert manifest['synaptic_contacts']==26
    brain=MaleCNSFullBrain(
        'full-fly',raw,compiled,
        expected_neurons=4,
        expected_directed_edges=4,
        expected_synaptic_contacts=26,
        substeps=3,
        sample_size=4,
    )
    obs=brain.step({'__hive_stimulus__':[[0,1.2]]})
    assert obs.metadata['full_connectome'] is True
    assert obs.metadata['real_connectome_topology'] is True
    assert obs.metadata['node_count']==4
    assert obs.metadata['edge_count']==4
    assert obs.metadata['synaptic_contacts']==26
    assert obs.metadata['input_encoding']=='explicit bridge stimulus'
    assert len(obs.state_vector)==4
    exported=brain.export_state()
    assert exported['state'].shape==(4,)
    assert exported['step'].tolist()==[1]


def test_full_malecns_compiler_rejects_wrong_expected_counts(tmp_path: Path):
    raw=write_malecns_full_fixture(tmp_path)
    compiled=tmp_path/'compiled-bad'
    import pytest
    with pytest.raises(ValueError,match='neuron count mismatch'):
        compile_full_malecns(raw,compiled,expected_neurons=5,expected_directed_edges=4,expected_synaptic_contacts=26)
