from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hive_connectome.db import HiveDB
from hive_connectome.workers import WorkerStore


def _jsonl(items: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(item, ensure_ascii=False, default=str, separators=(",", ":")) + "\n" for item in items)


def _connectome_receipts(data_dir: Path) -> list[dict[str, Any]]:
    root = data_dir / "connectomes"
    if not root.exists():
        return []
    receipts = []
    for path in sorted(root.glob("*/receipt.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["_relative_path"] = str(path.relative_to(data_dir))
            receipts.append(receipt)
        except Exception as exc:
            receipts.append({"_relative_path": str(path.relative_to(data_dir)), "_error": str(exc)})
    return receipts


def _run_csv(runs: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    fields = [
        "run_id", "event_id", "timestamp", "core_id", "route", "meaningful_signal", "novelty",
        "llm_needed", "modulation", "jev_called", "jev_model", "llm_called", "llm_provider",
        "llm_model", "stage_count", "bridge_count", "provider_call_count",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for run in runs:
        answers = run.get("decisions", {}).get("answers", {})
        execution = run.get("execution", {})
        writer.writerow({
            "run_id": run.get("run_id"),
            "event_id": run.get("event", {}).get("id"),
            "timestamp": run.get("event", {}).get("timestamp"),
            "core_id": execution.get("core_id"),
            "route": answers.get("route", {}).get("choice"),
            "meaningful_signal": answers.get("meaningful_signal", {}).get("noul"),
            "novelty": answers.get("novelty", {}).get("score"),
            "llm_needed": answers.get("llm_needed", {}).get("noul"),
            "modulation": run.get("modulation"),
            "jev_called": execution.get("jev", {}).get("called"),
            "jev_model": execution.get("jev", {}).get("model"),
            "llm_called": execution.get("llm", {}).get("called"),
            "llm_provider": execution.get("llm", {}).get("provider"),
            "llm_model": execution.get("llm", {}).get("model"),
            "stage_count": len(run.get("stages", {})),
            "bridge_count": len(execution.get("bridges", [])),
            "provider_call_count": len(execution.get("provider_call_ids", [])),
        })
    return buffer.getvalue()


def _provider_csv(calls: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    fields = [
        "call_id", "run_id", "stage_id", "provider", "capability", "endpoint", "requested_model",
        "returned_model", "started_at", "latency_ms", "http_status", "request_hash", "response_hash", "error",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for call in calls:
        writer.writerow({key: call.get(key) for key in fields})
    return buffer.getvalue()


def build_experiment_export(
    db: HiveDB,
    workers: WorkerStore,
    data_dir: Path,
    *,
    worker_id: str | None = None,
    limit: int = 5000,
) -> bytes:
    runs = db.list_runs(limit=limit, worker_id=worker_id)
    run_ids = {run.get("run_id") for run in runs}
    events_by_id: dict[str, dict[str, Any]] = {}
    for run in runs:
        event = run.get("event")
        if isinstance(event, dict) and event.get("id"):
            events_by_id[event["id"]] = event
    calls = [
        call for call in db.list_provider_calls(limit=max(limit * 8, 1000))
        if call.get("run_id") in run_ids
    ]
    selected_workers = [
        worker.model_dump(mode="json")
        for worker in workers.list()
        if worker_id is None or worker.id == worker_id
    ]
    manifest = {
        "format": "hive-experiment-bundle",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "worker_filter": worker_id,
        "limit": limit,
        "counts": {
            "runs": len(runs),
            "events": len(events_by_id),
            "provider_calls": len(calls),
            "cores": len(selected_workers),
        },
        "contents": {
            "runs.jsonl": "Lossless saved run records including stage observations, bridge traces, decisions, LLM output, and resolved Core config.",
            "events.jsonl": "Unique input events referenced by exported runs.",
            "provider_calls.jsonl": "Auditable external inference transport receipts. API keys are never exported.",
            "cores.json": "Core definitions at export time. Each run also embeds its resolved configuration.",
            "connectome_receipts.json": "Pinned dataset installation receipts available on this HIVE instance.",
            "runs.csv": "Flattened analysis convenience table; not lossless.",
            "provider_calls.csv": "Flattened provider-call convenience table.",
        },
    }

    readme = """HIVE experiment export

The JSONL files are canonical. CSV files are convenience projections and omit high-dimensional state.
A run embeds the resolved Core configuration used at execution time so later edits do not rewrite history.
Provider call receipts contain request/response hashes, models, endpoint, timing and status, but never API keys.
Connectome installation receipts prove downloaded bytes; stage execution metadata proves what engine actually ran.
"""

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("README.txt", readme)
        archive.writestr("runs.jsonl", _jsonl(runs))
        archive.writestr("events.jsonl", _jsonl(list(events_by_id.values())))
        archive.writestr("provider_calls.jsonl", _jsonl(calls))
        archive.writestr("cores.json", json.dumps(selected_workers, indent=2))
        archive.writestr("connectome_receipts.json", json.dumps(_connectome_receipts(data_dir), indent=2))
        archive.writestr("runs.csv", _run_csv(runs))
        archive.writestr("provider_calls.csv", _provider_csv(calls))
    return output.getvalue()
