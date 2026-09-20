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

- [x] parse corrected Cook 2019/2020 hermaphrodite adjacency workbook
- [x] execute compact graded recurrent dynamics over measured Cook topology
- [ ] add Witvliet developmental snapshots
- [ ] benchmark synthetic vs real vs shuffled worm
- [ ] checkpoint/state reset

## Phase 2 — primary full MaleCNS Bee

- [ ] parse and execute the full pinned MaleCNS v1.0 Feather graph **(primary readiness blocker)**
- [ ] validate loaded graph counts against the canonical experiment contract
- [ ] immutable graph + multiple independent state vectors
- [ ] Cook → full MaleCNS state handoff
- [ ] Windows CPU/GPU benchmarks
- [x] execute pinned 1,045-neuron / 17,224-edge MaleCNS locomotor subgraph **as a control only**
- [x] integrate LIF-style sparse dynamics for the locomotor control, adapted from DesktopFly
- [ ] full graph vs task-specific subgraphs as an explicit ablation

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
