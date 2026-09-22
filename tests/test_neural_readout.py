from pathlib import Path

import pytest

from connectome_fixtures import install_runtime_fixtures, write_malecns_full_fixture
from hive_connectome.brains.malecns_full import MaleCNSFullBrain
from hive_connectome.db import HiveDB
from hive_connectome.neural_readout import whole_state_readout
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import DecisionBundle, EventEnvelope, PipelineRequest
from hive_connectome.workers import WorkerStore


class CaptureJev:
    def __init__(self):
        self.states = []

    async def decide(self, state, questions, model=None):
        self.states.append(state)
        return DecisionBundle(
            provider="venice",
            model=model or "jev-latest",
            answers={
                "meaningful_signal": {"type": "noul", "noul": 0.75},
                "novelty": {"type": "score", "score": 1.1, "confidence": 0.9},
                "route": {"type": "choice", "choice": "store", "confidence": 0.9},
                "llm_needed": {"type": "noul", "noul": 0.5},
            },
            confidence=0.9,
        )


@pytest.mark.asyncio
async def test_jev_receives_whole_state_not_arbitrary_excerpt(tmp_path: Path):
    install_runtime_fixtures(tmp_path)
    db = HiveDB(tmp_path / "hive.db")
    workers = WorkerStore(
        tmp_path / "workers.json",
        Path(__file__).parents[1] / "config" / "workers.default.json",
    )
    jev = CaptureJev()
    pipeline = HivePipeline(db, workers, venice=jev, data_dir=tmp_path)

    out = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=True,
        llm_enabled=False,
        event=EventEnvelope(payload={"signal": "test"}),
    ))

    assert len(jev.states) == 2
    state = jev.states[-1]
    assert "stages" not in state
    assert "neural_state" in state
    fly = state["neural_state"]["fly"]["whole_state"]
    worm = state["neural_state"]["worm"]["whole_state"]
    assert fly["representation"] == "lossless_dense"
    assert worm["representation"] == "lossless_dense"
    assert len(fly["state"]["values"]) == 4
    assert len(worm["state"]["values"]) == 3
    assert fly["state_hash"] == out.fly.metadata.get("state_hash", fly["state_hash"])
    assert out.execution["stages"]["fly"]["whole_state_readout"]["neurons"] == 4
    db.close()


def test_full_malecns_large_readout_uses_every_neuron(tmp_path: Path):
    raw = write_malecns_full_fixture(tmp_path)
    compiled = tmp_path / "compiled" / "fly-malecns-v1"
    brain = MaleCNSFullBrain(
        "full-fly",
        raw,
        compiled,
        expected_neurons=4,
        expected_directed_edges=4,
        expected_synaptic_contacts=26,
        substeps=3,
        sample_size=2,
    )
    obs = brain.step({"__hive_stimulus__": [[0, 1.2]]})
    readout = whole_state_readout(brain, obs, dense_limit=2, top_k=2, chunks=2)

    assert readout["representation"] == "whole_state_multiresolution_v1"
    assert readout["neurons"] == 4
    assert len(readout["chunks"]) == 2
    assert readout["chunks"][0]["start"] == 0
    assert readout["chunks"][-1]["end"] == 4
    assert len(readout["top_absolute"]) == 2
    assert readout["state_hash"] == obs.metadata["state_hash"]
