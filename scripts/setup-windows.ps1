$ErrorActionPreference = "Stop"

Write-Host "HIVE Connectome - Windows / Docker Desktop setup"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker CLI not found. Install Docker Desktop first." }
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Desktop is installed but not running." }

New-Item -ItemType Directory -Force -Path ".secrets" | Out-Null
New-Item -ItemType Directory -Force -Path "data\inbox" | Out-Null
New-Item -ItemType Directory -Force -Path "data\out" | Out-Null

function Read-SecretToFile([string]$Label,[string]$Path) {
    $secure = Read-Host "$Label (press Enter to skip)" -AsSecureString
    if ($secure.Length -eq 0) { if (-not (Test-Path $Path)) { New-Item -ItemType File -Path $Path | Out-Null }; return }
    $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $plain=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr); [IO.File]::WriteAllText((Join-Path (Resolve-Path (Split-Path $Path -Parent)).Path (Split-Path $Path -Leaf)),$plain) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}
Read-SecretToFile "Venice API key for Jev" ".secrets\venice_api_key"
Read-SecretToFile "LM Studio API token (only if LM Studio authentication is enabled)" ".secrets\lmstudio_api_token"
try { icacls ".secrets" /inheritance:r /grant:r "$env:USERNAME`:(OI)(CI)F" *> $null } catch { Write-Warning "Confirm .secrets is readable only by your Windows account." }

docker compose up -d --build
$ok=$false
for ($i=0;$i -lt 30;$i++) {
    try { $r=Invoke-RestMethod -Uri "http://127.0.0.1:8088/api/health" -TimeoutSec 2; if ($r.ok) { $ok=$true; break } } catch {}
    Start-Sleep -Seconds 2
}
if (-not $ok) { docker compose logs --tail=100 hive; throw "HIVE did not become healthy." }
Write-Host "GUI: http://127.0.0.1:8088"
Write-Host "MCP: http://127.0.0.1:8090/mcp"
Start-Process "http://127.0.0.1:8088"
