# Data Sources

v0.1 supports public HTTP JSON, RSS/Atom, and a local file-drop inbox.

Local files go in `data/inbox/`; accepted formats are JSON, JSONL, TXT, Markdown, and CSV up to 10 MB.

Free examples in `config/sources.example.json` include DefiLlama protocols and the Base public JSON-RPC head, disabled by default. Public endpoints may change availability or limits, so HIVE records source health rather than assuming permanence.

Future adapters: GitHub, Discourse, wallet/account observers, Base logs/events, IRIS/Based Nut data layer, local chat exports, local repo index, and explicitly opted-in email/calendar connectors.
