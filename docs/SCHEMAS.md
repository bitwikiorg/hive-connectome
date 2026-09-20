# Canonical Schemas

Schemas live in `src/hive_connectome/schemas.py`.

## EventEnvelope

```text
id
timestamp
source_id
kind
subject
payload
provenance
tags
freshness_timestamp
```

Raw evidence is retained. Derived labels never overwrite source evidence.

## NeuralObservation

```text
brain_id
brain_kind
engine
step
state_vector
metrics
```

Real and synthetic engines use the same outer shape.

## DecisionBundle

```text
provider
model
answers
confidence
raw
```

Bounded decisions should never require downstream code to parse prose.

## PipelineResult

```text
run_id
event
worm
fly
decisions
llm
verification
modulation
labels
unresolved
```

## WorkerSpec

A saved worker is one complete experiment configuration:

```text
id / name / role
experiment
data_environment
larva
bee
jev
llm
runtime
outputs
```

JEV and LLM are capabilities on the same worker, not separate worker types. Temporary run/eval overrides can toggle them without mutating the saved worker.

## DataSourceSpec

```text
kind = http_json | rss | file_drop
endpoint/path
poll interval
enabled
auto_process
```

Network sources block private/loopback destinations by default.

## CronTaskSpec

```text
cron
action
target
payload
enabled
```

Cron creates events that pass through the same pipeline.

## ActionProposal

```text
tool
arguments
risk
reason
requires_approval
evidence_refs
```

A proposal is data, not permission.
