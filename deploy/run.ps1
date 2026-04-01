param(
    [string]$Action,
    [string]$ListenHost = "0.0.0.0",
    [int]$ApiPort = 8012,
    [int]$DashboardPort = 8502,
    [string]$ApiBaseUrl,
    [string]$DemoComposeFile = "deploy/docker/docker-compose.demo.yml",
    [string]$ApplianceComposeFile = "deploy/docker/docker-compose.appliance.yml"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = (Get-Command python -ErrorAction Stop).Source

if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) {
    $ApiBaseUrl = "http://127.0.0.1:$ApiPort"
}

function Show-Usage {
@"
Usage: .\deploy\run.ps1 <command>

Commands:
  backend         Run FastAPI backend locally
  dashboard       Run Streamlit dashboard locally
  both            Run backend in background and dashboard in foreground
  demo-up         Start Docker demo stack
  demo-down       Stop Docker demo stack
  appliance-up    Start Docker appliance stack
  appliance-down  Stop Docker appliance stack
  help            Show this help

Examples:
  .\deploy\run.ps1 backend
  .\deploy\run.ps1 dashboard
  .\deploy\run.ps1 both
  .\deploy\run.ps1 demo-up
"@ | Write-Host
}

function Invoke-Compose {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArgs
    )

    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($docker) {
        try {
            & docker compose version *> $null
            & docker compose @ComposeArgs
            return
        } catch {
        }
    }

    $dockerCompose = Get-Command docker-compose -ErrorAction SilentlyContinue
    if ($dockerCompose) {
        & docker-compose @ComposeArgs
        return
    }

    throw "docker compose or docker-compose is required."
}

function Run-Backend {
    Set-Location $ProjectRoot
    & $PythonExe -m uvicorn backend.main:app --host $ListenHost --port $ApiPort
}

function Run-Dashboard {
    Set-Location $ProjectRoot
    $env:API_BASE_URL = $ApiBaseUrl
    & $PythonExe -m streamlit run frontend/dashboard.py --server.address $ListenHost --server.port $DashboardPort
}

function Run-Both {
    Set-Location $ProjectRoot
    $env:API_BASE_URL = $ApiBaseUrl

    $backendJob = Start-Job -Name "log-system-backend" -ScriptBlock {
        param($ProjectRoot, $PythonExe, $ListenHost, $ApiPort)
        Set-Location $ProjectRoot
        & $PythonExe -m uvicorn backend.main:app --host $ListenHost --port $ApiPort
    } -ArgumentList $ProjectRoot, $PythonExe, $ListenHost, $ApiPort

    Start-Sleep -Seconds 2

    try {
        & $PythonExe -m streamlit run frontend/dashboard.py --server.address $ListenHost --server.port $DashboardPort
    }
    finally {
        if ($backendJob) {
            Stop-Job -Job $backendJob -ErrorAction SilentlyContinue | Out-Null
            Remove-Job -Job $backendJob -ErrorAction SilentlyContinue | Out-Null
        }
    }
}

if ([string]::IsNullOrWhiteSpace($Action)) {
    $Action = "help"
}

switch ($Action) {
    "backend"        { Run-Backend }
    "dashboard"      { Run-Dashboard }
    "both"           { Run-Both }
    "demo-up"        { Set-Location $ProjectRoot; Invoke-Compose -ComposeArgs @("-f", $DemoComposeFile, "up", "--build") }
    "demo-down"      { Set-Location $ProjectRoot; Invoke-Compose -ComposeArgs @("-f", $DemoComposeFile, "down") }
    "appliance-up"   { Set-Location $ProjectRoot; Invoke-Compose -ComposeArgs @("-f", $ApplianceComposeFile, "up", "--build") }
    "appliance-down" { Set-Location $ProjectRoot; Invoke-Compose -ComposeArgs @("-f", $ApplianceComposeFile, "down") }
    "help"           { Show-Usage }
    default          { Show-Usage }
}
