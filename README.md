# Unified Log Ingestion API — Refactored Version

Local-first refactor of a unified log ingestion platform with a FastAPI backend, Streamlit dashboard, automated tests, and cleaner project structure.

> Current status: local development flow is ready and tested. Docker / docker-compose instructions can be added in a later update.

## Overview

This project ingests logs from multiple inputs, normalizes them into a central schema, stores and queries them, and presents the results in a dashboard.

Main goals:
- accept logs from multiple ingestion paths
- normalize different raw formats into one schema
- support tenant-aware access control
- provide alerting and retention behavior
- keep the system easy to demo and test locally

## Key features

- HTTP JSON ingest via `POST /ingest`
- file ingest via `POST /ingest/file`
- UDP Syslog ingest
- normalization into a central schema
- log querying with filters
- alerting for repeated failed logins from the same IP
- retention cleanup for old logs
- role-based access with admin and viewer behavior
- Streamlit dashboard for interactive inspection and demo use
- automated tests with `pytest`

## Project structure

```text
.
├─ backend/
│  ├─ main.py
│  ├─ config.py
│  ├─ logging_config.py
│  ├─ auth.py
│  ├─ schemas.py
│  ├─ normalizer.py
│  ├─ parsers.py
│  ├─ response_utils.py
│  ├─ routers/
│  ├─ services/
│  └─ storage/
├─ frontend/
│  ├─ dashboard.py
│  ├─ config.py
│  ├─ api.py
│  ├─ demo_auth.py
│  ├─ session.py
│  ├─ styles.py
│  ├─ components/
│  └─ pages/
├─ tests/
├─ requirements-backend.txt
├─ requirements-frontend.txt
├─ requirements-dev.txt
├─ env.example
└─ README.md
```

## Tech stack

### Backend
- FastAPI
- Pydantic
- PostgreSQL via `psycopg` / `psycopg-pool` when `DATABASE_URL` is configured
- in-memory storage fallback for local/demo usage

### Frontend
- Streamlit
- pandas
- Plotly
- requests

### Testing
- pytest

## Authentication and access model

This refactored version keeps a simple demo-friendly auth model:
- API routes such as `/logs`, `/alerts`, `/whoami`, `/retention`, and `/retention/run` use the `X-User` header
- `admin1` can view all logs
- `viewerA` can view only tenant `demoA`
- `viewerB` can view only tenant `demoB`
- viewers cannot access another tenant

The Streamlit dashboard keeps a simple demo login and maps dashboard users to backend users.

## Supported ingestion paths

### 1. JSON ingest
Send one log object to `POST /ingest`.

### 2. File ingest
Upload supported files to `POST /ingest/file`.

Supported file types:
- `.json`
- `.jsonl`
- `.csv`
- `.log`
- `.txt`

### 3. UDP Syslog ingest
The backend listens on UDP for syslog messages and parses supported RFC-style input and key-value payloads.

## Central schema highlights

The central schema supports common normalized fields such as:
- `@timestamp`
- `tenant`
- `source`
- `vendor`
- `product`
- `event_type`
- `severity`
- `action`
- `src_ip` / `dst_ip`
- `user`
- `reason`
- `status`
- `workload`
- `file.hash.sha256`
- cloud-related fields
- `_tags`
- `raw`

## Alerts

The current built-in alert rule is:
- repeated failed logins from the same IP within 5 minutes

This is exposed through `GET /alerts` and is also shown in the dashboard.

## Retention

Retention is configured through environment variables and supports:
- startup cleanup
- scheduled background cleanup
- manual admin-triggered cleanup via `POST /retention/run`

## Environment variables

Create a `.env` file later if needed, or start with defaults for local testing.

Common variables:

| Variable | Purpose | Default |
|---|---|---|
| `API_BASE_URL` | Frontend base URL for backend API | `http://127.0.0.1:8012` |
| `DATABASE_URL` | PostgreSQL connection string | not set |
| `SYSLOG_UDP_HOST` | UDP bind host for syslog listener | `0.0.0.0` |
| `SYSLOG_UDP_PORT` | UDP bind port for syslog listener | `5515` |
| `RETENTION_DAYS` | retention window in days | `7` |
| `RETENTION_CLEANUP_INTERVAL_MINUTES` | cleanup interval for background retention worker | `60` |

## Local setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements-backend.txt -r requirements-frontend.txt
pip install -r requirements-dev.txt
```

## Run locally

### Start the backend

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8012
```

Backend docs:
- `http://127.0.0.1:8012/docs`

### Start the dashboard

Open a second terminal and run:

```powershell
streamlit run frontend/dashboard.py
```

## Dashboard demo accounts

Current demo login accounts:
- `admin / admin`
- `viewerA / viewerA`
- `viewerB / viewerB`

## Run tests

```powershell
pytest
```

## Example API usage

### Check current user

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8012/whoami" -Headers @{"X-User"="admin1"} -Method Get
```

### Ingest one log

```powershell
$body = @{
  tenant = "demoA"
  source = "aws"
  event_type = "login_failed"
  user = "alice"
  src_ip = "10.10.10.10"
  severity = 7
  reason = "wrong_password"
  "@timestamp" = "2026-03-31T10:00:00Z"
  raw = @{ message = "login failed" }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://127.0.0.1:8012/ingest" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### Query logs as admin

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8012/logs" -Headers @{"X-User"="admin1"} -Method Get
```

## Current development status

Completed and verified locally:
- refactored backend and frontend structure
- automated tests passing
- logging and configuration cleanup completed
- dashboard opens successfully
- ingest, query, alerts, syslog, and retention flows verified locally

Planned next step:
- add Docker and docker-compose instructions

## Notes

- This README is intentionally local-first.
- Docker, compose, and deployment instructions can be added after container paths and runtime commands are finalized.
- The current auth model is optimized for demo/testing, not production identity management.

