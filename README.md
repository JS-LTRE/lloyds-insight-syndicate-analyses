# Lloyd's Insight and Syndicate Analysis

Interactive Streamlit dashboard for analysing Lloyd's of London syndicate historical
performance data (2015–2025). Covers 162 syndicates across 11 years with P&L, balance
sheet, segmental line-of-business, and market benchmarking views.

---

## Standards compliance

| Standard | Status | Notes |
|---|---|---|
| **1Password** | N/A — no secrets | App requires no credentials; all data is pre-generated CSV files |
| **Snowflake** | N/A — no database | CSV-only data model; see [Non-standard exceptions](#non-standard-exceptions) |
| **Monday.com** | N/A — not applicable | Pure analytics tool with no CRM/PAS dependency |
| **Web route** | Partial — double-proxy | Accessible at standard path `http://svralia01.longtailre.com/lloyds-insight-syndicate-analysis` (port 80) via host nginx, but also directly on port **8502**. Host nginx proxies to the LID nginx container (8502) which then proxies to Streamlit — a non-standard double-proxy pattern |
| **GitHub org** | Non-compliant | Repo is under `JS-LTRE` (personal account), not `ME-LTRE` |
| **Style** | Partial | Uses Streamlit; does not follow the Lloyd's Data Ingestion React/Vite design language |
| **LAN fileshare** | Compliant (data refresh only) | `/mnt/ltre-f-drive` mounted read-only on host; not mounted into Docker containers |

---

## Purpose and ownership

**Purpose**: Provides Longtail Re underwriters and analysts with a self-service view of
Lloyd's syndicate and market performance — combined ratios, profitability, loss drivers,
LOB market share, and asset returns — without requiring access to raw ICMR data files.

**Business owner**: Underwriting / Cedants team

**Technical owner**: Jianhua Siew (`JS-LTRE`)

**Deployment URL**: `http://svralia01.longtailre.com:8502/lloyds-insight-syndicate-analysis`

**GitHub repository**: `JS-LTRE/lloyds-insight-syndicate-analyses`

**Local path on server**: `/srv/docker/lid`

---

## Application overview

### What it does

The app has two main views selectable from the sidebar:

**Market View**
- Major Industry Loss Events (1988–2025) — sourced from reinsurancene.ws
- Lloyd's Loss Drivers (2015–2025) — sourced from Lloyd's Annual Reports
- Market-wide **net** combined ratio, GWP, pre-tax margin, net loss/expense ratio trends
- **Line of Business Performance** — GWP composition, **gross** combined ratio, **gross** loss ratio, and net
  underwriting margin per LOB (all gross/pre-reinsurance), with a latest-year summary table
- Syndicate profitability vs volatility scatter plot
- Syndicate pre-tax margin distribution boxplot by year
- Market financial investments and asset return trend

**Syndicate View**
- Filtered by managing agent or syndicate number
- P&L trends, **net** combined ratio, balance sheet, LOB segmental breakdown (gross ratios)
- Percentile ranking vs market peers, asset return
- **Raw Data tab** includes a "Calculations used" reference covering the formula and basis
  (net vs gross) for every displayed column

### Tech stack

| Component | Technology |
|---|---|
| Frontend / backend | [Streamlit](https://streamlit.io) 1.55.0 |
| Data manipulation | pandas 2.3.3 |
| Charts | Plotly 6.6.0 |
| Excel ingestion | openpyxl 3.1.5 |
| Reverse proxy | nginx 1.27-alpine |
| Container runtime | Docker / Docker Compose |

### Runtime architecture

```
Browser
  └─► nginx (host port 8502) — container: lloyds-insight-syndicate-analysis-nginx
        └─► Streamlit app (internal port 8501) — container: lloyds-insight-syndicate-analysis-app
                └─► reads CSV files baked into the image at build time
```

All data is bundled into the Docker image at build time via `COPY . .` — there are no
runtime database connections or external API calls during normal operation.

---

## Source data inputs

### ICMR Excel file (primary source)

- **Location on LAN share**: `F:\Underwriting\Cedants\P&C\Lloyd's\<YoA> YoA\ICMR\ICMR Materials\`
- **Host mount path**: `/mnt/ltre-f-drive` (read-only CIFS mount)
- **Mount required for**: data refresh only — not needed for normal app operation
- **Latest file**: `Longtail_ICMRData_2015-2025_2026-04-15.xlsx`
- **Sheets used**:

| Sheet | Output CSV(s) |
|---|---|
| `Whole Account GBPk` | `01_whole_account_gbpk.csv` |
| `Whole Account original currency` | `02_whole_account_orig_ccy.csv` |
| `Segmental GBPk` | `03_segmental_gbpk.csv` |
| `Segmental original currency` | `04_segmental_orig_ccy.csv` |
| `Exchange rates` | `05_exchange_rates.csv` |
| `LOB Mapping` | `06_lob_mapping.csv` |

CSVs 07–12 are derived from 01–06 by `process_data.py`.

### Manually maintained data files

| File | Source | Frequency |
|---|---|---|
| `13_major_loss_events.csv` | [reinsurancene.ws](https://www.reinsurancene.ws/insurance-industry-losses-events-data/) | Annually |
| `14_lloyds_loss_drivers.csv` | Lloyd's Annual Reports | Annually |
| `15_Synd_Asset_Return.csv` | Syndicate annual accounts | Annually |

---

## External integrations

None during normal operation. The app is entirely self-contained once deployed.

Data refresh requires:
- Read access to the LAN fileshare (`/mnt/ltre-f-drive`)
- Manual download from reinsurancene.ws and Lloyd's annual report pages

---

## Running locally (Docker)

```bash
# Clone
git clone git@github.com:JS-LTRE/lloyds-insight-syndicate-analyses.git
cd lloyds-insight-syndicate-analyses

# Build and start
docker compose up --build -d

# Verify
docker exec lloyds-insight-syndicate-analysis-app python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8501/lloyds-insight-syndicate-analysis/_stcore/health').read())"
# Expected: b'ok'
```

App is available at: `http://localhost:8502/lloyds-insight-syndicate-analysis`

---

## Running locally (without Docker)

```bash
pip install streamlit==1.55.0 pandas==2.3.3 plotly==6.6.0 openpyxl==3.1.5

streamlit run syndicate_explorer.py \
  --server.baseUrlPath=/lloyds-insight-syndicate-analysis
```

---

## Deployment (server)

The app is deployed on `svralia01` under `/srv/docker/lid`.

```bash
# SSH to server, then:
cd /srv/docker/lid
git pull
docker compose up --build -d
```

Verify with the health check above. nginx on port 8502 is already configured and does
not need to be restarted when the Streamlit container is rebuilt.

---

## Annual data refresh

Run once per year when new ICMR data is available (typically Q2):

### 1 — Copy the new Excel file from the LAN share

```bash
cp "/mnt/ltre-f-drive/Underwriting/Cedants/P&C/Lloyd's/<YoA> YoA/ICMR/ICMR Materials/Longtail_ICMRData_2015-<YY>_<date>.xlsx" \
   /srv/docker/lid/
```

### 2 — Update the Excel path in process_data.py

Edit the `EXCEL_FILE` constant at the top of `process_data.py` to point to the new file.

### 3 — Regenerate CSV files 01–12

```bash
python3 /srv/docker/lid/process_data.py
```

### 4 — Manually update files 13, 14, 15

- **File 13** (`13_major_loss_events.csv`): append new events from reinsurancene.ws
- **File 14** (`14_lloyds_loss_drivers.csv`): add up to 5 rows from the Lloyd's Annual Report
- **File 15** (`15_Synd_Asset_Return.csv`): add rows from syndicate annual accounts, then
  re-run the conversion script to regenerate `15_Synd_Asset_Return_converted.csv`

### 5 — Update FX reference file

Append new year rows to `16_fx_rate_used.csv` (EUR, GBP, USD average rates).

### 6 — Update app labels

In `syndicate_explorer.py`, search for `2015–` and update the two expander labels
(`Major Industry Loss Events` and `Lloyd's Loss Drivers`) to the new year range.

### 7 — Rebuild and redeploy

```bash
cd /srv/docker/lid && docker compose up --build -d
```

---

## Recovery and restart

```bash
# Restart containers without rebuilding
docker compose restart

# Full rebuild and restart
cd /srv/docker/lid && docker compose up --build -d

# View live logs
docker logs -f lloyds-insight-syndicate-analysis-app

# Stop everything
docker compose down

# Remove containers and image entirely (data is safe — it lives in the repo)
docker compose down --rmi all
```

---

## Operational dependencies

| Dependency | Required for | Notes |
|---|---|---|
| Docker + Docker Compose | App runtime | Must be installed on `svralia01` |
| nginx (containerised) | Reverse proxy | Runs as `lloyds-insight-syndicate-analysis-nginx` |
| `/mnt/ltre-f-drive` LAN share | Data refresh only | CIFS mount; not needed for day-to-day app operation |
| Python 3.11+ with pandas, openpyxl | Data refresh only | For running `process_data.py` outside Docker |

---

## Non-standard exceptions

The following intentional deviations from Longtail Re project standards apply to this
project:

| Standard | Exception | Reason |
|---|---|---|
| **Snowflake** | Not used | Data is static year-end snapshots from Lloyd's reports. A database would add operational complexity with no benefit; pre-generated CSVs bundled into the Docker image are sufficient. |
| **1Password** | Not used | No application secrets are required — no database, no API keys, no external services. |
| **Monday.com** | Not used | Pure analytics tool with no CRM/PAS/workflow dependency. |
| **GitHub org** | `JS-LTRE` instead of `ME-LTRE` | Created under personal account; should be migrated to `ME-LTRE` in a future tidying pass. |
| **Port** | 8502 (non-standard) | Avoids collision with other apps on `svralia01`; not served through the standard nginx 80/443 layer. |
| **Framework** | Streamlit instead of React+Vite | Appropriate for a data analysis tool built by a single developer; the Lloyd's Data Ingestion design standard does not apply here. |

---

## Known issues

| Issue | Impact | Workaround |
|---|---|---|
| Dockerfile HEALTHCHECK uses wrong base URL path (`/_stcore/health` without prefix) | Container reports `unhealthy` in `docker ps` | Verify health manually using the Python `urllib.request` command shown above; ignore Docker's reported status |
| `COPY . .` copies all files into the image including source Excel files and scripts | Larger image size (~50–100 MB overhead) | No functional impact; add a `.dockerignore` in a future pass to exclude `*.xlsx`, `process_data.py`, shell scripts |
| Double-proxy routing: host nginx → LID nginx container (8502) → Streamlit (8501) | More moving parts than necessary; non-standard vs other apps | Functional; could be simplified by removing the LID nginx container and binding Streamlit to a localhost port, as other apps do |
| Local folder name `lid` does not match canonical app name | Minor naming inconsistency | No functional impact |
| GitHub repo under `JS-LTRE` (personal account) | Non-compliant with ME-LTRE standard | Transfer repo to `ME-LTRE` organisation when convenient |
| 2025 Lloyd's Annual Report does not publish granular per-event GBP loss figures | `14_lloyds_loss_drivers.csv` rows for 2025 have blank `lloyds_loss_gbp_m` for non-wildfire events | Update when Lloyd's publishes supplementary data; California Wildfires entry uses $2.3bn Lloyd's market estimate converted at 1.32 USD/GBP |
