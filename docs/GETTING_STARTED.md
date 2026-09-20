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
8. downloads and verifies the full corrected Cook pack;
9. downloads and verifies the required ~1.1 GB full MaleCNS v1.0 pack;
10. installs the reduced MaleCNS locomotor graph separately as a control;
11. compiles and executes one `primary-full` Cook → full MaleCNS smoke event with JEV/LLM disabled;
12. reports primary readiness from execution receipts;
13. checks whether Venice and LM Studio are reachable;
14. opens the GUI.

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

- the **Experiment Lab** front door, not an assistant/task menu;
- `primary-full` selected first;
- a visual **Resolved execution path** showing Input → neural stages → JEV → LLM → recorded result;
- each neural stage to show its real engine, dataset status, and whether it is primary/control;
- C. elegans and MaleCNS to be individually removable with visible switches;
- JEV and LLM to be independently switchable;
- a run result rendered as a numbered execution trace showing only stages that actually executed;
- raw JSON available only under the debugging disclosure;
- lossless experiment export and a four-way JEV/LLM ablation comparison.

## 6. Run the primary Core without external AI

Choose **PRIMARY · Primary Full Connectome — primary-full**.

1. switch **JEV decision layer** off;
2. switch **Language-model layer** off;
3. leave both biological neural stages enabled;
4. enter plain text or JSON in **Give this Core an input**;
5. click **Run this Core**.

The trace should show, in order:

```text
Input
→ C. elegans
→ explicit Worm → Fly bridge
→ full MaleCNS
→ fixed local readout
→ recorded result
```

The fixed readout is an engineered deterministic readout of the final neural observation. It is not JEV and it is not a claim that the connectome itself discovered semantic labels.

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

Open **Connections** in the GUI. You can configure Venice there without editing files or restarting HIVE.

- **Refresh connection status** checks reachability/model discovery.
- **Real JEV test** performs an actual Venice Decisions inference call and records its call ID, HTTP status, latency, request hash, and response hash.

A JEV-enabled Core sends the recorded neural/event state summary to Venice after the enabled neural stages execute. JEV and the LLM are independent layers.

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

Open **Connections** and click **Refresh connection status** again.

### Choose the local model

In the selected Core's **Language-model layer**:

1. enable the layer;
2. set **Provider** to `LM Studio`;
3. enter the exact loaded model identifier in **Model**;
4. choose `Always`, `JEV-gated`, or `Manual`;
5. save the Core;
6. run the experiment.

Use **Real LM Studio test** to prove an actual local model call before interpreting experimental results.

## 9. Run the four-way experiment

For one saved Core, **Ablation comparison → Run JEV/LLM 2 × 2** runs the same input with:

```text
JEV off · LLM off
JEV on  · LLM off
JEV off · LLM on
JEV on  · LLM on
```

The Core's input, neural stages, bridge configuration, prompts, and recording policy remain fixed. Only the JEV/LLM toggles change. This is the preferred first test of whether either external inference layer adds measurable value.

## 10. Connectome data

The Cook pack, full MaleCNS pack, and 1,045-neuron MaleCNS locomotor **control** pack are installed by the v0.7 first-run script. Full MaleCNS is required by the study contract. The setup then executes a `primary-full` smoke event; only a valid full-graph execution receipt can satisfy the primary readiness gate. The installer:

- uses pinned HTTPS URLs;
- writes to a temporary `.part` file;
- bounds download size;
- verifies SHA-256;
- atomically moves a verified file into place;
- records an installation receipt;
- never executes downloaded connectome data.

The full MaleCNS pack is roughly 1.1 GB. Installing it alone does not satisfy primary readiness; the full graph must actually execute and produce a matching receipt.

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

Use a Core whose data environment is configured as `file_drop`.

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

Use **Connections → Refresh connection status / Real JEV test** and inspect:

```powershell
docker compose logs --tail=200 hive
```

JEV/Decisions is a beta Venice surface, so current model availability should be confirmed through Venice's Models API rather than assumed indefinitely.