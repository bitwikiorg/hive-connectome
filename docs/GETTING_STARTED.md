# Getting Started — Windows + Docker Desktop

This is the recommended first-run path for HIVE Connectome.

## What you are installing

Docker Desktop runs two local services:

```text
hive       → GUI + API       → http://127.0.0.1:8088
hive-mcp   → MCP server      → http://127.0.0.1:8090/mcp
```

HIVE stores persistent application state in the Docker volume `hive-data`.
The local `data/inbox/` directory is mounted read-only into the container as an opt-in file-drop source.

LM Studio can stay outside Docker on Windows. Venice is remote and only requires an API key.

## 1. Install prerequisites

Install:

- Docker Desktop for Windows
- Git for Windows
- optional: LM Studio
- optional: a Venice API key

Start Docker Desktop and wait until the Docker engine reports that it is running.

## 2. Clone HIVE

Open PowerShell:

```powershell
cd $HOME

git clone https://github.com/bitwikiorg/hive-connectome.git
cd hive-connectome
```

If you already cloned it:

```powershell
cd path\to\hive-connectome
git pull --ff-only
```

## 3. First setup

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

The setup script:

1. verifies Docker Desktop is running;
2. creates `.secrets/`, `data/inbox/`, and `data/out/`;
3. optionally asks for a Venice API key;
4. optionally asks for an LM Studio API token;
5. builds the local Docker image;
6. starts the `hive` and `hive-mcp` services;
7. waits for the HIVE health endpoint;
8. automatically downloads and verifies the Cook runtime pack and the small MaleCNS runtime subgraph;
9. reports that full MaleCNS is required for the primary experiment but full-graph execution is still blocked;
10. reports control-runtime readiness separately from primary-experiment readiness;
11. checks whether Venice and LM Studio are reachable;
12. opens the GUI.

Secrets are written to `.secrets/`, which is excluded from Git.

## 4. What Docker Desktop should show

After setup, open Docker Desktop → **Containers**.

You should see a Compose application for this repository with two services:

```text
hive
hive-mcp
```

Both should be running. `hive` should become healthy after startup.

Useful Docker Desktop actions:

- click the `hive` service to inspect logs;
- use the stop/start buttons for the Compose application;
- inspect the published port for the GUI/API;
- inspect the `hive-data` volume under **Volumes**.

Docker Desktop's **Images** page will also show the locally built HIVE image.

## 5. Open HIVE

Open:

```text
http://127.0.0.1:8088
```

The MCP endpoint is:

```text
http://127.0.0.1:8090/mcp
```

On first boot, expect:

- several editable example workers;
- the corrected Cook connectome and the 1,045-neuron MaleCNS runtime subgraph installed + verified;
- the current development/control Larva→Bee worker path using those measured topologies;
- JEV available when Venice is configured and reachable; a requested JEV call fails visibly rather than silently falling back;
- LLM calls unavailable until an LM Studio or Venice chat model is configured for the worker;
- browser DOM/OCR and worker-to-worker bus surfaces to remain visibly marked as unfinished where they are not executable yet.

## 6. Test the current control path without external AI

Start with the `Scout` worker.

In **Experiment runner**:

1. leave JEV off;
2. leave LLM off;
3. keep the sample JSON or enter your own JSON;
4. click **Run selected worker**.

You should receive a result containing Cook and MaleCNS locomotor-control neural observations, the fixed readout, an execution receipt, labels, and unresolved items if any. This isolates the current measured-topology control path without JEV/LLM. It is not the primary full-MaleCNS experiment.

This path requires neither Venice nor LM Studio.

## 7. Connect Venice / JEV

If you did not enter the key during setup, put it in:

```text
.secrets/venice_api_key
```

Then restart the HIVE service:

```powershell
docker compose restart hive
```

In the GUI, click **Test Venice + LM Studio** under Provider health.

A Venice-enabled worker uses the worker's JEV model and typed questions. JEV and the LLM are independent toggles.

## 8. Connect LM Studio running on Windows

LM Studio remains a native Windows application. It does not need to run inside HIVE's Docker container.

Start LM Studio's local API server, normally on port `1234`.

HIVE reaches the Windows host through Docker Desktop using:

```text
http://host.docker.internal:1234/v1
```

The HIVE LM Studio adapter uses:

```text
GET  /v1/models
POST /v1/chat/completions
```

### If HIVE cannot reach LM Studio

LM Studio normally binds to Windows loopback. A Docker container may not be able to reach a server that only listens on `127.0.0.1`.

Use LM Studio's **Serve on Local Network** option or an equivalent non-loopback bind only when needed. If you broaden the bind:

- enable LM Studio API authentication;
- place the token in `.secrets/lmstudio_api_token`;
- restrict port `1234` with Windows Firewall;
- do not expose the LM Studio server to the public Internet.

Then restart HIVE:

```powershell
docker compose restart hive
```

Run **Provider health** again.

### Choose the local model

Provider health returns the models visible to LM Studio.

For a worker:

1. enable **LLM**;
2. set **Provider** to `lmstudio`;
3. enter the exact loaded model identifier in **Model**;
4. choose `always`, `jev_gate`, or `manual` activation;
5. save the worker;
6. run the experiment.

A blank worker model falls back to the optional `HIVE_LLM_MODEL` environment setting. Explicit worker model IDs are easier to reason about while experimenting.

## 9. Run the four-way experiment

For one saved worker, the **Toggle matrix eval** runs the same experiment with:

```text
JEV off · LLM off
JEV on  · LLM off
JEV off · LLM on
JEV on  · LLM on
```

The worker's data environment, prompts, Larva/Bee configuration, and expected task remain fixed. This is the preferred way to test whether either external inference layer actually adds value.

## 10. Connectome data

The Cook pack and 1,045-neuron MaleCNS locomotor **control** pack are installed for development. They do not make the primary experiment ready. Full MaleCNS is required by the study contract; v0.6 does not auto-download it because the full-graph engine cannot yet execute it. The installer:

- uses pinned HTTPS URLs;
- writes to a temporary `.part` file;
- bounds download size;
- verifies SHA-256;
- atomically moves a verified file into place;
- records an installation receipt;
- never executes downloaded connectome data.

The full MaleCNS pack is roughly 1.1 GB and remains installable for data preparation. Installing it still does not satisfy primary readiness until the full-graph engine actually executes it.

## 11. Put local test data into HIVE

Copy supported files into:

```text
data\inbox\
```

Supported file-drop types currently include JSON, JSONL, TXT, Markdown, and CSV.

The container sees this directory read-only at:

```text
/data/inbox
```

Use a worker whose data environment is configured as `file_drop`.

## 12. Update HIVE later

Recommended:

```powershell
cd path\to\hive-connectome
powershell -ExecutionPolicy Bypass -File .\scripts\update-windows.ps1
```

Equivalent manual commands:

```powershell
git pull --ff-only
docker compose up -d --build
```

Your `hive-data` Docker volume is retained across normal rebuilds.

## 13. Stop, restart, and inspect

Show status:

```powershell
docker compose ps
```

Follow logs:

```powershell
docker compose logs -f hive
```

Restart:

```powershell
docker compose restart
```

Stop containers but keep them:

```powershell
docker compose stop
```

Stop and remove containers/network while keeping the persistent volume:

```powershell
docker compose down
```

### Full data reset — destructive

This removes the Docker volume containing HIVE's saved state:

```powershell
docker compose down -v
```

Do not run `down -v` unless you intentionally want a clean HIVE state.

## 14. About "pulling from Docker Desktop"

There is currently **no published HIVE registry image** to `docker pull`.

The supported flow is:

```text
GitHub repo
   ↓ git clone / git pull
local source tree
   ↓ docker compose up -d --build
Docker Desktop local image + containers
```

Once the Compose application exists, Docker Desktop can start, stop, inspect, and remove it through the GUI.

If a prebuilt GHCR/Docker Hub image is published later, this document should be updated with an explicit image name and pull workflow. Do not guess an image name today.

## 15. Troubleshooting

### HIVE never becomes healthy

```powershell
docker compose ps
docker compose logs --tail=200 hive
```

### MCP service is not running

```powershell
docker compose logs --tail=200 hive-mcp
```

### Port already in use

Check whether another process owns `8088`, `8090`, or `1234`.

### LM Studio works in Windows but HIVE says unreachable

This is usually host/container binding rather than an OpenAI API-path problem. Review the LM Studio section above and `docs/WINDOWS.md`.

### Venice key is present but JEV fails

Use Provider health and inspect:

```powershell
docker compose logs --tail=200 hive
```

JEV/Decisions is a beta Venice surface, so current model availability should be confirmed through Venice's Models API rather than assumed indefinitely.