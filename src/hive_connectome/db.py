from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class HiveDB:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        schema = """
        CREATE TABLE IF NOT EXISTS events (
          id TEXT PRIMARY KEY,
          timestamp TEXT NOT NULL,
          source_id TEXT NOT NULL,
          kind TEXT NOT NULL,
          json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS runs (
          id TEXT PRIMARY KEY,
          timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          event_id TEXT NOT NULL,
          json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS provider_calls (
          call_id TEXT PRIMARY KEY,
          run_id TEXT,
          stage_id TEXT,
          provider TEXT NOT NULL,
          capability TEXT NOT NULL,
          timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_provider_calls_run_id ON provider_calls(run_id);
        CREATE TABLE IF NOT EXISTS sources (
          id TEXT PRIMARY KEY,
          json TEXT NOT NULL,
          last_polled REAL
        );
        CREATE TABLE IF NOT EXISTS tasks (
          id TEXT PRIMARY KEY,
          json TEXT NOT NULL,
          last_run TEXT
        );
        CREATE TABLE IF NOT EXISTS file_ingest (
          path TEXT PRIMARY KEY,
          mtime REAL NOT NULL
        );
        """
        with self._db:
            self._db.executescript(schema)

    def insert_event(self, event: dict[str, Any]) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO events(id,timestamp,source_id,kind,json) VALUES(?,?,?,?,?)",
                (event["id"], event["timestamp"], event["source_id"], event["kind"], json.dumps(event)),
            )

    def insert_run(self, run: dict[str, Any]) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO runs(id,event_id,json) VALUES(?,?,?)",
                (run["run_id"], run["event"]["id"], json.dumps(run)),
            )

    def insert_provider_call(self, receipt: dict[str, Any], *, run_id: str | None = None, stage_id: str | None = None) -> None:
        payload = {**receipt, "run_id": run_id, "stage_id": stage_id}
        with self._lock, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO provider_calls(call_id,run_id,stage_id,provider,capability,json) VALUES(?,?,?,?,?,?)",
                (
                    payload["call_id"],
                    run_id,
                    stage_id,
                    payload.get("provider", "unknown"),
                    payload.get("capability", "unknown"),
                    json.dumps(payload),
                ),
            )

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT json FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(r["json"]) for r in rows]

    def list_runs(self, limit: int = 500, worker_id: str | None = None) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT json FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        result = [json.loads(r["json"]) for r in rows]
        if worker_id is None:
            return result
        return [
            item for item in result
            if item.get("execution", {}).get("resolved_worker", {}).get("id") == worker_id
            or f"worker:{worker_id}" in item.get("labels", [])
        ]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._db.execute("SELECT json FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row["json"]) if row else None

    def list_provider_calls(self, limit: int = 1000, run_id: str | None = None) -> list[dict[str, Any]]:
        if run_id is None:
            rows = self._db.execute(
                "SELECT json FROM provider_calls ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT json FROM provider_calls WHERE run_id=? ORDER BY timestamp LIMIT ?", (run_id, limit)
            ).fetchall()
        return [json.loads(r["json"]) for r in rows]

    def upsert_source(self, spec: dict[str, Any]) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO sources(id,json,last_polled) VALUES(?,?,NULL) "
                "ON CONFLICT(id) DO UPDATE SET json=excluded.json",
                (spec["id"], json.dumps(spec)),
            )

    def list_sources(self) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT json,last_polled FROM sources ORDER BY id").fetchall()
        result = []
        for r in rows:
            item = json.loads(r["json"])
            item["_last_polled"] = r["last_polled"]
            result.append(item)
        return result

    def set_source_polled(self, source_id: str, ts: float) -> None:
        with self._lock, self._db:
            self._db.execute("UPDATE sources SET last_polled=? WHERE id=?", (ts, source_id))

    def upsert_task(self, spec: dict[str, Any]) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO tasks(id,json,last_run) VALUES(?,?,NULL) "
                "ON CONFLICT(id) DO UPDATE SET json=excluded.json",
                (spec["id"], json.dumps(spec)),
            )

    def list_tasks(self) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT json,last_run FROM tasks ORDER BY id").fetchall()
        result = []
        for r in rows:
            item = json.loads(r["json"])
            item["_last_run"] = r["last_run"]
            result.append(item)
        return result

    def set_task_run(self, task_id: str, stamp: str) -> None:
        with self._lock, self._db:
            self._db.execute("UPDATE tasks SET last_run=? WHERE id=?", (stamp, task_id))

    def file_seen(self, path: str, mtime: float) -> bool:
        row = self._db.execute("SELECT mtime FROM file_ingest WHERE path=?", (path,)).fetchone()
        return bool(row and float(row["mtime"]) >= mtime)

    def mark_file_seen(self, path: str, mtime: float) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO file_ingest(path,mtime) VALUES(?,?) "
                "ON CONFLICT(path) DO UPDATE SET mtime=excluded.mtime",
                (path, mtime),
            )

    def close(self) -> None:
        with self._lock:
            self._db.close()
