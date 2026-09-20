from __future__ import annotations

import pytest

import hive_connectome.app as app_module


def test_health_root_templates_and_seeded_sources(client, test_settings):
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["ok"] is True
    assert body["version"] == "0.4.0"
    assert {"scout", "browser", "stream"}.issubset(body["workers"])

    root = client.get("/")
    assert root.status_code == 200
    assert "What do you want HIVE to do?" in root.text

    templates = client.get("/api/experiment-templates").json()["templates"]
    assert {x["id"] for x in templates} >= {"manual_classifier", "browser_dom_reader", "stream_watch"}

    sources = client.get("/api/sources").json()
    inbox = next(x for x in sources if x["id"] == "local-inbox")
    assert inbox["path"] == str(test_settings.data_dir / "inbox")


def test_worker_crud_clone_and_validation(client):
    workers = client.get("/api/workers").json()
    scout = next(w for w in workers if w["id"] == "scout")
    assert client.get("/api/workers/missing").status_code == 404
    scout["experiment"]["task_prompt"] = "updated prompt"
    assert client.put("/api/workers/wrong", json=scout).status_code == 400
    saved = client.put("/api/workers/scout", json=scout)
    assert saved.status_code == 200
    assert saved.json()["experiment"]["task_prompt"] == "updated prompt"
    clone = client.post("/api/workers/scout/clone", params={"new_id": "scout-copy", "name": "Scout Copy"})
    assert clone.status_code == 200
    assert clone.json()["id"] == "scout-copy"
    assert client.post("/api/workers/scout/clone", params={"new_id": "scout-copy"}).status_code == 409
    assert client.post("/api/workers/missing/clone", params={"new_id": "x"}).status_code == 404
    assert client.delete("/api/workers/scout-copy").status_code == 200
    assert client.delete("/api/workers/scout-copy").status_code == 404


def test_create_from_template(client):
    r = client.post("/api/workers/from-template/browser_dom_reader", params={"worker_id": "reader", "name": "Reader"})
    assert r.status_code == 200
    body = r.json()
    assert body["data_environment"]["mode"] == "browser_dom"
    assert body["jev"]["enabled"] is True
    assert body["llm"]["enabled"] is True
    assert body["larva"]["substrate"] == "c_elegans"
    assert body["bee"]["substrate"] == "drosophila"
    assert client.post("/api/workers/from-template/browser_dom_reader", params={"worker_id": "reader"}).status_code == 409
    assert client.post("/api/workers/from-template/nope", params={"worker_id": "x"}).status_code == 404


def test_pipeline_run_reset_and_simulate(client):
    run = client.post("/api/pipeline/run", json={"worker_id": "scout", "jev_enabled": False, "llm_enabled": False, "mode": "auto", "event": {"source_id": "test", "kind": "manual", "payload": {"value": 3}}})
    assert run.status_code == 200
    body = run.json()
    assert body["decisions"]["provider"] == "brain-readout"
    assert "jev:off" in body["labels"] and "llm:off" in body["labels"]
    assert client.post("/api/pipeline/reset", params={"worker_id": "scout"}).json()["ok"] is True
    assert client.post("/api/pipeline/reset", params={"worker_id": "missing"}).status_code == 404
    assert client.post("/api/pipeline/run", json={"worker_id": "missing", "event": {"payload": {"x": 1}}}).status_code == 404
    sim = client.post("/api/simulate", params={"worker_id": "scout"}, json={"name": "two-events", "mode": "offline", "reset_brains": True, "events": [{"source_id": "sim", "kind": "sim", "payload": {"x": 1}}, {"source_id": "sim", "kind": "sim", "payload": {"x": 2}}]})
    assert sim.status_code == 200 and sim.json()["count"] == 2
    assert client.post("/api/simulate", params={"worker_id": "missing"}, json={"events": []}).status_code == 404


def test_eval_same_worker_toggle_matrix(client):
    r = client.post("/api/evals/run", json={"worker_id": "scout", "cases": [{"id": "case-1", "event": {"source_id": "eval", "kind": "eval", "payload": {"x": 7}}}]})
    assert r.status_code == 200
    body = r.json()
    assert set(body["summary"]) == {"jev_off_llm_off", "jev_on_llm_off", "jev_off_llm_on", "jev_on_llm_on"}
    assert len(body["rows"]) == 4
    assert client.post("/api/evals/run", json={"worker_id": "missing", "cases": []}).status_code == 404


def test_environment_modes(client, test_settings):
    assert client.post("/api/workers/scout/run-environment").status_code == 400
    stream = client.get("/api/workers/stream").json()
    stream["data_environment"]["source_ids"] = ["missing-source"]
    assert client.put("/api/workers/stream", json=stream).status_code == 200
    out = client.post("/api/workers/stream/run-environment")
    assert out.status_code == 200 and out.json()["results"][0]["error"] == "configured source not found"
    assert client.post("/api/workers/from-template/browser_dom_reader", params={"worker_id": "webtest"}).status_code == 200
    assert client.post("/api/workers/webtest/run-environment").status_code == 501
    file_worker = client.post("/api/workers/from-template/local_files_memory", params={"worker_id": "files"}).json()
    file_worker["data_environment"]["file_path"] = str(test_settings.data_dir / "inbox")
    client.put("/api/workers/files", json=file_worker)
    inbox = test_settings.data_dir / "inbox"
    (inbox / "note.json").write_text('{"project":"hive","state":"testing"}', encoding="utf-8")
    file_run = client.post("/api/workers/files/run-environment")
    assert file_run.status_code == 200 and len(file_run.json()["results"]) == 1


def test_environment_missing_worker_and_source_poll_error(client, monkeypatch):
    assert client.post("/api/workers/missing/run-environment").status_code == 404
    spec = {"id": "remote", "name": "remote", "kind": "http_json", "url": "https://example.test/api", "enabled": False}
    assert client.post("/api/sources", json=spec).status_code == 200
    async def boom(*args, **kwargs):
        raise ValueError("blocked")
    monkeypatch.setattr(app_module, "poll_source", boom)
    response = client.post("/api/sources/remote/poll")
    assert response.status_code == 400 and "blocked" in response.text


def test_sources_events_and_poll(client, test_settings):
    inbox = test_settings.data_dir / "inbox"
    (inbox / "a.md").write_text("hello hive", encoding="utf-8")
    spec = {"id": "test-files", "name": "Test files", "kind": "file_drop", "path": str(inbox), "interval_seconds": 10, "enabled": False, "auto_process": False}
    assert client.post("/api/sources", json=spec).status_code == 200
    polled = client.post("/api/sources/test-files/poll")
    assert polled.status_code == 200 and any(x["subject"] == "a.md" for x in polled.json())
    assert client.post("/api/sources/missing/poll").status_code == 404
    assert isinstance(client.get("/api/events", params={"limit": 5}).json(), list)
    assert client.get("/api/events", params={"limit": 0}).status_code == 422


def test_connectome_guardrails(client):
    packs = client.get("/api/connectomes")
    assert packs.status_code == 200 and any(x["id"] == "fly-malecns-v1" for x in packs.json())
    assert client.post("/api/connectomes/missing/install").status_code == 404
    assert client.post("/api/connectomes/fly-larval-mushroom-body/install").status_code == 400
    assert client.post("/api/connectomes/fly-malecns-v1/install").status_code == 409
    assert client.get("/api/connectomes/fly-malecns-v1/job").json()["status"] == "idle"


def test_connectome_install_queue_and_running_job(client, app, monkeypatch):
    installer = app.state.installer
    original_get = installer.get_pack
    monkeypatch.setattr(installer, "get_pack", lambda pack_id: {"id": pack_id, "installable": True, "files": []})
    async def fake_install(pack_id): return {"pack_id": pack_id, "files": []}
    monkeypatch.setattr(installer, "install", fake_install)
    response = client.post("/api/connectomes/tiny/install")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert client.get("/api/connectomes/tiny/job").json()["status"] in {"complete", "running"}
    monkeypatch.setattr(installer, "get_pack", original_get)


def test_provider_status_handles_unreachable_local_model(client):
    body = client.get("/api/providers/status").json()
    assert body["venice"]["configured"] is False
    assert body["lmstudio"]["ok"] is False and "error" in body["lmstudio"]


def test_provider_status_with_configured_venice(test_settings, monkeypatch):
    from fastapi.testclient import TestClient
    from hive_connectome.app import create_app
    from hive_connectome.providers import venice as venice_module
    configured = type(test_settings)(**{**test_settings.__dict__, "venice_api_key": "secret"})
    async def fake_models(self): return {"data": [{"id": "jev-latest"}]}
    monkeypatch.setattr(venice_module.VeniceJev, "list_models", fake_models)
    app = create_app(configured, start_heartbeat=False)
    with TestClient(app) as local_client:
        body = local_client.get("/api/providers/status").json()
        assert body["venice"]["configured"] is True and body["venice"]["ok"] is True


def test_tasks_valid_invalid_and_missing_dependency(client, monkeypatch):
    task = {"id": "tick", "name": "Tick", "cron": "*/5 * * * *", "action": "emit_event", "payload": {"x": 1}}
    monkeypatch.setattr(app_module, "validate_cron", lambda expr: False)
    assert client.post("/api/tasks", json=task).status_code == 400
    monkeypatch.setattr(app_module, "validate_cron", lambda expr: True)
    assert client.post("/api/tasks", json=task).status_code == 200
    assert client.get("/api/tasks").json()[0]["id"] == "tick"
    def unavailable(expr): raise RuntimeError("cron missing")
    monkeypatch.setattr(app_module, "validate_cron", unavailable)
    task["id"] = "tick2"
    assert client.post("/api/tasks", json=task).status_code == 503


def test_pipeline_errors_are_502(client, app, monkeypatch):
    async def broken(req): raise RuntimeError("provider exploded")
    monkeypatch.setattr(app.state.pipeline, "run", broken)
    response = client.post("/api/pipeline/run", json={"worker_id": "scout", "event": {"payload": {"x": 1}}})
    assert response.status_code == 502 and "provider exploded" in response.text