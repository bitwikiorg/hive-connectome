# Hivemind Model

HIVE is a runtime contract, not a single deployment or domain.

## Worker

A worker is configured as:

```text
experiment objective + evaluation target
+ data environment
+ Larvaᵢ → Beeᵢ
+ optional JEV
+ optional LLM
+ runtime
+ outputs / routing
```

The Larva and Bee belong to the same worker. Different workers can use different prompts, sources, providers, schedules, and eventually different neural engines while sharing the same outer schemas.

## Cohesive loop

```text
configured event/source
→ Larva recurrent step
→ Bee recurrent step
→ neural observations become structured decision state
→ optional JEV bounded decisions
→ optional bounded modulation of later neural stages in the same pass or the next harness pass
→ optional LLM reasoning according to worker policy
→ optional JEV verification
→ evidence/run state persists
→ optional follow-up routing
```

JEV and LLM are capabilities, not mandatory stages. The four JEV/LLM toggle combinations are first-class evaluation cases.

## Example deployment profiles

### Local workspace

Explicitly selected files, repositories, exported records, notes, or local services can become a data environment. Source access is opt-in and bounded by the configured adapter.

### On-chain / API environment

RPC endpoints, public APIs, read-only account state, protocol data, or event streams can feed a worker. Any irreversible executor remains outside inference.

These are examples only; the runtime is intended to remain domain-neutral.

## Scaling rule

Scale by replacing modules rather than changing the experiment contract:

- synthetic mini-brain → real connectome engine
- one dynamic state → many state instances sharing topology
- SQLite → larger event/state store
- local routing → distributed bus
- one inference host → multiple providers/hosts
- one machine → worker replicas
