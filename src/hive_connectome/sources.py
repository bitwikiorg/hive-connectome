from __future__ import annotations
import csv, ipaddress, json, socket
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree
import httpx
from hive_connectome.schemas import DataSourceSpec, EventEnvelope

def assert_safe_public_url(url:str)->None:
    parsed=urlparse(url)
    if parsed.scheme not in {"http","https"} or not parsed.hostname:
        raise ValueError("Only explicit http/https URLs are allowed")
    if parsed.hostname.lower() in {"localhost","localhost.localdomain"}:
        raise ValueError("Loopback destinations are blocked")
    try:
        addresses={info[4][0] for info in socket.getaddrinfo(parsed.hostname,parsed.port or (443 if parsed.scheme=="https" else 80))}
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve source host: {e}") from e
    for raw in addresses:
        ip=ipaddress.ip_address(raw)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise ValueError(f"Blocked non-public source address: {ip}")

async def poll_source(spec:DataSourceSpec,inbox_root:Path,transport=None)->list[EventEnvelope]:
    if spec.kind=="http_json":
        assert_safe_public_url(spec.url or "")
        async with httpx.AsyncClient(timeout=30,follow_redirects=False,transport=transport) as client:
            r=await (client.post(spec.url,json=spec.body) if spec.method=="POST" else client.get(spec.url))
            r.raise_for_status()
            payload=r.json()
        return [EventEnvelope(source_id=spec.id,kind="http_json",payload=payload,provenance={"url":spec.url})]

    if spec.kind=="rss":
        assert_safe_public_url(spec.url or "")
        async with httpx.AsyncClient(timeout=30,follow_redirects=False,transport=transport) as client:
            r=await client.get(spec.url); r.raise_for_status()
        root=ElementTree.fromstring(r.content)
        entries=[]
        for item in root.findall(".//item")[:50]:
            entries.append({"title":(item.findtext("title") or "").strip(),"link":(item.findtext("link") or "").strip(),"description":(item.findtext("description") or "").strip()})
        return [EventEnvelope(source_id=spec.id,kind="rss",payload=e,provenance={"url":spec.url}) for e in entries]

    if spec.kind=="file_drop":
        configured=Path(spec.path or "")
        try:
            configured.resolve().relative_to(inbox_root.resolve())
        except ValueError as e:
            raise ValueError("file_drop path must remain under configured inbox") from e
        events=[]
        for p in sorted(configured.glob("*"))[:100]:
            if not p.is_file() or p.suffix.lower() not in {".json",".jsonl",".txt",".md",".csv"} or p.stat().st_size>10*1024*1024:
                continue
            if p.suffix.lower()==".json":
                payload:Any=json.loads(p.read_text(encoding="utf-8"))
            elif p.suffix.lower()==".jsonl":
                payload=[json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
            elif p.suffix.lower()==".csv":
                with p.open("r",encoding="utf-8",newline="") as f:
                    payload=list(csv.DictReader(f))
            else:
                payload=p.read_text(encoding="utf-8")
            events.append(EventEnvelope(source_id=spec.id,kind="file",subject=p.name,payload=payload,provenance={"path":str(p)}))
        return events

    raise ValueError(f"Unsupported source kind: {spec.kind}")
