# Roadmap

## Phase 0 — experiment runtime

- [x] event schema
- [x] neural observation schema
- [x] Jev decision schema
- [x] LLM escalation path
- [x] persistent store
- [x] GUI
- [x] MCP surface
- [x] data-source daemon
- [x] cron + scheduled source polling
- [x] worker daemon/cron runtime with safe disabled-by-default automation
- [x] simulation endpoint
- [x] safe connectome manifests

## Phase 1 — real WormLink

- [ ] parse Cook 2020
- [ ] implement reproducible 302-neuron dynamics
- [ ] add Witvliet developmental snapshots
- [ ] benchmark synthetic vs real vs shuffled worm
- [ ] checkpoint/state reset

## Phase 2 — real FlyCore

- [ ] parse MaleCNS Feather data
- [ ] integrate a validated sparse dynamics engine
- [ ] immutable graph + multiple independent state vectors
- [ ] Windows CPU/GPU benchmarks
- [ ] full graph vs task-specific subgraphs

## Phase 3 — associative larval mini-brain

- [ ] pin redistribution-safe Eichler 2017 data
- [ ] implement KC/MBON/DAN circuit
- [ ] compare against an MB-inspired random sparse encoder
- [ ] use as optional classifier/memory head

## Phase 4 — multi-worker scaling

- [x] multiple independently configured workers
- [x] per-worker JEV/LLM settings and controlled toggle ablations
- [ ] executable worker-to-worker routing bus
- [ ] chain/braid/hive topology experiments
- [ ] shared immutable connectome graphs
- [ ] distributed event bus when needed

## Phase 5 — Domain deployment profiles

- [ ] chain/RPC log source
- [ ] read-only wallet source
- [ ] contract/pool observers
- [ ] domain data-layer source
- [ ] ecosystem state reducer
- [ ] label/index workers
- [ ] proposal-only contract actions
- [ ] signer/policy service outside inference

## Required controls

Compare:

- no connectome
- synthetic/random reservoir
- shuffled connectome
- worm only
- fly only
- worm → fly
- Jev only
- LLM only where relevant
- full HIVE
