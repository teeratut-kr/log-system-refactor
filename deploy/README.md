# Deploy

This folder contains project startup and deployment-related resources.

## Purpose

Use this folder when you want to:

- run the project locally through one entry point
- start or stop Docker stacks
- keep deployment resources separate from application code

## Expected Structure

```text
deploy/
  README.md
  run.ps1
  docker/
    dockerfile.backend
    dockerfile.dashboard
    docker-compose.demo.yml
    docker-compose.appliance.yml
```

## Main Entry Point

`run.ps1` is the main PowerShell command entry point.

It is intended to support commands such as:

- `backend`
- `dashboard`
- `both`
- `demo-up`
- `demo-down`
- `appliance-up`
- `appliance-down`

## Typical Usage

Run backend locally:

```powershell
.\deploy\run.ps1 backend
```

Run dashboard locally:

```powershell
.\deploy\run.ps1 dashboard
```

Run both backend and dashboard:

```powershell
.\deploy\run.ps1 both
```

Start Docker demo mode:

```powershell
.\deploy\run.ps1 demo-up
```

Stop Docker demo mode:

```powershell
.\deploy\run.ps1 demo-down
```

Start Docker appliance mode:

```powershell
.\deploy\run.ps1 appliance-up
```

Stop Docker appliance mode:

```powershell
.\deploy\run.ps1 appliance-down
```

## Design Choice

This folder is intentionally focused on **running and deploying the system**.

It does **not** contain helper scripts for:
- ingesting sample logs
- checking retention manually
- resetting PostgreSQL data

Those belong in `scripts/` because they are operational helpers, not startup/deployment commands.

## Notes

- Keep Docker files under `deploy/docker/`
- Keep the main project root cleaner by not placing many run/deploy files at the top level
- Prefer keeping deployment commands centralized here
