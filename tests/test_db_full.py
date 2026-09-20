from datetime import datetime, timezone

from hive_connectome.db import HiveDB


def test_db_sources_tasks_and_file_seen(tmp_path):
    db = HiveDB(tmp_path / "hive.db")
    db.upsert_source({"id": "s", "name": "S", "kind": "file_drop", "path": "/tmp", "interval_seconds": 10, "enabled": False, "auto_process": False})
    assert db.list_sources()[0]["id"] == "s"
    db.set_source_polled("s", 12.5)
    assert db.list_sources()[0]["_last_polled"] == 12.5

    db.upsert_task({"id": "t", "name": "T", "cron": "* * * * *", "action": "emit_event", "target_id": None, "payload": {}, "enabled": True})
    assert db.list_tasks()[0]["id"] == "t"
    stamp = datetime.now(timezone.utc).isoformat()
    db.set_task_run("t", stamp)
    assert db.list_tasks()[0]["_last_run"] == stamp

    assert db.file_seen("x", 1.0) is False
    db.mark_file_seen("x", 1.0)
    assert db.file_seen("x", 1.0) is True
    assert db.file_seen("x", 2.0) is False
    db.mark_file_seen("x", 3.0)
    assert db.file_seen("x", 2.0) is True
    db.close()
