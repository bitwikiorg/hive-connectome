from pathlib import Path
import json

import pytest

from connectome_fixtures import install_runtime_fixtures
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import DecisionBundle, EventEnvelope, LLMResult, PipelineRequest
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


class CaptureLLM:
    def __init__(self, feedback=0.6):
        self.contexts = []
        self.feedback = feedback

    async def chat(self, model, prompt, context, temperature=0.2):
        self.contexts.append(json.loads(context))
        return LLMResult(
            provider="lmstudio",
            model=model,
            text=json.dumps({
                "analysis": "captured",
                "unresolved": [],
                "neural_feedback": self.feedback,
            }),
        )


@pytest.mark.asyncio
async def test_llm_without_jev_does_not_receive_fake_jev_decision(tmp_path: Path):
    workers = _store(tmp_path)
    scout = workers.get("scout")
    scout.runtime.integration_cycles = 1
    scout.jev.enabled = False
    scout.llm.enabled = True
    scout.llm.model = "test-model"
    scout.architecture = ["worm", "readout", "llm"]
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    llm = CaptureLLM()
    pipeline = HivePipeline(
        db,
        workers,
        lmstudio=llm,
        default_llm_model="test-model",
        data_dir=tmp_path,
    )
    out = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=False,
        llm_enabled=True,
        event=EventEnvelope(payload={"signal": "llm-only"}),
    ))

    assert out.execution["jev"]["called"] is False
    assert out.execution["llm"]["called"] is True
    assert len(llm.contexts) == 1
    assert "jev_decision" not in llm.contexts[0]
    db.close()


@pytest.mark.asyncio
async def test_jev_and_llm_feedback_have_independent_targets(tmp_path: Path):
    workers = _store(tmp_path)
    scout = workers.get("scout")
    scout.runtime.integration_cycles = 2
    scout.jev.enabled = True
    scout.jev.feedback_to_brain = True
    scout.jev.feedback_targets = ["worm"]
    scout.llm.enabled = True
    scout.llm.model = "test-model"
    scout.llm.feedback_to_brain = True
    scout.llm.feedback_targets = ["fly"]
    scout.llm.verify_with_jev = False
    scout.architecture = [
        "worm",
        "worm-to-fly",
        "fly",
        "readout",
        "jev",
        "llm",
        "feedback",
    ]
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    llm = CaptureLLM(feedback=0.6)
    pipeline = HivePipeline(
        db,
        workers,
        venice=OrderedJev(),
        lmstudio=llm,
        default_llm_model="test-model",
        data_dir=tmp_path,
    )
    out = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=True,
        llm_enabled=True,
        event=EventEnvelope(payload={"signal": "feedback-targets"}),
    ))

    first_feedback = next(
        item for item in out.execution["integration"]["trace"][0]["components"]
        if item["type"] == "feedback"
    )
    assert first_feedback["applied"] is True
    assert first_feedback["sources"]["jev"]["targets"] == ["worm"]
    assert first_feedback["sources"]["llm"]["targets"] == ["fly"]
    assert first_feedback["target_modulations"]["worm"] == pytest.approx(0.24)
    assert first_feedback["target_modulations"]["fly"] == pytest.approx(0.6)
    db.close()


@pytest.mark.asyncio
async def test_jev_verifier_does_not_require_regular_jev_tag(tmp_path: Path):
    workers = _store(tmp_path)
    scout = workers.get("scout")
    scout.runtime.integration_cycles = 1
    scout.jev.enabled = True
    scout.llm.enabled = True
    scout.llm.model = "test-model"
    scout.llm.verify_with_jev = True
    scout.architecture = ["worm", "readout", "llm", "jev_verify"]
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    jev = OrderedJev()
    llm = CaptureLLM()
    pipeline = HivePipeline(
        db,
        workers,
        venice=jev,
        lmstudio=llm,
        default_llm_model="test-model",
        data_dir=tmp_path,
    )
    out = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=True,
        llm_enabled=True,
        event=EventEnvelope(payload={"signal": "verify-only"}),
    ))

    assert out.execution["jev"]["called"] is False
    assert out.execution["jev_verification"]["called"] is True
    assert len(jev.states) == 1
    assert "jev_decision" not in jev.states[0]
    assert "llm_output" in jev.states[0]
    db.close()


def test_feedback_targets_must_reference_real_neural_stages(tmp_path: Path):
    workers = _store(tmp_path)
    raw = workers.get("scout").model_dump(mode="json")
    raw["llm"]["feedback_targets"] = ["not-a-stage"]
    with pytest.raises(ValueError, match="llm feedback targets reference unknown neural stages"):
        WorkerSpec.model_validate(raw)


@pytest.mark.asyncio
async def test_llm_does_not_receive_stale_jev_decision_after_neural_change(tmp_path: Path):
    workers = _store(tmp_path)
    scout = workers.get("scout")
    scout.runtime.integration_cycles = 1
    scout.jev.enabled = True
    scout.llm.enabled = True
    scout.llm.model = "test-model"
    scout.architecture = [
        "worm",
        "readout",
        "jev",
        "worm",
        "readout",
        "llm",
    ]
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    llm = CaptureLLM()
    pipeline = HivePipeline(
        db,
        workers,
        venice=OrderedJev(),
        lmstudio=llm,
        default_llm_model="test-model",
        data_dir=tmp_path,
    )
    await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=True,
        llm_enabled=True,
        event=EventEnvelope(payload={"signal": "stale-jev"}),
    ))

    assert len(llm.contexts) == 1
    assert "jev_decision" not in llm.contexts[0]
    db.close()


@pytest.mark.asyncio
async def test_verifier_rejects_llm_output_from_stale_readout(tmp_path: Path):
    workers = _store(tmp_path)
    scout = workers.get("scout")
    scout.runtime.integration_cycles = 1
    scout.jev.enabled = True
    scout.llm.enabled = True
    scout.llm.model = "test-model"
    scout.llm.verify_with_jev = True
    scout.architecture = [
        "worm",
        "readout",
        "llm",
        "worm",
        "readout",
        "jev_verify",
    ]
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    pipeline = HivePipeline(
        db,
        workers,
        venice=OrderedJev(),
        lmstudio=CaptureLLM(),
        default_llm_model="test-model",
        data_dir=tmp_path,
    )
    with pytest.raises(RuntimeError, match="latest LLM output.*current readout"):
        await pipeline.run(PipelineRequest(
            worker_id="scout",
            jev_enabled=True,
            llm_enabled=True,
            event=EventEnvelope(payload={"signal": "stale-llm"}),
        ))
    db.close()


def test_legacy_llm_activation_values_migrate_to_tag_driven_always(tmp_path: Path):
    workers = _store(tmp_path)
    raw = workers.get("scout").model_dump(mode="json")
    raw["llm"]["activation"] = "jev_gate"
    migrated = WorkerSpec.model_validate(raw)
    assert migrated.llm.activation == "always"

    raw["llm"]["activation"] = "manual"
    migrated = WorkerSpec.model_validate(raw)
    assert migrated.llm.activation == "always"
