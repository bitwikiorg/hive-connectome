from __future__ import annotations

import json
from pathlib import Path

import pytest

from connectome_fixtures import install_runtime_fixtures, write_malecns_full_fixture
from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import (
    DecisionBundle,
    EventEnvelope,
    LLMResult,
    PipelineRequest,
)
from hive_connectome.workers import WorkerStore


ROOT = Path(__file__).parents[1]


def _workers(tmp_path: Path) -> WorkerStore:
    install_runtime_fixtures(tmp_path)
    return WorkerStore(
        tmp_path / "workers.json",
        ROOT / "config" / "workers.default.json",
    )


class GoodLLM:
    async def chat(self, model, prompt, context, temperature=0.2):
        return LLMResult(
            provider="lmstudio",
            model=model,
            text=json.dumps({
                "answer": "yes",
                "analysis": "supported",
                "confidence": 0.8,
                "evidence_refs": ["state"],
                "unresolved": [],
                "neural_feedback": 0.0,
            }),
            transport={
                "call_id": "llm-good",
                "provider": "lmstudio",
                "capability": "chat",
                "endpoint": "http://test/chat",
                "requested_model": model,
                "returned_model": model,
                "request_hash": "request",
                "response_hash": "response",
            },
        )


class BadLLM:
    async def chat(self, model, prompt, context, temperature=0.2):
        return LLMResult(
            provider="lmstudio",
            model=model,
            text="not-json",
        )


class BadJEV:
    async def decide(self, state, questions, model=None):
        return DecisionBundle(
            provider="venice",
            model=model or "jev-latest",
            answers={
                "meaningful_signal": {"type": "noul", "noul": 0.8},
                "novelty": {"type": "score", "score": 1.0},
                # route and llm_needed deliberately absent
            },
        )


@pytest.mark.asyncio
async def test_harness_passes_and_feedback_are_independent(tmp_path: Path):
    workers = _workers(tmp_path)
    db = HiveDB(tmp_path / "hive.db")
    pipeline = HivePipeline(db, workers, data_dir=tmp_path)

    out = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=False,
        llm_enabled=False,
        harness_passes=1,
        feedback_enabled=False,
        event=EventEnvelope(payload={"x": 1}),
    ))

    assert out.execution["integration"]["harness_passes"] == 1
    assert len(out.execution["integration"]["trace"]) == 1
    feedback = next(
        item
        for item in out.execution["integration"]["trace"][0]["components"]
        if item["type"] == "feedback"
    )
    assert feedback["called"] is False
    assert feedback["reason"] == "experiment_feedback_disabled"
    db.close()


@pytest.mark.asyncio
async def test_bridge_strategy_overrides_are_first_class_controls(tmp_path: Path):
    workers = _workers(tmp_path)
    db = HiveDB(tmp_path / "hive.db")
    pipeline = HivePipeline(db, workers, data_dir=tmp_path)

    zero = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=False,
        llm_enabled=False,
        harness_passes=1,
        bridge_engines={"worm-to-fly": "zero_bridge_v1"},
        event=EventEnvelope(payload={"x": 2}),
    ))
    zero_bridge = zero.execution["bridges"][0]
    assert zero_bridge["engine"] == "zero_bridge_v1"
    assert zero_bridge["source_values_used"] == len(zero.worm.state_vector)
    assert zero_bridge["stimulus_count"] == 0

    pipeline.reset("scout")
    random_control = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=False,
        llm_enabled=False,
        harness_passes=1,
        bridge_engines={"worm-to-fly": "random_projection_v1"},
        event=EventEnvelope(payload={"x": 2}),
    ))
    random_bridge = random_control.execution["bridges"][0]
    assert random_bridge["engine"] == "random_projection_v1"
    assert random_bridge["source_values_used"] == len(random_control.worm.state_vector)
    assert random_bridge["stimulus_count"] > 0
    db.close()


@pytest.mark.asyncio
async def test_llm_emits_common_task_result_and_context_artifact(tmp_path: Path):
    workers = _workers(tmp_path)
    scout = workers.get("scout")
    scout.llm.enabled = True
    scout.llm.model = "test-model"
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    pipeline = HivePipeline(
        db,
        workers,
        lmstudio=GoodLLM(),
        default_llm_model="test-model",
        data_dir=tmp_path,
    )
    out = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=False,
        llm_enabled=True,
        harness_passes=1,
        architecture=["worm", "readout", "llm"],
        event=EventEnvelope(payload={"question": "yes?"}),
    ))

    assert out.task_result.valid is True
    assert out.task_result.answer == "yes"
    assert out.task_result.confidence == pytest.approx(0.8)
    assert out.task_result.evidence_refs == ["state"]

    llm_component = next(
        item
        for item in out.execution["integration"]["trace"][0]["components"]
        if item["type"] == "llm"
    )
    artifact = tmp_path / llm_component["context_artifact"]
    assert artifact.exists()
    assert llm_component["context_hash"]
    db.close()


@pytest.mark.asyncio
async def test_malformed_llm_output_is_not_silent_zero_feedback(tmp_path: Path):
    workers = _workers(tmp_path)
    scout = workers.get("scout")
    scout.llm.enabled = True
    scout.llm.model = "test-model"
    workers.save(scout)

    db = HiveDB(tmp_path / "hive.db")
    pipeline = HivePipeline(
        db,
        workers,
        lmstudio=BadLLM(),
        default_llm_model="test-model",
        data_dir=tmp_path,
    )
    out = await pipeline.run(PipelineRequest(
        worker_id="scout",
        jev_enabled=False,
        llm_enabled=True,
        harness_passes=1,
        architecture=["worm", "readout", "llm", "feedback"],
        event=EventEnvelope(payload={"x": 3}),
    ))

    assert out.task_result.valid is False
    assert out.execution["llm"]["neural_feedback"] is None
    feedback = next(
        item
        for item in out.execution["integration"]["trace"][0]["components"]
        if item["type"] == "feedback"
    )
    assert feedback["sources"] == {}
    db.close()


@pytest.mark.asyncio
async def test_malformed_jev_bundle_fails_experiment(tmp_path: Path):
    workers = _workers(tmp_path)
    db = HiveDB(tmp_path / "hive.db")
    pipeline = HivePipeline(db, workers, venice=BadJEV(), data_dir=tmp_path)

    with pytest.raises(RuntimeError, match="JEV response missing structured answer"):
        await pipeline.run(PipelineRequest(
            worker_id="scout",
            jev_enabled=True,
            llm_enabled=False,
            harness_passes=1,
            architecture=["worm", "readout", "jev"],
            event=EventEnvelope(payload={"x": 4}),
        ))
    db.close()


@pytest.mark.asyncio
async def test_full_recordings_are_unique_per_harness_pass_and_primary_is_receipted(tmp_path: Path):
    install_runtime_fixtures(tmp_path)
    write_malecns_full_fixture(tmp_path)
    workers = WorkerStore(
        tmp_path / "workers.json",
        ROOT / "config" / "workers.default.json",
    )
    primary = workers.get("primary-full")
    primary.outputs.recording_level = "full"
    primary.jev.enabled = False
    primary.llm.enabled = False
    primary.runtime.harness_passes = 2
    fly_stage = next(stage for stage in primary.brain_chain if stage.id == "fly")
    fly_stage.config.update({
        "expected_neurons": 4,
        "expected_directed_connections": 4,
        "expected_synapses": 26,
        "substeps": 3,
        "sample_size": 4,
    })
    workers.save(primary)

    db = HiveDB(tmp_path / "hive.db")
    pipeline = HivePipeline(db, workers, data_dir=tmp_path)
    out = await pipeline.run(PipelineRequest(
        worker_id="primary-full",
        jev_enabled=False,
        llm_enabled=False,
        mode="offline",
        event=EventEnvelope(payload={"signal": "fixture"}),
    ))

    fly_artifacts = []
    for cycle in out.execution["integration"]["trace"]:
        for component in cycle["components"]:
            if component.get("type") == "neural_stage" and component.get("tag") == "fly":
                fly_artifacts.append(component.get("recording_artifact"))
    assert len(fly_artifacts) == 2
    assert len(set(fly_artifacts)) == 2
    assert all((tmp_path / relative).exists() for relative in fly_artifacts)

    primary_receipt = out.execution.get("primary_execution_receipt")
    assert primary_receipt
    receipt = json.loads((tmp_path / primary_receipt).read_text())
    assert receipt["end_to_end"] is True
    assert receipt["run_id"] == out.run_id
    assert receipt["bridges"][0]["source_values_used"] == len(out.worm.state_vector)
    db.close()
