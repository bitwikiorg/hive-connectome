# Windows + Docker Desktop

For step-by-step installation and first use, start with [`GETTING_STARTED.md`](GETTING_STARTED.md).

**Important:** HIVE is currently built locally from this Git repository. There is no published registry image to pull in Docker Desktop. After `docker compose up -d --build`, Docker Desktop shows the resulting Compose application, local image, services, logs, ports, and persistent volume.

Recommended layout:

- Docker Desktop runs HIVE.
- LM Studio runs natively on Windows.
- HIVE reaches host services through Docker Desktop's documented `host.docker.internal` DNS name.
- The browser reaches HIVE on `http://127.0.0.1:8088`.

## LM Studio outside Docker

LM Studio's API server defaults to port `1234` and binds to `127.0.0.1` by default. HIVE uses the OpenAI-compatible base URL:

```text
http://host.docker.internal:1234/v1
```

Start LM Studio from the Developer page or with:

```powershell
lms server start --port 1234
```

A Docker container cannot rely on a Windows service that is listening only on host loopback. If HIVE cannot reach LM Studio, enable **Serve on Local Network** in LM Studio or start it on a non-loopback bind:

```powershell
lms server start --port 1234 --bind 0.0.0.0
```

Any bind other than `127.0.0.1` increases exposure. LM Studio explicitly recommends authentication in that case. Enable **Require Authentication**, create an API token, store it through HIVE's setup script, and use Windows Firewall to restrict port `1234`. Do not expose the server to the public Internet.

LM Studio endpoints used by HIVE:

```text
GET  /v1/models
POST /v1/chat/completions
```

## Venice

The setup script stores the Venice API key in `.secrets/venice_api_key`, mounted read-only into the container. HIVE uses:

```text
GET  https://api.venice.ai/api/v1/models?type=decision
POST https://api.venice.ai/api/v1/decisions
POST https://api.venice.ai/api/v1/chat/completions   # only for workers configured to use Venice as the LLM
```

Jev/Decisions is beta. The Models API is authoritative for current model availability, pricing, and limits.

## Docker Desktop networking

Docker Desktop documents `host.docker.internal` as the supported name for a container to reach a service on the host. HIVE's own published ports remain restricted to loopback:

```text
127.0.0.1:8088 -> HIVE GUI/API
127.0.0.1:8090 -> HIVE MCP
```

## Updating

```powershell
git pull
docker compose up -d --build
```

Persistent state lives in the Docker volume `hive-data`.
