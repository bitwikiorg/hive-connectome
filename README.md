# HIVE Connectome

HIVE Connectome is an always-on Hivemind runtime for **mini-brains + typed decisions + occasional LLM reasoning + tools**.

The first deployment target is **Windows + Docker Desktop**. The same schemas are intended to scale into **Based Nut's Hivemind** and a private personal Hivemind.

## Core loop

```text
ALWAYS-ON DATA
     ↓
WormLink / "larva" connector
     ↓
FlyCore recurrent state
     ↓
Venice Jev typed decisions
     ↓
high confidence ───────────────→ state / labels / routing
     │
     └─ uncertain/open-ended → LM Studio local AI
                                  ↓
                             optional Jev verify
                                  ↓
                           Comb / durable memory
```

A **Bee Unit** is a bounded worker composed of:

```text
WormLink + FlyCore + Jev head + optional LLM escalation + policy
```

Multiple Bee Units communicate over the **Waggle bus** and share the **Comb** state store. This is the Hivemind.

`WormLink` is a project metaphor for the connector role. The current biological substrate is **C. elegans**, not a bee larva.

## Why JEV sits next to neural state

The connectome provides persistent recurrent dynamics. It does not know what a wallet event, file, block, chat, or API response means.

Jev receives a structured state containing:

- raw event
- WormLink readouts
- FlyCore readouts
- current Hive context

Jev turns that combined state into bounded judgments such as `noul`, `choice`, and `score`. An LLM enters only when bounded classification is insufficient.

## Current v0.1 scope

Implemented in this scaffold:

- FastAPI local runtime
- browser GUI
- deterministic mini-brain test engines
- SQLite event/run store
- Venice Jev adapter
- LM Studio adapter
- automatic LLM escalation policy
- HTTP/RSS/local-file data sources
- heartbeat daemon
- cron tasks
- simulation endpoint
- MCP server
- SHA-256 verified connectome data installer
- Windows/Docker Desktop setup
- real Cook/Witvliet/MaleCNS data manifests

Not falsely claimed as complete:

- real Cook/Witvliet dynamics adapter
- real MaleCNS dynamics adapter
- Drosophila larval mushroom-body runtime
- production wallet signing / contract mutation

Those come after the schemas and orchestration are stable.

## Windows quick start

Prerequisites:

1. Docker Desktop
2. Git
3. Optional: LM Studio for local LLM escalation
4. Optional: Venice API key for live Jev calls

```powershell
git clone https://github.com/bitwikiorg/hive-connectome
cd hive-connectome
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

Open:

- GUI/API: `http://127.0.0.1:8088`
- MCP: `http://127.0.0.1:8090/mcp`

## LM Studio

HIVE defaults to:

```text
http://host.docker.internal:1234/v1
```

See `docs/WINDOWS.md` before changing LM Studio's bind address.

## Connectome installation

The GUI exposes only fixed source manifests.

Downloads are:

1. streamed to `.part`
2. size-bounded
3. SHA-256 verified
4. atomically renamed
5. recorded in an install receipt

Downloaded connectome data is **never executed**.

## Docs

- `docs/ARCHITECTURE.md`
- `docs/SCHEMAS.md`
- `docs/SECURITY.md`
- `docs/WINDOWS.md`
- `docs/DATA_SOURCES.md`
- `docs/ROADMAP.md`
- `docs/REFERENCES.md`

## Tests

```bash
python -m pip install -e ".[dev]"
pytest -q
```
