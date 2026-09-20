# HIVE semantic state — v0.6

This file is the human-readable canonical state of the experiment. The machine-readable contract is `config/experiment_contract.json`.

## HYDRATE — what the study actually is

The primary experiment is:

```text
full Cook C. elegans connectome
        ↓
full MaleCNS v1.0 connectome
        ↓
JEV independently ON/OFF
        ↓
LLM independently ON/OFF
        ↓
fixed task + fixed data + fixed evaluation
```

The full MaleCNS graph is the central Bee substrate. It is not an optional enhancement and may not be replaced by the 1,045-neuron locomotor subgraph in the primary experiment.

## STRUCTURE — semantic ownership

### Primary substrates

- **Larva:** full corrected Cook C. elegans hermaphrodite connectome.
- **Bee:** full MaleCNS v1.0 graph: 166,700 retained neurons and 25,582,938 directed connections in the reference full-graph runtime; the pinned dataset also represents 124,177,617 synapses.

### Independent experiment toggles

```text
JEV OFF · LLM OFF
JEV ON  · LLM OFF
JEV OFF · LLM ON
JEV ON  · LLM ON
```

Those four runs must use the same substrate, data, prompt, task, and evaluation case.

### Controls only

The following are useful, but they are **not the primary experiment**:

- MaleCNS 1,045-neuron locomotor subgraph;
- synthetic/random reservoir;
- shuffled connectome;
- no-connectome path;
- Larva-only;
- Bee-only.

## VERIFY — current implementation truth

As of v0.6 state reset:

- Cook full-connectome data + compact Cook engine: **implemented**.
- MaleCNS 1,045-neuron locomotor control: **implemented**.
- Full MaleCNS pinned dataset manifest: **implemented**.
- Full MaleCNS execution engine: **NOT IMPLEMENTED**.
- Therefore the **primary experiment is NOT READY**.

Downloading the full MaleCNS files does not change that state. Data possession is not execution.

## ALIGN — correction from v0.5

v0.5 incorrectly promoted:

```text
Cook → 1,045-neuron MaleCNS locomotor subgraph
```

as the default study runtime. v0.6 explicitly demotes that path to **CONTROL / DEVELOPMENT ONLY**.

The runtime must never report the primary experiment as ready merely because the Cook pack and locomotor subgraph are installed.

## STABILIZE — anti-drift invariants

1. Full MaleCNS is required for the primary Bee stage.
2. Subgraphs never silently satisfy a full-graph requirement.
3. Installed ≠ imported ≠ executed.
4. A stage requested by the experiment may not silently fall back.
5. JEV/LLM toggles never alter the neural substrate.
6. Controls remain clearly labeled controls in code, setup, GUI, receipts, and documentation.
7. Readiness is derived from the experiment contract, not from marketing copy or a convenient runnable path.

## PROMOTION GATE — what v0.7 must prove

The primary experiment may be promoted to READY only when all of these are true:

```text
[ ] full MaleCNS dataset installed + verified
[ ] full MaleCNS importer loads the complete graph
[ ] runtime reports loaded node/connection counts and validates them
[ ] full graph actually propagates state during a run
[ ] execution receipt identifies full MaleCNS, not a control graph
[ ] Cook → full MaleCNS handoff works
[ ] JEV/LLM four-way ablation keeps substrate/data/task constant
[ ] null, shuffled, replay, reset, and transition tests pass
```

Until then, HIVE may run controls for development, but those outputs must be labeled **CONTROL RESULT — NOT PRIMARY EXPERIMENT**.

## ROLLBACK RULE

Any change that makes a reduced graph satisfy `primary_experiment_ready`, calls the full MaleCNS dataset optional, or describes a control result as the primary study is semantic drift and must be rejected or rolled back.
