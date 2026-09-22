# HIVE Composition Experiment Audit

Date: 2026-09-22  
Status: **software integrity pass complete; empirical validation pending**

## Scope

HIVE is currently an experimental composition lab, not a general agent harness.

The research object is the **composition topology**:

```text
input
→ neural substrate(s)
→ explicit bridge/readout
→ JEV and/or LLM
→ optional bounded feedback
→ repeated harness pass when configured
→ common TaskResult
```

The central questions are:

1. Does changing the composition change the internal computation?
2. Does that change improve, worsen, or leave task performance unchanged?
3. Does a composition contribute something beyond its individual parts and beyond simply spending more compute?

## Current implementation truth

### Execution model

Implemented:

- ordered executable architecture tags;
- removable/reorderable/repeatable neural, bridge, readout, JEV, LLM, verifier, and feedback components;
- independent JEV and LLM toggles;
- explicit `harness_passes` distinct from neural-engine substeps;
- feedback independently enabled/disabled and targeted;
- transient per-run/per-variant architecture overrides without mutating the saved Core;
- transient bridge, root-input, neural-engine, and neural-config controls.

The runtime no longer uses “integration cycle” as the canonical concept. A **harness pass** means one complete traversal of the tagged architecture over the same input.

### Neural substrates

Implemented:

- full corrected Cook C. elegans topology runtime;
- full MaleCNS v1.0 sparse runtime;
- 1,045-neuron MaleCNS locomotor control;
- deterministic synthetic reservoir;
- deterministic shuffled-MaleCNS topology control.

The scientifically defensible description remains:

> **engineered dynamical computation over measured connectome topology**

The topology is measured. The state dynamics, sign rules, normalization, task input encoding, bridge encoding, readout, and feedback transforms contain explicit engineering choices.

### Handoff and input controls

Implemented:

- canonical `whole_state_projection_v1` Cook → MaleCNS bridge;
- legacy first-N excerpt projection control;
- random projection control;
- zero/null bridge control;
- explicit zero root-input encoder control;
- transient synthetic neural-stage substitution;
- deterministic `shuffle_presynaptic_v1` full-MaleCNS topology null.

Control variants are classified as controls and cannot satisfy the canonical primary-readiness gate.

### Provider/readout integrity

Implemented:

- small neural states are passed losslessly;
- large neural states use deterministic whole-state multiresolution readout derived from the complete state;
- complete-state SHA-256 binding;
- provider-facing context artifacts persisted by run/pass/component;
- provider receipts bind request/response hashes, provider/model identity, timing, and token usage when supplied by the backend;
- JEV responses are strictly validated against declared typed questions;
- malformed structured LLM task output is marked invalid rather than silently converted to valid zero feedback;
- LLM and JEV feedback traces include source call/context provenance;
- feedback adapters are explicitly versioned.

### Evaluation integrity

Implemented:

- architecture-independent `TaskResult`;
- common scorer surface;
- `ArchitectureVariant` beyond the original JEV/LLM 2×2;
- frozen task-set hash;
- worker/variant hashes;
- explicit reset policy;
- repetitions;
- deterministic per-repetition condition ordering;
- durable `ExperimentRun` manifest;
- task score, failure count, latency, uncertainty, provider-call counts, neural-stage-call counts, and harness-pass counts;
- compute signatures and an explicit `compute_matched` flag;
- experiment export includes runs, provider receipts, experiment manifests, state artifacts, and provider-facing contexts.

### Primary readiness

The readiness gate now requires one canonical end-to-end execution rather than disjoint stage receipts.

A readiness-promoting run must prove:

```text
full Cook
→ canonical whole_state_projection_v1 bridge
→ full unshuffled MaleCNS
→ readout
```

and bind:

- verified install receipts;
- Cook source SHA-256;
- MaleCNS source-file hashes;
- compiled MaleCNS array hashes;
- compiled manifest hash;
- exact stage counts;
- resolved architecture/config hash;
- full per-pass numerical state artifacts;
- provider/readout context artifacts;
- one end-to-end execution receipt.

Null/random/shuffled/synthetic/input-zero controls cannot write the canonical readiness receipt.

## Software gaps closed during this audit

The following earlier findings are now resolved:

- JEV/LLM-only 2×2 evaluator → generalized architecture variants;
- no common task answer → `TaskResult`;
- first-32 Cook bridge → canonical whole-state bridge + explicit controls;
- case-state contamination → explicit reset policy;
- disjoint stage receipts satisfying readiness → end-to-end receipt required;
- provider context hashed but not persisted → context artifacts persisted/exported;
- repeated full-state recordings overwriting each other → per-pass/component artifacts;
- no durable experiment grouping → `ExperimentRun`;
- harness repetition conflated with neural substeps → separate `harness_passes`;
- feedback hidden behind JEV config → independent feedback controls/targets/adapters;
- malformed LLM output silently becoming zero feedback → invalid structured result;
- weak JEV schema validation → strict typed validation;
- no bridge/null controls → whole-state/random/zero/legacy controls;
- no input null → explicit zero root-input control;
- no shuffled topology control → deterministic shuffled MaleCNS null;
- no compute accounting → compute signatures + provider usage capture;
- weak dataset/compiled provenance → source + compiled hash binding;
- feedback provenance incomplete → source call/context bound into trace;
- stale “integration cycle” model → canonical harness-pass terminology.

## What remains empirical, not a software bug

These cannot be completed by repository edits alone:

1. install and verify the pinned full datasets on the target machine;
2. execute the exact full 166,700-neuron / 25,582,938-edge / 124,177,617-contact MaleCNS runtime;
3. obtain the canonical end-to-end primary receipt from that real execution;
4. exercise authenticated real JEV/LLM providers for provider-enabled variants;
5. choose and freeze the first real benchmark task set;
6. run enough repetitions for stochastic providers;
7. compare feed-forward, repeated-no-feedback, closed-loop, ablations, and null controls;
8. determine whether any observed improvement survives compute matching and null controls.

## Remaining research-design limitations

These are deliberate future experimental dimensions, not unresolved integrity defects:

- current feedback is bounded scalar modulation rather than learned/structured population-target feedback;
- current full-state provider representation is multiresolution rather than literal 166,700-value JSON;
- root task encoding is engineered and should itself be tested as a variable for future task families;
- only exact/route scorers are currently generic; additional task families may need dedicated deterministic scorers;
- model aliases can still refer to provider-side mutable versions unless users pin concrete model identifiers;
- the system has not yet established a causal composition effect.

## Scientific interpretation gate

Do **not** claim that a composition is better unless:

- the task set is identical and hashed;
- reset/checkpoint policy is identical;
- the architecture/config variant is hashed;
- every declared component has an execution record;
- provider calls are tied to persisted contexts;
- feedback is tied to its source call/context;
- intermediate states are preserved;
- all variants use the same task scorer;
- relevant null controls are included;
- compute signatures are reported;
- stochastic conditions have repetitions and uncertainty;
- the effect survives the appropriate simpler/compute-matched comparison.

## Current maturity

```text
Execution ordering / traceability        strong
Provider-call truth                     strong
Whole-state readout                     strong
Architecture configurability            strong
Experiment grouping / reset semantics   strong
Bridge/input/topology controls           strong
Trajectory preservation                 strong
Primary readiness semantics             strong
Full target-machine execution           pending empirical proof
Real composition effect                 not established
```

The next meaningful work is **running the experiment**, not adding more harness machinery.
