from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

import hive_connectome.app as app_module


def test_health_root_templates_and_seeded_sources(client, test_settings):
    health = client.get("/api/health")
    assert health.status_code == 200
    body = health.json()
    assert body["ok"] is True
    assert body["version"] == "0.7.0"
    assert body["neural_runtime"]["primary_experiment_ready"] is False
    assert body["neural_runtime"]["study_mode"] == "CONTROL_ONLY"
    assert body["neural_runtime"]["control_runtime"]["ready"] is True
    assert any("full MaleCNS" in x for x in body["neural_runtime"]["primary"]["blockers"])
    assert "primary-full" in body["workers"]
    assert {"scout", "browser", "stream"}.issubset(body["workers"])

    root = client.get("/")
    assert root.status_code == 200
    assert "HIVE EXPERIMENT LAB" in root.text
    assert "See exactly what happened" in root.text

    templates = client.get("/api/experiment-templates").json()["templates"]
    assert {x["id"] for x in templates} >= {"manual_classifier", "browser_dom_reader", "stream_watch"}

    sources = client.get("/api/sources").json()
    inbox = next(x for x in sources if x["id"] == "local-inbox")
    assert inbox["path"] == str(test_settings.data_dir / "inbox")


def test_experiment_plan_exposes_backend_resolved_execution_path(client):
    plan = client.get("/api/experiments/primary-full/plan")
    assert plan.status_code == 200
    body = plan.json()
    assert body["core_id"] == "primary-full"
    assert body["is_primary_topology"] is True
    assert [stage["id"] for stage in body["stages"]] == ["worm", "fly"]
    assert body["stages"][0]["engine_label"] == "Cook full C. elegans"
    assert body["stages"][1]["engine_label"] == "Full MaleCNS v1.0"
    assert body["bridges"][0]["label"] == "Neural state projection"
    assert body["sequence"][0]["type"] == "input"
    assert body["sequence"][-1]["type"] == "output"
    assert client.get("/api/experiments/missing/plan").status_code == 404


def test_worker_crud_clone_and_validation(client):
    workers = client.get("/api/workers").json()
    scout = next(w for w in workers if w["id"] == "scout")

    assert client.get("/api/workers/missing").status_code == 404

    scout["experiment"]["task_prompt"] = "updated prompt"
    bad = client.put("/api/workers/wrong", json=scout)
    assert bad.status_code == 400

    saved = client.put("/api/workers/scout", json=scout)
    assert saved.status_code == 200
    assert saved.json()["experiment"]["task_prompt"] == "updated prompt"

    clone = client.post("/api/workers/scout/clone", params={"new_id": "scout-copy", "name": "Scout Copy"})
    assert clone.status_code == 200
    assert clone.json()["id"] == "scout-copy"
    assert client.post("/api/workers/scout/clone", params={"new_id": "scout-copy"}).status_code == 409
    assert client.post("/api/workers/missing/clone", params={"new_id": "x"}).status_code == 404

    deleted = client.delete("/api/workers/scout-copy")
    assert deleted.status_code == 200
    assert client.delete("/api/workers/scout-copy").status_code == 404


def test_create_from_template(client):
    r = client.post(
        "/api/workers/from-template/browser_dom_reader",
        params={"worker_id": "reader", "name": "Reader"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data_environment"]["mode"] == "browser_dom"
    assert body["jev"]["enabled"] is True
    assert body["llm"]["enabled"] is True
    assert body["larva"]["engine"] == "cook2019_connectome"
    assert body["bee"]["engine"] == "malecns_locomotor"
    assert body["bee"]["substrate"] == "drosophila_malecns_v1_locomotor"
    assert client.post("/api/workers/from-template/browser_dom_reader", params={"worker_id": "reader"}).status_code == 409
    assert client.post("/api/workers/from-template/nope", params={"worker_id": "x"}).status_code == 404


def test_pipeline_run_reset_and_simulate(client):
    run = client.post(
        "/api/pipeline/run",
        json={
            "worker_id": "scout",
            "jev_enabled": False,
            "llm_enabled": False,
            "mode": "auto",
            "event": {"source_id": "test", "kind": "manual", "payload": {"value": 3}},
        },
    )
    assert run.status_code == 200
    body = run.json()
    assert body["decisions"]["provider"] == "brain-readout"
    assert "jev:off" in body["labels"]
    assert "llm:off" in body["labels"]

    assert client.post("/api/pipeline/reset", params={"worker_id": "scout"}).json()["ok"] is True
    assert client.post("/api/pipeline/reset", params={"worker_id": "missing"}).status_code == 404
    assert client.post("/api/pipeline/run", json={
        "worker_id": "missing",
        "event": {"payload": {"x": 1}},
    }).status_code == 404

    sim = client.post(
        "/api/simulate",
        params={"worker_id": "scout"},
        json={
            "name": "two-events",
            "mode": "offline",
            "reset_brains": True,
            "events": [
                {"source_id": "sim", "kind": "sim", "payload": {"x": 1}},
                {"source_id": "sim", "kind": "sim", "payload": {"x": 2}},
            ],
        },
    )
    assert sim.status_code == 200
    assert sim.json()["count"] == 2
    assert client.post("/api/simulate", params={"worker_id": "missing"}, json={"events": []}).status_code == 404


def test_eval_same_worker_toggle_matrix(client):
    r = client.post(
        "/api/evals/run",
        json={
            "worker_id": "scout",
            "cases": [{
                "id": "case-1",
                "event": {"source_id": "eval", "kind": "eval", "payload": {"x": 7}},
            }],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert set(body["summary"]) == {
        "jev_off_llm_off",
        "jev_on_llm_off",
        "jev_off_llm_on",
        "jev_on_llm_on",
    }
    assert len(body["rows"]) == 4
    assert client.post("/api/evals/run", json={"worker_id": "missing", "cases": []}).status_code == 404


def test_environment_modes(client, app, test_settings):
    assert client.post("/api/workers/scout/run-environment").status_code == 400

    stream = client.get("/api/workers/stream").json()
    stream["data_environment"]["source_ids"] = ["missing-source"]
    assert client.put("/api/workers/stream", json=stream).status_code == 200
    out = client.post("/api/workers/stream/run-environment")
    assert out.status_code == 200
    assert out.json()["results"][0]["error"] == "configured source not found"

    browser = client.post(
        "/api/workers/from-template/browser_dom_reader",
        params={"worker_id": "webtest"},
    ).json()
    assert client.post("/api/workers/webtest/run-environment").status_code == 501

    file_worker = client.post(
        "/api/workers/from-template/local_files_memory",
        params={"worker_id": "files"},
    ).json()
    file_worker["data_environment"]["file_path"] = str(test_settings.data_dir / "inbox")
    file_worker["jev"]["enabled"] = False
    file_worker["llm"]["enabled"] = False
    client.put("/api/workers/files", json=file_worker)
    inbox = test_settings.data_dir / "inbox"
    (inbox / "note.json").write_text('{"project":"hive","state":"testing"}', encoding="utf-8")
    file_run = client.post("/api/workers/files/run-environment")
    assert file_run.status_code == 200
    assert len(file_run.json()["results"]) == 1


def test_sources_events_and_poll(client, test_settings):
    inbox = test_settings.data_dir / "inbox"
    (inbox / "a.md").write_text("hello hive", encoding="utf-8")
    spec = {
        "id": "test-files",
        "name": "Test files",
        "kind": "file_drop",
        "path": str(inbox),
        "interval_seconds": 10,
        "enabled": False,
        "auto_process": False,
    }
    assert client.post("/api/sources", json=spec).status_code == 200
    polled = client.post("/api/sources/test-files/poll")
    assert polled.status_code == 200
    assert any(x["subject"] == "a.md" for x in polled.json())
    assert client.post("/api/sources/missing/poll").status_code == 404

    assert isinstance(client.get("/api/events", params={"limit": 5}).json(), list)
    assert client.get("/api/events", params={"limit": 0}).status_code == 422


def test_connectome_guardrails(client):
    packs = client.get("/api/connectomes")
    assert packs.status_code == 200
    assert any(x["id"] == "fly-malecns-v1" for x in packs.json())
    assert client.post("/api/connectomes/missing/install").status_code == 404
    assert client.post("/api/connectomes/fly-larval-mushroom-body/install").status_code == 400
    assert client.post("/api/connectomes/fly-malecns-v1/install").status_code == 409
    assert client.get("/api/connectomes/fly-malecns-v1/job").json()["status"] == "idle"


def test_provider_status_handles_unreachable_local_model(client):
    body = client.get("/api/providers/status").json()
    assert body["venice"]["configured"] is False
    assert body["lmstudio"]["ok"] is False
    assert "error" in body["lmstudio"]


def test_tasks_valid_invalid_and_missing_dependency(client, monkeypatch):
    task = {"id": "tick", "name": "Tick", "cron": "*/5 * * * *", "action": "emit_event", "payload": {"x": 1}}

    monkeypatch.setattr(app_module, "validate_cron", lambda expr: False)
    assert client.post("/api/tasks", json=task).status_code == 400

    monkeypatch.setattr(app_module, "validate_cron", lambda expr: True)
    good = client.post("/api/tasks", json=task)
    assert good.status_code == 200
    assert client.get("/api/tasks").json()[0]["id"] == "tick"

    def unavailable(expr):
        raise RuntimeError("cron missing")
    monkeypatch.setattr(app_module, "validate_cron", unavailable)
    task["id"] = "tick2"
    assert client.post("/api/tasks", json=task).status_code == 503


def test_core_graph_can_remove_stages_and_bridge_is_explicit(client):
    scout=client.get("/api/workers/scout").json()
    assert [stage["id"] for stage in scout["brain_chain"]] == ["worm","fly"]
    assert scout["bridges"][0]["engine"] == "state_projection_v1"

    run=client.post("/api/pipeline/run",json={
        "worker_id":"scout","jev_enabled":False,"llm_enabled":False,"mode":"offline",
        "event":{"source_id":"test","kind":"manual","payload":{"x":3}},
    }).json()
    assert set(run["stages"]) == {"worm","fly"}
    assert run["execution"]["bridges"][0]["source"] == "worm"
    assert run["execution"]["bridges"][0]["target"] == "fly"
    assert run["execution"]["bridges"][0]["engine"] == "state_projection_v1"
    assert run["execution"]["bee"]["metadata"]["input_encoding"] == "explicit bridge stimulus"

    scout["brain_chain"][0]["enabled"]=False
    assert client.put("/api/workers/scout",json=scout).status_code == 200
    run=client.post("/api/pipeline/run",json={
        "worker_id":"scout","jev_enabled":False,"llm_enabled":False,"mode":"offline",
        "event":{"source_id":"test","kind":"manual","payload":{"x":4}},
    }).json()
    assert set(run["stages"]) == {"fly"}
    assert run["worm"] is None
    assert run["fly"] is not None
    assert run["execution"]["bridges"] == []


def test_hive_chain_and_experiment_export(client):
    chain=client.post("/api/hive/run",json={
        "core_ids":["scout","auditor"],
        "mode":"offline",
        "jev_enabled":False,
        "llm_enabled":False,
        "event":{"source_id":"test","kind":"manual","payload":{"signal":"x"}},
    })
    assert chain.status_code == 200
    body=chain.json()
    assert body["count"] == 2
    assert body["results"][1]["event"]["kind"] == "core_handoff"
    assert body["results"][1]["event"]["provenance"]["parent_run_id"] == body["results"][0]["run_id"]

    runs=client.get("/api/runs").json()
    assert len(runs) >= 2
    detail=client.get(f"/api/runs/{body['results'][0]['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["execution"]["resolved_worker"]["id"] == "scout"

    exported=client.get("/api/exports/experiment",params={"worker_id":"scout"})
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(exported.content)) as zf:
        names=set(zf.namelist())
        assert {"manifest.json","runs.jsonl","events.jsonl","provider_calls.jsonl","cores.json","runs.csv"}.issubset(names)
        manifest=json.loads(zf.read("manifest.json"))
        assert manifest["format"] == "hive-experiment-bundle"
        assert manifest["counts"]["runs"] >= 1


def test_provider_config_is_live_persistent_and_secrets_are_write_only(client, app, test_settings):
    initial=client.get("/api/providers/config")
    assert initial.status_code==200
    assert "venice_api_key" not in initial.json()
    saved=client.put("/api/providers/config",json={
        "venice_base_url":"https://api.venice.test/api/v1",
        "venice_decision_model":"jev-latest",
        "venice_api_key":"secret-venice",
        "lmstudio_base_url":"http://lm.test/v1",
        "lmstudio_api_token":"secret-local",
        "default_llm_model":"tiny",
    })
    assert saved.status_code==200
    body=saved.json()
    assert body["venice_api_key_configured"] is True
    assert body["lmstudio_api_token_configured"] is True
    assert "secret-venice" not in json.dumps(body)
    public=json.loads((test_settings.data_dir/"providers.json").read_text())
    assert "venice_api_key" not in public and public["lmstudio_base_url"]=="http://lm.test/v1"
    assert (test_settings.data_dir/"provider-secrets"/"venice_api_key").read_text()=="secret-venice"
    assert app.state.pipeline.venice is not None
    assert app.state.pipeline.default_llm_model=="tiny"


def test_provider_real_call_endpoint_returns_transport_receipt(client, app):
    from hive_connectome.schemas import DecisionBundle, LLMResult

    class FakeJev:
        async def decide(self,state,questions,model=None):
            return DecisionBundle(
                provider="venice",model=model or "jev-latest",
                answers={"reachable":{"type":"noul","noul":1.0}},
                transport={"call_id":"jev-proof","provider":"venice","capability":"decisions","endpoint":"https://test/decisions","requested_model":model or "jev-latest","returned_model":model or "jev-latest","latency_ms":1.2,"http_status":200,"request_hash":"a","response_hash":"b"},
            )
    class FakeChat:
        async def chat(self,model,prompt,context,temperature=0.0):
            return LLMResult(
                provider="venice",model=model,text="HIVE_PROVIDER_OK",
                transport={"call_id":"chat-proof","provider":"venice","capability":"chat","endpoint":"https://test/chat/completions","requested_model":model,"returned_model":model,"latency_ms":2.0,"http_status":200,"request_hash":"c","response_hash":"d"},
            )

    app.state.pipeline.venice=FakeJev()
    app.state.pipeline.venice_chat=FakeChat()
    jev=client.post("/api/providers/test",json={"capability":"venice_jev","model":"jev-latest"})
    assert jev.status_code==200
    assert jev.json()["transport"]["call_id"]=="jev-proof"
    chat=client.post("/api/providers/test",json={"capability":"venice_chat","model":"tiny-chat"})
    assert chat.status_code==200
    assert chat.json()["transport"]["call_id"]=="chat-proof"
    calls=client.get("/api/provider-calls").json()
    assert {"jev-proof","chat-proof"}.issubset({row["call_id"] for row in calls})
