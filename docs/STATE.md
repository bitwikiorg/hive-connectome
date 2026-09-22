# HIVE semantic state — v0.7

This file is the human-readable canonical state of the experiment. The machine-readable contract is `config/experiment_contract.json`.

## CURRENT COMPOSITION AUDIT

The architecture/composition audit dated 2026-09-22 is canonical for the next implementation phase:

- `docs/AUDIT.md` — full gap and scientific-integrity audit;
- `docs/NEXT_SESSION.md` — exact next-session implementation handoff;
- `docs/ROADMAP.md` — roadmap realigned around composition experiments rather than a general agent harness.

The immediate goal is to make staged vs recurrent architecture comparisons causally interpretable before adding new processor types.

## HYDRATE — what the study actually is

The primary experiment is:

```text
full Cook C. elegans connectome
        ↓
explicit neural bridge
        ↓
full MaleCNS v1.0 connectome
        ↓
whole-state neural representation
        ↓
JEV independently ON/OFF
        ↓
LLM independently ON/OFF
        ↓
bounded recurrent feedback
        ↺ same-input neural refinement
        ↓
fixed task + fixed data + fixed evaluation
```

The full MaleCNS graph is the central Bee substrate. It is not an optional enhancement and may not be replaced by the 1,045-neuron locomotor subgraph in the primary experiment.

## STRUCTURE — semantic ownership

### Primary substrates

- **Larva:** full corrected Cook C. elegans hermaphrodite connectome.
- **Bee:** full MaleCNS v1.0 graph: 166,700 retained neurons, 25,582,938 directed connections, and 124,177,617 synaptic contacts in the pinned runtime contract.
- **Bridge:** explicit, logged, configurable Core-stage handoff. The canonical biological chain uses `whole_state_projection_v1`; excerpt/random/zero bridges are controls.

### Core and Hive

A **Core** is one complete experimental unit: data environment + zero or more neural stages + explicit bridges + JEV + optional LLM + recording policy.

A **Hive** is an ordered chain of Cores with provenance-linked handoffs.

Neural stages are removable. A Core can run worm-only, fly-only, neither, or another configured chain without pretending that a removed stage executed.

### Independent experiment toggles

```text
JEV OFF · LLM OFF
JEV ON  · LLM OFF
JEV OFF · LLM ON
JEV ON  · LLM ON
```

Those four runs must use the same substrate, data, prompt, task, and evaluation case. Every enabled inference member executes on every harness pass; JEV is not an LLM gate.

### Controls only

- MaleCNS 1,045-neuron locomotor subgraph;
- synthetic/random reservoir;
- shuffled connectome;
- no-connectome path;
- Larva-only;
- Bee-only.

## VERIFY — current implementation truth

As of v0.7:

- Cook full-connectome engine: **implemented**.
- MaleCNS 1,045-neuron locomotor control: **implemented**.
- Full MaleCNS pinned dataset manifest: **implemented**.
- Full MaleCNS sparse execution engine `malecns_full_v1`: **implemented**.
- Generic Core graph + explicit bridges: **implemented**.
- Hive Core chaining: **implemented**.
- Venice JEV / Venice chat / LM Studio proof-call receipts: **implemented**.
- Whole-state neural representation for JEV/LLM context: **implemented**.
- Same-input recurrent neural → JEV → LLM → feedback integration loop: **implemented**.
- Ordered comma-tagged Core architecture with executable stage/bridge/readout/provider/feedback tags: **implemented**.
- Experiment ZIP export with JSONL, CSV, provider receipts, execution receipts, and optional full state artifacts: **implemented**.
- Primary readiness remains runtime-derived: **installed data and implemented code are not enough**.

The primary experiment becomes READY only after the exact full datasets execute successfully in the canonical Cook → whole-state bridge → full MaleCNS path, preserve full per-pass state/context artifacts, and produce a matching end-to-end receipt.

## PROMOTION GATE

```text
[x] full MaleCNS importer/runtime implemented
[x] expected node/connection/synapse counts encoded in the contract
[x] execution receipts required by readiness
[x] Cook → full MaleCNS handoff implemented
[x] JEV/LLM four-way ablation harness exists
[ ] target machine downloads + verifies the pinned full MaleCNS files
[ ] target machine executes the exact full graph successfully
[ ] resulting execution receipt matches 166700 / 25582938 / 124177617
```

The Windows first-run script now installs the full required pack and performs a `primary-full` no-JEV/no-LLM smoke run so the target machine can satisfy the remaining runtime gates empirically.

## ANTI-DRIFT INVARIANTS

1. Full MaleCNS is required for the primary Bee stage.
2. Subgraphs never silently satisfy a full-graph requirement.
3. Installed ≠ imported ≠ executed.
4. A stage requested by the experiment may not silently fall back.
5. JEV/LLM toggles never alter the neural substrate.
6. Controls remain clearly labeled controls in code, setup, GUI, receipts, and documentation.
7. Readiness is derived from the experiment contract plus execution receipts, not marketing copy.
8. External inference claims require actual provider-call receipts, not a model-list response.
9. JEV/LLM context must be derived from the complete executed neural state; arbitrary first-N state excerpts are forbidden as the primary neural representation.
10. If JEV or an LLM is enabled, it executes on every harness pass or the run fails explicitly.
11. JEV/LLM feedback must affect a same-input neural refinement cycle when harness_passes > 1.
12. Core architecture order is defined by executable component tags; the runtime, plan API, GUI, traces, and tests must resolve the same ordered sequence.
13. A JEV/LLM call may not consume stale neural context: a readout must follow the most recent neural/bridge change before a provider call.
14. JEV and LLM feedback are independent sources with independent enable flags and target sets.
15. LLM context may contain `jev_decision` only when a real regular JEV call executed earlier in that harness pass.
16. `jev_verify` may operate without a regular `jev` tag; it verifies the latest LLM output and includes prior JEV state only if that state actually exists.

## ROLLBACK RULE

Any change that makes a reduced graph satisfy `primary_experiment_ready`, calls the full MaleCNS dataset optional, describes a control result as the primary study, truncates the primary inference context to arbitrary neural excerpts, restores JEV-gated LLM execution, or prevents enabled inference members from participating in the same-input recurrent Core, hardcodes a path that ignores the saved component-tag sequence, or reports a different architecture than the runtime actually executes is semantic drift and must be rejected or rolled back.
