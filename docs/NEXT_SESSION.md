# HIVE — Next Session Handoff

Date prepared: 2026-09-22  
Canonical audit: `docs/AUDIT.md`

## Do not change the project goal

HIVE is **not currently a full agent harness**.

The near-term project is:

> Build loops and staged calls that let us experimentally compare different compositions of neural substrates, JEV, LLMs, and later other processors.

A future minimal agent harness may reuse successful HIVE composition patterns, but terminal/tool autonomy is not the current milestone.

## Start the next session here

Read, in order:

1. `docs/AUDIT.md`
2. `docs/STATE.md`
3. `docs/ARCHITECTURE.md`
4. `src/hive_connectome/evals.py`
5. `src/hive_connectome/app.py` — `/api/evals/run`
6. `src/hive_connectome/pipeline.py`
7. `src/hive_connectome/workers.py`

Do not start by adding new models/components.

## First implementation target

The first target should be **experiment truth**, not new architecture features.

Implement a minimal composition-comparison harness with:

### A. TaskResult

A canonical architecture-independent final result, roughly:

```text
answer
structured_output
confidence (optional)
evidence refs
unresolved
```

The exact schema can be task-specific, but every architecture must expose something the same scorer can evaluate.

### B. ArchitectureVariant

A variant should freeze at minimum:

```text
variant id
architecture tags/order
neural substeps/settings
harness passes
feedback enabled
feedback sources + targets
bridge config
readout config
JEV config/model/questions
LLM config/model/prompt
reset/checkpoint policy
```

Compute a deterministic config hash.

### C. ExperimentRun manifest

Persist one object binding:

```text
experiment id
task-set hash
variant hashes
run IDs
case IDs
condition order
repetition
scorer/version
timestamps
```

### D. Reset semantics

Independent benchmark cases must start from the same state.

Support explicit modes:

```text
reset_per_case
restore_checkpoint_per_case
persistent_sequence
```

## Second implementation target

Fix the primary biological handoff.

The current canonical bridge still uses `source.state_vector[:32]` and at most 24 target drives.

Do not replace it with another unexplained compression. Make bridge strategies explicit and testable.

At minimum compare:

```text
legacy excerpt projection       control
whole-state deterministic projection
random projection control
zero/null bridge
```

Later semantic/learned encoders can be added separately.

## Third implementation target

Separate recurrence concepts in configuration.

Do not let one variable represent all of these:

```text
neural substeps
harness passes
cross-component feedback
```

A clean feed-forward run means:

```text
harness_passes = 1
feedback = off
```

A repeated-but-no-feedback run means:

```text
harness_passes > 1
feedback = off
```

A true closed loop means:

```text
harness_passes > 1
feedback = on
```

## Fourth implementation target

Fix observability before running the science.

Current full state artifacts overwrite earlier calls.

Persist:

```text
run
→ cycle/pass
→ component index
→ stage step
→ full state artifact
```

Also persist every provider-facing readout/context and bind:

```text
provider call
→ context hash/artifact
→ provider output
→ feedback application
```

## Fifth implementation target

Strengthen readiness.

Current stage-level receipts can satisfy Cook and MaleCNS readiness independently.

Primary readiness must prove one canonical run executed:

```text
full Cook
→ declared bridge
→ full MaleCNS
```

with exact dataset hashes and resolved architecture/config.

## Required control set before interpreting results

Do not claim architecture benefit until these are executable:

```text
ordinary LLM baseline
JEV only
LLM only
Cook only
MaleCNS only
Cook → MaleCNS
synthetic reservoir
shuffled topology
zero feedback
shuffled feedback
feed-forward full composition
repeated no-feedback composition
closed-loop composition
```

## The first questions the harness must answer

Keep the explanation simple:

1. Does changing the architecture actually change what the system does internally?
2. Does that make the task result better, worse, or the same?
3. Does the combination contribute something beyond the individual parts?

Everything else is supporting measurement.

## Important known gaps not to lose

Critical:

- eval is only a JEV/LLM 2x2;
- no canonical task answer/scorer;
- Cook→MaleCNS bridge truncates to first 32 values by default;
- eval cases inherit state within each condition;
- primary readiness accepts disjoint stage executions;
- provider request context is hashed but not fully persisted;
- full stage recordings overwrite earlier cycles;
- eval runs lack a durable experiment-group manifest.

High:

- harness repetition vs neural recurrence vs feedback are conflated;
- generic input encoding is hash-based;
- feedback is scalar/global;
- JEV→feedback formula is hand-written;
- malformed LLM output silently becomes zero feedback;
- strict JEV output validation is absent;
- several documented controls are not implemented;
- comparisons are not compute-matched;
- task sets/condition order/repetitions are not frozen;
- mutable model aliases reduce reproducibility;
- readout fidelity is not experimentally validated;
- readiness does not bind dataset/compiled hashes strongly enough;
- feedback trace lacks source context/call provenance.

## Scope guard

Do not spend the next session implementing:

- general terminal autonomy;
- dozens of tools;
- browser-agent loops;
- general subagent orchestration;
- embeddings/rerankers as production features;
- plugin ecosystems.

Those come after the experiment harness can distinguish a real composition effect from extra compute, state contamination, arbitrary encoders, or evaluation artifacts.

## Completion target for next session

A good next-session endpoint is not “more features.”

It is:

> HIVE can run a small fixed task set through at least two genuinely different architecture variants, start each case from identical state, emit a common TaskResult, preserve every intermediate state/context, and score the variants with one common evaluator.

Once that works on fixtures/control substrates, move it to the full Cook + full MaleCNS primary run.
