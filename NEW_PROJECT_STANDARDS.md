# Longtail Re New Project Standards

Use the following markdown in each new Longtail Re project.

---

# Longtail Re Project Standards

## 1. Secrets and Credentials

Full details are in **[SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md)**. Key rules:

- All application secrets must be stored in **1Password** (vault: **`DM Service Accounts`**).
- Every project must include:
  - `.env.tpl` — uses `{{ op://... }}` syntax for secrets, literal values for non-sensitive config
  - `.env.example` — blank or dummy values for documentation
  - `.gitignore` — must exclude `.env`
  - `scripts/render_env.sh` — one-command local setup
  - `.pre-commit-config.yaml` — blocks `.env` commits and detects leaked secrets
- Standard local/server render step:

```bash
./scripts/render_env.sh
# or: op inject -i .env.tpl -o .env --force
```

- Deployed applications must use systemd `ExecStartPre=/usr/bin/op inject` to render secrets at service start.
- Standard rule: do not commit live credentials, exported `.env` files, or convenience files containing plaintext tokens.
- Standard rule: all `.env.tpl` files must use the `{{ op://... }}` syntax (not bare `op://` references).

## 2. Database Standard

- **Snowflake is the standard application database/storage platform.**
- Database: `SANDBOX_ACTUARIAL`
- Rule: **each application must have its own schema in `SANDBOX_ACTUARIAL`**.
- Schema name should match the canonical application name in uppercase with underscores where appropriate.
- Examples from existing projects:
  - `LLOYDS_DATA_INGESTION`
  - `NDA_DATABASE`
  - `UNDERWRITING_FOLDER_SCANNER`
- New projects should not default to SQLite or local-only persistence except as an explicitly documented local development fallback.

## 3. Monday.com Standard

- **Monday.com is the single source of truth for the business.**
- This applies especially to:
  - CRM
  - PAS (Policy Administration System)
- If an application needs client, deal, cedant, opportunity, PAS, or workflow status data, it should source that from Monday.com unless there is a documented exception.
- Where appropriate, applications should store Monday item IDs and URLs alongside internal records so users can trace back to the system of record.
- Existing board IDs seen in current applications:
  - PAS board: `4527766176`
  - CRM cedant board: `4441241930`
- New projects should document which board(s) they depend on and what fields are consumed.

## 4. Web App Routing Standard

- Standard host pattern for internal web apps:

```text
http://svralia01.longtailre.com/<app-name>
```

- The last path segment must be the canonical application name.
- The application must support deployment behind a path prefix by using an app path prefix setting such as:

```text
APP_PATH_PREFIX=/<app-name>
```

- Backend and frontend must both be path-prefix aware.

## 5. GitHub Standard

- All Longtail Re application repositories should live under the **`xx-LTRE`** GitHub organization unless there is a documented reason otherwise.
- Repository path should match the canonical application name.
- The GitHub repository name, nginx route, Docker/environment path prefix, and user-facing app name should be aligned as much as possible.
- Avoid split naming such as:
  - local folder with underscores
  - route with hyphens
  - GitHub repo under a personal account

## 6. Graphics and Style Standard

- Standard visual reference:

```text
http://svralia01.longtailre.com/lloyds-data-ingestion
```

- New internal web apps should generally follow the Lloyd's Data Ingestion design language:
  - clean dashboard presentation
  - restrained palette
  - clear cards/panels
  - strong information hierarchy
  - path-aware branding assets
  - polished typography and spacing
- Applications may vary by function, but they should not regress to generic default styling if a richer internal standard already exists.

## 7. LAN Fileshare Mount Standard

- If an application needs access to a company LAN fileshare, the mount pattern should follow the most up-to-date approach used in `nda_database`.
- Use a stable host mount path under `/mnt`, for example:

```text
/mnt/ltre-legal
```

- Mount the share into the container as **read-only** unless there is a documented reason to allow writes.
- Only mount the share into the service that actually needs it. Do not expose a LAN share to every container by default.
- Keep application-owned writable storage separate from network-share mounts. Typical split:
  - local writable bind mounts for app data, uploads, caches, and outputs
  - read-only LAN share mount for source/reference files
- Document:
  - the host mount path
  - whether the mount is required for normal app operation or only for batch/crawler jobs
  - whether the share is read-only or read-write
  - what folder tree on the share the app expects
- Example pattern from `nda_database`:

```yaml
services:
  app:
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads

  crawler:
    volumes:
      - ./data:/app/data
      - /mnt/ltre-legal:/mnt/ltre-legal:ro
```

## 8. Standard Project Setup

Each new project should include:

- `README.md` with purpose, dependencies, local run steps, Docker run steps, deployment notes, and operational dependencies
- `.env.tpl` with `{{ op://... }}` syntax (see [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md))
- `.env.example` with blank or dummy values
- `.gitignore` excluding `.env`
- `scripts/render_env.sh`
- `.pre-commit-config.yaml`
- Dockerfile
- `docker-compose.yml`
- `systemd/<app-name>.service` with `ExecStartPre=op inject` (for deployed apps)
- health endpoint at `/api/health`
- explicit deployment path prefix
- documented external integrations

## 9. Standard Deployment Pattern

- Deploy internal web apps behind nginx on `svralia01`.
- All deployable applications must be Dockerized unless a documented exception is approved.
- Bind application containers to localhost only, for example:

```text
127.0.0.1:<host-port>:8000
```

- Put nginx in front of the container and publish only the route prefix.
- Use non-root container users where practical.
- Include a healthcheck in Docker.

## 10. Standard Documentation Requirements

Each project should document:

- purpose and business owner
- technical owner
- source data inputs
- external integrations
- Snowflake schema name
- Monday board IDs and fields used
- mount points or network shares required
- deployment URL
- recovery/restart steps

Each project should also maintain a dedicated documentation set, suitable for reuse by future teams, that includes:

- a **new-project standards guide** stating the Longtail Re engineering standards that the project follows
- an **IT application guide** covering:
  - what the application does
  - the major backend/frontend/components used
  - runtime dependencies and mounts
  - standards compliance
  - notable software, operational, and repository-hygiene issues
- enough detail that the documents can be pasted into future projects as a starting point
- explicit notes where the project is intentionally non-standard or is a legacy exception

The instructions used in this review should be treated as the minimum documentation bar for future projects:

- define 1Password usage and vault/item conventions
- define Snowflake schema ownership
- define Monday.com usage and source-of-truth expectations
- define deployment URL and path-prefix standard
- define GitHub ownership and naming
- define graphics/style reference
- define LAN fileshare mount requirements where relevant
- review compliance against those standards
- document function, components, and support issues for IT

## 11. Additional Standards That Should Be Documented

Based on the current codebases, the following standards should also be formalized:

- Canonical app naming convention:
  - recommend a single slug for route and GitHub repo, preferably hyphenated for URLs and repo names
  - document how local folder names should relate to that slug
- Secret template convention:
  - standardized on `{{ op://... }}` syntax with `op inject` — see [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md)
- Snowflake authentication convention:
  - standardize whether projects use PAT-based auth or password auth
- Frontend structure convention:
  - React + Vite is common for full web apps, but one codebase uses server-rendered FastAPI/Jinja; document when each pattern is acceptable
- Logging and monitoring convention:
  - define required logs, healthchecks, and runbooks
- Data retention convention:
  - document where uploads, generated outputs, caches, and extracted artifacts live
- Testing minimums:
  - define minimum smoke/integration tests before deployment
- CORS/auth stance for internal apps:
  - current apps are broadly open because they run on a protected server; this should still be documented explicitly instead of being implicit

## 12. Current Compliance Snapshot

### `lloyds_data_ingestion`

- 1Password: mostly compliant
- Snowflake: compliant
- Monday.com: not used; acceptable for this use case
- Web route: compliant at `/lloyds-data-ingestion`
- GitHub org: compliant
- Style reference: this is the reference implementation
- Notes:
  - repository name uses underscores while route uses hyphens
  - `.env.tpl` syntax differs from other projects

### `nda_database`

- 1Password: compliant
- Snowflake: partially compliant
- Monday.com: compliant and directly integrated
- Web route: compliant at `/nda-database`
- GitHub org: compliant
- Style reference: partially aligned with existing Longtail internal styling, but less polished than Lloyd's Data Ingestion
- Notes:
  - code defaults to SQLite in settings and `.env.example`, so Snowflake is not the effective default everywhere
  - repository has untracked deployment/support files, indicating operational documentation drift

### `underwriting_folder_scanner`

- 1Password: compliant
- Snowflake: compliant
- Monday.com: compliant
- Web route: route prefix exists as `/underwriting-folder-scanner`
- GitHub org: non-compliant; repo is under a personal account
- Style reference: not applicable in the same way; the web layer is a simple chat UI rather than a dashboard app
- Notes:
  - uses Snowflake password fields rather than the PAT pattern used elsewhere
  - deployment standard to `svralia01.longtailre.com/<app-name>` is not documented as clearly as other apps

### `uw_memo_writer`

- 1Password: partially compliant
- Snowflake: non-compliant
- Monday.com: compliant
- Web route: compliant at `/uw-memo-writer`
- GitHub org: partially compliant
- Style reference: older shared internal style, not aligned to the Lloyd's Data Ingestion standard
- Notes:
  - has both `xx-LTRE` and personal GitHub remotes
  - does not use Snowflake for primary storage
  - repository hygiene around local secret convenience files should remain strict

## 13. Recommended New-Project Template

For any new Longtail Re application:

1. Pick a canonical app slug, for example `my-new-app`.
2. Create the repo under `xx-LTRE/my-new-app`.
3. Reserve the route `http://svralia01.longtailre.com/my-new-app`.
4. Create schema `SANDBOX_ACTUARIAL.MY_NEW_APP`.
5. Create or assign 1Password items in `DM Service Accounts`.
6. Document all Monday.com board dependencies.
7. Include Docker, healthcheck, path-prefix support, and deployment notes from day one.

---

Reviewed against current repositories on 2026-03-24. Secrets management standard added 2026-03-30.
