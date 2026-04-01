\
# Sample

This folder contains reusable sample inputs and one PowerShell runner for sending them into the system.

## Design Choice

This layout is intentionally flat.

Instead of splitting into:

- `sample/http/`
- `sample/file/`
- `sample/syslog/`

all sample files stay in one folder because the number of files is still small and keeping them flat makes the commands shorter.

## Files

- `run-sample.ps1`
- `http_ingest_app_login_failed.json`
- `crowdstrike_sample.json`
- `AWS_M365_AD_sample.json`
- `firewall_syslog.log`
- `router_syslog.log`

## How The Runner Works

This script supports **two modes**:

1. **No argument**
   - opens a simple menu
   - you choose by number
   - the script runs immediately

2. **Argument provided**
   - runs directly without opening the menu

Examples:

```powershell
.\sample\run-sample.ps1
.\sample\run-sample.ps1 firewall
.\sample\run-sample.ps1 filebatch
```

## Commands

Show help:

```powershell
.\sample\run-sample.ps1 list
```

Send one HTTP login-failed sample:

```powershell
.\sample\run-sample.ps1 loginfail
```

Send CrowdStrike HTTP sample:

```powershell
.\sample\run-sample.ps1 crowdstrike
```

Upload the JSON array file through `/ingest/file`:

```powershell
.\sample\run-sample.ps1 filebatch
```

Send firewall syslog:

```powershell
.\sample\run-sample.ps1 firewall
```

Send router syslog:

```powershell
.\sample\run-sample.ps1 router
```

Send all HTTP single-event samples:

```powershell
.\sample\run-sample.ps1 allhttp
```

Send all syslog samples:

```powershell
.\sample\run-sample.ps1 allsyslog
```

Check retention status:

```powershell
.\sample\run-sample.ps1 retention-status
```

Run retention now:

```powershell
.\sample\run-sample.ps1 retention-run
```

Reset PostgreSQL logs table:

```powershell
.\sample\run-sample.ps1 postgres-reset
```

## Notes

- `filebatch` is separate from `allhttp`
- `postgres-reset` asks for confirmation inside the script
- defaults:
  - API base URL: `http://127.0.0.1:8012`
  - UDP syslog host: `127.0.0.1`
  - UDP syslog port: `5515`
  - admin user for retention endpoints: `admin1`
