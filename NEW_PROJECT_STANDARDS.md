# Longtail Re — New Project Standards

This document defines the minimum technical standards for all new applications built and
deployed by or for Longtail Re. It applies to any application that is:

- hosted on `svralia01.longtailre.com`
- committed to a Longtail Re GitHub account
- built with company data or company-managed credentials

Existing projects predate some of these standards. Non-compliant legacy exceptions are
noted in `IT_APPLICATION_GUIDE.md`.

---

## 1. Secrets Management — 1Password

**Standard:** All application secrets must be stored in 1Password and injected at runtime
via the 1Password CLI. Secrets must never appear in source code, committed `.env` files,
or Docker image layers.

**Vault:** `DM Service Accounts`

**Pattern:**

1. Create a `.env.tpl` file (committed to the repo) that contains only 1Password secret
   references — no actual values. Example:

   ```
   SNOWFLAKE_PASSWORD=op://DM Service Accounts/<item-name>/password
   OPENAI_API_KEY=op://DM Service Accounts/<item-name>/api_key
   ```

2. Start containers by injecting secrets at runtime:

   ```bash
   op run --env-file=.env.tpl -- docker compose up -d
   ```

   This resolves the references and injects them as environment variables — nothing is
   written to disk.

3. For systemd-managed services, the service unit should call `op run` on start:

   ```ini
   ExecStart=op run --env-file=/srv/docker/<app>/.env.tpl -- docker compose up -d
   ```

**Item naming:** Name secrets in 1Password after the application and credential type,
e.g. `LEAP Snowflake Service Account`, `UW Memo Writer OpenAI Key`.

**Evidence from existing apps:**
- `leap`: `op run --env-file=.env.production -- docker compose up -d`
- `mcp-gateway`: `op run --env-file=.env.tpl -- docker compose up -d`; referenced as
  `op://DM Service Accounts/PROD-Database-READONLY/...`
- `uw-memo-writer`: 1Password references in `.env.tpl` for OpenAI and Monday.com keys

**Not applicable when:** The application has no secrets whatsoever (e.g. fully offline
CSV-only apps with no external integrations).

---

## 2. Database — Snowflake

**Standard:** All applications that require persistent data storage must use Snowflake.
Do not use SQLite, PostgreSQL, or other self-managed databases as the primary store for
production data.

**Database:** `SANDBOX_ACTUARIAL`

**Schema convention:** Each application must have its own schema named after the
application. Use uppercase, underscores, no hyphens:

| Application | Schema |
|---|---|
| LEAP | `SANDBOX_ACTUARIAL.PUBLIC` (legacy — new apps should use named schema) |
| NDA Database | `SANDBOX_ACTUARIAL.NDA_DATABASE` |
| Underwriting Folder Scanner | `SANDBOX_ACTUARIAL.UNDERWRITING_FOLDER_SCANNER` |

**Authentication:** Prefer Snowflake Programmatic Access Token (PAT) over
username/password. Store the token in 1Password. Example environment variables:

```
SNOWFLAKE_ACCOUNT=IWFRVPL-YX69610
SNOWFLAKE_USER=<service-account>
SNOWFLAKE_AUTHENTICATOR=PROGRAMMATIC_ACCESS_TOKEN
SNOWFLAKE_PAT=op://DM Service Accounts/<item>/pat
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SANDBOX_ACTUARIAL
SNOWFLAKE_SCHEMA=<APP_SCHEMA>
```

**Warehouse:** Use `COMPUTE_WH` unless workload warrants a dedicated warehouse.

**Evidence from existing apps:**
- LEAP uses `SANDBOX_ACTUARIAL.PUBLIC` with 12 tables (legacy schema name)
- NDA Database uses `SANDBOX_ACTUARIAL.NDA_DATABASE` (correct pattern)
- Underwriting Folder Scanner uses `SANDBOX_ACTUARIAL.UNDERWRITING_FOLDER_SCANNER` with
  11+ tables including vector storage

**Not applicable when:** The application is genuinely read-only and operates on static
data that is refreshed manually (e.g. CSV-embedded dashboards with no user writes).

---

## 3. Monday.com Integration

**Standard:** Monday.com is the single source of truth for deal pipeline, cedant
relationships, and workflow status. Applications that display or act on this data must
read it from Monday.com via the API — not from a local database copy.

**Primary board ID:** `4527766176` (main deals/cedants board)

**Secondary board ID:** `4441241930` (secondary reference board, used by UW Folder Scanner)

**API key:** Store in 1Password. Inject at runtime via `op run`.

**Integration points in existing apps:**

| App | Integration |
|---|---|
| NDA Database | Reads cedant/counterparty data for NDA matching |
| UW Folder Scanner | Syncs board items and columns; stores in Snowflake Monday tables |
| UW Memo Writer | Reads deal timeline, status, and business relationships for memo population |

**Not applicable when:** The application has no dependency on deal lifecycle, cedant
identity, or workflow state.

---

## 4. URL and Routing Convention

**Standard:** All browser-facing applications must be accessible at:

```
http://svralia01.longtailre.com/<app-name>
```

on port **80** via the host nginx at `/etc/nginx/sites-enabled/svralia01.conf`.

**App-name convention:** Use lowercase kebab-case. The path segment should match the
application's `APP_PATH_PREFIX` environment variable inside the container.

**Routing pattern:**

1. Bind the container to `127.0.0.1:<port>` (not `0.0.0.0:<port>`) in `docker-compose.yml`
2. Add a `location /<app-name>/` block to `svralia01.conf` proxying to `http://127.0.0.1:<port>/`
3. Pass `X-Forwarded-Prefix: /<app-name>` to help frameworks resolve asset URLs

Example `docker-compose.yml`:

```yaml
services:
  app:
    ports:
      - "127.0.0.1:8003:8000"
    environment:
      - APP_PATH_PREFIX=/<app-name>
```

Example `svralia01.conf` block:

```nginx
location /<app-name>/ {
    proxy_pass http://127.0.0.1:8003/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /<app-name>;
    proxy_read_timeout 300s;
    client_max_body_size 100M;
}
```

**Registered port allocations on svralia01:**

| Port | App |
|---|---|
| 8000 | UW Memo Writer |
| 8001 | LEAP / UW Folder Scanner bot API |
| 8002 | NDA Database |
| 8004 | UW Folder Scanner (bot frontend) |
| 8005 | UW Folder Scanner (Slack websocket) |
| 8012 | Lloyd's Data Ingestion |
| 8080 | MCP Gateway (API-only, not browser-routed) |
| 8501 | LISA Streamlit internal (behind LISA nginx) |
| 8502 | LISA nginx (non-standard, avoid for new apps) |
| 8503 | LISA dev instance |

**Do not expose container ports on `0.0.0.0`** — bind to `127.0.0.1` only.

**Non-standard exception:** LISA (`lid`) currently exposes its
own nginx container on port 8502. The host nginx also routes `/lloyds-insight-syndicate-analysis/`
to port 8502. New apps should not replicate this double-proxy pattern — bind Streamlit
directly to a localhost port and route via the single host nginx.

---

## 5. GitHub Repository Ownership

**Standard:** All repositories must be owned by a `**-LTRE` GitHub account. The preferred
organisation is `ME-LTRE`.

**Account convention:** Personal LTRE accounts use the format `<initials>-LTRE`
(e.g. `ME-LTRE`, `JS-LTRE`, `YS-LT`). Repositories should ultimately be transferred to
`ME-LTRE` when the team organisation is formalised.

**Repository naming:** Use lowercase kebab-case matching the app-name URL path segment
where practical.

**Existing exceptions:**

| Repo | Owner | Status |
|---|---|---|
| `lloyds-insight-syndicate-analyses` | `JS-LTRE` | Non-compliant; should migrate to `ME-LTRE` |
| `LEAP` | `YS-LT` | Non-compliant; should migrate to `ME-LTRE` |
| `uw_memo_writer` | `mdevans21` | Non-compliant; should migrate to `ME-LTRE` |
| NDA Database | (no remote) | Non-compliant; should be added to GitHub |
| Underwriting Folder Scanner | (no remote) | Non-compliant; should be added to GitHub |
| MCP Gateway | (no remote) | Non-compliant; should be added to GitHub |

---

## 6. Frontend Stack and Style

**Standard:** Browser-facing applications should use the React + Vite + TypeScript stack
to maintain a consistent look and feel across the platform.

**Reference application:** `http://svralia01.longtailre.com/lloyds-data-ingestion`

**Stack:**

| Component | Technology |
|---|---|
| Framework | React 18 + Vite 5 |
| Language | TypeScript |
| Data fetching | @tanstack/react-query |
| Charts | Recharts (primary) |
| UI components | Shadcn/ui or compatible |
| Build output | Static files served from FastAPI or nginx |

**Exception:** Data analysis tools built by a single developer for internal analyst use
may use Streamlit as a pragmatic alternative to React+Vite. This exception applies where:
- The primary audience is analysts, not business users
- The developer does not have React experience
- Rich interactivity requirements are limited to filters and charts

Streamlit apps should still follow all other standards (Docker, 1Password, URL routing,
documentation).

---

## 7. Backend Stack

**Standard:** Use FastAPI (Python 3.12+) for all REST API backends.

**Standard patterns:**

- `uvicorn` as the ASGI server
- `pydantic-settings` for configuration loading from environment variables
- `structlog` for structured JSON logging
- `APP_PATH_PREFIX` environment variable to control base URL path

**Async tasks:** Use Celery + Redis for long-running background jobs (document processing,
report generation). Do not block the FastAPI request thread for jobs >5s.

---

## 8. LAN Fileshare Mount Pattern

**Standard:** Applications that need to read files from the Longtail Re file server must
follow the CIFS Kerberos mount pattern established in the Underwriting Folder Scanner.

**Service account:** `sa_alia` (Kerberos-authenticated CIFS mount)

**Host mount points:**

| Share | Mount path | Contents |
|---|---|---|
| F: drive (underwriting) | `/mnt/ltre-f-drive` | Underwriting, cedants, ICMR data |
| Legal share | `/mnt/ltre-legal` | Legal contracts, NDAs |

**Mount pattern:**

- Mount on host (not inside containers) using CIFS + Kerberos
- Refresh Kerberos ticket every 2 hours via systemd timer (`ensure-mount.sh`)
- Mount only inside containers that need access, as a bind mount (read-only preferred)
- Auto-recovery: `ensure-mount.sh` checks mount health and remounts if needed, using
  the 1Password service account token to retrieve credentials

**Exception:** If files are needed only for an infrequent manual process (e.g. annual
data refresh), it is acceptable to access the mount from the host without mounting into
a container. Document this clearly in the README.

---

## 9. Dockerization

**Standard:** All applications must run inside Docker containers managed by Docker
Compose. No application should run directly on the host.

**Required files:**

- `Dockerfile` — multi-stage build preferred (e.g. Node build → Python runtime)
- `docker-compose.yml` — defines all services
- `.dockerignore` — exclude `*.xlsx`, large binaries, dev-only scripts

**Container naming convention:**

```
<app-name>-app
<app-name>-worker  (if Celery worker)
<app-name>-redis   (if Redis)
<app-name>-nginx   (avoid — use host nginx instead)
```

**Port binding:** Bind to `127.0.0.1:<port>` not `0.0.0.0:<port>`.

**Healthcheck:** Include a `HEALTHCHECK` in the Dockerfile pointing to the correct
health endpoint including the base URL path, e.g.:

```dockerfile
HEALTHCHECK CMD curl -f http://localhost:8000/<app-name>/api/health || exit 1
```

**Restart policy:** Use `restart: unless-stopped` for all long-running services.

**Volume management:**

- Application data that must persist across rebuilds should use named volumes or host
  bind mounts to `./data`, `./uploads`, `./output` as appropriate
- Source files (inputs/templates) should be bind-mounted read-only

---

## 10. Documentation

**Standard:** Every application must include:

### README.md

A README at the repo root following this structure:

1. **Application name and one-line description**
2. **Standards compliance table** — one row per standard (Met / Partially met / Not met /
   N/A) with brief notes
3. **Purpose and ownership** — business owner, technical owner, deployment URL, GitHub repo
4. **Application overview** — what it does, tech stack table, runtime architecture diagram
5. **Source data inputs** — where data comes from, how it is refreshed
6. **External integrations** — Snowflake schema, Monday.com boards, APIs
7. **Running locally** — Docker and non-Docker instructions
8. **Deployment (server)** — git pull + rebuild steps
9. **Annual / routine data refresh** — step-by-step
10. **Recovery and restart commands**
11. **Operational dependencies table**
12. **Non-standard exceptions** — explicit list with rationale
13. **Known issues** — explicit list with workarounds

### CLAUDE.md

A CLAUDE.md at the repo root for AI-assisted development. Must include:

1. Ordered startup checklist (confirm files present, rebuild, health-check)
2. Architecture overview
3. Data dictionary (all files/tables and their purpose)
4. Key formulas and business logic
5. App section map (which file/function renders which UI section)
6. Annual refresh guide

---

## Standards Compliance Matrix

Use this matrix in `IT_APPLICATION_GUIDE.md` to summarise every application's compliance
status at a glance. Status values: **Met** | **Partial** | **Not met** | **N/A**

| Standard | Assessed per app in IT_APPLICATION_GUIDE.md |
|---|---|
| 1Password | |
| Snowflake | |
| Snowflake schema per app | |
| Monday.com | |
| Standard URL (port 80, `/app-name`) | |
| GitHub under `**-LTRE` | |
| React + Vite style standard | |
| LAN mount pattern | |
| Dockerized | |
| README + CLAUDE.md documentation | |
