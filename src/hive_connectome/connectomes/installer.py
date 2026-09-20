from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


class ConnectomeInstaller:
    def __init__(self, manifest_path: Path, data_dir: Path, transport=None):
        self.manifest_path = manifest_path
        self.data_dir = data_dir
        self.transport = transport

    def manifest(self) -> dict[str, Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def get_pack(self, pack_id: str) -> dict[str, Any]:
        for pack in self.manifest()["packs"]:
            if pack["id"] == pack_id:
                return pack
        raise KeyError(pack_id)

    @staticmethod
    def _hash(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _git_blob_sha(path: Path) -> str:
        size = path.stat().st_size
        h = hashlib.sha1()
        h.update(f"blob {size}\0".encode("ascii"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _file_ok(self, path: Path, spec: dict[str, Any]) -> bool:
        if not path.exists():
            return False
        if spec.get("bytes") is not None and path.stat().st_size != int(spec["bytes"]):
            return False
        if spec.get("sha256") and self._hash(path) != spec["sha256"]:
            return False
        if spec.get("git_blob_sha") and self._git_blob_sha(path) != spec["git_blob_sha"]:
            return False
        return bool(spec.get("sha256") or spec.get("git_blob_sha"))

    def status(self, pack: dict[str, Any]) -> dict[str, Any]:
        root = self.data_dir / "connectomes" / pack["id"]
        complete = bool(pack.get("installable")) and bool(pack.get("files"))
        files = []
        for spec in pack.get("files", []):
            path = root / spec["name"]
            ok = self._file_ok(path, spec)
            complete = complete and ok
            files.append({"name": spec["name"], "installed": ok})
        return {**pack, "installed": complete, "file_status": files}

    def list_status(self) -> list[dict[str, Any]]:
        return [self.status(pack) for pack in self.manifest()["packs"]]

    async def install(self, pack_id: str) -> dict[str, Any]:
        pack = self.get_pack(pack_id)
        if not pack.get("installable"):
            raise ValueError(pack.get("reason", "pack is not installable"))
        root = self.data_dir / "connectomes" / pack_id
        root.mkdir(parents=True, exist_ok=True)
        receipt = {"pack_id": pack_id, "installed_at": datetime.now(timezone.utc).isoformat(), "files": []}

        async with httpx.AsyncClient(timeout=None, follow_redirects=True, transport=self.transport) as client:
            for spec in pack["files"]:
                target = root / spec["name"]
                if self._file_ok(target, spec):
                    receipt["files"].append({"name": spec["name"], "cached": True, "sha256": self._hash(target)})
                    continue
                tmp = target.with_suffix(target.suffix + ".part")
                tmp.unlink(missing_ok=True)
                expected = int(spec.get("bytes") or 0)
                hard_limit = int(expected * 1.05) if expected else 2 * 1024 * 1024 * 1024
                count = 0
                sha256 = hashlib.sha256()
                async with client.stream("GET", spec["url"]) as response:
                    response.raise_for_status()
                    with tmp.open("wb") as handle:
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            count += len(chunk)
                            if count > hard_limit:
                                tmp.unlink(missing_ok=True)
                                raise ValueError(f"{spec['name']} exceeded configured size bound")
                            sha256.update(chunk)
                            handle.write(chunk)
                if expected and count != expected:
                    tmp.unlink(missing_ok=True)
                    raise ValueError(f"{spec['name']} size mismatch: {count} != {expected}")
                digest = sha256.hexdigest()
                if spec.get("sha256") and digest != spec["sha256"]:
                    tmp.unlink(missing_ok=True)
                    raise ValueError(f"{spec['name']} SHA-256 mismatch")
                if spec.get("git_blob_sha") and self._git_blob_sha(tmp) != spec["git_blob_sha"]:
                    tmp.unlink(missing_ok=True)
                    raise ValueError(f"{spec['name']} Git blob hash mismatch")
                if not spec.get("sha256") and not spec.get("git_blob_sha"):
                    tmp.unlink(missing_ok=True)
                    raise ValueError(f"{spec['name']} has no pinned integrity hash")
                tmp.replace(target)
                receipt["files"].append({
                    "name": spec["name"],
                    "sha256": digest,
                    "git_blob_sha": spec.get("git_blob_sha"),
                    "bytes": count,
                    "cached": False,
                })

        (root / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return receipt
