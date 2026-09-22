# Architecture

## Runtime unit

A HIVE Core is one **integrated recurrent computation**, not a neural model followed by optional utilities.

```text
INPUT / DATA
    ↓
configured neural chain
    ↓
whole-state neural representation
    ↓
JEV                         independently ablatable
    ↓
LLM                         independently ablatable
    ↓
bounded recurrent feedback
    ↺ same input / next integration cycle
    ↓
recorded result + trace
```

A Core owns its experiment objective, data environment, neural configuration, explicit bridges, JEV questions, LLM configuration, recurrent integration-cycle count, recording policy, and outputs. A Hive chains multiple Cores only when the experiment explicitly requires a multi-Core topology.

## Comma-tagged executable architecture

A Core's architecture is an ordered list of executable component tags. Configuration accepts either a list or a comma-separated string. The default full composition is:

```text
worm,worm-to-fly,fly,readout,jev,llm,jev_verify,feedback
```

Tags are not descriptive metadata. The runtime resolves and executes them in exactly that order:

- neural stage IDs such as `worm` and `fly` call their configured neural engines;
- bridge IDs such as `worm-to-fly` execute that explicit bridge and queue its output for the target stage;
- `readout` builds the whole-state provider representation;
- `jev` calls the configured Venice Decisions model when JEV is enabled;
- `llm` calls the configured Venice or LM Studio model when the LLM is enabled;
- `jev_verify` performs the explicit post-LLM JEV verification call when enabled;
- `feedback` converts the latest enabled JEV/LLM feedback into bounded neural modulation.

Reordering tags changes the computation. Repeating a tag repeats that component call. Removing a tag removes that component from the architecture. JEV/LLM enable flags remain ablation switches: a tagged but disabled inference component is recorded as skipped rather than silently called.

A provider-facing `jev` or `llm` tag requires a `readout` after the most recent neural/bridge state change. Invalid orderings fail explicitly instead of silently consuming stale state.

## Neural state supplied to JEV and the LLM

The inference layers must receive a representation derived from the complete executed neural state.

For small substrates, HIVE sends the neural state losslessly. For large substrates such as full MaleCNS, HIVE uses `whole_state_multiresolution_v1`: global distributions, deterministic chunks covering every neuron, high-salience activations, recent firing activity, population summaries, temporal deltas, metadata, and a SHA-256 integrity hash of the complete state.

The representation is intentionally bounded for provider context limits, but it may not be replaced by arbitrary first-N excerpts.

```json
{
  "event": {},
  "neural_state": {
    "worm": {"whole_state": {}},
    "fly": {"whole_state": {}}
  },
  "bridges": []
}
```

## Recurrent integration

When JEV and/or an LLM are enabled, the default Core runs multiple integration cycles over the same input:

```text
neural pass
→ JEV decision
→ LLM reasoning
→ optional JEV verification
→ bounded feedback
→ neural refinement on the same input
```

Every enabled member executes on every integration cycle. JEV is not merely an LLM gate. LLM execution is not silently skipped because JEV reports low uncertainty.

The ablation switches remain independent:

```text
Neural only
Neural + JEV
Neural + LLM
Neural + JEV + LLM
```

Those conditions change only the explicitly ablated member. Input, data, neural substrate, prompts/questions, and evaluation case remain fixed.

## Provider truth

Mock providers are permitted only for software unit tests. Integration/scientific runs require actual configured provider calls and provider receipts. An enabled provider that is unavailable is an execution error; HIVE does not silently substitute or skip it.

LLM responses use a structured recurrent contract with an analysis, unresolved items, and a bounded `neural_feedback` value in [-1, 1]. JEV retains its typed `noul`, `choice`, and `score` interface.

## Authority boundary

```text
observe → integrated recurrent Core → proposal/output
                                  ↓
                         deterministic policy
                                  ↓
                        explicit external executor
```

Inference output is not authority. Irreversible or high-impact actions require a separate deterministic permission/execution boundary.

## Primary substrates

- Larva: corrected Cook C. elegans full measured topology.
- Bee: full MaleCNS v1.0 graph via `malecns_full_v1`.
- Development/control Bee: MaleCNS v1.0 1,045-neuron locomotor subgraph.
- Synthetic/random/shuffled engines: controls only.

Primary readiness remains empirical: the exact pinned full datasets must execute successfully and produce matching execution receipts.
