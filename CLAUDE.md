# Lloyd's Insight and Syndicate Analysis — Docker Deployment

## Project Overview

A Streamlit web application for interactive analysis of Lloyd's of London syndicate
historical performance data (2015–2025). Covers 162 syndicates across 11 years with
P&L, balance sheet, segmental line-of-business, and market benchmarking views.

The app runs entirely from pre-generated CSV files — no database required.

---

## Instructions for Claude Code

When you read this file, execute the following steps in order. Do not skip steps.
All commands should be run from `/srv/docker/lid`.

### Step 1 — Confirm required files are present

The following files must exist before proceeding:

**Application**
- `syndicate_explorer.py` — main Streamlit app
- `nginx/nginx.conf` — nginx reverse proxy config

**Data processing**
- `process_data.py` — regenerates CSV files 01–12 from the source Excel file

**Source Excel file**
- `Longtail_ICMRData_2015-2025_2026-04-15.xlsx` — latest ICMR data (update filename each year)

**Data files (CSV)**
- `07_whole_account_kpis.csv`
- `08_segmental_kpis.csv`
- `09_market_annual_summary.csv`
- `11_lob_market_share_by_year.csv`
- `12_syndicate_percentile_rankings.csv`
- `13_major_loss_events.csv`
- `14_lloyds_loss_drivers.csv`
- `15_Synd_Asset_Return_converted.csv`

**Reference files (not loaded by app, for audit purposes)**
- `16_fx_rate_used.csv` — FX rates used to convert USD/EUR → GBP

**Docker config**
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`

---

### Step 2 — Rebuild and start all containers

Run:

```bash
cd /srv/docker/lid && docker compose up --build -d
```

This builds the Streamlit app image and starts two containers:

| Container | Role |
|---|---|
| `lloyds-insight-syndicate-analysis-app` | Streamlit app on internal port 8501 |
| `lloyds-insight-syndicate-analysis-nginx` | nginx reverse proxy, exposed on port **8502** |

The app is served at the path `/lloyds-insight-syndicate-analysis` via nginx.

---

### Step 3 — Verify the deployment

```bash
# Check both containers are running
docker ps --filter "name=lloyds-insight"

# Check the app is responding (from inside the app container, using Python)
docker exec lloyds-insight-syndicate-analysis-app python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8501/lloyds-insight-syndicate-analysis/_stcore/health').read())"
```

Expected output from health check: `b'ok'`

If the health check fails, check logs:
```bash
docker logs lloyds-insight-syndicate-analysis-app
```

---

### Step 4 — Report success

Once healthy, confirm to the user:
- App container: `lloyds-insight-syndicate-analysis-app`
- Nginx container: `lloyds-insight-syndicate-analysis-nginx`
- URL: `http://<server-ip>:8502/lloyds-insight-syndicate-analysis`
- Status: running / healthy

---

## Useful management commands

```bash
# Stop all containers
docker compose down

# Rebuild and restart after any code or CSV changes
cd /srv/docker/lid && docker compose up --build -d

# View live app logs
docker logs -f lloyds-insight-syndicate-analysis-app

# Remove containers and image entirely
docker compose down --rmi all
```

---

## Architecture

```
Browser → nginx (port 8502) → Streamlit app (internal port 8501)
```

- nginx handles routing under `/lloyds-insight-syndicate-analysis`
- Streamlit is configured with `--server.baseUrlPath=/lloyds-insight-syndicate-analysis`
- The Dockerfile HEALTHCHECK uses the wrong path (no base URL) — ignore unhealthy status,
  verify manually using the Python method in Step 3 above

---

## Data dictionary

### Raw / intermediate files (not loaded by app)

| CSV file | Contents |
|---|---|
| `01_whole_account_gbpk.csv` | Whole account P&L and balance sheet, GBP thousands |
| `02_whole_account_orig_ccy.csv` | Whole account in original reporting currency |
| `03_segmental_gbpk.csv` | Segmental (LOB) underwriting data, GBP thousands |
| `04_segmental_orig_ccy.csv` | Segmental data in original reporting currency |
| `05_exchange_rates.csv` | Average and year-end FX rates (USD, EUR → GBP) |
| `06_lob_mapping.csv` | Syndicate COB → Harmonised LOB → Aggregate LOB mapping |

### App data files (loaded by `syndicate_explorer.py`)

| CSV file | Contents |
|---|---|
| `07_whole_account_kpis.csv` | P&L + balance sheet + derived ratios per syndicate/year |
| `08_segmental_kpis.csv` | Underwriting data by line of business + derived ratios |
| `09_market_annual_summary.csv` | Market-wide annual aggregates |
| `11_lob_market_share_by_year.csv` | LOB market share % by year |
| `12_syndicate_percentile_rankings.csv` | Annual net profit percentile bucket per syndicate |
| `13_major_loss_events.csv` | Major global insured loss events (1988–2025) sourced from reinsurancene.ws |
| `14_lloyds_loss_drivers.csv` | Top Lloyd's-specific loss drivers per year (2015–2025), sourced from Lloyd's Annual Reports |
| `15_Synd_Asset_Return_converted.csv` | Syndicate financial investment cost and asset return (2024–2025), converted to GBP thousands |
| `16_fx_rate_used.csv` | FX rates (average annual) used to convert USD/EUR → GBP, confirmed against files 01 and 02 |

All monetary values are in **GBP thousands** unless otherwise noted.
Years covered: **2015–2025** (files 07–14); **2024–2025** (file 15).

---

## Key formulas used in the app

| Metric | Formula |
|---|---|
| Pre-tax Margin | Result Before Tax ÷ Net Earned Premium × 100 |
| Combined Ratio | Loss Ratio + Expense Ratio |
| Loss Ratio | \|Net Claims Incurred\| ÷ Net Earned Premium × 100 |
| Expense Ratio | \|Operating Expenses\| ÷ Net Earned Premium × 100 |
| Return on Assets | Result Before Tax ÷ Total Assets × 100 |
| Total Assets / NEP | Total Assets ÷ Net Earned Premium |
| Asset Return | Technical Investment Income ÷ Financial Investments × 100 |
| Gross Loss Ratio | \|Gross Incurred\| ÷ Gross Earned Premium × 100 |
| Net UW Margin | Net UW Result ÷ Gross Earned Premium × 100 |
| Percentile Rank | Syndicate rank by pretax_margin within year ÷ total syndicates in year × 100 |

Note: **Pre-tax Margin includes investment income** (Technical Investment Income flows through
Balance on Technical Account into Result Before Tax).

---

## App sections

### Market View
- **Major Industry Loss Events (2015–2025)** — sourced from `13_major_loss_events.csv`
- **Lloyd's Loss Drivers (2015–2025)** — sourced from `14_lloyds_loss_drivers.csv`
- **Market-Wide Combined Ratio** — bar chart by year
- **Market GWP & Pre-tax Margin** — dual-axis bar+line chart
- **Loss Ratio vs Expense Ratio** — stacked bar by year
- **Line of Business Performance — Market View** — 4 charts (GWP by LOB, gross combined ratio,
  gross loss ratio, net UW margin) + summary table; computed from `08_segmental_kpis.csv`;
  LOB filter defaults to Casualty, MAT, Motor, Property, Reinsurance (excludes Energy/Life)
- **Syndicate Profitability vs Volatility** — scatter plot
- **Syndicate Pre-tax Margin Distribution** — boxplot by year
- **Market Financial Investments & Asset Return** — dual-axis bar+line

### Syndicate View
- Filtered by managing agent or syndicate number
- P&L, balance sheet, combined ratio, LOB breakdown, percentile rankings, asset returns

---

## Annual refresh guide

When new Lloyd's data becomes available (typically Q2 of the following year):

### 1 — Copy the new Excel file

Copy the new ICMR Excel file (e.g. `Longtail_ICMRData_2015-2026_YYYY-MM-DD.xlsx`) from the
F: drive share into `/srv/docker/lid`. The share is mounted at `/mnt/ltre-f-drive`.

```bash
cp "/mnt/ltre-f-drive/Underwriting/Cedants/P&C/Lloyd's/20XX YoA/ICMR/ICMR Materials/Longtail_ICMRData_2015-20XX_YYYY-MM-DD.xlsx" /srv/docker/lid/
```

### 2 — Run the data processing script

Update the `EXCEL_FILE` path in `process_data.py` to point to the new Excel file, then run:

```bash
python3 /srv/docker/lid/process_data.py
```

This regenerates CSV files **01–12** automatically. It handles:
- Column renames from the new Excel format (see column mapping section below)
- KPI derivation (ratios, percentile ranks, GWP buckets)
- Exchange rate lookup from the Excel `Exchange rates` sheet

### 3 — Update exchange rates (file 16)

Append new rows to `16_fx_rate_used.csv` for the new year (EUR, GBP, USD rates from
`05_exchange_rates.csv`). Format:

```
currency,year,fx_rate_usd_eur_per_gbp,source
USD,20XX,1.XX,05_exchange_rates.csv (average_fx) — from Longtail_ICMRData_2015-20XX_YYYY-MM-DD.xlsx
```

### 4 — Update major loss events (file 13)

Visit [reinsurancene.ws/insurance-industry-losses-events-data](https://www.reinsurancene.ws/insurance-industry-losses-events-data/)
and append new events at the top of the file. Column format:

```
loss_name, month_year, industry_loss, economic_loss, loss_type, notes, year
```

### 5 — Update Lloyd's loss drivers (file 14)

Add up to 5 rows for the new year from the Lloyd's Annual Report. Column format:

```
year, rank, driver_name, driver_type, primary_lob, lloyds_loss_gbp_m,
total_market_loss_usd_bn, notes, source
```

`driver_type` values: `Natural Catastrophe`, `Man-made Event`, `Attritional & Pricing`,
`Reserve Strengthening`, `Investment Loss`

### 6 — Update asset return data (file 15)

Add new rows to `15_Synd_Asset_Return.csv` from the syndicate annual accounts, then
re-run the conversion script to regenerate `15_Synd_Asset_Return_converted.csv`.

### 7 — Update app labels

In `syndicate_explorer.py`, update the two expander labels (search for `2015–`):
- `Major Industry Loss Events (2015–20XX)`
- `Lloyd's Loss Drivers (2015–20XX)`

### 8 — Rebuild and redeploy

```bash
cd /srv/docker/lid && docker compose up --build -d
```

---

## process_data.py — column mapping reference

The new Excel format (from 2025 refresh onwards) uses different column names from the
legacy format used in the existing CSVs. Key renames applied by `process_data.py`:

| New Excel column | CSV column | File(s) |
|---|---|---|
| `net_claims_incurred` | `net_claims_incrred` | 01, 02 (typo preserved for compatibility) |
| `ri_share_claims_outstanding` | `ri_assets` | 01, 02 |
| `ri_unearned_premium` | `unearned_premium` | 01, 02 |
| `total_liabilities_capital_and_reserves` | `total_liabilities` | 01, 02 |

The `Whole Account GBPk` sheet in the new Excel has expanded columns (acquisition cost
detail, sub-expense lines, etc.) that are not carried through to the CSVs — only the
columns matching the legacy CSV schema are selected.

### Percentile rank formula

```
percentile_rank = rank_within_year / total_syndicates_in_year × 100
```

Where `rank_within_year` is ascending rank by `pretax_margin` (1 = lowest margin),
`total_syndicates_in_year` is the count of all syndicates including those with NaN
pretax_margin. Verified to match pre-existing data exactly.

### GWP size buckets

| Bucket label | GWP range (GBP thousands) |
|---|---|
| Micro (<50m) | < 50,000 |
| Small (50-200m) | 50,000 – 199,999 |
| Mid (200-500m) | 200,000 – 499,999 |
| Large (500m-1bn) | 500,000 – 999,999 |
| XL (>1bn) | ≥ 1,000,000 |
