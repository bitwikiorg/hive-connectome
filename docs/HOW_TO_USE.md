# How to use HIVE v0.6

## Read this first

The primary experiment is:

```text
full Cook C. elegans
  ↓
full MaleCNS v1.0
  ↓
JEV independently ON/OFF
  ↓
LLM independently ON/OFF
  ↓
fixed evaluation
```

**That primary experiment is not ready in v0.6.** The full MaleCNS execution engine is not implemented yet.

The currently runnable neural path is:

```text
full Cook C. elegans
  ↓
1,045-neuron MaleCNS locomotor subgraph
```

That path is a **CONTROL / DEVELOPMENT path only**. Its results are useful for exercising HIVE's UI, provider calls, state flow, and evaluation machinery, but they are not the primary experiment.

## Why the full 1.1 GB MaleCNS pack is not auto-downloaded yet

Full MaleCNS is **required**, not optional. v0.6 deliberately does not auto-download the ~1.1 GB pack during setup because the full-graph execution engine cannot use it yet. Downloading it automatically would consume bandwidth without advancing the experiment.

Readiness remains blocked until both of these are true:

```text
full MaleCNS data installed + verified
AND
full MaleCNS graph actually executed
```

Data possession alone is not execution.

## What you can do now

You can use the GUI to run **control/development experiments** and test:

- Cook → locomotor-subgraph neural flow;
- live Venice/JEV calls;
- LM Studio calls;
- the four JEV/LLM toggle combinations;
- data-source ingestion;
- memory/state behavior;
- UI and execution receipts.

Every current control result should be treated as:

```text
CONTROL RESULT — NOT PRIMARY EXPERIMENT
```

## JEV truth

If a run requests JEV, HIVE does not silently replace it with the fixed readout. A live JEV result requires:

```text
decisions.provider = venice
execution.jev.called = true
```

## Canonical state

The experiment definition and promotion gates live in:

- `config/experiment_contract.json`
- `docs/STATE.md`

Those two files are authoritative. A convenience runtime may not redefine the study.
