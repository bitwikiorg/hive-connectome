# Architecture

## Runtime unit

HIVE is not one neural network and not one LLM. The primary unit is a saved worker experiment:

```text
                    ┌──────────── Worker A ────────────┐
data environment →  │ Larva_A → Bee_A → JEV? → LLM? │ → output/state
                    └──────────────────────────────────┘
                                  │ optional routing
                    ┌──────────── Worker B ────────────┐
                    │ Larva_B → Bee_B → JEV? → LLM? │
                    └──────────────────────────────────┘
```

Each worker owns its experiment objective, data environment, prompts/questions, neural configuration, provider toggles, runtime, and outputs. This keeps experiments reproducible and makes ablations meaningful.

## Neural + JEV cohesion

The bridge is explicit structured state:

```json
{
  "worker": {"experiment": {}, "data_environment": {}},
  "event": {},
  "larva": {"metrics": {}, "state_excerpt": []},
  "bee": {"metrics": {}, "state_excerpt": []}
}
```

JEV evaluates that shared state with bounded questions. When enabled, a JEV-derived modulation value may feed the next neural cycle. This is an engineered closed loop, not a claim that JEV reproduces biological neuromodulation.

For `noul`, the returned value is the probability of “yes”; it is not a separate confidence field. `choice` and `score` may include confidence/distributions according to the provider schema.

## LLM behavior

LLM use is independently configurable per worker:

- `always`
- `jev_gate`
- `manual`

Workers can use LM Studio or Venice Chat when configured. A worker may also run with no LLM at all.

## Authority boundary

```text
observe → recurrent state → bounded decision → optional LLM → proposal/output
                                                           ↓
                                                  deterministic policy
                                                           ↓
                                                explicit external executor
```

Inference output is not authority. Irreversible or high-impact actions require a separate deterministic permission/execution boundary.

## Deployment profiles

Profiles are examples rather than identities of the project. The same worker/event contracts can be applied to local workspace data, public APIs, on-chain state, simulation fixtures, or other explicitly configured sources.

## Scaling

The external contracts stay stable while internals improve:

- synthetic Larva → real small-connectome engine
- synthetic Bee → real larger-connectome engine
- one state instance → multiple states sharing immutable topology
- SQLite → larger event/state store
- in-process routing → distributed event bus if needed
- local inference → another model host/cluster
- one process → worker replicas
