import json
from pathlib import Path

from hive_connectome.experiment_contract import experiment_readiness, load_experiment_contract

ROOT = Path(__file__).parents[1]


def test_primary_experiment_contract_cannot_be_reduced_to_subgraph():
    contract = json.loads((ROOT / "config" / "experiment_contract.json").read_text())
    bee = contract["primary_pipeline"]["bee"]
    assert bee["pack_id"] == "fly-malecns-v1"
    assert bee["scope"] == "full_connectome"
    assert bee["engine"] == "malecns_full_v1"
    assert bee["expected_neurons"] == 166700
    assert bee["expected_directed_connections"] == 25582938
    assert contract["primary_pipeline"]["larva"]["scope"] == "full_connectome"
    controls = {x["id"]: x for x in contract["controls"]}
    assert controls["malecns_locomotor_subgraph"]["role"] == "control_only"


def test_primary_readiness_stays_blocked_when_only_control_runtime_exists(tmp_path):
    contract = load_experiment_contract(ROOT / "config" / "experiment_contract.json")
    # Pretend all primary files were downloaded. Full engine support is still required.
    cook = tmp_path / "connectomes" / "worm-cook-2020"
    cook.mkdir(parents=True)
    (cook / "cook_2020_adjacency.xlsx").write_bytes(b"x")
    full = tmp_path / "connectomes" / "fly-malecns-v1"
    full.mkdir(parents=True)
    for name in contract["primary_pipeline"]["bee"]["required_files"]:
        (full / name).write_bytes(b"x")
    status = experiment_readiness(
        contract,
        data_dir=tmp_path,
        supported_engines={"cook2019_connectome", "malecns_locomotor"},
    )
    assert status["primary_experiment_ready"] is False
    assert any("full MaleCNS execution engine" in x for x in status["blockers"])


def test_full_malecns_is_required_not_optional_in_public_state():
    setup = (ROOT / "scripts" / "setup-windows.ps1").read_text()
    state = (ROOT / "docs" / "STATE.md").read_text()
    manifest = json.loads((ROOT / "config" / "connectomes.json").read_text())
    full = next(x for x in manifest["packs"] if x["id"] == "fly-malecns-v1")
    subgraph = next(x for x in manifest["packs"] if x["id"] == "fly-malecns-locomotor")
    assert full["primary_required"] is True
    assert subgraph["control_only"] is True
    assert "required for the primary experiment, not optional" in setup.lower()
    assert "not an optional enhancement" in state.lower()


def test_primary_readiness_requires_execution_receipts_even_when_engine_exists(tmp_path):
    contract=load_experiment_contract(ROOT/"config"/"experiment_contract.json")
    cook=tmp_path/"connectomes"/"worm-cook-2020"
    cook.mkdir(parents=True)
    (cook/"cook_2020_adjacency.xlsx").write_bytes(b"x")
    full=tmp_path/"connectomes"/"fly-malecns-v1"
    full.mkdir(parents=True)
    for name in contract["primary_pipeline"]["bee"]["required_files"]:
        (full/name).write_bytes(b"x")
    status=experiment_readiness(
        contract,data_dir=tmp_path,
        supported_engines={"cook2019_connectome","malecns_full_v1"},
    )
    assert status["primary_experiment_ready"] is False
    assert status["primary_pipeline"]["bee"]["engine_supported"] is True
    assert any("execution receipt" in item for item in status["blockers"])


def test_primary_readiness_accepts_only_matching_execution_receipts(tmp_path):
    contract=load_experiment_contract(ROOT/"config"/"experiment_contract.json")
    cook=tmp_path/"connectomes"/"worm-cook-2020"
    cook.mkdir(parents=True)
    (cook/"cook_2020_adjacency.xlsx").write_bytes(b"x")
    full=tmp_path/"connectomes"/"fly-malecns-v1"
    full.mkdir(parents=True)
    for name in contract["primary_pipeline"]["bee"]["required_files"]:
        (full/name).write_bytes(b"x")
    receipts=tmp_path/"execution_receipts"
    receipts.mkdir()
    (receipts/"cook2019_connectome--worm-cook-2020.json").write_text(json.dumps({
        "requested_engine":"cook2019_connectome","observed_engine":"cook2019-corrected-connectome-graded-v1",
        "pack_id":"worm-cook-2020","step":1,"node_count":300,"edge_count":1,
        "full_connectome":False,"metadata":{"real_connectome_topology":True},
    }))
    (receipts/"malecns_full_v1--fly-malecns-v1.json").write_text(json.dumps({
        "requested_engine":"malecns_full_v1","observed_engine":"malecns-full-v1-sparse-lif-v1",
        "pack_id":"fly-malecns-v1","step":1,"node_count":166700,"edge_count":25582938,
        "synaptic_contacts":124177617,"full_connectome":True,"state_hash":"abc",
        "metadata":{"real_connectome_topology":True,"full_connectome":True},
    }))
    status=experiment_readiness(
        contract,data_dir=tmp_path,
        supported_engines={"cook2019_connectome","malecns_full_v1"},
    )
    assert status["primary_experiment_ready"] is True
    assert status["blockers"] == []
