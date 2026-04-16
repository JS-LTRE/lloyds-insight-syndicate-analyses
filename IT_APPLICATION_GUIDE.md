# Longtail Re — IT Application Guide

Reference guide for IT, operations, and new developers covering all applications hosted
on `svralia01.longtailre.com`. All apps run on Docker + Docker Compose on the internal
application server.

**Server:** `svralia01.longtailre.com` (IP: `10.0.1.4`)  
**Host OS:** Linux (Ubuntu/Debian)  
**Docker runtime:** Docker + Docker Compose  
**Host nginx:** `/etc/nginx/sites-enabled/svralia01.conf` — routes all apps via port 80

---

## Application Inventory

| App | URL path | Port | Tech | Owner |
|---|---|---|---|---|
| [Lloyd's Data Ingestion](#lloydS-data-ingestion) | `/lloyds-data-ingestion` | 8012 | FastAPI + React + Vite | — |
| [LEAP](#leap) | `/leap` | 8001 | FastAPI + React + Vite | Ethan Kochav |
| [LISA (Lloyd's Insight and Syndicate Analysis)](#lisa-lloyds-insight-and-syndicate-analysis) | `/lloyds-insight-syndicate-analysis` | 8502 | Streamlit | Jianhua Siew |
| [NDA Database](#nda-database) | `/nda-database` | 8002 | FastAPI + React + Vite | Matthew Evans |
| [Underwriting Folder Scanner / Atlas](#underwriting-folder-scanner--atlas) | `/underwriting-folder-scanner` | 8004/8005 | FastAPI + marker-pdf + Snowflake | Matthew Evans |
| [UW Memo Writer](#uw-memo-writer) | `/uw-memo-writer` | 8000 | FastAPI + React + Vite + Celery | Matthew Evans |
| [MCP Gateway](#mcp-gateway) | (API only) | 8080 | FastAPI + pyodbc | — |

---

## Lloyd's Data Ingestion

> **Note:** This application is referenced in the host nginx config (`/lloyds-data-ingestion/` → port 8012) but its source directory is not present under `/srv/docker/`. It may be deployed under a different path or from a different location. Details below are inferred from the nginx config entry only.

- **URL:** `http://svralia01.longtailre.com/lloyds-data-ingestion`
- **Purpose:** Reference style application — described as the design standard for all other Longtail Re browser-facing apps
- **Port:** 8012 (internal)
- **Docker path:** Unknown

---

## LEAP

**Full name:** Longtail Exposure Analytics Platform

### Purpose

Web application for catastrophe reinsurance modelling and exposure analysis. Replaces an
R CLI toolkit. Used by the Actuarial/Risk Management team for portfolio optimisation and
exposure analysis across a Year of Account.

### Ownership

| Role | Person |
|---|---|
| Business owner | Actuarial / Risk Management |
| Technical owner | Ethan Kochav |
| GitHub | `YS-LT/LEAP` |

### URLs

| Environment | URL |
|---|---|
| Production | `http://svralia01.longtailre.com/leap` |

### Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI (Python 3.12) |
| Frontend | React 18 + Vite 5 + TypeScript |
| Data | pandas, numpy, scipy |
| Charts | Recharts |
| Database | Snowflake (`SANDBOX_ACTUARIAL.PUBLIC`) |
| Reverse proxy | Host nginx (port 8001) |

### Runtime Architecture

```
Browser → nginx (port 80) → LEAP container (port 8001) → Snowflake
```

Multi-stage Docker build: Node 22 builds React frontend → Python runtime serves both.

### Snowflake Schema

Database: `SANDBOX_ACTUARIAL`, schema: `PUBLIC` (legacy; new apps should use named schema)

Key tables: `risk_models`, `yelt` (28.9M rows), `ep_curves`, `ep_curve_data`,
`region_peril_mappings`, `mapping_runs`, `region_mapping`, `trades`, `trade_history`,
`portfolios`, `portfolio_results`, `portfolio_trades`

### Monday.com

Not used.

### Secrets

| Secret | 1Password reference |
|---|---|
| `SNOWFLAKE_ACCOUNT` | `op://DM Service Accounts/<item>/account` |
| `SNOWFLAKE_PASSWORD` | `op://DM Service Accounts/<item>/password` |

Injected via: `op run --env-file=.env.production -- docker compose up -d`

### LAN Mounts

None — all data lives in Snowflake.

### Required Mounts

None.

### Deployment

```bash
cd /srv/docker/leap
op run --env-file=.env.production -- docker compose up -d --build
```

### Notable Risks

- YELT table has 28.9M rows — Snowflake query performance is workload-sensitive
- Service account `KHALEEL.DALEY@LONGTAILRE.COM` with role `SANDBOX_ACTUARIAL_ADMIN`
  — review whether admin role is still needed
- GitHub repo under personal account `YS-LT` — not compliant with `ME-LTRE` standard

---

## LISA (Lloyd's Insight and Syndicate Analysis)

### Purpose

Interactive Streamlit dashboard for analysing Lloyd's of London syndicate historical
performance data (2015–2025). Covers 162 syndicates across 11 years. Provides P&L,
balance sheet, segmental line-of-business views, market benchmarking, asset return data,
and LOB market-level performance — without requiring access to raw ICMR data files.

### Ownership

| Role | Person |
|---|---|
| Business owner | Underwriting / Cedants |
| Technical owner | Jianhua Siew |
| GitHub | `JS-LTRE/lloyds-insight-syndicate-analyses` |

### URLs

| Environment | URL |
|---|---|
| Production | `http://svralia01.longtailre.com/lloyds-insight-syndicate-analysis` |
| Direct (non-standard) | `http://svralia01.longtailre.com:8502/lloyds-insight-syndicate-analysis` |
| Dev | `http://svralia01.longtailre.com/lloyds-insight-syndicate-analysis-dev` |

### Tech Stack

| Component | Technology |
|---|---|
| Frontend / backend | Streamlit 1.55.0 |
| Data manipulation | pandas 2.3.3 |
| Charts | Plotly 6.6.0 |
| Excel ingestion | openpyxl 3.1.5 |
| App reverse proxy | nginx 1.27-alpine (container) |
| Host reverse proxy | nginx (host, port 80) |

### Runtime Architecture

```
Browser
  └─► host nginx (port 80) → /lloyds-insight-syndicate-analysis/
        └─► LISA nginx container (port 8502)
              └─► Streamlit app (internal port 8501)
                    └─► CSV files baked into Docker image
```

Note: This is a double-proxy pattern (unusual). Other apps go directly from host nginx
to the container. New apps should not replicate this.

### Data Storage

No database. All data is pre-generated CSV files bundled into the Docker image at build
time. No runtime database connections.

**CSV files (16 total):**

| File(s) | Contents |
|---|---|
| `01–06` | Raw ICMR data (whole account, segmental, exchange rates, LOB mapping) |
| `07–12` | Derived KPIs (ratios, percentile ranks, market summaries, LOB market share) |
| `13` | Major global insured loss events (reinsurancene.ws) |
| `14` | Lloyd's-specific annual loss drivers (Lloyd's Annual Reports) |
| `15` | Syndicate financial investment cost and asset return (2024–2025) |
| `16` | FX rates (annual averages, GBP/USD/EUR) |

**Source:** Annual ICMR Excel file from LAN share (`/mnt/ltre-f-drive`). Not baked into
the image.

**Data refresh:** Manual, annually (Q2). Requires copying the new Excel file, running
`process_data.py`, manually updating CSVs 13–15, then rebuilding the Docker image.

### Monday.com

Not used.

### Secrets

None. No external API keys or database credentials required.

### LAN Mounts

`/mnt/ltre-f-drive` on host — used manually for annual data refresh only. Not mounted
into containers.

### Required Mounts

None for day-to-day operation.

### Deployment

```bash
cd /srv/docker/lid
git pull
docker compose up --build -d
```

### Annual Data Refresh

See `README.md` and `CLAUDE.md` in the `/srv/docker/lid` repo for the 7-step refresh
guide. Key steps:

1. Copy new ICMR Excel from `/mnt/ltre-f-drive`
2. Update `EXCEL_FILE` path in `process_data.py`
3. Run `python3 process_data.py` → regenerates CSVs 01–12
4. Update `16_fx_rate_used.csv` (append new year rates)
5. Update `13_major_loss_events.csv` (new events from reinsurancene.ws)
6. Update `14_lloyds_loss_drivers.csv` (new year drivers from Lloyd's Annual Report)
7. Update `15_Synd_Asset_Return.csv` (syndicate asset returns from annual accounts)
8. Rebuild and redeploy: `docker compose up --build -d`

### Notable Risks

- **Dockerfile HEALTHCHECK** uses wrong base URL path — `docker ps` reports unhealthy
  but the app is working. Verify manually using the `urllib.request` health check
  documented in CLAUDE.md.
- **Double-proxy architecture** (host nginx → LISA nginx → Streamlit) is non-standard
  and fragile. Consider simplifying by removing the LISA nginx container and binding
  Streamlit directly to a localhost port.
- **GitHub repo under personal account** `JS-LTRE` — should migrate to `ME-LTRE`.
- **`COPY . .` includes source Excel files and scripts** in the Docker image, adding
  ~50–100 MB. Add `.dockerignore` to exclude `*.xlsx` and `process_data.py`.
- **Annual refresh is fully manual** — no automation or alerting when new ICMR data is
  available.
- **2025 Lloyd's Annual Report** does not publish granular per-event GBP figures
  for all events — some rows in `14_lloyds_loss_drivers.csv` have blank `lloyds_loss_gbp_m`.

---

## NDA Database

### Purpose

Document management system for Non-Disclosure Agreements and reinsurance contracts.
Provides search, extraction, and management of legal contracts using AI-powered document
analysis. Integrates with the LAN legal share, Monday.com, Azure OpenAI, and Snowflake.

### Ownership

| Role | Person |
|---|---|
| Business owner | Legal |
| Technical owner | Matthew Evans |
| GitHub | None (no remote configured) |

### URLs

| Environment | URL |
|---|---|
| Production | `http://svralia01.longtailre.com/nda-database` |

### Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI (Python 3.12) |
| Frontend | React + Vite |
| Document processing | marker-pdf (OCR), markitdown (Office/email), PyMuPDF |
| Database (local) | SQLite |
| Database (cloud) | Snowflake (`SANDBOX_ACTUARIAL.NDA_DATABASE`) |
| AI | Azure OpenAI (GPT-5-mini) |
| Reverse proxy | Host nginx (port 8002) |

### Runtime Architecture

```
Browser → nginx (port 80) → NDA container (port 8002)
                               ├─► SQLite (local metadata)
                               ├─► Snowflake NDA_DATABASE (vector embeddings)
                               ├─► Azure OpenAI (document analysis)
                               └─► Monday.com (cedant data)
```

**Two service modes:**
- `app` — FastAPI API + React web UI (normal operation)
- `crawler` — one-off background job that scans the LAN legal share and populates the database

### Snowflake Schema

Database: `SANDBOX_ACTUARIAL`, schema: `NDA_DATABASE`  
Tables: artifact storage + vector table for embeddings

### Monday.com

Board ID: `4527766176`. Used to read cedant and counterparty data for NDA matching.

### Secrets

| Secret | Notes |
|---|---|
| `OPENAI_API_KEY` | Azure OpenAI key |
| `MONDAY_API_KEY` | Monday.com API key |
| `SNOWFLAKE_PAT` | Snowflake programmatic access token |

Stored in 1Password; injected via environment at runtime.

### LAN Mounts

`/mnt/ltre-legal` — legal contracts and NDAs. Used by the crawler service only (read-only).
Path inside container: `NDA_LEGAL_SHARE_PATH=/mnt/ltre-legal/Legal/01. Reinsurance Contracts/01. NDA's`

### Required Mounts

For crawler: `/mnt/ltre-legal` must be mounted read-only.

### Deployment

```bash
cd /srv/docker/nda-database
op run --env-file=.env -- docker compose up -d --build
```

### Notable Risks

- **No GitHub remote** — code not backed up externally
- **SQLite** for local metadata is not replicated and would be lost if the volume is deleted
- **marker-pdf** requires significant CPU for OCR on scanned PDFs

---

## Underwriting Folder Scanner / Atlas

### Purpose

Automated document scanning pipeline and AI knowledge base for underwriting, legal, and
UW package documents. Converts documents to markdown, embeds them as vector chunks in
Snowflake, and exposes the knowledge base via:

1. An MCP server (`mcp_rag`) for AI assistant integrations
2. **Atlas** — an AI bot accessible via web UI and Slack (`/ltre-bot`) for natural-language
   queries against the embedded knowledge base

### Ownership

| Role | Person |
|---|---|
| Business owner | Underwriting |
| Technical owner | Matthew Evans |
| GitHub | None (no remote configured) |

### URLs

| Endpoint | URL |
|---|---|
| Bot web UI | `http://svralia01.longtailre.com/ltre-bot` |
| Bot API | `http://svralia01.longtailre.com/ltre-bot-api` |
| Scanner (no browser UI) | Internal only |

### Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI (Python 3.12) |
| Document processing | marker-pdf (GPU OCR), pdfminer, openpyxl, markitdown |
| AI (summarisation) | Azure OpenAI (GPT-5-mini) |
| AI (embeddings) | Azure OpenAI (text-embedding-3-small) |
| Vector database | Snowflake (with vector search) |
| MCP server | mcp_rag, mcp_monday |
| Slack bot | Atlas (port 8005 websocket) |
| GPU | NVIDIA A10-8Q (required for marker-pdf OCR) |

### Runtime Architecture

```
Nightly systemd timer (04:00 UTC)
  └─► scanner container (GPU)
        ├─► Stage 1–3: Scan legal / underwriting / UW package from LAN share
        ├─► Stage 4: Embed non-spreadsheets → Snowflake vector table
        └─► Stage 5–6: Summarise + embed spreadsheets → Snowflake

Atlas bot (port 8001/8005)
  └─► RAG against Snowflake vector table
  └─► Monday.com API
  └─► MSSQL internal SQL Server
  └─► Brave Search web API
```

### Snowflake Schema

Database: `SANDBOX_ACTUARIAL`, schema: `UNDERWRITING_FOLDER_SCANNER`

Key tables: `MARKDOWN_ARTIFACTS`, `VECTOR_TABLE`, `SOURCE_FILES`, `EXTRACTION_TABLE`,
`MONDAY_BOARDS`, `MONDAY_COLUMNS`, `MONDAY_ITEMS`, `MONDAY_REFERENCES`, `MONDAY_MATCHES`,
`PAS_EXTRACTION_RESULTS`, `BOT_QUERY_LOG`, `RAW_FILE_STAGE`

### Monday.com

Board IDs: `4527766176` (primary), `4441241930` (secondary)  
Syncs board items and columns to Snowflake Monday tables. Atlas bot can query and
reference Monday data.

### Secrets

| Secret | Notes |
|---|---|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key |
| `MONDAY_API_KEY` | Monday.com API key |
| `SNOWFLAKE_PASSWORD` | Snowflake service account password |
| `BRAVE_API_KEY` | Brave Search API key (bot only) |
| 1Password service account token | Used by `ensure-mount.sh` for LAN mount recovery |

Stored in 1Password; injected via `op run`.

### LAN Mounts

| Share | Mount path | Contents |
|---|---|---|
| F: drive underwriting | `/mnt/ltre-f-drive` | `F:\Underwriting\Cedants\P&C` (excl. zz_Archive) |
| F: drive legal | `/mnt/ltre-f-drive` | `F:\Legal\01. Reinsurance Contracts` |
| F: drive UW package | `/mnt/ltre-f-drive` | `F:\Underwriting\UW Package` |

Mount method: CIFS + Kerberos, service account `sa_alia`  
Auto-recovery: `ensure-mount.sh` runs on systemd timer every 2 hours  
Kerberos refresh: systemd timer every 2 hours

### Required Mounts

`/mnt/ltre-f-drive` must be mounted and healthy for nightly scanner runs.

### Deployment

```bash
cd /srv/docker/underwriting-folder-scanner
op run --env-file=.env.tpl -- docker compose up -d --build
```

Nightly pipeline managed by systemd timer (see `/etc/systemd/system/`).

### Notable Risks

- **GPU dependency** — scanner will not run if NVIDIA A10-8Q is unavailable
- **No GitHub remote** — code not backed up externally
- **Nightly pipeline** — any LAN mount failure silently skips scanned documents
- **Kerberos expiry** — if `ensure-mount.sh` fails, mount goes stale; next night's scan
  will fail silently
- **10,000 row cap** on spreadsheets — very large spreadsheets will be truncated

---

## UW Memo Writer

### Purpose

Automated underwriting memorandum generation. Transforms Excel economic models and Word
templates into professional board-ready underwriting memos. Renders 60+ template
variables from Excel, Monday.com deal data, and Azure OpenAI. Produces formatted Word
documents following standard naming conventions.

### Ownership

| Role | Person |
|---|---|
| Business owner | Underwriting |
| Technical owner | Matthew Evans |
| GitHub | `mdevans21/uw_memo_writer` (non-compliant — personal account) |

### URLs

| Environment | URL |
|---|---|
| Production | `http://svralia01.longtailre.com/uw-memo-writer` |

### Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI (Python 3.12) |
| Frontend | React + Vite (TypeScript) |
| Task queue | Celery + Redis 7-alpine |
| Exhibit rendering | matplotlib, Great Tables, Playwright (Chromium) |
| Document templating | docxtpl |
| Excel parsing | openpyxl |
| AI | Azure OpenAI (GPT-5-mini) |
| Reverse proxy | Host nginx (port 8000) |

### Runtime Architecture

```
Browser → nginx (port 80) → UW Memo Writer app (port 8000)
                               └─► Redis task queue
                                     └─► Celery worker (background)
                                           ├─► Excel parsing
                                           ├─► Monday.com API
                                           ├─► Azure OpenAI
                                           └─► Playwright + matplotlib rendering
```

### Snowflake Schema

Not used.

### Monday.com

Board ID: `4527766176`. Reads deal timeline, status, and business relationships for memo
population.

### Secrets

| Secret | 1Password path |
|---|---|
| `OPENAI_API_KEY` | `op://DM Service Accounts/uw-memo-writer/add more/OPENAI_API_KEY` |
| `MONDAY_API_KEY` | 1Password (item name varies) |

Injected via `op run --env-file=.env.tpl -- docker compose up -d`

### LAN Mounts

None. Excel templates and source files are provided via web UI upload or placed in
`./source` directory.

### Required Mounts

None.

### Deployment

```bash
cd /srv/docker/uw-memo-writer
op run --env-file=.env.tpl -- docker compose up -d --build
```

### Notable Risks

- **Playwright + Chromium** required for exhibit rendering; pre-installed in Dockerfile
  but adds significant image size
- **Font cache** must be pre-warmed at build time to avoid non-root user cache miss at
  runtime (handled in Dockerfile)
- **GitHub repo under personal account** `mdevans21` — not compliant with `ME-LTRE`
- **Celery worker healthcheck disabled** — worker failures may not be immediately visible
- **Playwright Chromium** requires GPU-compatible rendering environment

---

## MCP Gateway

### Purpose

Centralized Model Context Protocol (MCP) data gateway providing policy-governed
read-only access to Azure SQL Server analytics data. Designed for AI assistant
integrations. Eliminates per-user database credential distribution. Future path to a
full MCP server for business users.

### Ownership

| Role | Person |
|---|---|
| Business owner | IT / Data |
| Technical owner | — |
| GitHub | None (no remote configured) |

### URLs

| Environment | URL |
|---|---|
| Health check | `http://localhost:8080/healthz` |

This is an API-only service. It is not routed through the host nginx and is not
browser-accessible by default.

### Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI (Python 3.12) |
| Database | Azure SQL Server (ODBC Driver 18) |
| Query execution | pyodbc (parameterized queries) |
| Logging | structlog (structured audit log) |
| Config | YAML policy file + pydantic-settings |

### Runtime Architecture

```
AI client (MCP) → MCP Gateway (port 8080) → Azure SQL Server (PROD-Database-READONLY)
```

All access is policy-driven via `config/policy.yaml`. Only allowlisted datasets can be
queried. Arbitrary SQL is rejected. All requests are audit-logged.

### Snowflake Schema

Not used — reads Azure SQL, not Snowflake.

### Monday.com

Not used.

### Secrets

| Secret | 1Password path |
|---|---|
| `SQL_SERVER` | `op://DM Service Accounts/PROD-Database-READONLY/server` |
| `SQL_DATABASE` | `op://DM Service Accounts/PROD-Database-READONLY/database` |
| `SQL_USERNAME` | `op://DM Service Accounts/PROD-Database-READONLY/username` |
| `SQL_PASSWORD` | `op://DM Service Accounts/PROD-Database-READONLY/password` |

Injected via `op run --env-file=.env.tpl -- docker compose up -d`

### LAN Mounts

None.

### Notable Risks

- **No API-level authentication** — restrict access at network/firewall level; this
  service should not be exposed beyond `localhost`
- **No GitHub remote** — code not backed up externally
- **Read-only only** — write/DDL verbs are blocked by policy; verify this constraint
  is enforced in code review if the policy file is ever updated

---

## Standards Compliance Matrix

Assessment as of April 2026. Status: **Met** | **Partial** | **Not met** | **N/A**

| Standard | LEAP | LISA | NDA Database | UW Folder Scanner | UW Memo Writer | MCP Gateway |
|---|---|---|---|---|---|---|
| **1Password** | Met | N/A | Met | Met | Met | Met |
| **Snowflake** | Met | N/A — CSV-only | Met | Met | N/A — no DB | N/A — Azure SQL |
| **Snowflake schema per app** | Not met (uses `PUBLIC`) | N/A | Met | Met | N/A | N/A |
| **Monday.com** | N/A | N/A | Met | Met | Met | N/A |
| **Standard URL (port 80, `/app-name`)** | Met | Partial — also on port 8502 | Met | Met | Met | N/A — API only |
| **GitHub under `**-LTRE`** | Not met (`YS-LT`) | Not met (`JS-LTRE`) | Not met (no remote) | Not met (no remote) | Not met (`mdevans21`) | Not met (no remote) |
| **React + Vite style standard** | Met | Partial — Streamlit | Met | Met | Met | N/A |
| **LAN mount pattern** | N/A | Partial — host only, not containerised | Partial — crawler only | Met | N/A | N/A |
| **Dockerized** | Met | Met | Met | Met | Met | Met |
| **README documentation** | Partial — PROJECT_CONTEXT.md only | Met | Partial | Partial | Partial | Met |
| **CLAUDE.md** | No | Met | No | No | No | Met |

### Compliance notes

**1Password — LISA (N/A):** The app has no secrets; this is a legitimate exception, not
an oversight. No credentials of any kind are required.

**Snowflake — LISA (N/A):** Data is static year-end snapshots from Lloyd's reports.
A database would add operational complexity with no benefit. Pre-generated CSVs
bundled into the Docker image are the correct architecture for this use case.

**Snowflake schema — LEAP (Not met):** LEAP uses `SANDBOX_ACTUARIAL.PUBLIC` — the
generic/default schema — rather than a dedicated named schema. All new applications must
use their own named schema.

**Standard URL — LISA (Partial):** LISA is accessible at the standard path
(`http://svralia01.longtailre.com/lloyds-insight-syndicate-analysis`) but also exposes
port 8502 directly. The host nginx routes to port 8502 rather than directly to the
container, creating a double-proxy. New apps should not replicate this.

**GitHub — All apps (Not met / Partial):** No application currently has its repository
under the `ME-LTRE` organisation. This is the single most widespread compliance gap and
should be addressed as a one-off migration task.

**LAN mount — LISA (Partial):** The LAN share is used only for annual data refresh and
is accessed from the host — not mounted into any container. This is a documented and
justified exception. If refresh were automated, the mount would need to follow the
standard containerised pattern.

**LAN mount — NDA Database (Partial):** The LAN mount is used only by the crawler
service (not the main app container), but the crawler is a defined service in
`docker-compose.yml` and the mount is documented. This is closer to compliant than LISA's
approach.

**CLAUDE.md — Most apps (No):** Only LISA and MCP Gateway have CLAUDE.md files. All
other apps should add one to improve AI-assisted development and onboarding.

---

## Port Allocation Registry

| Port | Bound to | App | Notes |
|---|---|---|---|
| 80 | `0.0.0.0` | Host nginx | Routes all browser apps |
| 8000 | `127.0.0.1` | UW Memo Writer | App container |
| 8001 | `0.0.0.0` | LEAP / UW Folder Scanner bot API | Shared port; avoid for new apps |
| 8002 | `127.0.0.1` | NDA Database | App container |
| 8004 | `127.0.0.1` | UW Folder Scanner bot (web UI) | |
| 8005 | `127.0.0.1` | UW Folder Scanner (Slack websocket) | |
| 8012 | — | Lloyd's Data Ingestion | Location unknown |
| 8080 | `127.0.0.1` | MCP Gateway | API-only; not browser-accessible |
| 8501 | internal | LISA Streamlit | Internal to LISA Docker network |
| 8502 | `0.0.0.0` | LISA nginx container | Non-standard; also proxied via port 80 |
| 8503 | `0.0.0.0` | LISA dev instance | Non-standard |

---

## Operational Checklist for IT

### Restarting a service after code changes

```bash
cd /srv/docker/<app>
git pull
# For apps with 1Password secrets:
op run --env-file=.env.tpl -- docker compose up -d --build
# For LISA (no secrets):
docker compose up --build -d
```

### Checking container health

```bash
docker ps --filter "name=<app>"
docker logs -f <container-name>
```

### Full server app status

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Emergency stop (all apps)

```bash
cd /srv/docker/<app> && docker compose down
```

### Verifying host nginx is routing correctly

```bash
sudo nginx -t
sudo systemctl status nginx
curl -I http://localhost/<app-name>/
```
