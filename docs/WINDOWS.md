# Windows + Docker Desktop

Recommended layout: Docker Desktop runs HIVE; LM Studio runs natively on Windows; Docker reaches it through `host.docker.internal`; the browser reaches HIVE on `127.0.0.1:8088`.

Start LM Studio from Developer or:

```powershell
lms server start --port 1234
```

HIVE uses `http://host.docker.internal:1234/v1`.

If that fails while Windows can reach `http://127.0.0.1:1234/v1/models`, LM Studio is probably bound only to loopback. A broader bind is `lms server start --port 1234 --bind 0.0.0.0`; use it only with LM Studio authentication and a restrictive Windows Firewall rule.

The setup script stores the Venice key in `.secrets/venice_api_key`. Jev is beta, so model discovery remains authoritative.

Update with:

```powershell
git pull
docker compose up -d --build
```
