# Inspiration Repo Audit — What to Reuse

Repositories audited include the supplied DesktopFly, DOOMFLY, Fly OCR, Fly Chess, fly-as-a-lm,
Fruit Fly Laboratory, fly-brain, WING, Fly/Wirehead, flybody, flyingtrade, FlyCoder, amfly,
yaxis-lab/fly-brain, plus the TypeSafe/Agent Zero plugin references.

## Patterns worth copying

### 1. Model/data boundary must be explicit

Best examples repeatedly state:

```text
measured anatomy != modeled physiology
real spikes != natural task semantics
connectome != proof of intelligence
```

HIVE should expose `engine`, `substrate`, encoder version, readout version, and source hashes in every run.

### 2. Causal lesion tests beat demos

DesktopFly tests graph removal, motor silencing, no-input behavior, steering perturbation, and display-rate invariance.

DOOMFLY explicitly discovered that apparently active behavior can survive black input because tonic currents/readouts still drive actions.

**Rule:** every new HIVE behavior gets a lesion/null test before it gets a marketing name.

### 3. Negative results are first-class

DOOMFLY preserves failed learning candidates.
`fly-as-a-lm` reports that ordinary models did better/faster.

**Rule:** eval storage keeps failures and rejected hypotheses, not only winners.

### 4. Separate computation from authority

`fly-766/fly` cleanly separates:

```text
neural proposal
action admissibility
accounting
verification
execution
```

For HIVE:

```text
worker output != tool permission
JEV output != policy
LLM output != authority
```

### 5. Exact replay matters

Strong repos pin:

- source URLs
- source hashes
- graph version
- seed
- model configuration
- checkpoints
- exact numerical environment when needed

HIVE eval receipts should do the same.

### 6. Engine portability is valuable

Observed implementations include Python/C++, Rust/WASM, JS/WASM/WebGPU, Electron, and event-driven CPU code.

**Rule:** keep HIVE's neural engine behind one adapter. Do not entangle the GUI/JEV/LLM with one simulator.

### 7. Small learned heads are useful

Fly OCR is especially relevant: retained connectome features + a small trained decoder produces a measurable task result.

That is a better precedent for HIVE than pretending recurrent state is already semantic.

### 8. Multiple brains can share graph data

amfly shows multiple logical MaleCNS instances. For HIVE, immutable topology should be shareable while each worker owns independent dynamic state.

### 9. State continuity needs its own tests

DesktopFly found bugs only when moving between modes/states, despite steady-state tests passing.

HIVE must test worker reset, pause/resume, provider failover, JEV toggle, LLM toggle, and chain handoff.

### 10. UI is telemetry, not evidence

Pretty neural views are useful, but sampled activity and animations must never be confused with the computed graph or evaluation result.

## Patterns to avoid

- treating a readout mapping as natural meaning;
- claiming learning because weights changed;
- selecting examples that look successful without a fixed benchmark;
- using the same LLM to both generate and grade with no independent check;
- hiding tonic inputs or fallback policies;
- turning one random seed into a performance claim;
- conflating reproducibility with biological validity;
- putting irreversible actions directly behind model outputs.
