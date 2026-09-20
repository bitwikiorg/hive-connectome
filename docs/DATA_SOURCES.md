# Data Sources

## Current built-ins

### HTTP JSON

Public HTTP/HTTPS JSON API, GET or POST.

### RSS / Atom

For publications, updates, changelogs, and feeds.

### File drop

Export/copy files into:

```text
data/inbox/
```

The container reads only `.json`, `.jsonl`, `.txt`, `.md`, and `.csv` up to 10 MB each.

## Free examples

`config/sources.example.json` includes disabled examples for:

- DefiLlama public protocols endpoint
- Base public JSON-RPC head
- local inbox

Public endpoints may change limits or availability; HIVE records source health rather than assuming permanence.

## Future adapters

- GitHub
- Discourse
- wallet/account observers
- Base logs/events
- domain-specific data APIs
- local chat exports
- local repo index
- email/calendar through explicit opt-in connectors
