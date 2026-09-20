# How to use HIVE

## First: what HIVE is actually running today

A default v0.5 run is:

```text
your event / text
  ↓ engineered deterministic sensory encoding
Cook corrected C. elegans connectome (measured topology)
  ↓ graded recurrent dynamics
MaleCNS v1.0 locomotor subgraph (1,045 neurons / 17,224 edges)
  ↓ LIF-style recurrent dynamics over measured signed weights
optional live Venice/JEV typed judgments
  ↓
optional LLM explanation
  ↓
SQLite event/run memory + execution receipt
```

The anatomical wiring is real published connectome data. The arbitrary text/event-to-sensory-neuron mapping and compact dynamics are engineered experimental layers. HIVE does **not** claim this is a complete biological reconstruction of either animal.

Synthetic recurrent engines still exist, but only as explicit experimental controls. They are not the default worker runtime.

## What setup downloads

A fresh Windows setup automatically downloads and integrity-verifies the two packs required by the default runtime:

1. corrected Cook C. elegans adjacency workbook;
2. pinned MaleCNS v1.0 1,045-neuron locomotor runtime subgraph.

The full ~1.1 GB MaleCNS research pack is optional and the setup script asks before downloading it. It is not needed for the default runtime.

If either mandatory runtime pack cannot be installed and verified, setup fails instead of starting HIVE in a silent synthetic fallback mode.

## The normal user workflow

Open the GUI and ignore **Advanced experiment controls** unless you are debugging or comparing internals.

1. Pick a job under **What do you want HIVE to do?**
2. Paste ordinary text, an event, a claim, an API result, or an observation.
3. Press **Run HIVE**.
4. Read the human result card.
5. Check the execution truth row: it tells you whether real topology executed and whether JEV was a live Venice call.
6. Expand **Raw run JSON** only when you need machine detail.

| Job | Use it for | What runs |
|---|---|---|
| **Understand new information** | Default note/event/observation | Cook → MaleCNS → JEV → LLM if JEV gates it |
| **Sort / route an event** | Fast keep / inspect / escalate / ignore | Cook → MaleCNS → JEV |
| **Explain something with local AI** | Open-ended prose interpretation | Cook → MaleCNS → local LLM |
| **Decide what is worth remembering** | Durable-state / memory decisions | Cook → MaleCNS → JEV → optional LLM |
| **Check a claim against evidence** | Support, contradictions, missing evidence | Cook → MaleCNS → JEV → optional LLM |
| **Interpret browser evidence** | DOM/accessibility/OCR supplied by another tool | Cook → MaleCNS → JEV → optional LLM |
| **Test the connectome neural layer** | Isolate neural substrate | Cook → MaleCNS only |

## How to know JEV really ran

When a job requests JEV, HIVE no longer silently substitutes the fixed readout if Venice is unavailable. The run fails visibly instead.

A successful live JEV run has both:

```text
decisions.provider = venice
execution.jev.called = true
```

The human result shows `Jev LIVE call succeeded`. Provider reachability alone is not treated as proof that a particular run used JEV.

## How to know the connectomes really ran

A successful default neural run reports:

```text
execution.larva.real_connectome_topology = true
execution.bee.real_connectome_topology = true
```

and the engines identify themselves as:

```text
cook2019-corrected-connectome-graded-v1
malecns-v1-locomotor-lif-v1
```

The human result says `Real connectome topology executed: YES`. This means measured graph topology was loaded and propagated. It does **not** mean every physiological property is biologically measured.

## What the workers are

Workers are complete experiment configurations, not different kinds of model. `Scout`, `Keeper`, `Auditor`, `Browser`, and `Stream Watcher` mainly differ in their task prompt, JEV questions, data environment, and runtime policy. Each can independently toggle JEV and LLM while using the same Larva→Bee neural pair.

## Why the neural result is not the final semantic answer

The connectome stages provide recurrent state and topology-dependent features. Generic text is not a natural stimulus for a worm or fly, so HIVE uses a deterministic engineered encoder to stimulate bounded sensory/ascending neurons. JEV then makes task-specific typed judgments over the raw event plus neural observations. This separation is intentional and measurable.

## Advanced controls

Use Advanced controls for:

- editing worker prompts/questions;
- toggling JEV and LLM independently;
- running the 2×2 JEV/LLM ablation;
- switching to synthetic/shuffled controls as they are added;
- provider health;
- MCP integration;
- raw execution receipts.
