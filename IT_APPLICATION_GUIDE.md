# Longtail Re Application Guide For IT

This guide summarizes the current codebases in `/home/matthew.evans@longtailre.com/Code`, what each application does, the major components used, the observed standards compliance, and notable software/security issues.

Assumptions for this guide:

- applications run on a protected internal server
- data is not sensitive and may be shared across the company
- therefore, external-grade hardening is not required

That said, repository hygiene, credential handling, operational stability, and consistency still matter.

## Portfolio Summary

| Application | Primary Function | Main Stack | Key Integrations | Standards Position |
|---|---|---|---|---|
| `lloyds_data_ingestion` | Lloyd's quarterly pack ingestion and exhibit review | FastAPI, React/Vite, Snowflake | Snowflake, Azure OpenAI | strongest match to target app standard |
| `nda_database` | NDA ingestion, extraction, search, and PAS linkage | FastAPI, React/Vite, Snowflake/SQLite | Snowflake, Monday.com, Azure OpenAI | mostly aligned, but default persistence still mixed |
| `underwriting_folder_scanner` | scan underwriting folders, convert docs, store artifacts, RAG search | Python CLI, FastAPI/Jinja, Snowflake | Snowflake, Monday.com, OpenAI/Azure OpenAI | functionally strong, naming/repo/deployment conventions less aligned |
| `uw_memo_writer` | generate underwriting memos from Excel and Word templates | FastAPI, React/Vite, Celery, Redis | Monday.com, Azure OpenAI | useful app, but furthest from current target standards |
| `projection_extract` | extract actuarial projection data from cedant .xlsm workbooks, write Hx upload template .xlsx files | Python CLI (argparse) | Azure OpenAI | compliant CLI tool; no web or database layer |
| `hx_testing` | E2E testing for Hx web app; batch upload orchestration via PAS/Monday.com | Playwright, pytest, Python CLI | Monday.com, Hx (longtailre.hxrenew.com) | compliant local testing tool; must run in WSL |
| `remount_kerberos` | keep Kerberos-authenticated CIFS mounts alive on Linux hosts | shell scripts, systemd | 1Password (service account), Kerberos, cifs-utils | infrastructure tooling — most standards not applicable; intentionally not containerized |

## Application URLs

- `lloyds_data_ingestion`: `http://svralia01.longtailre.com/lloyds-data-ingestion`
- `nda_database`: `http://svralia01.longtailre.com/nda-database`
- `underwriting_folder_scanner`: `http://svralia01.longtailre.com/underwriting-folder-scanner`
- `uw_memo_writer`: `http://svralia01.longtailre.com/uw-memo-writer`
- `projection_extract`: N/A (local CLI tool, not deployed as a web service)
- `hx_testing`: N/A (local E2E testing tool, must run in WSL)
- `remount_kerberos`: N/A (host-level infrastructure tooling, no web interface)

## Cross-Cutting Findings

### Good patterns seen repeatedly

- Dockerized deployment is common.
- Most apps support path-prefix hosting with `APP_PATH_PREFIX`.
- Most apps expose `/api/health`.
- Most repos ignore `.env`.
- Snowflake is already the persistence target for three of the four applications.
- Monday.com is already integrated where business-system linkage matters.

### Standards gaps that should be addressed going forward

- naming is inconsistent across local folders, routes, and GitHub repository names
- ~~1Password template syntax is inconsistent across repositories~~ **Resolved 2026-03-30**: all repos now use `{{ op://... }}` syntax — see [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md)
- Snowflake authentication approach is inconsistent across repositories
- visual design standards are not yet consistently applied
- not every repo has a clean, current deployment runbook

### Highest-priority repository issue found during the original review

- Plaintext local secret convenience files had appeared in repository history. Those references have been removed from the current documentation set, and credentials are being rotated separately.
- **2026-03-30**: All repositories now have `.pre-commit-config.yaml` hooks to block `.env` commits and detect secrets. All repositories have standardized `.env.tpl` files, `scripts/render_env.sh`, and systemd `op inject` integration (where applicable). See [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md).

## Application Reviews

## `lloyds_data_ingestion`

### Function

- Ingests Lloyd's reporting pack data into Snowflake.
- Serves a read-only web application for plan-versus-actual review by syndicate, reporting period, year of account, class, channel, reserves, major losses, and reinsurance.

### Main Components

Backend:

- `api/main.py`: FastAPI entrypoint, CORS setup, SPA/static serving.
- `api/routers/reporting.py`: reporting endpoints.
- `api/services/exhibits.py`: query layer for KPI, ratio, premium, reserve, loss, reinsurance, and narrative views.
- `api/services/reference_inventory.py`: source/reference file inventory.
- `api/db/connector.py`: Snowflake and SQLite connection logic.
- `scripts/rebuild_schema_and_load.py`: schema rebuild and load workflow.

Frontend:

- `frontend/src/App.tsx`: single-page dashboard client.
- `frontend/src/index.css`: strongest current design reference in the portfolio.

Infrastructure and dependencies:

- FastAPI
- React 18 + Vite + TypeScript
- Snowflake connector
- Docker multi-stage build
- Azure OpenAI dependency present for narrative support/extraction workflows

### Observed Compliance

- 1Password: yes
- Snowflake per-app schema: yes, `SANDBOX_ACTUARIAL.LLOYDS_DATA_INGESTION`
- Monday.com: not applicable to current function
- URL: `http://svralia01.longtailre.com/lloyds-data-ingestion`
- Standard route: yes, `/lloyds-data-ingestion`
- GitHub under `ME-LTRE`: yes
- Visual style reference: yes, this is the current reference implementation

### Software/Operational Notes

- Cleanest example of the target internal web-app pattern.
- Frontend is functionally rich but concentrated in a very large `App.tsx`, so future change cost will rise unless it is broken into components.
- README and deployment notes are relatively complete.

### Potential Issues

- Repository name uses underscores while public route uses hyphens; naming convention is not fully standardized.
- Uses permissive CORS. Acceptable for current protected-server deployment, but it should be an explicit internal-only policy decision.
- `.env.tpl` uses a different 1Password style from some other repos, which makes secret handling harder to standardize.

## `nda_database`

### Function

- Maintains an NDA repository with upload, extraction, edit, search, expiry tracking, and Monday/PAS linkage.
- Can crawl a mounted legal share and ingest documents into the database.

### Main Components

Backend:

- `api/main.py`: FastAPI entrypoint, static serving, health endpoint.
- `api/routers/upload.py`: upload endpoint for PDF and DOCX ingestion.
- `api/routers/documents.py`: list, view, update, delete, re-extract, download, markdown endpoints.
- `api/routers/search.py`: search, stats, cedants, expiring NDAs.
- `api/routers/extraction.py`: extraction-related endpoints.
- `api/services/conversion_service.py`: document conversion.
- `api/services/extraction_service.py`: AI extraction pipeline.
- `api/services/document_service.py`: orchestration layer.
- `api/services/pas_service.py`: PAS/Monday linkage.
- `api/db/repository.py`: persistence access.
- `crawler/`: legal-share crawler job.

Frontend:

- `frontend/src/pages/DocumentList.tsx`: main list/search view.
- `frontend/src/pages/DocumentView.tsx`: detail page.
- `frontend/src/pages/Upload.tsx`: upload page.
- `frontend/src/components/DocumentTable.tsx`
- `frontend/src/components/DocumentDetail.tsx`
- `frontend/src/components/FieldEditor.tsx`
- `frontend/src/components/SearchBar.tsx`
- `frontend/src/components/UploadForm.tsx`
- `frontend/src/components/Header.tsx`

Infrastructure and dependencies:

- FastAPI
- React 18 + React Router + Vite + TypeScript
- Snowflake connector
- SQLite fallback
- marker-pdf, markitdown, PyMuPDF, Pillow
- Azure OpenAI
- Monday.com API
- Docker multi-stage build

### Observed Compliance

- 1Password: yes
- Snowflake per-app schema: partially yes, `SANDBOX_ACTUARIAL.NDA_DATABASE`
- Monday.com: yes
- URL: `http://svralia01.longtailre.com/nda-database`
- Standard route: yes, `/nda-database`
- GitHub under `ME-LTRE`: yes
- Visual style: partially aligned, but still on the older shared style system

### Software/Operational Notes

- Clear application structure with separated pages and components.
- Most directly aligned with the business-system requirement that Monday.com act as source of truth.
- Dual-mode persistence exists: Snowflake and SQLite.

### Potential Issues

- Snowflake is not the default everywhere. `api/settings.py` and `.env.example` still default to SQLite, which conflicts with the desired Longtail standard.
- Repository currently has untracked operational files (`deploy.sh`, `docker-compose.nomount.yml`, `frontend/package-lock.json`), suggesting deployment artifacts are not fully normalized.
- Permissive CORS is used.
- No README was present at repository root during review, so onboarding and recovery knowledge currently lives in code and ad hoc scripts rather than a single runbook.

## `underwriting_folder_scanner`

### Function

- Scans cedant opportunity folders.
- Produces Stage 1 plans, Stage 2 document conversions, and Stage 3 vector embeddings in Snowflake.
- Provides a Stage 4 web UI for RAG-style querying over the embedded content.
- Syncs Monday CRM/PAS metadata and reconciles source files to Monday references.

### Main Components

CLI and core pipeline:

- `src/cli/autoscan.py`: CLI entrypoint.
- `src/core/STAGE_01_scan_plan.py`: folder discovery and planning.
- `src/core/STAGE_02_pipeline.py`: extraction/conversion orchestration.
- `src/core/scanner.py`: scanner engine.
- `src/core/converters.py`: document conversion layer.
- `src/core/snowflake_utils.py`: Snowflake schema/bootstrap/artifact store logic.
- `src/core/reporting.py`: run reporting.

AI and retrieval:

- `src/ai/STAGE_03_chunk_embed.py`: chunking, embeddings, extraction, Snowflake vector storage.
- `src/ai/openai_client.py`
- `src/ai/vector_search.py`
- `src/ai/run_logger.py`

Monday integration:

- `src/integrations/monday_client.py`
- normalization and matching scripts/tests under `scripts/` and `tests/`

Web:

- `src/web/app.py`: FastAPI/Jinja chat UI.
- `src/web/query_service.py`: vector search and answer synthesis.
- `src/web/templates/chat.html`: rendered frontend template.

Infrastructure and dependencies:

- Python CLI + FastAPI
- Jinja2 server-rendered UI
- Snowflake connector
- marker-pdf
- markitdown
- langchain text splitters
- OpenAI / Azure OpenAI
- Docker multi-stage build with separate app and scanner targets

### Observed Compliance

- 1Password: yes
- Snowflake per-app schema: yes, `SANDBOX_ACTUARIAL.UNDERWRITING_FOLDER_SCANNER`
- Monday.com: yes
- URL: `http://svralia01.longtailre.com/underwriting-folder-scanner`
- Standard route: path prefix exists as `/underwriting-folder-scanner`
- GitHub under `ME-LTRE`: yes (`ME-LTRE/underwriting-folder-scanner`)
- Visual style: not intended to match dashboard standard; this is a functional query UI

### Software/Operational Notes

- Most technically broad codebase in the set.
- Strong test presence compared with the other applications.
- Good use of staged processing and explicit Snowflake schema bootstrap.

### Potential Issues

- Repo ownership does not match the proposed `ME-LTRE` standard.
- Uses `SNOWFLAKE_PASSWORD` rather than the PAT convention used elsewhere, so Snowflake authentication is not standardized across the portfolio.
- README and `.env.tpl` show some deployment/default-path differences, which can create confusion during support.
- The app is not a React/Vite app; that is fine for its use case, but the allowed frontend patterns should be documented so this reads as intentional rather than inconsistent.

## `uw_memo_writer`

### Function

- Generates underwriting memos from Excel models, projections models, Word templates, and optional attachments.
- Pulls supporting relationship/current-business data from Monday.com.
- Can generate AI-assisted narrative content.
- Renders exhibits and composes final `.docx` memo outputs.

### Main Components

Backend:

- `api/main.py`: FastAPI entrypoint.
- `api/routers/upload.py`: upload-related APIs.
- `api/routers/jobs.py`: job creation, job status, file download, job history.
- `api/routers/config.py`: template and config endpoints.
- `api/services/memo_service.py`: main orchestration layer.
- `api/services/file_service.py`: upload handling.
- `api/services/job_store.py`: job persistence helpers.
- `api/tasks/celery_app.py` and `api/tasks/generate.py`: Celery worker integration.

Core document-generation modules:

- `generate_memo.py`
- `document_builder.py`
- `exhibit_renderer.py`
- `great_tables_renderer.py`
- `model_detector.py`
- YAML config files for memo variables and exhibit definitions

Frontend:

- `frontend/src/App.tsx`: main workflow shell.
- `frontend/src/components/FileUploadSection.tsx`
- `frontend/src/components/ConfigForm.tsx`
- `frontend/src/components/GenerateButton.tsx`
- `frontend/src/components/JobProgress.tsx`
- `frontend/src/components/JobHistory.tsx`
- `frontend/src/components/Header.tsx`

Infrastructure and dependencies:

- FastAPI
- React 18 + Vite + TypeScript
- Celery + Redis
- openpyxl
- docxtpl
- matplotlib, pandas, numpy, seaborn
- Great Tables
- Playwright/Chromium in container
- Azure OpenAI
- Monday.com API

### Observed Compliance

- 1Password: partial
- Snowflake per-app schema: no
- Monday.com: yes
- URL: `http://svralia01.longtailre.com/uw-memo-writer`
- Standard route: yes, `/uw-memo-writer`
- GitHub under `ME-LTRE`: partial; both org and personal remotes exist
- Visual style: older shared internal style, not aligned with the Lloyd's Data Ingestion standard

### Software/Operational Notes

- Strong business utility and a clear end-to-end workflow.
- Most operationally complex runtime because it includes app server, worker, Redis, template files, uploaded inputs, and generated outputs.
- Uses in-memory job storage in the jobs router, which is adequate for light internal use but fragile across process restarts.

### Potential Issues

- Does not use Snowflake as the application data platform, which is the biggest standards gap in the portfolio.
- Repository hygiene around local secret convenience files should remain strict.
- Has both `ME-LTRE` and personal GitHub remotes, which can cause confusion about the canonical upstream.
- Uses permissive CORS.
- Exposes `/uploads` and `/output` as static mounts; acceptable internally, but worth documenting because it broadens what the running app can serve.
- In-memory job state means active jobs and history can be lost on restart.

## `projection_extract`

### Function

- Extracts actuarial projection data (triangles, selections, parameters) from cedant Projections Model `.xlsm` workbooks.
- Writes Hx-compatible upload template `.xlsx` files using direct XML manipulation to preserve template structure (calcChain, shared strings, drawings).
- Uses Azure OpenAI to infer LOB, origin basis, proportionality, region, and country from class descriptions.
- Optionally recalculates the output workbook via VBScript/COM on WSL.
- Produces per-run diagnostics markdown reports covering LOB mappings, triangle normalization, and data-element inventories.

### Main Components

CLI and core pipeline:

- `projection_extract/cli.py`: CLI entrypoint (argparse).
- `projection_extract/config.py`: configuration via environment variables and CLI overrides (`AppConfig`, `OpenAIConfig`).
- `projection_extract/processor.py`: main processing workflow — load workbook, extract, infer, normalize, write.
- `projection_extract/extract.py`: worksheet extraction helpers (parameters from `A0 Parameters`, LOB info from `C1 Combining`, triangles from `A1 Projections`, selections from `B1 Selections`).
- `projection_extract/transform.py`: triangle year-range detection and normalization.
- `projection_extract/output.py`: column-map definitions and openpyxl-based sheet population (Parameters, Triangles, Projections).
- `projection_extract/xlsx_writer.py`: direct XML/ZIP writer that modifies template xlsx without openpyxl round-tripping.
- `projection_extract/excel_io.py`: VBScript-based Excel recalculation via COM, workbook comparison utility.
- `projection_extract/diagnostics.py`: markdown diagnostics report generation.

AI inference:

- `projection_extract/ai.py`: `OpenAIInferencer` class with caching — infers LOB, origin basis, proportionality, region, and country via Azure OpenAI or keyword matching fallback.

Tests:

- `tests/test_pipeline.py`

Scripts:

- `scripts/render_env.sh`: 1Password `.env` rendering helper.

Batch orchestration (external):

- Batch runs across multiple cedants are orchestrated from the sibling `hx_testing` repository (`scripts/extract_projections.py`), which also handles Monday.com PAS board integration for cedant matching.

Infrastructure and dependencies:

- Python CLI (argparse, no web framework)
- openpyxl
- openai (Azure OpenAI)
- python-dotenv
- No Docker container, no database, no frontend

### Observed Compliance

- 1Password: yes (`{{ op://DM Service Accounts/... }}` syntax in `.env.tpl`, `render_env.sh`, pre-commit hooks)
- Snowflake per-app schema: not applicable (no database; reads `.xlsm`, writes `.xlsx`)
- Monday.com: indirect, via `hx_testing` batch orchestration (PAS board for cedant matching)
- URL: not applicable (local CLI tool, not deployed as a web service)
- Standard route: not applicable
- GitHub under `ME-LTRE`: yes (`ME-LTRE/projection-extract`)
- Visual style: not applicable (no UI)
- Dockerized deployment: not applicable (local CLI tool)
- LAN fileshare mount pattern: yes, reads source `.xlsm` files from `/mnt/f/` network drive

### Software/Operational Notes

- Clean separation between extraction, transformation, AI inference, and output writing.
- The `xlsx_writer.py` module operates directly on xlsx ZIP archives (XML-level manipulation) to avoid openpyxl round-trip corruption of calcChain, shared strings, and formula cached values. This is the most distinctive technical pattern in the tool.
- Supports two template column layouts (`v4` and `v6`) via configurable column maps.
- AI inference includes a keyword-matching fast path with Azure OpenAI fallback, plus per-session caching to minimize API calls.
- Shares its Azure OpenAI API key with `uw_memo_writer` (stored in 1Password vault "DM Service Accounts").
- Diagnostics output provides an audit trail for every LOB mapping, inference call, and normalization decision.

### Potential Issues

- No Docker container or deployment automation exists, which is acceptable for a local CLI tool but means reproducibility depends on the developer's local Python environment.
- VBScript/COM recalculation step depends on Excel being installed on the Windows side of WSL. This will silently skip if Excel is not available, but should be documented as a requirement for complete output validation.
- Batch orchestration logic lives in the separate `hx_testing` repository rather than being self-contained, so operational knowledge is split across two repos.
- No README was present at repository root during review, so onboarding knowledge currently lives in `INSTRUCTIONS.md` and `AGENTS.md` rather than a standard `README.md`.

## `hx_testing`

### Function

- End-to-end testing suite for the Hx web application at `https://longtailre.hxrenew.com`.
- Automates the full 16-step policy workflow: create policy, upload data, load triangles, select classes, export results.
- Includes a batch orchestration pipeline: fetch PAS entries from Monday.com, match to cedant projection models on the LAN share, extract upload templates (via `projection_extract`), and upload to Hx in bulk.
- Must run in WSL to allow Playwright's Chromium browser to execute in batch/headless mode.

### Main Components

Testing framework:

- `conftest.py`: Pytest fixtures, persistent Chromium browser context with Azure AD login support, screenshot-on-failure hook.
- `pages/policy_list_page.py`: Page object for steps 1-7 (navigate, create policy, open option).
- `pages/policy_detail_page.py`: Page object for steps 8-16 (upload, triangles, export). Includes async task polling, retry logic, and server error capture from MUI popovers.
- `utils/timing.py`: Timer context manager for performance logging.
- `utils/downloads.py`: Download save helper.
- `tests/test_e2e_workflow.py`: Main 16-step E2E workflow test.
- `tests/test_batch_v6_upload.py`: Parametrized batch upload test.

Batch orchestration:

- `scripts/fetch_pas.py`: Step 1 — fetch PAS entries from Monday.com by underwriting year.
- `scripts/match_projections.py`: Step 2 — fuzzy-match PAS entries to cedant folders and projection model files on `/mnt/f/`.
- `scripts/extract_projections.py`: Step 3 — batch-run `projection_extract` for all matched entries.
- `scripts/keepalive.py`: Session keepalive daemon — periodically refreshes the Hx session to prevent Azure AD timeout.
- `scripts/discover_board_columns.py`: Monday.com board column discovery utility.

Infrastructure and dependencies:

- Playwright (Chromium)
- pytest with pytest-playwright
- python-dotenv
- PyYAML (for PAS data files)
- Persistent Chromium profile (`.browser_profile/`) for Azure AD + MFA session reuse

### Observed Compliance

- 1Password: yes — `.env.tpl` with `{{ op://... }}` syntax, `render_env.sh`, `.pre-commit-config.yaml`
- Snowflake: not applicable (testing tool, not a data application)
- Monday.com: yes — PAS board `4527766176` used for batch orchestration
- Web route: not applicable (not a deployed web app)
- GitHub org: yes — `ME-LTRE/hx-testing`
- Graphics/style: not applicable (no UI)
- Dockerized deployment: not applicable (local testing tool, must run in WSL)
- LAN fileshare mount pattern: yes — reads projection model `.xlsm` files from `/mnt/f/` (read-only)
- Documentation: yes — `README.md` with purpose, setup, dependencies, Monday board fields, mount requirements

### Software/Operational Notes

- Authentication relies on a persistent Chromium profile with Azure AD session cookies. Session expires require manual MFA re-authentication via a visible browser window.
- The batch upload test creates real test policies on the Hx platform. Test policies are not cleaned up automatically.
- Async task detection (Load Triangles, Export Policy) uses polling with configurable timeouts and retry logic.
- Server error capture reads the MUI popover UI, including the "Show Developer Output" flow for full tracebacks. The popover must be dismissed with Escape to prevent backdrop blocking.
- The `match_projections.py` script depends on the `reserving_pattern_scanner` sibling repo for `FolderScanner` and `FuzzyMatcher` classes.

### Potential Issues

- Local folder name uses underscores (`hx_testing`) while GitHub repo uses hyphens (`hx-testing`); naming convention is not fully standardized.
- No Docker container exists, which is acceptable for a local testing tool but means it can only run on a developer's WSL environment.
- Azure AD session management is manual — session expiry during long batch runs can block the pipeline until the user re-authenticates.
- Batch orchestration knowledge is split across this repo and `projection_extract`, so operational understanding requires familiarity with both.

## `remount_kerberos`

### Function

- Keeps Kerberos-authenticated CIFS mounts alive on Linux hosts connected to Azure Files shares.
- Runs as a systemd timer (every 2 hours and on boot), probing mount health and recovering automatically if the Kerberos ticket has expired or the mount has gone stale.
- Does not use Snowflake, Monday.com, or a web interface — it is host-level infrastructure tooling, not an application.

### Why not a container?

This tooling is deliberately **not containerized**. Kerberos mount management is a host-level privileged operation: it calls `mount`/`umount`, writes to kernel keyrings, escalates via `sudo`, and must interact directly with the host network stack and CIFS upcall mechanism. Containerizing it would require `--privileged` or `SYS_ADMIN` capability (eliminating isolation benefits) plus bind-mounting `/tmp`, `/etc/krb5.conf`, and `/run`. The result would be more complex, harder to debug, and no more isolated. Running directly on the host as a systemd timer is lightweight (a few shell scripts firing every 2 hours), more stable (no container runtime in the critical path of mount recovery), and has full access to host facilities. Infrastructure scripts that must touch host kernel state belong on the host.

### Main Components

```
remount_kerberos/
├── bin/
│   ├── ensure-mount.sh        Main entrypoint: probe → renew → refresh
│   ├── probe-mount.sh         Health check: actual directory listing, not just mountpoint presence
│   ├── refresh-mount.sh       Unmount and remount CIFS share (runs as root via sudo)
│   ├── renew-ticket.sh        Ticket renewal: kinit -R first, then 1Password fallback
│   └── renew-user-ticket.sh   User-facing ticket renewal via 1Password (interactive use)
├── systemd/
│   ├── kerberos-mount-keepalive.service
│   └── kerberos-mount-keepalive.timer   (OnBootSec=2min, OnUnitActiveSec=2h)
├── install.sh                 Install systemd units
├── install-sudoers.sh         Configure passwordless sudo for mount/umount
├── fix-mount-now.sh           Immediate recovery: kinit + mount + restart timer
├── patch-system-script.sh     Patch /usr/local/sbin/refresh_share_mount.sh for MOUNT_CRUID
└── create-user-keytab.sh      One-time keytab creation for kinit -k
```

### Recovery Flow

```
systemd timer fires (every 2h, or 2min after boot)
        ↓
ensure-mount.sh f-drive
        ↓
probe-mount.sh ──── healthy ────→ exit 0
        ↓ unhealthy
Service account renewal (preferred, fully unattended):
  ├─ renew_kerberos_service_account.sh (from underwriting_folder_scanner)
  ├─ sudo refresh_share_mount.sh with MOUNT_CRUID=170605696 (sa_alia UID)
  └─ re-probe → exit 0 on success
        ↓ still unhealthy
  exit 1
```

The service account path decouples mount health from user sessions — the mount stays alive even when no user is logged in.

### Mount Targets

| Target | Mountpoint | Mode | Probe path |
|--------|-----------|------|------------|
| `f-drive` | `/mnt/ltre-f-drive` | read-only | `/mnt/ltre-f-drive/Underwriting/Cedants` |
| `legal` | `/mnt/ltre-legal` | read-write | `/mnt/ltre-legal/Legal` |

Both connect to `//longtailrestorage01.file.core.windows.net/shared` over CIFS/SMB 3.1.1 with `sec=krb5`.

### Runtime Dependencies

- `krb5-user` (`kinit`, `klist`)
- `cifs-utils` (`mount.cifs`)
- `util-linux` (`mountpoint`, `findmnt`)
- `sudo` (for mount/umount privilege escalation)
- `op` (1Password CLI — optional, for unattended credential renewal)
- `underwriting_folder_scanner` sibling repo (provides `scripts/infra/renew_kerberos_service_account.sh`)

### Observed Compliance

- 1Password: yes — service account credentials fetched from vault `DM Service Accounts`, item `Service Account - SVRALIA01`
- Snowflake: not applicable (no data storage)
- Monday.com: not applicable
- Web URL / route: not applicable (no web interface)
- GitHub under `ME-LTRE`: no — no remote configured; repository lives only on the local host
- Dockerized: intentionally not (see above)
- LAN fileshare mount: this repo *is* the mount management layer

### Software/Operational Notes

- Runs as user `matthew.evans@longtailre.com` under systemd; sudoers entry grants passwordless mount/umount.
- Logs are in the system journal: `journalctl -u kerberos-mount-keepalive`.
- The `fix-mount-now.sh` script is the fastest manual recovery path.
- Depends on `patch-system-script.sh` having been run once on the host to enable `MOUNT_CRUID` passthrough in the system mount script.
- Shares a dependency on `underwriting_folder_scanner` for service account ticket renewal — if that repo moves, the path in `ensure-mount.sh` must be updated.

### Potential Issues

- No GitHub remote configured. The code exists only on the local host; a hardware failure would lose it. Should be pushed to `ME-LTRE/remount-kerberos`.
- Hard-coded paths to sibling repo (`../underwriting_folder_scanner/scripts/infra/renew_kerberos_service_account.sh`) create a coupling that is not expressed as a dependency anywhere.
- Service unit hard-codes the full path to `ensure-mount.sh` under the current user's home directory. Moving the repo requires updating the unit file.
- No alerting if mount recovery fails — the service exits 1 silently into the journal. Consider an `OnFailure=` unit or monitoring hook.

## Recommended IT Actions

1. ~~Standardize local secret-handling workflow so convenience files do not reappear in source-controlled guidance.~~ **Done 2026-03-30** — pre-commit hooks added to all repos.
2. ~~Standardize one 1Password templating pattern across all repos.~~ **Done 2026-03-30** — all repos use `{{ op://... }}` syntax.
3. Standardize Snowflake authentication method across all repos.
4. Move `underwriting_folder_scanner` and `projection_extract` to `ME-LTRE`.
5. Decide whether `uw_memo_writer` should remain an exception to the Snowflake standard or be refactored toward it.
6. Make `nda_database` Snowflake-first by default if that is now the intended operating model.
7. Publish one canonical naming rule for repo name, route name, schema name, and app slug.
8. Require every repo to maintain a current README/runbook.

## Suggested Canonical Metadata For Each App

IT should maintain the following fields for each application:

- application name
- GitHub repo
- owner
- backup owner
- deployment URL
- nginx path prefix
- container port
- Snowflake schema
- Monday board IDs used
- mounted shares required
- restart command
- healthcheck URL
- recovery notes

## Standards Compliance Matrix

| Standard | `lloyds_data_ingestion` | `nda_database` | `underwriting_folder_scanner` | `uw_memo_writer` | `projection_extract` | `hx_testing` | `remount_kerberos` |
|---|---|---|---|---|---|---|---|
| 1Password for secrets | Met | Met | Met | Met | Met | Met | Met |
| Snowflake as primary storage | Met | Partially met | Met | Not met | Not applicable | Not applicable | Not applicable |
| Own Snowflake schema in `SANDBOX_ACTUARIAL` | Met | Met | Met | Not met | Not applicable | Not applicable | Not applicable |
| Monday.com used as source of truth where applicable | Met | Met | Met | Met | Partially met | Met | Not applicable |
| Standard web URL on `svralia01.longtailre.com/<app-name>` | Met | Met | Partially met | Met | Not applicable | Not applicable | Not applicable |
| GitHub under `ME-LTRE` | Met | Met | Not met | Partially met | Not met | Met | Not met |
| Graphics/style aligned to Lloyd's Data Ingestion standard | Met | Partially met | Not applicable | Not met | Not applicable | Not applicable | Not applicable |
| Dockerized deployment standard | Met | Met | Met | Met | Not applicable | Not applicable | Not applicable (intentional — see review) |
| LAN fileshare mount pattern documented where relevant | Not applicable | Met | Partially met | Not applicable | Met | Met | Met (this repo manages the mounts) |
| Documentation standard | Met | Not met | Partially met | Partially met | Partially met | Met | Met |
| WSL requirement documented | Not applicable | Not applicable | Not applicable | Not applicable | Not applicable | Met | Not applicable |

Status interpretation:

- `Met`: matches the target standard as reviewed.
- `Partially met`: some alignment exists, but there is a meaningful gap or inconsistency.
- `Not met`: does not currently satisfy the standard.
- `Not applicable`: the standard does not materially apply to that application.

Reviewed against current repositories on 2026-03-24. Secrets management standardization completed 2026-03-30. hx_testing added 2026-03-31.
