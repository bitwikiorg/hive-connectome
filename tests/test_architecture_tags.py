from pathlib import Path

import pytest

from connectome_fixtures import install_runtime_fixtures
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import DecisionBundle, EventEnvelope, PipelineRequest
from hive_connectome.workers import WorkerSpec, WorkerStore


class OrderedJev:
    def __init__(self):
        self.states = []

    async def decide(self, state, questions, model=None):
        self.states.append(state)
        return DecisionBundle(
            provider="venice",
            model=model or "jev-latest",
            answers={
                "meaningful_signal": {"type": "noul", "noul": 0.8},
                "novelty": {"type": "score", "score": 1.0, "confidence": 0.9},
                "route": {"type": "choice", "choice": "store", "confidence": 0.9},
                "llm_needed": {"type": "noul", "noul": 0.5},
            },
            confidence=0.9,
        )


def _store(tmp_path: Path) -> WorkerStore:
    install_runtime_fixtures(tmp_path)
    return WorkerStore(
        tmp_path / "workers.json",
        Path(__file__).parents[1] / "config" / "workers.default.json",
    )


def test_default_architecture_parses_comma_tags(tmp_path: Path):
    workers = _store(tmp_path)
    scout = workers.get("scout")
    assert scout.architecture == [
        "worm",
        "worm-to-fly",
        "fly",
        "readout",
        "jev",
        "llm",
        "jev_verify",
        "feedback",
    ]


def test_unknown_architecture_tag_is_rejected(tmp_path: Path):
    workers = _store(tmp_path)
    raw = workers.get("scout").model_dump(mode="json")
    raw["architecture"] = "worm,definitely-not-a-component"
    with pytest.raises(ValueError, match="unknown component tags"):
        WorkerSpec.model_validate(raw)


@pytest.mark.asyncio
async def test_architecture_order_is_execution_order(tmp_path: Path):
    workers = _store(tmp_path)
    scout = workers.get("scout")
    scout.runtime.integration_cycles = 1
    scout.llm.enabled = False
    scout.jev.enabled = True
    scout.architecture = [
        "worm",
        "readout",
        "jev",
        "feedback",
        "worm",
        "readout",
        "jev",
    ]
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    jev = OrderedJev()
    pipeline = HivePipeline(db, workers, venice=jev, data_dir=tmp_path)
    out = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=True,
        llm_enabled=False,
        event=EventEnvelope(payload={"signal": "ordered"}),
    ))

    tags = [item["tag"] for item in out.execution["integration"]["trace"][0]["components"]]
    assert tags == scout.architecture
    assert out.worm.step == 2
    assert out.fly is None
    assert out.execution["jev"]["calls"] == 2
    assert len(jev.states) == 2
    assert jev.states[0]["neural_state"]["worm"]["whole_state"]["state_hash"] != (
        jev.states[1]["neural_state"]["worm"]["whole_state"]["state_hash"]
    )
    db.close()


@pytest.mark.asyncio
async def test_bridge_tag_must_precede_its_target_stage(tmp_path: Path):
    workers = _store(tmp_path)
    scout = workers.get("scout")
    scout.runtime.integration_cycles = 1
    scout.architecture = ["worm", "fly", "worm-to-fly"]
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    pipeline = HivePipeline(db, workers, data_dir=tmp_path)
    with pytest.raises(RuntimeError, match="without a later target stage"):
        await pipeline.run(PipelineRequest(
            worker_id="scout",
            jev_enabled=False,
            llm_enabled=False,
            event=EventEnvelope(payload={"signal": "bad-order"}),
        ))
    db.close()
