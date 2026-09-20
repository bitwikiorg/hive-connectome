$ErrorActionPreference = "Stop"

Write-Host "HIVE Connectome - update"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not available in PATH."
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI not found. Start/install Docker Desktop first."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed but the Docker engine is not running."
}

if (-not (Test-Path ".git")) {
    throw "Run this script from the root of a cloned hive-connectome repository."
}

Write-Host "Pulling latest source..."
git pull --ff-only
if ($LASTEXITCODE -ne 0) {
    throw "git pull failed. Resolve local changes/divergence before updating HIVE."
}

Write-Host "Rebuilding and starting HIVE..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed."
}

Write-Host "Waiting for HIVE health..."
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:8088/api/health" -TimeoutSec 2
        if ($r.ok) { $ok = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}

if (-not $ok) {
    docker compose logs --tail=100 hive
    throw "HIVE did not become healthy after the update."
}

Write-Host "HIVE updated and healthy."
Write-Host "GUI: http://127.0.0.1:8088"
Write-Host "MCP: http://127.0.0.1:8090/mcp"
