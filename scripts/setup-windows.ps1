$ErrorActionPreference = "Stop"

Write-Host "HIVE Connectome - Windows / Docker Desktop setup"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI not found. Install Docker Desktop first."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed but not running."
}

New-Item -ItemType Directory -Force -Path ".secrets" | Out-Null
New-Item -ItemType Directory -Force -Path "data\inbox" | Out-Null
New-Item -ItemType Directory -Force -Path "data\out" | Out-Null

function Read-SecretToFile([string]$Label, [string]$Path) {
    $secure = Read-Host "$Label (press Enter to skip)" -AsSecureString
    if ($secure.Length -eq 0) {
        if (-not (Test-Path $Path)) { New-Item -ItemType File -Path $Path | Out-Null }
        return
    }
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        [IO.File]::WriteAllText((Join-Path (Resolve-Path (Split-Path $Path -Parent)).Path (Split-Path $Path -Leaf)), $plain)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

Read-SecretToFile "Venice API key for Jev" ".secrets\venice_api_key"
Read-SecretToFile "LM Studio API token (only if LM Studio authentication is enabled)" ".secrets\lmstudio_api_token"

try {
    icacls ".secrets" /inheritance:r /grant:r "$env:USERNAME`:(OI)(CI)F" *> $null
} catch {
    Write-Warning "Could not tighten ACL automatically. Confirm .secrets is readable only by your Windows account."
}

Write-Host "Building HIVE..."
docker compose up -d --build

Write-Host "Waiting for health endpoint..."
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
    throw "HIVE did not become healthy."
}

Write-Host "HIVE is running."
Write-Host "GUI: http://127.0.0.1:8088"
Write-Host "MCP: http://127.0.0.1:8090/mcp"

function Install-HiveConnectomePack([string]$PackId,[bool]$ConfirmLarge=$false){
    Write-Host "Installing verified connectome pack: $PackId"
    $status=Invoke-RestMethod -Uri "http://127.0.0.1:8088/api/connectomes" -TimeoutSec 20
    $pack=$status|Where-Object{$_.id -eq $PackId}|Select-Object -First 1
    if(-not $pack){throw "Connectome pack not found: $PackId"}
    if($pack.installed){Write-Host "  already installed + verified";return}
    $confirm=if($ConfirmLarge){"true"}else{"false"}
    Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8088/api/connectomes/$PackId/install?confirm=$confirm" -TimeoutSec 30|Out-Null
    for($i=0;$i -lt 900;$i++){
        Start-Sleep -Seconds 1
        $job=Invoke-RestMethod -Uri "http://127.0.0.1:8088/api/connectomes/$PackId/job" -TimeoutSec 10
        if($job.status -eq "complete"){Write-Host "  installed + verified";return}
        if($job.status -eq "error"){throw "Connectome install failed for $PackId`: $($job.error)"}
    }
    throw "Timed out installing connectome pack: $PackId"
}

Write-Host "Installing development/control substrates..."
Install-HiveConnectomePack "worm-cook-2020"
Install-HiveConnectomePack "fly-malecns-locomotor"

$runtime=Invoke-RestMethod -Uri "http://127.0.0.1:8088/api/health" -TimeoutSec 10
Write-Host ""
Write-Warning "PRIMARY EXPERIMENT: BLOCKED"
Write-Host "The study requires full Cook C. elegans -> full MaleCNS execution."
Write-Host "v0.6 does not yet implement the full MaleCNS execution engine."
Write-Host "The 1,045-neuron locomotor graph installed above is CONTROL / DEVELOPMENT ONLY."
Write-Host "The full ~1.1 GB MaleCNS dataset is REQUIRED for the primary experiment, not optional."
Write-Host "It is not downloaded automatically in v0.6 because the full-graph engine cannot execute it yet; this avoids wasting bandwidth while the promotion gate is blocked."
if($runtime.neural_runtime.primary.blockers){
    Write-Host "Primary blockers:"
    foreach($b in $runtime.neural_runtime.primary.blockers){Write-Host "  - $b"}
}

try{
    $providers=Invoke-RestMethod -Uri "http://127.0.0.1:8088/api/providers/status" -TimeoutSec 15
    if($providers.lmstudio.ok){Write-Host "LM Studio: reachable from Docker"}else{Write-Warning "LM Studio is not reachable from Docker. See docs/WINDOWS.md."}
    if($providers.venice.configured -and $providers.venice.ok){Write-Host "Venice/Jev: reachable"}elseif($providers.venice.configured){Write-Warning "Venice key is configured but the Decisions API check failed."}
}catch{Write-Warning "Provider connectivity check failed: $($_.Exception.Message)"}
Start-Process "http://127.0.0.1:8088"
