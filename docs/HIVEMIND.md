# Hivemind Model

HIVE is a runtime contract, not a single deployment.

## Deployment profiles

### Local / personal Hivemind

Private, local-first inputs such as chats, files, repos, notes, and local services. Raw sources remain local where possible; agents receive evidence slices through MCP.

### Based Nut Hivemind

Always-on ecosystem state capture across Base RPC/logs, read-only wallet state, contracts, pools, IRIS/data layer, and ecosystem services. It labels and navigates the data layer, detects transitions/anomalies, maintains current state, and may emit action proposals. Signing remains outside inference.

## Bee Unit

A Bee Unit is configured as:

```text
role
+ ordered brain_chain[]
+ Jev decision head[]
+ LLM escalation policy
+ tools
+ permissions
```

`brain_chain[]` is generic. A unit may be:

```text
WormLink → FlyCore → Jev
WormLink → LarvalMB → FlyCore → Jev
WormLink ─┐
WormLink ─┼→ FlyCore → Jev
WormLink ─┘
```

The Drosophila larval mushroom-body stage is represented in schema now but remains disabled until a pinned, reproducible dataset/runtime is integrated.

## Cohesive loop

```text
always-on event
→ brain chain advances recurrent state
→ neural observations become structured JEV state
→ Jev makes bounded typed decisions
→ decision values modulate next neural cycle
→ LLM is called only on escalation
→ optional Jev verification
→ Comb stores evidence + derived state
→ Waggle routes follow-up work to another Bee Unit
```

The LLM is an intermittent semantic reasoner, not the heartbeat. Jev is the cheap typed decision layer. The connectomes provide recurrent temporal state. Deterministic policy owns authority.

## Scaling rule

The external contracts stay stable while internals improve:

- synthetic brain → real connectome engine
- one brain state → many state instances sharing immutable topology
- SQLite → larger event/state store
- in-process Waggle → distributed event bus
- LM Studio → larger local inference host or cluster
- one machine → worker replicas

The system should scale by replacing modules, not rewriting the event/decision/permission model.
