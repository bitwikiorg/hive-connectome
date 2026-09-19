# Canonical Schemas

`EventEnvelope`: id, timestamp, source_id, kind, subject, payload, provenance, tags, freshness_timestamp.

`NeuralObservation`: brain_id, brain_kind, engine, step, state_vector, metrics.

`DecisionBundle`: provider, model, answers, confidence, raw.

`PipelineResult`: run_id, event, worm, fly, decisions, llm, verification, modulation, labels, unresolved.

A Bee Unit combines role, WormLink, FlyCore, Jev head, LLM policy, tools, and permissions.

A data source is explicit and independently enabled: `http_json | rss | file_drop`, target, interval, enabled, auto_process. Network sources block private/loopback targets.

Cron creates events and sends them through the same pipeline.

Future `ActionProposal` objects contain tool, arguments, risk, reason, approval requirement, and evidence references. A proposal is data, not permission.
