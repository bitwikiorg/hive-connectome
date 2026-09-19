# Architecture

HIVE is not one neural network and not one LLM.

```text
data → Waggle bus → Bee Unit
                    WormLink → FlyCore → JEV → LLM?
                                   ↓
                              Comb memory
```

A Bee Unit is independently replaceable. v0.1 uses deterministic synthetic mini-brains so orchestration can be tested before large biological data is loaded.

## Neural + Jev cohesion

Jev receives explicit structured state containing the event, WormLink metrics/state excerpt, and FlyCore metrics/state excerpt. Its typed answers produce an engineered modulation scalar that is fed back into mini-brain state on the next cycle. This is a testable closed loop, not a claim that JEV is biological neuromodulation.

## LLM escalation

The LLM is not in the always-on hot path. Escalate for `llm_needed`, an `escalate` route, low confidence, generation/explanation, or semantic merge. Prefer LM Studio; if unavailable, preserve unresolved state.

## Authority

```text
observe → neural state → JEV → optional LLM → JEV verify → proposal
                                                        ↓
                                              deterministic policy
                                                        ↓
                                               explicit executor
```

## Deployment profiles

**Personal/local:** files, chats, repos, notes, local services, explicit connectors.

**Based Nut Hivemind:** Base RPC, wallets, IRIS/data layer, contracts, pools, ecosystem services.

Both use the same schemas. Scale by replacing synthetic brains with real Cook/Witvliet and MaleCNS engines, SQLite with a larger event store, and the in-process bus with a distributed bus only when measurements justify it.
