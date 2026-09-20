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
9. optionally offers the full ~1.1 GB MaleCNS research pack;
10. verifies the real-connectome runtime is ready;
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

- the corrected Cook connectome and the 1,045-neuron MaleCNS runtime subgraph installed + verified;
- the default Larva→Bee path using those measured topologies;
- JEV available when Venice is configured and reachable; a requested JEV call fails visibly rather than silently falling back;
- LLM calls unavailable until an LM Studio or Venice chat model is configured;
- browser DOM/OCR and worker-to-worker bus surfaces to remain visibly marked unfinished where they are not executable yet.

## 6. Test the neural path first

Choose **Test the connectome neural layer** in the GUI and load the example.

That path runs:

```text
Cook measured topology → MaleCNS measured topology
```

with JEV and LLM intentionally disabled. The result should say:

```text
Real connectome topology executed: YES
```

and name the actual engines used.

## 7. Test live Venice / JEV

Choose **Sort / route an event**. This turns JEV on and the LLM off.

If Venice/JEV is really used, the result must say:

```text
Jev LIVE call succeeded
```

and the raw execution receipt must contain:

```text
decisions.provider = venice
execution.jev.called = true
```

If JEV is requested but unavailable, HIVE fails the run instead of silently substituting a fixed readout.

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

If HIVE cannot reach LM Studio because it is bound only to `127.0.0.1`, enable LM Studio's local-network serving only when needed, enable API authentication, and restrict port `1234` with Windows Firewall.

## 9. Run the four-way experiment

For one saved worker, the comparison runs the same experiment with:

```text
JEV off · LLM off
JEV on  · LLM off
JEV off · LLM on
JEV on  · LLM on
```

The worker's data environment, prompts, Larva/Bee configuration, and expected task remain fixed.

## 10. Connectome data

The two default runtime packs are installed automatically during first setup. Open **Connectomes** to inspect their verification status or install optional packs. The installer:

- uses pinned HTTPS URLs;
- writes to a temporary `.part` file;
- bounds download size;
- verifies SHA-256 or pinned Git blob identity;
- atomically moves a verified file into place;
- records an installation receipt.

The installer itself never executes a downloaded file. The neural runtime later opens only configured, verified runtime packs.

The full MaleCNS research pack is roughly 1.1 GB and is optional.

## 11. Update HIVE later

```powershell
cd path\to\hive-connectome
powershell -ExecutionPolicy Bypass -File .\scripts\update-windows.ps1
```

Equivalent:

```powershell
git pull --ff-only
docker compose up -d --build
```

## 12. Stop, restart, and inspect

```powershell
docker compose ps
docker compose logs -f hive
docker compose restart
docker compose stop
docker compose down
```

A destructive full data reset is:

```powershell
docker compose down -v
```

Do not use `-v` unless you intentionally want to delete HIVE's persistent state and downloaded connectome packs.

## 13. Docker Desktop pull model

There is currently no published HIVE registry image. The supported flow is:

```text
GitHub repo
   ↓ git clone / git pull
local source
   ↓ docker compose up -d --build
Docker Desktop local image + containers
```
