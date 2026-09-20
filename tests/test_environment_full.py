from __future__ import annotations

from pathlib import Path

import pytest

import hive_connectome.environment as environment
from hive_connectome.db import HiveDB
from hive_connectome.environment import EnvironmentModeError, EnvironmentNotImplemented, WorkerEnvironmentRunner
from hive_connectome.schemas import EventEnvelope
from hive_connectome.workers import WorkerStore


class FakePipeline:
    def __init__(self):
        self.requests = []
    async def run(self, req):
        self.requests.append(req)
        class Result:
            def model_dump(self, mode=None):
                return {"event": req.event.model_dump(mode="json"), "worker_id": req.worker_id}
        return Result()


def _runner(tmp_path: Path):
    db = HiveDB(tmp_path / "db.sqlite")
    defaults = Path(__file__).parents[1] / "config" / "workers.default.json"
    workers = WorkerStore(tmp_path / "workers.json", defaults)
    pipe = FakePipeline()
    inbox = tmp_path / "inbox"; inbox.mkdir()
    return WorkerEnvironmentRunner(db, workers, pipe, inbox), db, workers, pipe, inbox


@pytest.mark.asyncio
async def test_manual_and_not_implemented_modes(tmp_path):
    runner, db, workers, pipe, inbox = _runner(tmp_path)
    with pytest.raises(EnvironmentModeError):
        await runner.run("scout")
    browser = workers.get("browser")
    with pytest.raises(EnvironmentNotImplemented, match="browser"):
        await runner.run(browser.id)
    browser.data_environment.mode = "simulation"
    workers.save(browser)
    with pytest.raises(EnvironmentNotImplemented, match="simulation"):
        await runner.run(browser.id)
    db.close()


@pytest.mark.asyncio
async def test_source_ids_and_file_drop(tmp_path, monkeypatch):
    runner, db, workers, pipe, inbox = _runner(tmp_path)
    db.upsert_source({
        "id":"feed","name":"Feed","kind":"http_json","url":"https://example.test",
        "method":"GET","body":None,"interval_seconds":60,"enabled":False,"auto_process":True,
    })
    stream = workers.get("stream")
    stream.data_environment.source_ids = ["feed", "missing"]
    workers.save(stream)

    async def fake_poll(spec, inbox_root):
        return [EventEnvelope(source_id=spec.id, kind="test", payload={"ok":True})]
    monkeypatch.setattr(environment, "poll_source", fake_poll)
    result = await runner.run("stream")
    assert any(x.get("source_id") == "missing" for x in result["results"])
    assert len(pipe.requests) == 1

    scout = workers.get("scout")
    scout.data_environment.mode = "file_drop"
    scout.data_environment.file_path = str(inbox)
    workers.save(scout)
    (inbox / "note.md").write_text("hello", encoding="utf-8")
    monkeypatch.undo()
    file_result = await runner.run("scout")
    assert len(file_result["results"]) == 1
    db.close()
