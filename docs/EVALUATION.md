# Evaluation

The unit under evaluation is one saved worker.

The worker defines:

```text
data environment
experiment question
Larva+Bee configuration
JEV questions
LLM prompt
runtime behavior
expected output
```

## Primary JEV/LLM ablation

For one worker and one fixed test set, run:

| Case | JEV | LLM |
|---|---:|---:|
| `jev_off_llm_off` | off | off |
| `jev_on_llm_off` | on | off |
| `jev_off_llm_on` | off | on |
| `jev_on_llm_on` | on | on |

Nothing else should change.

Measure:

- task correctness
- calibration where applicable
- latency
- JEV calls
- LLM calls
- unresolved cases
- failure rate
- state hashes
- exact worker/config version

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
