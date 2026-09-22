# HIVE — Next Session Handoff

Date prepared: 2026-09-22  
Canonical audit: `docs/AUDIT.md`

## Project boundary

HIVE is not currently a full agent harness.

It is an experimental composition lab for testing staged and recurrent combinations of neural substrates, JEV, LLMs, and later other processors.

The software integrity pass is complete enough to begin controlled pilot experiments.

## Start here

Read:

1. `docs/AUDIT.md`
2. `docs/STATE.md`
3. `docs/ARCHITECTURE.md`
4. `docs/EVALUATION.md`

Do not start by adding embeddings, rerankers, tools, or more agent infrastructure.

## First next-session objective

Run a **small controlled pilot on the existing fixture/control substrates** to prove the experiment protocol end to end before spending time on the full target-machine graph.

Freeze one tiny deterministic task set and compare at least:

```text
A  one-pass feed-forward
B  repeated passes, feedback off
C  repeated passes, feedback on
D  zero bridge
E  random bridge
F  zero root input
G  synthetic-stage control
```

Where applicable also run:

```text
Neural only
Neural + JEV
Neural + LLM
Neural + JEV + LLM
```

Use the same cases and scorer across variants.

## Required pilot settings

For independent cases:

```text
reset_policy = reset_per_case
repetitions >= 1 for deterministic controls
repetitions > 1 for stochastic external models
condition_order_seed = fixed integer
```

Record and inspect:

- task-set hash;
- variant hash;
- exact architecture;
- harness passes;
- feedback setting;
- bridge/input/stage overrides;
- state/context artifacts;
- provider receipts where enabled;
- task score;
- uncertainty;
- compute signatures;
- `compute_matched`.

The pilot is successful when two genuinely different variants can be replayed and compared without hidden state/config differences.

## Then move to the primary run

On the target machine:

1. install/verify the pinned Cook and MaleCNS datasets;
2. run canonical `primary-full`;
3. confirm exact MaleCNS counts:
   - 166,700 neurons;
   - 25,582,938 directed connections;
   - 124,177,617 synaptic contacts;
4. confirm full per-pass recordings exist;
5. confirm the end-to-end receipt binds source + compiled hashes;
6. confirm `primary_experiment_ready = true` only for the canonical unshuffled whole-state bridge path;
7. separately exercise authenticated JEV/LLM variants.

## First real hypothesis family

Use the same task set to compare:

```text
ordinary LLM baseline
JEV only
LLM only
Cook only
MaleCNS only
Cook → MaleCNS
full feed-forward composition
repeated no-feedback composition
closed-loop composition
zero/random bridge controls
zero input
synthetic reservoir
shuffled MaleCNS topology
```

The questions are:

1. Does architecture change the internal trajectory?
2. Does it change task performance?
3. Does the combination add something beyond its parts?
4. Does any improvement survive compute matching and null controls?

## Known research dimensions for later

Only after the first experiment produces interpretable evidence:

- structured or population-targeted feedback;
- alternative input encoders;
- alternative whole-state readouts;
- embeddings;
- rerankers;
- additional model providers;
- generic component registry;
- minimal agent/tool loop.

## Do not reopen as bugs

These are already implemented and tested:

- common `TaskResult`;
- architecture variants;
- harness-pass separation;
- reset/repetition/order manifests;
- whole-state bridge;
- bridge/input/stage/topology null controls;
- per-pass state/context persistence;
- strict JEV validation;
- invalid LLM-result handling;
- end-to-end readiness receipt;
- source/compiled hash binding;
- compute signatures;
- feedback source/context provenance.

If a future change regresses any of those, treat it as semantic drift.
