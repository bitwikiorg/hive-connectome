# Roadmap

Current focus: **run the composition experiments**.

HIVE is not being expanded into a full agent harness until the composition hypothesis is tested.

## Foundation — complete

- [x] event and neural-observation schemas
- [x] persistent run/event/provider/experiment store
- [x] GUI/API
- [x] ordered executable architecture tags
- [x] independent JEV / LLM toggles
- [x] independent feedback settings and targets
- [x] Cook full-connectome engine
- [x] MaleCNS locomotor control
- [x] full MaleCNS v1.0 sparse engine
- [x] deterministic synthetic reservoir
- [x] whole-state provider readout
- [x] explicit bridge machinery
- [x] real provider receipts
- [x] full-state + context export
- [x] Docker / Windows deployment path

## Experiment integrity — complete

- [x] canonical architecture-independent `TaskResult`
- [x] common exact/route scorers
- [x] `ArchitectureVariant` + deterministic variant hash
- [x] durable `ExperimentRun` manifest
- [x] task-set hash
- [x] explicit reset policy
- [x] repetitions and deterministic condition ordering
- [x] uncertainty summary
- [x] compute signatures and `compute_matched`
- [x] neural substeps separated from harness passes
- [x] harness passes separated from feedback
- [x] one-pass feed-forward mode
- [x] repeated-no-feedback mode
- [x] closed-loop feedback mode
- [x] canonical whole-state Cook → MaleCNS bridge
- [x] legacy excerpt bridge control
- [x] random bridge control
- [x] zero bridge control
- [x] explicit zero root-input control
- [x] transient neural-engine/config variants
- [x] deterministic shuffled-MaleCNS topology control
- [x] per-pass/component full-state artifacts
- [x] persisted provider-facing contexts
- [x] provider output ↔ context provenance
- [x] feedback ↔ source call/context provenance
- [x] strict typed JEV validation
- [x] malformed LLM task-result failure handling
- [x] versioned feedback adapters
- [x] end-to-end primary execution receipt
- [x] canonical control variants barred from readiness
- [x] Cook source hash binding
- [x] MaleCNS source + compiled-array hash binding
- [x] resolved primary config hash

## Primary target-machine proof — next

- [ ] install/verify pinned full Cook + MaleCNS data on target machine
- [ ] execute exact full MaleCNS graph
- [ ] verify 166,700 / 25,582,938 / 124,177,617
- [ ] produce canonical Cook → whole-state bridge → full MaleCNS end-to-end receipt
- [ ] verify full per-pass state/context artifacts
- [ ] confirm `primary_experiment_ready = true`
- [ ] exercise real authenticated JEV/LLM calls for enabled variants

## First causal pilot

- [ ] freeze first benchmark task set
- [ ] ordinary LLM baseline
- [ ] JEV-only
- [ ] LLM-only
- [ ] Cook-only
- [ ] MaleCNS-only
- [ ] Cook → MaleCNS
- [ ] full one-pass feed-forward
- [ ] repeated no-feedback
- [ ] closed-loop feedback
- [ ] zero bridge
- [ ] random bridge
- [ ] zero input
- [ ] synthetic reservoir
- [ ] shuffled MaleCNS topology
- [ ] repeat stochastic variants
- [ ] report uncertainty
- [ ] compare compute signatures / compute-matched baselines

## First scientific decision point

For one frozen task family, answer:

1. Does composition topology change internal trajectories?
2. Does it change task outcomes?
3. Does the combination add something beyond the parts?
4. Does any benefit survive null controls and compute matching?

Do not make claims about biological-connectome advantage until those comparisons are run.

## Later processor experiments

Only after the first causal pilot:

- [ ] alternate input encoders
- [ ] alternate readout encoders
- [ ] structured/population-targeted feedback
- [ ] embeddings
- [ ] rerankers
- [ ] classifiers
- [ ] alternate model providers
- [ ] small generic component interface

## Possible future harness work

Only if experiment results justify it:

- terminal/tool loop;
- agent memory;
- subagents;
- browser autonomy;
- generic plugin ecosystem.

The next milestone is evidence, not more orchestration.
