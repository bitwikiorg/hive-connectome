from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx

class ConnectomeInstaller:
    def __init__(self, manifest_path: Path, data_dir: Path, transport=None):
        self.manifest_path=manifest_path
        self.data_dir=data_dir
        self.transport=transport

    def manifest(self)->dict[str,Any]:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def get_pack(self, pack_id:str)->dict[str,Any]:
        for p in self.manifest()["packs"]:
            if p["id"]==pack_id:
                return p
        raise KeyError(pack_id)

    @staticmethod
    def _hash(path:Path)->str:
        h=hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""):
                h.update(chunk)
        return h.hexdigest()

    def status(self, pack:dict[str,Any])->dict[str,Any]:
        root=self.data_dir/"connectomes"/pack["id"]
        complete=bool(pack.get("installable")) and bool(pack.get("files"))
        files=[]
        for spec in pack.get("files",[]):
            path=root/spec["name"]
            ok=path.exists()
            if ok and spec.get("bytes") is not None:
                ok=path.stat().st_size==int(spec["bytes"])
            if ok:
                ok=self._hash(path)==spec["sha256"]
            complete=complete and ok
            files.append({"name":spec["name"],"installed":ok})
        return {**pack,"installed":complete,"file_status":files}

    def list_status(self)->list[dict[str,Any]]:
        return [self.status(p) for p in self.manifest()["packs"]]

    async def install(self, pack_id:str)->dict[str,Any]:
        pack=self.get_pack(pack_id)
        if not pack.get("installable"):
            raise ValueError(pack.get("reason","pack is not installable"))
        root=self.data_dir/"connectomes"/pack_id
        root.mkdir(parents=True,exist_ok=True)
        receipt={"pack_id":pack_id,"installed_at":datetime.now(timezone.utc).isoformat(),"files":[]}

        async with httpx.AsyncClient(timeout=None,follow_redirects=True,transport=self.transport) as client:
            for spec in pack["files"]:
                target=root/spec["name"]
                if target.exists() and self._hash(target)==spec["sha256"]:
                    receipt["files"].append({"name":spec["name"],"sha256":spec["sha256"],"cached":True})
                    continue
                tmp=target.with_suffix(target.suffix+".part")
                tmp.unlink(missing_ok=True)
                expected=int(spec.get("bytes") or 0)
                hard_limit=int(expected*1.05) if expected else 2*1024*1024*1024
                h=hashlib.sha256()
                count=0
                async with client.stream("GET",spec["url"]) as response:
                    response.raise_for_status()
                    with tmp.open("wb") as f:
                        async for chunk in response.aiter_bytes(1024*1024):
                            count+=len(chunk)
                            if count>hard_limit:
                                raise ValueError(f"{spec['name']} exceeded configured size bound")
                            h.update(chunk); f.write(chunk)
                if expected and count!=expected:
                    tmp.unlink(missing_ok=True)
                    raise ValueError(f"{spec['name']} size mismatch: {count} != {expected}")
                digest=h.hexdigest()
                if digest!=spec["sha256"]:
                    tmp.unlink(missing_ok=True)
                    raise ValueError(f"{spec['name']} SHA-256 mismatch")
                tmp.replace(target)
                receipt["files"].append({"name":spec["name"],"sha256":digest,"bytes":count,"cached":False})

        (root/"receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
        return receipt
