# HIVE Connectome v0.3.2 Audit

Audit date: 2026-09-19

## Goal

Treat HIVE as a public experiment lab rather than a demo with optimistic claims. The audit prioritizes the common and consequential paths:

- the app boots and exposes the intended API;
- GUI controls point to real routes and save/run the settings they display;
- one worker remains one complete experiment configuration;
- JEV and LLM are independent toggles/ablations;
- provider payloads match current upstream documentation;
- Docker Desktop/Windows networking is documented conservatively;
- downloaded connectome data is verified before use;
- daemons/cron jobs do not silently bypass the normal pipeline;
- public copy stays domain-neutral;
- unsupported experiment surfaces fail explicitly rather than pretending to work.

The target was at least 80% branch-aware coverage without chasing low-value 100% coverage.

## Result

```text
Python tests:            62 passed
Branch-aware coverage:  88.21%
Coverage floor:          80%
Python compilation:      PASS
Public-copy audit:       PASS
GUI Chromium smoke:      PASS
GUI console errors:      0
GUI page errors:         0
Python wheel build:      PASS (no build isolation, due sandbox network restrictions)
```

High-value coverage includes:

```text
DB                         100%
source adapters             100%
LM Studio adapter           100%
connectome installer         98%
worker model/store           95%
environment runner           92%
Venice provider adapters     90%
FastAPI application          88%
pipeline                     84%
```

The MCP module is intentionally not counted as dynamically covered in this environment because the `mcp` package is not installed here and sandbox DNS prevented dependency installation. Its import/bind/security contract is statically tested, and CI installs the declared dependency before running/building.

## GUI verification

The browser smoke test uses the real:

- `index.html`
- `style.css`
- `app.js`

with deterministic API fixtures. The real FastAPI endpoints are tested separately with `TestClient`.

The smoke test verifies:

- stylesheet is actually applied;
- the first worker is selected and populates the editor;
- data-environment controls switch correctly;
- worker execution renders a result;
- the four JEV/LLM toggle combinations render eval results;
- provider status is displayed;
- connectome packs and install controls render;
- no browser console/page errors occur.

A render audit caught a real bug that Python tests did not: after dynamic worker-list population, the multi-row `<select>` could have no selected value, leaving the form blank. `refreshWorkers()` now explicitly selects the first worker when no valid previous selection exists.

Re-run locally with:

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
python scripts/gui-smoke.py --screenshot audit/gui-audit.png
```

## Runtime fixes found during audit

### App lifecycle

The app now uses a testable `create_app(...)` factory while preserving the Docker/uvicorn factory entrypoint. Tests can use isolated temporary data/config directories without mutating real experiment state.

### Source daemon resilience

The default file source no longer assumes `/data/inbox` outside Docker. Seeded paths are resolved to the active data directory. A failing source no longer kills the whole heartbeat loop.

### Worker runtime

Worker-level `daemon` and `cron` settings are now executable when explicitly enabled. Automatic worker runtime defaults to disabled. Scheduled `poll_source` tasks now execute rather than merely validating in schema.

### Worker settings that previously did not affect execution

- LLM temperature is passed to LM Studio/Venice chat.
- `persist_brain_state=false` resets paired neural state after each run.
- `write_labels=false` suppresses returned labels.
- worker-specific JEV model selection is passed per request instead of mutating a shared provider client.

### JEV semantics

The old `confidence_threshold` wording was misleading for `noul`. Venice documents `noul` as a yes-probability from 0 to 1 with no separate confidence field. The setting is now `llm_gate_threshold`, with backward-compatible loading of old configs.

### LLM providers

LM Studio and Venice Chat Completions are both executable LLM provider options. The previous GUI option for Venice no longer points to an unimplemented runtime path.

### MCP / Docker binding

The MCP server listens on `0.0.0.0:8000` **inside the container**, while Compose publishes it only to `127.0.0.1:8090` on the host. This is required for Docker forwarding while keeping host exposure local. Explicit MCP transport-security host/origin allowlists are configured.

### Connectome GUI

The installer API existed but the install action had disappeared from the GUI. Install buttons are restored. Large packs still require explicit confirmation; source URLs/hashes remain fixed by manifest.

### Planned controls

The worker-to-worker bus is not executed yet. Its UI controls are disabled and labeled planned instead of implying a working distributed Hivemind.

## External documentation verification

### Venice JEV

Verified against current Venice docs:

- `POST /api/v1/decisions`
- `GET /api/v1/models?type=decision`
- typed questions: `noul`, `choice`, `score`
- `noul` is a probability of yes, not a confidence field
- structured JSON `state` is supported
- Decisions/JEV is beta
- `jev-latest` is currently listed at $0.00 input / $0.00 output; model discovery remains authoritative

Venice Chat is wired to:

```text
POST /api/v1/chat/completions
```

### LM Studio

Verified against current LM Studio docs:

- default server: `http://localhost:1234`
- OpenAI-compatible `GET /v1/models`
- OpenAI-compatible `POST /v1/chat/completions`
- chat accepts inference parameters including `temperature`
- default CLI bind is `127.0.0.1`
- non-loopback binds such as `0.0.0.0` increase exposure; authentication is recommended
- API token authentication is supported

### Docker Desktop

Verified against current Docker Desktop docs:

- `host.docker.internal` is the documented hostname for a container reaching a host service;
- published container ports listen broadly by default unless a host IP is specified;
- Compose mappings such as `127.0.0.1:8088:8080` keep the published service local to the host.

HIVE therefore uses:

```text
container → host LM Studio:  http://host.docker.internal:1234/v1
host → HIVE GUI/API:         127.0.0.1:8088
host → HIVE MCP:             127.0.0.1:8090
```

## Public-repo language audit

Public-facing docs/config were checked for deployment-specific leakage. The project is described as a domain-neutral experiment runtime. Local workspace and on-chain/API environments are examples rather than project identity.

A dedicated script prevents known project-specific phrases from being reintroduced:

```bash
python scripts/audit-public-copy.py
```

## Explicit limitations

These are **not** claimed as verified here:

1. **Docker image startup on Windows:** Docker CLI/Desktop is unavailable in this execution environment. Dockerfile/Compose contracts are tested and CI builds the image, but the local audit did not launch Docker Desktop.
2. **Live MCP handshake:** the `mcp` dependency is absent in this execution environment and network restrictions blocked installing missing packages. CI installs declared dependencies. MCP source/config contracts are tested here.
3. **Live LM Studio inference:** no LM Studio server is running in this environment. Request shape/auth/model-list behavior is tested with HTTP mocks and checked against official docs.
4. **Live Venice calls:** no user Venice key is used in the audit. Decisions and Chat request shapes are tested with HTTP mocks and checked against official docs.
5. **Browser data adapter:** browser DOM/OCR experiment schemas and GUI exist, but automated browser data ingestion remains intentionally unimplemented. `run-environment` returns an explicit `501` for these modes.
6. **Real connectome dynamics:** Cook/Witvliet/MaleCNS manifests and installer guardrails exist, but the current runnable mini-brain engine is still the deterministic synthetic experimental engine.
7. **Large connectome downloads:** the installer logic, size guards, caching, and checksum failures are tested with controlled payloads; the audit did not download the ~1.1 GB MaleCNS pack.

## Why coverage stops here

The suite intentionally does not chase 100%. The remaining uncovered lines are concentrated in dependency-unavailable MCP startup, process lifecycle edges, rare provider/network failures, and a few defensive branches. The current suite focuses on the paths most likely to make an experiment misleading, unsafe, unreproducible, or simply unusable.
