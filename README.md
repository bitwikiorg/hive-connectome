# HIVE Connectome

HIVE Connectome is an experimental runtime for **paired mini-brains + typed decisions + optional LLM reasoning + tools**.

> **Current runtime truth:** HIVE currently executes deterministic synthetic recurrent test stages. Cook/Witvliet/MaleCNS packs can be downloaded and SHA-256 verified, but the current runtime does **not** execute those biological connectomes yet. The GUI reports this explicitly. See [`docs/HOW_TO_USE.md`](docs/HOW_TO_USE.md).

The first deployment target is **Windows + Docker Desktop**. The runtime is deliberately modular so experiments can change the data environment, neural substrate, decision layer, model provider, schedule, and evaluation without rewriting the application.

## Core loop

```text
DATA ENVIRONMENT
      ↓
Larvaᵢ → Beeᵢ
      ↓
     JEV? ───── bounded typed decisions
      ↓
     LLM? ───── open-ended reasoning when enabled/needed
      ↓
    OUTPUT / STATE / NEXT WORKER
```

A worker is one complete experiment configuration. The current biological candidates are **C. elegans** for the smaller Larva stage and Drosophila connectomes for the larger Bee stage; the names describe project roles, not claims that either organism is literally a bee larva or bee.

## Why JEV sits next to neural state

The neural stage provides recurrent state and dynamics; task semantics still come from explicit encoders, readouts, prompts, and decision questions.

JEV can evaluate the combined event + neural observation as bounded `noul`, `choice`, and `score` questions. An LLM is optional and can be used for open-ended interpretation when the experiment calls for it. The two are independently switchable so their contribution can be measured rather than assumed.

## Worker experiment model

```text
Workerᵢ =
  experiment objective + evaluation target
  + data environment
  + Larvaᵢ → Beeᵢ
  + JEV settings/toggle
  + LLM settings/toggle
  + runtime
  + outputs
```

The GUI exposes these settings together. For a controlled ablation, the same saved worker can be run with:

```text
JEV off · LLM off
JEV on  · LLM off
JEV off · LLM on
JEV on  · LLM on
```

Everything else stays fixed.

See `docs/WORKERS.md`, `docs/EVALUATION.md`, `docs/REPO_LEARNINGS.md`, and `docs/BROWSER_LAB.md`.

## Current v0.4 scope

Implemented and covered by the automated suite:

- FastAPI local runtime and app factory
- browser experiment GUI
- editable/saved complete worker configurations
- deterministic mini-brain test engines
- SQLite event/run store
- Venice JEV/Decisions adapter
- LM Studio OpenAI-compatible LLM adapter
- Venice Chat Completions LLM adapter
- independent JEV/LLM run overrides and four-way eval matrix
- HTTP JSON, RSS, and local-file data sources
- heartbeat daemon
- worker interval/cron runtime
- explicit cron tasks, including source polling
- simulation endpoint
- MCP server surface
- SHA-256 verified connectome data installer
- Windows/Docker Desktop configuration
- Cook/Witvliet/MaleCNS source manifests

Intentionally not claimed as complete:

- real Cook/Witvliet dynamics adapter
- real MaleCNS dynamics adapter
- Drosophila larval mushroom-body runtime
- automated browser DOM/OCR adapter
- distributed worker/Waggle bus
- irreversible external-action executors

Unsupported experiment surfaces remain visible as planned/experimental rather than silently pretending to execute.

## Windows quick start

For a full first-run walkthrough, including Docker Desktop, LM Studio, Venice, updates, troubleshooting, and what to expect from the current experimental build, see **[`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md)**.

Prerequisites:

1. Docker Desktop
2. Git
3. Optional: LM Studio for local LLM inference
4. Optional: Venice API key for JEV and/or Venice-hosted LLM calls

```powershell
git clone https://github.com/bitwikiorg/hive-connectome
cd hive-connectome
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

Open:

- GUI/API: `http://127.0.0.1:8088`
- MCP: `http://127.0.0.1:8090/mcp`


## Updating an existing install

From PowerShell in the cloned repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\update-windows.ps1
```

This performs a fast-forward-only `git pull`, rebuilds the Compose services, starts them, and checks the health endpoint. Persistent HIVE state remains in the `hive-data` Docker volume.

There is currently no published registry image to `docker pull`; HIVE is built locally from the cloned repository. See `docs/GETTING_STARTED.md` for the exact Docker Desktop workflow.

## LM Studio + Docker Desktop

The container uses Docker Desktop's host bridge:

```text
http://host.docker.internal:1234/v1
```

LM Studio binds to `127.0.0.1` by default. A container may therefore need LM Studio to listen on a non-loopback interface. If you enable that, enable LM Studio API authentication and restrict the port with the host firewall. See `docs/WINDOWS.md`.

## Connectome installation

The GUI exposes only fixed source manifests. Downloads are:

1. streamed to `.part`
2. size-bounded
3. SHA-256 verified
4. atomically renamed
5. recorded in an install receipt

Downloaded connectome data is **never executed** by the installer.

## Tests

```bash
python -m pip install -e ".[dev]"
pytest -q
python scripts/audit-public-copy.py
```

The test configuration enforces **>=80% branch-aware coverage**. Browser rendering has a separate Playwright smoke check; see `scripts/gui-smoke.py`.

## Docs

- `docs/GETTING_STARTED.md`
- `docs/HOW_TO_USE.md`
- `docs/REFERENCE_CORPUS.md`
- `docs/ARCHITECTURE.md`
- `docs/WORKERS.md`
- `docs/EVALUATION.md`
- `docs/SCHEMAS.md`
- `docs/SECURITY.md`
- `docs/WINDOWS.md`
- `docs/DATA_SOURCES.md`
- `docs/BROWSER_LAB.md`
- `docs/ROADMAP.md`
- `docs/REFERENCES.md`
- `docs/AUDIT.md`