# Workers

A worker is a **complete experiment configuration**, not a JEV/LLM variant.

```text
Workerᵢ
  ├─ experiment objective + task prompt
  ├─ data environment
  ├─ Larvaᵢ
  ├─ Beeᵢ
  ├─ JEV settings + questions + toggle
  ├─ LLM settings + prompt + toggle
  ├─ runtime / daemon / cron settings
  └─ outputs / next workers
```

The basic neural unit remains:

```text
Larvaᵢ → Beeᵢ
```

JEV and LLM are optional capabilities attached to that same worker:

```text
data environment
      ↓
Larvaᵢ → Beeᵢ
      ↓
    JEV? ──→ LLM?
      ↓
    output
```

## Experimentation

Do not create four different saved workers merely to test JEV and LLM.

Keep one worker fixed and temporarily run it with:

```text
JEV off / LLM off
JEV on  / LLM off
JEV off / LLM on
JEV on  / LLM on
```

The data environment, prompts, brain settings, task, and expected output stay identical.

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
- Larva engine/substrate/config
- Bee engine/substrate/config
- JEV model/questions/gate threshold/feedback behavior
- LLM provider/model/prompt/activation/temperature
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
