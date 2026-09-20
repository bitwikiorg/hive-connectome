# Security

## Default exposure

Docker Compose binds HIVE and MCP only to `127.0.0.1`.

## Secrets

Credentials are read from:

```text
/run/secrets/venice_api_key
/run/secrets/lmstudio_api_token
```

The host `.secrets/` directory is git-ignored. The GUI reports only whether a secret is configured.

## Connectome downloader

Only entries in `config/connectomes.json` are installable.

The downloader:

- does not accept arbitrary download URLs
- streams to a temporary file
- enforces a size bound
- verifies expected bytes when known
- verifies SHA-256
- deletes mismatches
- never executes downloaded files
- writes an install receipt

## Data source SSRF protection

HTTP/RSS sources reject loopback, private, link-local, multicast, reserved, and unspecified addresses.

Local data enters through `/data/inbox` instead.

## LM Studio

If Docker cannot reach LM Studio while it is loopback-only, see `docs/WINDOWS.md`.
Do not expose LM Studio broadly without authentication and firewall controls.

## Wallets/contracts

HIVE currently contains no signer.

```text
inference != authority
proposal != signature
```
