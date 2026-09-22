# Roadmap

Current focus: **composition experiment integrity**.

HIVE is not being expanded into a full agent harness at this stage. The immediate objective is to make staged and recurrent architecture comparisons causally interpretable.

## Implemented foundation

- [x] event and neural-observation schemas
- [x] persistent run/event/provider store
- [x] GUI/API
- [x] ordered executable architecture tags
- [x] independently toggleable JEV and LLM calls
- [x] independently configurable JEV/LLM feedback targets
- [x] context-freshness protections for provider calls
- [x] Cook corrected full-connectome engine
- [x] MaleCNS 1,045-neuron locomotor control engine
- [x] full MaleCNS v1.0 sparse engine
- [x] whole-state provider readout
- [x] explicit Cook→MaleCNS bridge machinery
- [x] real provider receipts
- [x] full-state export capability
- [x] experiment export bundle
- [x] Docker / Windows deployment path

## Phase A — experiment truth

- [ ] define canonical `TaskResult`
- [ ] define executable task scorers
- [ ] define `ArchitectureVariant` + deterministic config hash
- [ ] define durable `ExperimentRun` manifest/grouping
- [ ] freeze/hash task sets
- [ ] add explicit reset/checkpoint policy per case
- [ ] support repeated trials and condition ordering
- [ ] collect uncertainty, not only point estimates
- [ ] add compute/call-budget reporting

## Phase B — separate architecture variables

- [ ] separate neural substeps from harness passes
- [ ] separate harness passes from cross-component feedback
- [ ] make clean one-pass feed-forward mode first-class
- [ ] make repeated-no-feedback mode first-class
- [ ] make closed-loop feedback mode first-class

## Phase C — repair and generalize neural handoffs

- [ ] replace first-32 Cook excerpt as canonical primary bridge
- [ ] preserve legacy excerpt bridge as a control
- [ ] implement whole-state deterministic bridge strategy
- [ ] implement random-projection bridge control
- [ ] implement zero/null bridge control
- [ ] version/hash bridge encoders
- [ ] make neural input encoder an explicit experimental component

## Phase D — complete observability

- [ ] preserve every stage state per pass/component/step
- [ ] persist every provider-facing readout/context artifact
- [ ] bind provider outputs to stored context artifacts
- [ ] bind feedback application to source call/context
- [ ] record complete trajectory manifests
- [ ] prevent intermediate artifacts from being overwritten

## Phase E — strengthen primary readiness

- [ ] require one end-to-end primary execution receipt
- [ ] bind full Cook + bridge + full MaleCNS to one run
- [ ] bind exact dataset hashes
- [ ] bind compiled graph hashes
- [ ] bind resolved architecture/config hash
- [ ] target-machine execute 166,700 / 25,582,938 / 124,177,617 primary graph
- [ ] verify real JEV/LLM calls where enabled

## Phase F — causal controls

- [ ] ordinary LLM baseline
- [ ] JEV-only
- [ ] LLM-only
- [ ] Cook-only
- [ ] MaleCNS-only
- [ ] Cook→MaleCNS
- [ ] deterministic synthetic reservoir
- [ ] matched random reservoir
- [ ] shuffled connectome topology
- [ ] zero feedback
- [ ] shuffled feedback
- [ ] feed-forward full composition
- [ ] repeated no-feedback composition
- [ ] closed-loop composition
- [ ] compute-matched simpler baselines

## Phase G — evaluate the first real composition hypothesis

For a frozen task set, answer:

1. Does architecture change the internal trajectory?
2. Does it improve task outcome?
3. Does the combination add something beyond its parts?

Only after these comparisons survive null controls and replication should HIVE make claims about useful composition effects.

## Phase H — extensible processors

After the experiment harness is trustworthy:

- [ ] small generic processor/component interface
- [ ] embeddings
- [ ] rerankers
- [ ] classifiers
- [ ] alternate readouts
- [ ] alternate model providers
- [ ] task-specific encoders

Do not turn this phase into a large agent framework unless experimental results justify it.

## Later / non-core surfaces

These may remain available but are not the current research priority:

- worker/Core chaining
- browser environments
- schedulers/daemons
- MCP
- domain deployment profiles
- external action/tool execution

See `docs/AUDIT.md` and `docs/NEXT_SESSION.md`.
