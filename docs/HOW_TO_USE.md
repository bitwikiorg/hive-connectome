# How to use HIVE

## First: what HIVE is actually running today

HIVE currently runs an **orchestration experiment**, not a biological brain simulator.

A normal run is:

```text
your input
  ↓
16-state deterministic recurrent test stage
  ↓
64-state deterministic recurrent test stage
  ↓
optional Jev typed judgments
  ↓
optional local LLM explanation
  ↓
SQLite event/run memory
```

The two recurrent stages are synthetic test engines used to validate persistence, routing, state handoff, evaluation, and UI behavior. They are deliberately small and deterministic.

The Connectomes panel can download and SHA-256 verify Cook/Witvliet C. elegans and MaleCNS datasets. **Those files are data on disk. The current runtime does not execute them.** Downloading one changes the data status from `NOT DOWNLOADED` to `DATA INSTALLED + VERIFIED`; it does not change `Real connectome running` from `NO` to `YES`.

## The normal user workflow

Open the GUI and ignore **Advanced experiment controls** unless you are debugging or comparing internals.

1. Pick a job under **What do you want HIVE to do?**
2. Paste ordinary text, an event, a claim, an API result, or an observation.
3. Press **Run HIVE**.
4. Read the human result card.
5. Expand **Raw run JSON** only when you need machine detail.

The front-door jobs are:

| Job | Use it for | What runs |
|---|---|---|
| **Understand new information** | Default for a note, event, API result, or observation | recurrent state → Jev → local LLM only if needed |
| **Sort / route an event** | Fast keep / inspect / escalate / ignore decisions | recurrent state → Jev |
| **Explain something with local AI** | Open-ended prose interpretation | recurrent state → local LLM |
| **Decide what is worth remembering** | Durable-state / memory decisions | recurrent state → Jev → optional LLM |
| **Check a claim against evidence** | Contradictions, support, missing evidence | recurrent state → Jev → optional LLM |
| **Interpret a browser observation** | DOM/accessibility/OCR/page evidence supplied by another browser tool | recurrent state → Jev → optional LLM |
| **Test the neural state layer** | Research baseline only | the two synthetic recurrent stages, no Jev, no LLM |

The names above are user jobs. The old internal labels (`forager`, `triage`, `keeper`, and so on) remain implementation IDs under Advanced controls so existing APIs and experiments do not break.

## What the result means

The result page separates five things that were previously mixed together:

- **Route** — the bounded action label HIVE selected, if Jev ran.
- **Meaningful / novelty / LLM needed** — typed judgment outputs, not permissions or truth guarantees.
- **Interpretation** — prose from the local LLM, only if that worker actually called it.
- **Stage state** — recurrent-engine telemetry, useful for experiments, not semantic proof.
- **What HIVE did** — a human-readable trace of which components actually ran.

Every run also displays the neural-runtime truth explicitly. Until a real adapter is implemented and enabled, the UI says:

```text
Biological connectome executed: NO
```

## What the workers really are

The worker names are **configurations of one pipeline**, not seven little autonomous creatures.

A clearer engineering split is:

```text
OBSERVE
code gathers the event and state

PICK
Jev answers narrow typed questions when enabled

READ / WRITE
an LLM handles open-ended language only when enabled

GATE
code owns thresholds, permissions, freshness, retries and side effects

REMEMBER
SQLite stores events, runs and selected state
```

This follows the strongest pattern across the audited Jev projects: the model makes a bounded judgment; code owns execution and authority. HIVE should not ask a user to understand `forager` versus `keeper` before they can use it.

## What the terminal setup did

The Windows/Docker setup builds the HIVE service and starts its containers. It does **not** silently download multi-hundred-megabyte or gigabyte connectome datasets. Large biological datasets require an explicit **Download data** action so disk/network use is visible and checksums can be verified.

Even after that download, HIVE still needs a real dynamics adapter that loads the data into an executable neural engine. That adapter is the next biological-runtime milestone; it is separate from installation.

## Utility today

The useful thing HIVE provides now is an inspectable **always-on decision/memory harness** for answering questions such as:

- Did this new event matter?
- Should I keep, inspect, escalate, or ignore it?
- Does this claim appear supported by supplied evidence?
- Is an expensive LLM call warranted?
- What changed since the last event?
- Which result should become durable memory?
- How do Jev-only, LLM-only, both, and neither compare on the same input?

That is real utility, but it is not yet evidence that biological connectomes improve any of those tasks. The purpose of the coming biological adapters is to test that claim against direct, shuffled, disconnected, and conventional-reservoir controls rather than assume it.

## Advanced controls

Use Advanced controls for:

- editing internal worker prompts/questions;
- changing Jev or LLM modes;
- running the 2×2 Jev/LLM ablation;
- inspecting provider health;
- MCP integration.

Machine JSON stays available there and under each human result because it is useful for debugging and agents. It is intentionally no longer the primary human interface.