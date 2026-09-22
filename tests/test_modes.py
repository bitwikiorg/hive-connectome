import pytest
from pathlib import Path

from hive_connectome.db import HiveDB
from hive_connectome.pipeline import HivePipeline
from hive_connectome.schemas import DecisionBundle, EventEnvelope, LLMResult, PipelineRequest
from hive_connectome.workers import WorkerStore
from connectome_fixtures import install_runtime_fixtures


class FakeJev:
    async def decide(self, state, questions, model=None):
        answers = {
            "meaningful_signal": {"type":"noul","noul":0.8},
            "novelty": {"type":"score","score":1.0,"confidence":0.9},
            "route": {"type":"choice","choice":"store","confidence":0.9},
            "llm_needed": {"type":"noul","noul":0.1},
        }
        if list(questions) == ["supported"]:
            answers = {"supported":{"type":"noul","noul":0.9}}
        return DecisionBundle(provider="venice",model="fake-jev",answers=answers,confidence=0.9)


class FakeLLM:
    def __init__(self):
        self.calls = 0
    async def chat(self, model, prompt, context, temperature=0.2):
        self.calls += 1
        return LLMResult(provider="lmstudio",model=model,text='{"analysis":"ok","unresolved":[],"neural_feedback":0.4}')


def make(tmp_path):
    install_runtime_fixtures(tmp_path)
    db=HiveDB(tmp_path/"hive.db")
    workers=WorkerStore(tmp_path/"workers.json",Path(__file__).parents[1]/"config"/"workers.default.json")
    lm=FakeLLM()
    return HivePipeline(db,workers,venice=FakeJev(),lmstudio=lm,default_llm_model="tiny"),lm


@pytest.mark.asyncio
async def test_brain_only_calls_neither(tmp_path):
    p,lm=make(tmp_path)
    out=await p.run(PipelineRequest(
        worker_id="scout",jev_enabled=False,llm_enabled=False,
        event=EventEnvelope(payload={"x":1})
    ))
    assert out.decisions.provider=="brain-readout"
    assert out.llm is None
    assert lm.calls==0
    p.db.close()


@pytest.mark.asyncio
async def test_brain_llm_calls_llm_without_jev(tmp_path):
    p,lm=make(tmp_path)
    out=await p.run(PipelineRequest(
        worker_id="scout",jev_enabled=False,llm_enabled=True,
        event=EventEnvelope(payload={"x":1})
    ))
    assert out.decisions.provider=="brain-readout"
    assert out.llm is not None
    assert lm.calls==2
    assert out.execution["integration"]["harness_passes"]==2
    p.db.close()


@pytest.mark.asyncio
async def test_brain_jev_does_not_call_llm(tmp_path):
    p,lm=make(tmp_path)
    out=await p.run(PipelineRequest(
        worker_id="scout",jev_enabled=True,llm_enabled=False,
        event=EventEnvelope(payload={"x":1})
    ))
    assert out.decisions.provider=="venice"
    assert out.llm is None
    assert lm.calls==0
    p.db.close()


@pytest.mark.asyncio
async def test_jev_and_llm_execute_together(tmp_path):
    p,lm=make(tmp_path)
    out=await p.run(PipelineRequest(
        worker_id="scout",jev_enabled=True,llm_enabled=True,
        event=EventEnvelope(payload={"x":1})
    ))
    assert out.decisions.provider=="venice"
    assert out.llm is not None
    assert lm.calls==2
    assert out.execution["integration"]["harness_passes"]==2
    assert all(item["jev_called"] and item["llm_called"] for item in out.execution["integration"]["trace"])
    p.db.close()

class FakeVeniceChat:
    def __init__(self):
        self.calls=[]
    async def chat(self, model, prompt, context, temperature=0.2):
        self.calls.append((model,prompt,temperature))
        return LLMResult(provider="venice",model=model,text='{"analysis":"venice-ok","unresolved":[],"neural_feedback":0.2}')


@pytest.mark.asyncio
async def test_venice_llm_provider_and_worker_temperature(tmp_path):
    install_runtime_fixtures(tmp_path)
    db=HiveDB(tmp_path/"hive.db")
    workers=WorkerStore(tmp_path/"workers.json",Path(__file__).parents[1]/"config"/"workers.default.json")
    scout=workers.get("scout")
    scout.llm.provider="venice"
    scout.llm.model="chat-model"
    scout.llm.temperature=0.6
    workers.save(scout)
    vc=FakeVeniceChat()
    p=HivePipeline(db,workers,venice_chat=vc)
    out=await p.run(PipelineRequest(worker_id="scout",jev_enabled=False,llm_enabled=True,event=EventEnvelope(payload={"x":1})))
    assert out.llm.provider == "venice"
    assert vc.calls[0][0] == "chat-model"
    assert vc.calls[0][2] == 0.6
    db.close()


@pytest.mark.asyncio
async def test_nonpersistent_brain_state_resets_and_labels_can_be_disabled(tmp_path):
    install_runtime_fixtures(tmp_path)
    db=HiveDB(tmp_path/"hive.db")
    workers=WorkerStore(tmp_path/"workers.json",Path(__file__).parents[1]/"config"/"workers.default.json")
    scout=workers.get("scout")
    scout.runtime.persist_brain_state=False
    scout.outputs.write_labels=False
    workers.save(scout)
    p=HivePipeline(db,workers)
    a=await p.run(PipelineRequest(worker_id="scout",jev_enabled=False,llm_enabled=False,event=EventEnvelope(payload={"x":1})))
    b=await p.run(PipelineRequest(worker_id="scout",jev_enabled=False,llm_enabled=False,event=EventEnvelope(payload={"x":1})))
    assert a.worm.step == 2 and b.worm.step == 2
    assert a.labels == [] and b.labels == []
    db.close()

@pytest.mark.asyncio
async def test_jev_requested_without_venice_never_silently_falls_back(tmp_path):
    install_runtime_fixtures(tmp_path)
    db = HiveDB(tmp_path / "hive.db")
    workers = WorkerStore(
        tmp_path / "workers.json",
        Path(__file__).parents[1] / "config" / "workers.default.json",
    )
    pipeline = HivePipeline(db, workers, venice=None)
    with pytest.raises(RuntimeError, match="will not silently substitute"):
        await pipeline.run(PipelineRequest(
            worker_id="scout",
            jev_enabled=True,
            llm_enabled=False,
            mode="auto",
            event=EventEnvelope(payload={"x": 1}),
        ))
    db.close()
