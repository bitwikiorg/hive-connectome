# Security

Docker Compose binds HIVE and MCP only to `127.0.0.1`.

Secrets are read from `/run/secrets/venice_api_key` and `/run/secrets/lmstudio_api_token`; the host `.secrets/` directory is git-ignored.

## Connectome downloader

Only entries in `config/connectomes.json` are installable. Downloads stream to a temporary file, are size-bounded and SHA-256 verified, are atomically renamed, never executed, and receive an install receipt.

## Data-source SSRF protection

HTTP/RSS sources reject loopback, private, link-local, multicast, reserved, and unspecified addresses. Local data enters through `/data/inbox`.

## LM Studio

If Docker cannot reach LM Studio while it is loopback-only, see `docs/WINDOWS.md`. Do not expose LM Studio broadly without authentication and firewall controls.

## Wallets/contracts

v0.1 contains no signer.

```text
inference != authority
proposal != signature
```
