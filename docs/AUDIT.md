# HIVE Connectome — Composition Experiment Audit

Audit date: 2026-09-22  
Audited code head: `723ca23d51e5f040d72346c687a0b9a05eeb3db5`  
Scope: architecture/composition experiment integrity, not a general agent-harness build.

## Executive conclusion

HIVE is now a credible **execution harness for staged and recurrent heterogeneous computation**, but it is not yet a credible **causal comparison harness** for answering the central research question:

> Given the same task and comparable resources, does a particular composition of neural substrates, JEV, LLMs, and later other processors perform better than its alternatives?

The runtime is stronger than the evaluator. HIVE can now show what components executed, in what order, with provider receipts and neural-state hashes. It cannot yet prove that architecture A solved a task better than architecture B, nor can it yet cleanly attribute why.

This audit treats HIVE as a laboratory for composition patterns, not as a finished agent framework. A future agent harness may grow out of successful composition patterns, but terminal/tool autonomy is not required for the present research question.

## Canonical project definition

HIVE Connectome is an experimental runtime for composing heterogeneous computational components into explicit staged or recurrent architectures and measuring what each component and composition adds.

The initial component family is:

```text
input
→ C. elegans connectome
→ explicit bridge
→ MaleCNS connectome
→ whole-state readout
→ JEV
→ LLM
→ optional feedback
→ optional additional pass
→ output
```

Every element must be independently controllable. Architecture order, repeated calls, feedback, and harness repetition are experimental variables, not hidden implementation behavior.

The initial scientific objective is **not** to prove that connectomes or recursion are beneficial. It is to determine whether any measurable and reproducible advantage exists, under controlled comparisons, and to localize where that advantage comes from.

## What is already strong

### Executable architecture order

The Core architecture is an ordered tag sequence. Neural stages, bridges, readout, JEV, LLM, JEV verification, and feedback execute in tag order. Reordering or repeating tags changes the computation.

### Orthogonal JEV / LLM execution

JEV and LLM calls are independently toggleable. JEV no longer gates whether the LLM runs. Disabled components are recorded as skipped rather than silently substituted.

### Context freshness protections

Provider calls require a fresh whole-state readout after neural/bridge changes. JEV outputs are bound to the readout hash that produced them, and stale JEV state is not injected into an LLM call for a different readout. JEV verification also rejects an LLM result generated from a stale readout.

### Whole-state provider readout

JEV/LLM no longer receive arbitrary first-N MaleCNS state excerpts as their primary neural context. Small states are lossless. Large MaleCNS states use deterministic multiresolution statistics, chunks spanning all neurons, salient activations, group summaries, firing information, deltas, and a full-state SHA-256.

### Real provider truth

Enabled JEV/LLM providers fail explicitly if unavailable. Real integration/scientific runs are distinct from unit tests using mocks. Provider call receipts store model, endpoint, timing, HTTP status, request/response hashes, and call IDs.

### Full MaleCNS engine exists

The full MaleCNS sparse runtime is implemented with exact expected graph counts encoded. The code correctly labels its LIF-style dynamics, transmitter sign rule, normalization, input encoding, and feedback as engineering choices rather than biological ground truth.

---

# Findings

Severity meanings:

- **Critical** — can invalidate the principal experiment or make a claimed result scientifically uninterpretable.
- **High** — can materially confound attribution, reproducibility, or comparison.
- **Medium** — limits extensibility or clarity but does not by itself invalidate a correctly constrained run.

## C1 — Evaluation is still a JEV/LLM toggle test, not an architecture experiment

`src/hive_connectome/evals.py` defines only four conditions:

```text
JEV off / LLM off
JEV on  / LLM off
JEV off / LLM on
JEV on  / LLM on
```

That is useful, but the current research question is broader. HIVE needs to compare, as first-class variants:

```text
feed-forward vs recurrent
one pass vs repeated passes
different component order
different bridges
feedback off vs on
different feedback targets
different neural substrates
different readout/encoding strategies
eventually embeddings/rerankers/other processors
```

The evaluator must accept an explicit **architecture variant matrix**, not only two booleans.

## C2 — There is no canonical task-output contract

The pipeline currently has several possible outputs:

- `DecisionBundle` from JEV;
- a heuristic `brain_readout()` when JEV did not produce the final decision;
- free-form LLM text constrained to JSON keys `analysis`, `unresolved`, and `neural_feedback`;
- neural telemetry and modulation.

There is no universal field representing:

> **the system's answer to the task**

The LLM system prompt does not even require an `answer` field. `ExperimentSpec.expected_output` and `eval_metric` are descriptive strings, not executable output schemas or scorers.

The current eval endpoint scores `route` from `result.decisions`. In an LLM-only or Neural+LLM condition, the LLM can materially solve the task while the evaluator ignores that output entirely.

Before comparing architectures, HIVE needs a canonical `TaskResult` and task-specific scorer independent of which architecture generated it.

## C3 — The primary Cook → MaleCNS bridge still truncates the neural state

Provider context was fixed, but the biological-to-biological bridge still uses:

```python
source.state_vector[:source_excerpt]
```

with the legacy default:

```text
source_excerpt = 32
target_count = 24
```

For Cook, the full neural state is available, but the default `state_projection_v1` uses only the first 32 values and projects at most 24 values into target candidates.

Therefore the nominal primary chain is currently closer to:

```text
full Cook execution
→ arbitrary first-32 state slice
→ <=24 MaleCNS drives
→ full MaleCNS execution
```

than to a principled whole-state Cook → MaleCNS handoff.

This is one of the most important remaining architecture gaps.

## C4 — Evaluation cases contaminate each other through persistent neural state

`/api/evals/run` resets the pipeline **once per toggle condition**, then executes all evaluation cases sequentially.

Because neural engines are stateful, case B inherits neural state from case A. That may be correct for an explicitly defined streaming-memory experiment, but it is incorrect for independent benchmark cases.

The harness needs an explicit reset policy:

```text
reset_per_case
reset_per_variant
persistent_sequence
checkpoint_restore
```

Independent benchmark tasks should default to reset/checkpoint restore per case.

## C5 — Primary readiness does not prove the primary pipeline actually ran end-to-end

Readiness checks one execution receipt for Cook and one execution receipt for full MaleCNS. Those receipts are stored by:

```text
execution_receipts/<engine>--<pack>.json
```

They can come from different runs, different workers, different architectures, and different inputs.

For example, a Cook stage can be executed in a control worker, and full MaleCNS can be executed separately. If both receipts satisfy counts, readiness can become true without proving:

```text
Cook
→ declared bridge
→ full MaleCNS
```

ever executed together in one canonical primary run.

Primary readiness must require a **single end-to-end primary execution receipt** containing the resolved architecture, bridge, worker/config hash, stage receipts, dataset hashes, and run ID.

## C6 — Provider input receipts are hashes, not replayable context records

Provider transport receipts store `request_hash`, but the exact intermediate provider request is not persisted as a first-class run artifact.

The final run stores neural observations and the final stage readout, but JEV/LLM may have been called multiple times on earlier readouts. `cycle_trace` records context hashes, not the full context content.

Therefore after the run we can prove:

> “JEV call X received some payload with hash H”

but cannot always inspect/replay exactly what payload H contained.

For scientific reproducibility, every provider-facing readout/context should be persisted or stored as a content-addressed artifact referenced by hash.

## C7 — Full neural recordings overwrite earlier cycles and repeated stage calls

`_record_full_state()` currently writes:

```text
recordings/<run_id>/<stage_id>.npz
```

Every execution of the same stage in a run writes the same path.

If a stage executes twice because:

- the architecture repeats the stage;
- `integration_cycles > 1`;
- a feedback experiment performs a refinement pass;

earlier full-state artifacts are overwritten. Only the final full state survives.

That prevents analysis of the exact neural trajectory—the object we explicitly want to compare.

Artifacts need cycle/component/step identity, for example:

```text
recordings/<run>/<cycle>/<component-index>-<stage>-step-<n>.npz
```

## C8 — The evaluator has no durable experiment-run grouping

Individual pipeline runs are persisted, but `/api/evals/run` does not persist a canonical experiment session that binds:

- task-set version/hash;
- variant definitions;
- condition order;
- run IDs;
- reset policy;
- repetitions;
- scorer version;
- summary statistics.

A later analysis must infer which runs belonged together. That is unsafe.

A matched experiment needs a durable `ExperimentRun`/manifest ID.

---

## H1 — Three different meanings of “recursion” are currently conflated

These are separate experimental variables:

### Neural recurrence

Internal connectome dynamics and substeps:

```text
neuron → neuron → neuron
```

### Harness repetition

`integration_cycles` reruns the architecture on the same input:

```text
architecture pass 1
→ architecture pass 2
```

### Cross-component feedback

A later processor modifies an earlier neural stage:

```text
JEV / LLM
→ feedback
→ neural stage
```

Current code always uses `worker.runtime.integration_cycles`, even when JEV and LLM are disabled. Thus “feedback off” does not imply “single-pass feed-forward.”

The experiment schema must name these variables independently.

## H2 — Input encoding is reproducible but semantically arbitrary

Without explicit neural stimulus, Cook and MaleCNS convert task payloads into sensory drives through SHA-256-based deterministic mappings.

This is useful as a reproducible generic adapter, but it is not a semantic sensory encoder. A performance effect could reflect the hash mapping rather than connectome computation.

Input encoding must be treated as an experimental component with controls:

- deterministic hash encoder;
- fixed random projection;
- learned/task-specific encoder;
- semantic embedding projection;
- null/zero encoder;
- domain-specific sensory mapping when justified.

## H3 — Feedback is currently a one-dimensional global control channel

JEV and LLM each reduce to one scalar `[-1, 1]`. Full MaleCNS applies it as a uniform tonic offset:

```python
self.v += tonic + feedback * 0.05
```

Cook similarly injects a global scalar term.

This is a valid first feedback experiment, but it must not be confused with a general mechanism for JEV/LLM to “write neural state.”

Future experiments may compare:

- scalar global modulation;
- targeted population modulation;
- sparse neuron/group stimuli;
- structured feedback vectors;
- read-only neural state.

## H4 — The JEV feedback formula is an untested hand-written adapter

JEV feedback is derived from:

```text
meaningful_signal
+ novelty
→ fixed weighted formula
→ scalar feedback
```

That mapping is itself an architecture hypothesis. It needs to be explicit, versioned, replaceable, and independently ablated.

## H5 — Malformed LLM structured output silently becomes zero feedback

`_llm_feedback_signal()` returns `0.0` when:

- JSON parsing fails;
- `neural_feedback` is missing;
- conversion fails.

That makes malformed output observationally identical to a deliberate zero-feedback decision.

The structured LLM contract needs schema validation and an explicit status:

```text
valid_output
invalid_output
missing_feedback
feedback=0.0
```

These are not equivalent.

Also, `PipelineResult.unresolved` is initialized but not populated from the LLM's requested `unresolved` array.

## H6 — JEV answer shape is not strongly validated at the experiment boundary

`DecisionBundle.answers` is an arbitrary dictionary. Pipeline helpers fall back to neutral values such as 0.5 when expected fields are absent.

For software resilience that is convenient. For a scientific run it can hide a provider/schema failure.

Strict experiment mode should validate that every requested JEV question returned the required type and value domain.

## H7 — Declared null controls are not all runnable first-class controls

The contract/documentation lists:

- shuffled connectome;
- random reservoir;
- no-connectome;
- synthetic reservoir;
- Larva-only;
- Bee-only.

A deterministic synthetic mini-brain exists. Architecture removal can approximate no-connectome/Larva-only/Bee-only cases.

But there is no implemented topology-shuffle engine and no explicit random-reservoir control matching the claimed control set. Code search finds no runnable shuffled-connectome implementation.

Controls should exist as executable, versioned variants, not only documentation.

## H8 — Comparisons are not compute-matched

A recurrent composition can make more provider calls and more neural passes than a simpler composition. Better results could be due merely to more inference compute.

The harness currently reports call counts and latency, but does not build compute-matched baselines.

Required comparisons include, where feasible:

```text
same LLM call count
same JEV call count
same neural pass count
same token budget / context budget
same wall-clock or cost envelope
```

Provider receipts currently do not normalize token usage/cost across providers.

## H9 — Task sets and condition order are not frozen for reproducible comparisons

Eval cases are submitted in the API request. There is no canonical dataset hash/version persisted with an experiment run.

Conditions also execute in a fixed order unless the caller manually changes them. Hosted model drift, caching, temporal load, or stochasticity can correlate with condition order.

A rigorous harness needs:

- task-set content hash;
- scorer hash/version;
- randomized or counterbalanced condition order;
- explicit repetitions;
- fixed seeds where supported.

## H10 — Model identity is not fully pinned

`jev-latest` is a mutable alias. LLM model names may also point to mutable local/hosted builds.

Receipts record returned model names, which is good, but reproducible experiments should prefer immutable model IDs/checkpoints when possible and record provider/model metadata.

## H11 — The whole-state readout is an encoder and has not itself been validated

`whole_state_multiresolution_v1` is far better than arbitrary excerpts because it touches every neuron and exposes salient information.

But it remains an engineered lossy representation. Its fidelity to task-relevant neural information has not been measured.

It should eventually be a first-class architecture component so we can compare:

- lossless dense state where feasible;
- current multiresolution readout;
- group-only summaries;
- top-k sparse readout;
- learned/embedded readout;
- random projection controls.

## H12 — Dataset integrity is stronger at install time than at readiness/runtime time

The installer validates pinned hashes. However:

- readiness checks file existence rather than invoking installer hash validation;
- execution receipts do not bind the dataset hashes used;
- an existing compiled MaleCNS manifest is accepted primarily by counts/version/array presence, not by re-verifying every source/compiled array hash each run.

For strong experiment provenance, the end-to-end receipt should bind exact source and compiled hashes.

## H13 — Intermediate feedback provenance is incomplete

JEV and LLM calls carry context hashes, but the `feedback` trace records only source value and targets. If neural state changes between provider call and feedback application, the feedback may intentionally be delayed—but the trace does not identify the exact provider context that produced it.

Feedback records should include source call ID and source context hash.

---

## M1 — The executor is configurable but not yet a generic component registry

Neural stage IDs and bridge IDs are generic, but reserved components are hard-coded in `pipeline.py`:

```text
readout
jev
llm
jev_verify
feedback
```

Adding an embedder or reranker currently requires editing the executor.

That is acceptable for the present phase. We should not build a full plugin/agent framework before proving the composition experiment. Later, a small `Component` interface/registry can generalize the loop without importing a large agent framework.

## M2 — Some repository surfaces are beyond the present research scope

The repository already contains:

- browser modes;
- schedulers/daemons;
- multi-Core Hive chaining;
- source ingestion;
- MCP;
- future worker-output routing.

These can remain, but they should not drive the next research phase. The central work is architecture comparison, not general autonomy.

## M3 — Documentation has historical drift

Before this audit:

- `docs/AUDIT.md` was still a v0.3.2 / 2026-09-19 audit and described the real connectome runtime as not yet implemented;
- `docs/ROADMAP.md` still listed the full MaleCNS parser/runtime and Cook→MaleCNS handoff as unimplemented, although those code paths now exist.

This audit supersedes that historical state.

---

# Scientific interpretation boundary

Even after the software gaps are fixed, HIVE should use precise language.

The system does execute measured connectome topology, but the dynamics are engineered.

For Cook:

- measured corrected anatomical topology;
- engineered graded recurrent dynamics;
- chemical adjacency workbook lacks complete signed physiological semantics in this runtime;
- generic task input is artificially encoded.

For full MaleCNS:

- measured retained graph topology;
- transmitter sign heuristic is an engineering choice;
- incoming-weight normalization is engineered;
- point-neuron LIF-like dynamics are engineered;
- tonic drive is engineered;
- task input mapping is engineered;
- feedback mapping is engineered.

Therefore the defensible description is:

> **engineered dynamical computation over measured connectome topology**

not “a simulated worm brain” or “a simulated fly brain.”

---

# The experiment HIVE should be able to run

The simplest meaningful architecture family should become:

## A — ordinary model baseline

```text
input → LLM → task answer
```

## B — staged feed-forward composition

```text
input
→ Cook
→ bridge
→ MaleCNS
→ readout
→ JEV
→ LLM
→ task answer
```

with one harness pass and no write-back.

## C — same composition, repeated without cross-component feedback

```text
pass 1
→ pass 2
```

This isolates whether simple repeated processing helps.

## D — closed-loop composition

```text
Cook
→ MaleCNS
→ JEV
→ LLM
→ feedback
→ Cook/MaleCNS
→ JEV
→ LLM
→ task answer
```

This tests whether write-back adds value beyond repetition.

## E — causal/null controls

At minimum:

```text
same topology + zero feedback
same topology + shuffled feedback
shuffled topology
synthetic reservoir
no neural substrate
Cook only
MaleCNS only
JEV only
LLM only
```

Then later:

```text
embedding → ...
reranker → ...
alternative readout → ...
alternative bridge → ...
```

The research object is **composition topology**.

---

# What HIVE must measure

The top-level questions remain intentionally plain:

1. **Does changing the architecture change the computation?**
2. **Does that change make the task result better, worse, or unchanged?**
3. **Does the combination do something that its parts do not do alone?**

Those questions require four measurement layers.

## Execution truth

Did exactly the declared components run?

Required evidence:

- architecture variant ID/hash;
- exact component order;
- stage execution receipts;
- bridge/readout identity;
- provider call IDs;
- model IDs;
- input/task hash;
- reset/checkpoint policy.

## State change

Did the architecture produce a different internal trajectory?

Useful metrics include:

- per-stage state hashes;
- trajectory distance;
- active/firing population change;
- state energy/distribution change;
- convergence/stability across passes;
- feedback magnitude/targets.

These are secondary scientific metrics, not the task score itself.

## Task outcome

Did the system solve the actual task better?

The scorer must be task-specific and architecture-independent:

- exact match;
- classification accuracy/F1;
- ranking metrics;
- structured extraction accuracy;
- deterministic programmatic evaluator;
- blind external judge only when no objective scorer exists.

## Cost / compute

What did the improvement cost?

Record:

- neural passes;
- JEV calls;
- LLM calls;
- tokens where available;
- latency;
- wall-clock;
- provider cost when available.

A more expensive architecture should be compared against a compute-matched simpler baseline.

---

# Required implementation order

Do not begin by adding embeddings, rerankers, tools, or more agent features.

## 1. Define a canonical task result and scorer

Create a real machine-readable task output contract. The same evaluator must score N, NJ, NL, NJL, feed-forward, recurrent, and future architectures.

## 2. Generalize evaluation from toggle matrix to architecture-variant matrix

A variant must freeze:

- architecture tags/order;
- integration/harness passes;
- feedback enabled/targets;
- bridge/readout configuration;
- neural engine parameters;
- provider/model configuration;
- prompt/question configuration;
- reset/checkpoint policy.

## 3. Separate the three recurrence variables

Represent independently:

- neural internal substeps;
- number of harness passes;
- cross-component feedback/write-back.

## 4. Fix Cook → MaleCNS handoff

Replace the arbitrary first-32 slice as the canonical primary bridge. Make bridge encoding explicit and ablatable.

## 5. Preserve every intermediate state and provider context

Do not overwrite repeated stage artifacts. Persist each readout/provider context by content hash and bind provider/feedback calls to it.

## 6. Fix evaluation isolation and grouping

Add:

- reset/checkpoint per independent case;
- sequence mode for memory experiments;
- experiment-run manifest;
- task-set hash;
- condition ordering;
- repetition index;
- scorer version.

## 7. Strengthen primary readiness

Require one canonical full-pipeline execution receipt, not independent stage receipts.

## 8. Implement real null controls

Especially:

- shuffled topology;
- shuffled feedback;
- zero feedback;
- synthetic/random matched reservoir;
- no-connectome baseline.

## 9. Add compute-matched comparison

Only after the task scorer is correct.

## 10. Generalize component registry later

After staged/recurrent composition can be evaluated correctly, add small generic processor components for embeddings, rerankers, classifiers, or other model calls.

---

# Acceptance gate before claiming a composition effect

A HIVE result should not be interpreted as evidence that architecture X is better unless all are true:

- identical task cases are used across variants;
- cases have a frozen content hash;
- independent cases start from the same checkpoint/reset state;
- model/provider versions are recorded;
- architecture/config has a deterministic variant hash;
- every declared component has an execution record;
- every provider call is tied to the exact persisted context it saw;
- every feedback application is tied to the provider output/context that caused it;
- repeated neural states are preserved rather than overwritten;
- the final task answer is scored by a common evaluator;
- null controls are included;
- compute/call counts are reported;
- multiple trials are run when stochastic components are present;
- result summaries include uncertainty, not only a single score.

---

# Current maturity

```text
Execution ordering / traceability        strong
Provider call truth                     strong
Whole-state provider readout            moderate-to-strong
Full connectome runtime                 implemented, target-machine proof pending
Architecture configurability            moderate-to-strong
Biological-to-biological handoff         weak
Task-output contract                    weak
Architecture comparison harness         weak
Null-control implementation             weak
Trajectory preservation                 weak
Primary readiness semantics             incomplete
Causal scientific evidence              not established
```

That is not a negative conclusion. It means the difficult runtime plumbing is now far enough along that the next work can focus on the part that makes the project scientifically meaningful: **fair architecture comparison**.

