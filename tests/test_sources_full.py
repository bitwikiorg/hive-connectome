from __future__ import annotations

import socket
from pathlib import Path

import httpx
import pytest

from hive_connectome.schemas import DataSourceSpec
from hive_connectome.sources import assert_safe_public_url, poll_source


def _public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])


def test_safe_url_accepts_public_and_rejects_invalid(monkeypatch):
    _public_dns(monkeypatch)
    assert_safe_public_url("https://example.com/data")
    with pytest.raises(ValueError):
        assert_safe_public_url("ftp://example.com/data")
    with pytest.raises(ValueError):
        assert_safe_public_url("http://localhost/x")

    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 80))])
    with pytest.raises(ValueError):
        assert_safe_public_url("http://example.com/x")

    def bad_dns(*a, **k):
        raise socket.gaierror("nope")
    monkeypatch.setattr(socket, "getaddrinfo", bad_dns)
    with pytest.raises(ValueError, match="Could not resolve"):
        assert_safe_public_url("https://example.com/x")


@pytest.mark.asyncio
async def test_http_json_get_and_post(monkeypatch, tmp_path):
    _public_dns(monkeypatch)

    def handler(request: httpx.Request):
        if request.method == "POST":
            return httpx.Response(200, json={"posted": True})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    get_spec = DataSourceSpec(id="get", name="Get", kind="http_json", url="https://example.com/data")
    post_spec = DataSourceSpec(id="post", name="Post", kind="http_json", url="https://example.com/data", method="POST", body={"x": 1})
    get_events = await poll_source(get_spec, tmp_path, transport=transport)
    post_events = await poll_source(post_spec, tmp_path, transport=transport)
    assert get_events[0].payload == {"ok": True}
    assert post_events[0].payload == {"posted": True}


@pytest.mark.asyncio
async def test_rss_poll(monkeypatch, tmp_path):
    _public_dns(monkeypatch)
    xml = b"""<rss><channel><item><title>A</title><link>https://x/a</link><description>D</description></item></channel></rss>"""
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=xml))
    spec = DataSourceSpec(id="rss", name="RSS", kind="rss", url="https://example.com/feed")
    events = await poll_source(spec, tmp_path, transport=transport)
    assert events[0].payload["title"] == "A"


@pytest.mark.asyncio
async def test_file_drop_formats_filters_and_boundary(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a.json").write_text('{"x":1}', encoding="utf-8")
    (inbox / "b.jsonl").write_text('{"x":1}\n{"x":2}\n', encoding="utf-8")
    (inbox / "c.csv").write_text('name,value\na,1\n', encoding="utf-8")
    (inbox / "d.md").write_text('hello', encoding="utf-8")
    (inbox / "ignore.bin").write_bytes(b"x")
    spec = DataSourceSpec(id="files", name="Files", kind="file_drop", path=str(inbox))
    events = await poll_source(spec, inbox)
    by_name = {e.subject: e.payload for e in events}
    assert by_name["a.json"] == {"x": 1}
    assert by_name["b.jsonl"] == [{"x": 1}, {"x": 2}]
    assert by_name["c.csv"] == [{"name": "a", "value": "1"}]
    assert by_name["d.md"] == "hello"
    assert "ignore.bin" not in by_name

    outside = tmp_path / "outside"
    outside.mkdir()
    bad = DataSourceSpec(id="bad", name="Bad", kind="file_drop", path=str(outside))
    with pytest.raises(ValueError, match="configured inbox"):
        await poll_source(bad, inbox)


@pytest.mark.asyncio
async def test_poll_unknown_kind_defensive(tmp_path):
    spec = DataSourceSpec.model_construct(id="x", name="x", kind="unknown", interval_seconds=60, enabled=False, auto_process=True)
    with pytest.raises(ValueError, match="Unsupported"):
        await poll_source(spec, tmp_path)
