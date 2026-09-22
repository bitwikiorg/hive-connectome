# HIVE Connectome

HIVE Connectome is an experimental lab for **connecting heterogeneous neural/computational substrates, changing the composition, and measuring what each component actually adds**.


> **Current runtime truth (v0.7):** the primary study is **full Cook C. elegans → full MaleCNS v1.0**. The full `malecns_full_v1` sparse engine is implemented, but readiness remains empirical: the pinned full datasets must be installed and the exact full graph must execute successfully on the target machine and produce matching execution receipts. The 1,045-neuron MaleCNS locomotor path remains **control/development only**. See [`docs/STATE.md`](docs/STATE.md).

The first deployment target is **Windows + Docker Desktop**. The runtime is deliberately modular so experiments can change the data environment, neural substrate, decision layer, model provider, schedule, and evaluation without rewriting the application.

## Core loop

The primary GUI is an experiment instrument, not an AI-assistant task menu:

```text
INPUT
  ↓
configured neural chain
  ↓
whole-state neural representation
  ↓
JEV                            independently ablatable
  ↓
LLM                            independently ablatable
  ↓
bounded recurrent feedback
  ↺ same-input neural refinement
  ↓
RECORDED RESULT + TRACE + EXPORT
```

A saved **Core** defines one such composition. Its executable architecture is comma-taggable—for example `worm,worm-to-fly,fly,readout,jev,llm,jev_verify,feedback`—and HIVE executes those tags in that exact order. Reordering/removing/repeating tags changes the experimental architecture. A **Hive** chains multiple Cores only when multi-Core experiments are desired. The GUI resolves the Core through the backend, shows the exact tagged path before execution, then renders the component calls that actually executed and keeps raw JSON behind an advanced debugging view.

## Why JEV sits next to neural state

The neural stage provides recurrent state and dynamics; task semantics still come from explicit encoders, readouts, prompts, and decision questions.

JEV evaluates the event plus a whole-state representation derived from the complete executed neural substrate using bounded `noul`, `choice`, and `score` questions. When an LLM is enabled it executes wherever its `llm` tag appears and receives the current whole-state neural evidence; it also receives a JEV decision only when a real JEV call ran earlier against that same readout. Their bounded feedback is applied before the same input is refined by the neural substrate. JEV and LLM remain independently switchable only so their contribution can be measured by ablation. Neural stages, bridges, readout, JEV, LLM, JEV verification, feedback, feedback sources/targets, and harness-pass depth are all explicit experimental controls rather than hidden routing behavior.

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

## Current v0.7 state

The repository is stabilized around a machine-readable experiment contract:

- primary Larva = full corrected Cook C. elegans connectome;
- primary Bee = full MaleCNS v1.0;
- JEV and LLM remain independent toggles;
- reduced MaleCNS, synthetic, shuffled, no-connectome, Larva-only, and Bee-only paths are controls only;
- primary readiness requires the full datasets to be installed, verified, and actually executed by their declared engines;
- `malecns_full_v1` is implemented; `primary_experiment_ready` remains false until the target machine successfully executes the exact full datasets and produces valid execution receipts.

Runnable development/control surfaces remain available for testing the application, providers, data flow, and evaluation harness, but they must not be interpreted as the primary study.

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

The installer never executes downloaded files. Verification only establishes data integrity; it does not satisfy the primary execution gate.

## Tests

```bash
python -m pip install -e ".[dev]"
pytest -q
python scripts/audit-public-copy.py
```

The test configuration enforces **>=80% branch-aware coverage**. Browser rendering has a separate Playwright smoke check; see `scripts/gui-smoke.py`.

## Docs

- `docs/STATE.md`
- `docs/GETTING_STARTED.md`
- `docs/HOW_TO_USE.md`
- `docs/REFERENCE_CORPUS.md`
- `docs/REPO_AUDIT.md`
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
