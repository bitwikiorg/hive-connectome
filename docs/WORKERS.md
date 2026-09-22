# Workers

A worker is a **complete experiment configuration**, not a JEV/LLM variant.

```text
Workerᵢ
  ├─ experiment objective + task prompt
  ├─ data environment
  ├─ ordered architecture tags
  ├─ neural stages + explicit bridges
  ├─ JEV settings + questions + toggle
  ├─ LLM settings + prompt + toggle
  ├─ runtime / daemon / cron settings
  └─ outputs / next workers
```

The worker executes its saved comma-tagged architecture in order. The default composition is:

```text
worm,worm-to-fly,fly,readout,jev,llm,jev_verify,feedback
```

Stage IDs and bridge IDs are executable tags. Reserved tags execute the whole-state readout, JEV, LLM, verification, and feedback adapters. Reordering/removing/repeating tags changes the computation. JEV/LLM toggles are independent ablations over the same saved architecture.

## Experimentation

Do not create four different saved workers merely to test JEV and LLM.

Keep one worker fixed and temporarily run it with:

```text
JEV off / LLM off
JEV on  / LLM off
JEV off / LLM on
JEV on  / LLM on
```

The data environment, prompts, neural settings, architecture tags, integration-cycle count, task, and expected output stay identical.

That makes JEV and LLM true ablations.

## Full worker settings

Each worker owns:

- experiment kind
- objective
- experiment/task prompt
- expected output
- evaluation metric
- data environment
- data-source bindings
- browser/OCR settings where relevant
- ordered executable architecture tags
- neural stage engine/substrate/config
- explicit bridge engine/config
- JEV model/questions/toggle/feedback behavior
- LLM provider/model/prompt/toggle/temperature
- on-demand/daemon/cron runtime
- state persistence
- output persistence
- Hivemind routing

The GUI exposes these together because they describe one experiment.

## Templates

Templates are starting configurations, not special worker classes.

Current templates include:

- manual classifier
- browser DOM reader
- browser visual/OCR reader
- always-on stream watcher
- local files/chat-memory worker

A template must align:

```text
experiment question
↔ GUI
↔ data environment
↔ prompts
↔ evaluation metric
```
