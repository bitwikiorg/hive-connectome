# Evaluation

The unit under evaluation is one saved worker.

The worker defines:

```text
data environment
experiment question
ordered architecture tags
neural stage + bridge configuration
JEV questions
LLM prompt
harness-pass count
runtime behavior
expected output
```

## Architecture variants

The evaluator is no longer limited to the JEV/LLM 2×2. A variant can freeze architecture order, harness passes, feedback, bridge strategy, input encoder, neural stage engine/config, and the JEV/LLM toggles. The legacy 2×2 remains a useful subset.

## Primary JEV/LLM ablation

For one worker and one fixed test set, run:

| Case | JEV | LLM |
|---|---:|---:|
| `jev_off_llm_off` | off | off |
| `jev_on_llm_off` | on | off |
| `jev_off_llm_on` | off | on |
| `jev_on_llm_on` | on | on |

Nothing else should change. In particular, the architecture tags and harness-pass count stay identical across the four JEV/LLM ablations; only the two inference toggles change. If architecture order or cycle count is the variable under study, that must be a separate named experiment.

Measure:

- task score through one architecture-independent `TaskResult` scorer;
- uncertainty across repetitions;
- latency and latency dispersion;
- JEV, LLM, neural-stage, and harness-pass call budgets;
- whether compared variants are compute-matched;
- unresolved/invalid results and failure rate;
- state/context hashes and artifacts;
- exact worker/variant/task-set/scorer hashes.

## Neural controls

Once real connectomes are executing, add:

- Larva only
- Bee only
- Larva → Bee
- shuffled connectome
- random reservoir
- no neural state

## Causal controls inherited from the inspiration repos

- disconnect graph
- silence readout
- neutral/black input
- frozen vs adaptive weights
- shuffled feedback/reward
- same seed vs different seeds
- exact checkpoint replay
- held-out chronological evaluation
- ordinary model baseline

Software passing tests is not evidence that the biological wiring improves the task.
