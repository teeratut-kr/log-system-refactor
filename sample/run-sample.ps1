param(
    [string]$Action,
    [string]$ApiBaseUrl = "http://127.0.0.1:8012",
    [string]$User = "admin1",
    [string]$ComposeFile = "deploy/docker/docker-compose.appliance.yml",
    [string]$PostgresService = "postgres",
    [string]$PostgresDb = "logs_db",
    [string]$PostgresUser = "logs_user",
    [string]$SyslogTargetHost = "127.0.0.1",
    [int]$SyslogPort = 5515
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SampleDir = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $SampleDir

$ValidCommands = @(
    "help",
    "list",
    "loginfail",
    "crowdstrike",
    "filebatch",
    "firewall",
    "router",
    "allhttp",
    "allsyslog",
    "retention-status",
    "retention-run",
    "postgres-reset"
)

function Get-ApiBaseUrl {
    param([string]$Base)
    return $Base.TrimEnd("/")
}

function Get-SamplePath {
    param([Parameter(Mandatory = $true)][string]$FileName)
    return [System.IO.Path]::GetFullPath((Join-Path $SampleDir $FileName))
}

function New-AuthHeaders {
    param([string]$UserName = "admin1")
    return @{ "X-User" = $UserName }
}

function Read-JsonFileText {
    param([Parameter(Mandatory = $true)][string]$FileName)
    $path = Get-SamplePath -FileName $FileName
    if (-not (Test-Path $path)) {
        throw "Sample file not found: $path"
    }
    return [System.IO.File]::ReadAllText($path)
}

function Test-BackendReachable {
    $base = Get-ApiBaseUrl -Base $ApiBaseUrl
    try {
        $null = Invoke-RestMethod -Method GET -Uri "$base/" -ErrorAction Stop
        return $true
    } catch {
        throw "Backend is not reachable at $base. Start it first with .\deploy\run.ps1 backend or open the backend/docs URL to confirm it is running."
    }
}

function Invoke-ApiJson {
    param(
        [Parameter(Mandatory = $true)][ValidateSet("GET", "POST", "PUT", "DELETE")][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [hashtable]$Headers,
        [string]$Body,
        [string]$ContentType = "application/json"
    )

    $params = @{
        Method      = $Method
        Uri         = $Uri
        ErrorAction = "Stop"
    }

    if ($Headers) {
        $params["Headers"] = $Headers
    }

    if ($Body) {
        $params["Body"] = $Body
        $params["ContentType"] = $ContentType
    }

    return Invoke-RestMethod @params
}

function Invoke-MultipartUpload {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$FileName,
        [hashtable]$FormFields
    )

    $resolvedFile = Get-SamplePath -FileName $FileName
    if (-not (Test-Path $resolvedFile)) {
        throw "Sample file not found: $resolvedFile"
    }

    Add-Type -AssemblyName System.Net.Http | Out-Null

    $handler = [System.Net.Http.HttpClientHandler]::new()
    $client = [System.Net.Http.HttpClient]::new($handler)

    try {
        $content = [System.Net.Http.MultipartFormDataContent]::new()

        if ($FormFields) {
            foreach ($key in $FormFields.Keys) {
                $stringContent = [System.Net.Http.StringContent]::new([string]$FormFields[$key])
                [void]$content.Add($stringContent, $key)
            }
        }

        $bytes = [System.IO.File]::ReadAllBytes($resolvedFile)
        $fileContent = [System.Net.Http.ByteArrayContent]::new($bytes)
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/octet-stream")
        [void]$content.Add($fileContent, "file", [System.IO.Path]::GetFileName($resolvedFile))

        $response = $client.PostAsync($Uri, $content).GetAwaiter().GetResult()
        $raw = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

        if (-not $response.IsSuccessStatusCode) {
            throw "Upload failed with status $([int]$response.StatusCode): $raw"
        }

        try {
            return $raw | ConvertFrom-Json
        } catch {
            return $raw
        }
    }
    finally {
        $client.Dispose()
        $handler.Dispose()
    }
}

function Invoke-UdpLine {
    param(
        [Parameter(Mandatory = $true)][string]$Line,
        [string]$TargetHost = "127.0.0.1",
        [int]$TargetPort = 5514
    )

    $udp = [System.Net.Sockets.UdpClient]::new()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Line)
        [void]$udp.Send($bytes, $bytes.Length, $TargetHost, $TargetPort)
    }
    finally {
        $udp.Dispose()
    }
}

function Send-HttpSample {
    param([Parameter(Mandatory = $true)][string]$FileName)
    Test-BackendReachable | Out-Null
    $base = Get-ApiBaseUrl -Base $ApiBaseUrl
    $body = Read-JsonFileText -FileName $FileName
    Write-Host "POST $base/ingest"
    Write-Host "Sample: $FileName"
    $response = Invoke-ApiJson -Method POST -Uri "$base/ingest" -Body $body
    $response | ConvertTo-Json -Depth 10
}

function Send-FileBatchSample {
    param(
        [Parameter(Mandatory = $true)][string]$FileName,
        [string]$SourceHint = "network",
        [string]$Tenant = ""
    )

    Test-BackendReachable | Out-Null
    $base = Get-ApiBaseUrl -Base $ApiBaseUrl
    $formFields = @{ source_hint = $SourceHint }
    if ($Tenant) {
        $formFields["tenant"] = $Tenant
    }

    Write-Host "POST $base/ingest/file"
    Write-Host "Sample: $FileName"
    $response = Invoke-MultipartUpload -Uri "$base/ingest/file" -FileName $FileName -FormFields $formFields
    $response | ConvertTo-Json -Depth 10
}

function Send-SyslogSample {
    param([Parameter(Mandatory = $true)][string]$FileName)
    $path = Get-SamplePath -FileName $FileName
    if (-not (Test-Path $path)) {
        throw "Sample file not found: $path"
    }

    $lines = Get-Content -Path $path | Where-Object { $_.Trim() -ne "" }
    foreach ($line in $lines) {
        Invoke-UdpLine -Line $line -TargetHost $SyslogTargetHost -TargetPort $SyslogPort
        Write-Host "Sent syslog line to ${SyslogTargetHost}:${SyslogPort} -> $line"
    }
}

function Show-RetentionStatus {
    Test-BackendReachable | Out-Null
    $base = Get-ApiBaseUrl -Base $ApiBaseUrl
    $headers = New-AuthHeaders -UserName $User
    Write-Host "GET $base/retention"
    $response = Invoke-ApiJson -Method GET -Uri "$base/retention" -Headers $headers
    $response | ConvertTo-Json -Depth 10
}

function Run-Retention {
    Test-BackendReachable | Out-Null
    $base = Get-ApiBaseUrl -Base $ApiBaseUrl
    $headers = New-AuthHeaders -UserName $User
    Write-Host "POST $base/retention/run"
    $response = Invoke-ApiJson -Method POST -Uri "$base/retention/run" -Headers $headers
    $response | ConvertTo-Json -Depth 10
}

function Invoke-Compose {
    param([Parameter(Mandatory = $true)][string[]]$ComposeArgs)

    Set-Location $ProjectRoot

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

function Reset-PostgresLogs {
    $answer = Read-Host "This will TRUNCATE the logs table in PostgreSQL. Continue? (y/N)"
    if ($answer -notin @("y", "Y", "yes", "YES")) {
        Write-Host "Cancelled."
        return
    }

    $sql = "TRUNCATE TABLE logs RESTART IDENTITY;"
    Invoke-Compose -ComposeArgs @(
        "-f", $ComposeFile,
        "exec", "-T", $PostgresService,
        "psql", "-U", $PostgresUser, "-d", $PostgresDb, "-c", $sql
    )
}

function Show-Help {
@"
Available commands

  help, list
    Show help and menu

  loginfail
    POST http_ingest_app_login_failed.json to /ingest

  crowdstrike
    POST crowdstrike_sample.json to /ingest

  filebatch
    Upload AWS_M365_AD_sample.json to /ingest/file

  firewall
    Send firewall_syslog.log over UDP syslog

  router
    Send router_syslog.log over UDP syslog

  allhttp
    Send:
      - http_ingest_app_login_failed.json
      - crowdstrike_sample.json

  allsyslog
    Send:
      - firewall_syslog.log
      - router_syslog.log

  retention-status
    GET /retention as admin

  retention-run
    POST /retention/run as admin

  postgres-reset
    TRUNCATE logs table in PostgreSQL appliance mode

Examples

  .\sample\run-sample.ps1
  .\sample\run-sample.ps1 loginfail
  .\sample\run-sample.ps1 crowdstrike
  .\sample\run-sample.ps1 filebatch
  .\sample\run-sample.ps1 firewall
  .\sample\run-sample.ps1 router
  .\sample\run-sample.ps1 retention-run
"@ | Write-Host
}

function Show-Menu {
    @(
        "1. Send HTTP login failed",
        "2. Send HTTP CrowdStrike",
        "3. Send file batch",
        "4. Send firewall syslog",
        "5. Send router syslog",
        "6. Send all HTTP samples",
        "7. Send all syslog samples",
        "8. Show retention status",
        "9. Run retention now",
        "10. Reset PostgreSQL logs",
        "0. Exit"
    ) | ForEach-Object { Write-Host $_ }

    $choice = Read-Host "Select an option"
    switch ($choice) {
        "1"  { return "loginfail" }
        "2"  { return "crowdstrike" }
        "3"  { return "filebatch" }
        "4"  { return "firewall" }
        "5"  { return "router" }
        "6"  { return "allhttp" }
        "7"  { return "allsyslog" }
        "8"  { return "retention-status" }
        "9"  { return "retention-run" }
        "10" { return "postgres-reset" }
        default { return "" }
    }
}

if ([string]::IsNullOrWhiteSpace($Action)) {
    Write-Host ""
    Write-Host "Sample runner menu"
    Write-Host "------------------"
    $Action = Show-Menu
    if ([string]::IsNullOrWhiteSpace($Action)) {
        Write-Host "Exit."
        exit 0
    }
}

if ($ValidCommands -notcontains $Action) {
    Write-Host "Unknown command: $Action"
    Write-Host ""
    Show-Help
    exit 1
}

switch ($Action) {
    "help"             { Show-Help }
    "list"             { Show-Help }
    "loginfail"        { Send-HttpSample -FileName "http_ingest_app_login_failed.json" }
    "crowdstrike"      { Send-HttpSample -FileName "crowdstrike_sample.json" }
    "filebatch"        { Send-FileBatchSample -FileName "AWS_M365_AD_sample.json" -SourceHint "network" }
    "firewall"         { Send-SyslogSample -FileName "firewall_syslog.log" }
    "router"           { Send-SyslogSample -FileName "router_syslog.log" }
    "retention-status" { Show-RetentionStatus }
    "retention-run"    { Run-Retention }
    "postgres-reset"   { Reset-PostgresLogs }
    "allhttp" {
        Send-HttpSample -FileName "http_ingest_app_login_failed.json"
        Send-HttpSample -FileName "crowdstrike_sample.json"
    }
    "allsyslog" {
        Send-SyslogSample -FileName "firewall_syslog.log"
        Send-SyslogSample -FileName "router_syslog.log"
    }
}
