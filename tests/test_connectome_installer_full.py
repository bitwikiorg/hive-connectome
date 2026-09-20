from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from hive_connectome.connectomes.installer import ConnectomeInstaller


def _manifest(tmp_path: Path, *, content: bytes = b"abc", expected_bytes: int | None = None, digest: str | None = None):
    sha = digest or hashlib.sha256(content).hexdigest()
    data = {
        "version": 1,
        "packs": [
            {
                "id": "small",
                "name": "Small",
                "installable": True,
                "files": [
                    {
                        "name": "data.bin",
                        "url": "https://example.test/data.bin",
                        "sha256": sha,
                        **({"bytes": expected_bytes} if expected_bytes is not None else {}),
                    }
                ],
            },
            {
                "id": "reference-only",
                "name": "Reference",
                "installable": False,
                "reason": "research only",
                "files": [],
            },
        ],
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_manifest_lookup_status_and_unknown(tmp_path):
    manifest = _manifest(tmp_path)
    installer = ConnectomeInstaller(manifest, tmp_path / "data")
    assert installer.manifest()["version"] == 1
    assert installer.get_pack("small")["name"] == "Small"
    with pytest.raises(KeyError):
        installer.get_pack("missing")
    status = installer.list_status()
    assert status[0]["installed"] is False
    assert status[1]["installed"] is False


@pytest.mark.asyncio
async def test_install_success_receipt_status_and_cached(tmp_path):
    content = b"abc"
    manifest = _manifest(tmp_path, content=content, expected_bytes=len(content))
    calls = 0

    def handler(request: httpx.Request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=content)

    installer = ConnectomeInstaller(manifest, tmp_path / "data", transport=httpx.MockTransport(handler))
    receipt = await installer.install("small")
    assert receipt["files"][0]["cached"] is False
    target = tmp_path / "data" / "connectomes" / "small" / "data.bin"
    assert target.read_bytes() == content
    assert installer.get_pack("small")["id"] == "small"
    assert installer.list_status()[0]["installed"] is True
    assert (target.parent / "receipt.json").exists()

    again = await installer.install("small")
    assert again["files"][0]["cached"] is True
    assert calls == 1


@pytest.mark.asyncio
async def test_install_rejects_reference_size_and_hash_mismatch(tmp_path):
    content = b"abc"
    manifest = _manifest(tmp_path, content=content, expected_bytes=99)
    installer = ConnectomeInstaller(
        manifest,
        tmp_path / "data",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, content=content)),
    )
    with pytest.raises(ValueError, match="research only"):
        await installer.install("reference-only")
    with pytest.raises(ValueError, match="size mismatch"):
        await installer.install("small")
    part = tmp_path / "data" / "connectomes" / "small" / "data.bin.part"
    assert not part.exists()

    bad_manifest = _manifest(tmp_path / "bad", content=content, digest="0" * 64)
    bad = ConnectomeInstaller(
        bad_manifest,
        tmp_path / "bad-data",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, content=content)),
    )
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        await bad.install("small")
