# Lloyd's Insight and Syndicate Analysis — Docker Deployment

## Project Overview

A Streamlit web application for interactive analysis of Lloyd's of London syndicate
historical performance data (2015–2024). Covers 156 syndicates across 10 years with
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

| CSV file | Contents |
|---|---|
| `07_whole_account_kpis.csv` | P&L + balance sheet + derived ratios per syndicate/year |
| `08_segmental_kpis.csv` | Underwriting data by line of business |
| `09_market_annual_summary.csv` | Market-wide annual aggregates |
| `11_lob_market_share_by_year.csv` | LOB market share % by year |
| `12_syndicate_percentile_rankings.csv` | Annual net profit percentile bucket per syndicate |
| `13_major_loss_events.csv` | Major global insured loss events (1988–2025) sourced from reinsurancene.ws |
| `14_lloyds_loss_drivers.csv` | Top Lloyd's-specific loss drivers per year (2015–2024), sourced from Lloyd's Annual Reports |
| `15_Synd_Asset_Return_converted.csv` | Syndicate financial investment cost and asset return (2024–2025), converted to GBP thousands |
| `16_fx_rate_used.csv` | FX rates (average annual) used to convert USD/EUR → GBP, confirmed against files 01 and 02 |

All monetary values are in **GBP thousands** unless otherwise noted.
Years covered: **2015–2024** (files 07–14); **2024–2025** (file 15).

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

Note: **Pre-tax Margin includes investment income** (Technical Investment Income flows through
Balance on Technical Account into Result Before Tax).

---

## Annual refresh guide

When new Lloyd's data becomes available (typically Q2 of the following year):

### 1 — Update syndicate underwriting data (files 07–12)

Replace the existing CSVs with new versions that include the additional year's rows.
The app will automatically detect the new year range from `07_whole_account_kpis.csv`.

### 2 — Update market annual summary (file 09)

Add one row for the new year with market-wide combined ratio, GWP, and pre-tax margin
figures from the Lloyd's Annual Report.

### 3 — Update major loss events (file 13)

Visit [reinsurancene.ws/insurance-industry-losses-events-data](https://www.reinsurancene.ws/insurance-industry-losses-events-data/)
and append new events using the same column format:

```
loss_name, month_year, industry_loss, economic_loss, loss_type, notes, year
```

### 4 — Update Lloyd's loss drivers (file 14)

Add up to 5 rows for the new year. Column format:

```
year, rank, driver_name, driver_type, primary_lob, lloyds_loss_gbp_m,
total_market_loss_usd_bn, notes, source
```

`driver_type` values: `Natural Catastrophe`, `Man-made Event`, `Attritional & Pricing`,
`Reserve Strengthening`, `Investment Loss`

### 5 — Update asset return data (file 15)

Add new rows to `15_Synd_Asset_Return.csv` from the syndicate annual accounts, then
re-run the conversion script to regenerate `15_Synd_Asset_Return_converted.csv`.

FX rates for new years should be added to `05_exchange_rates.csv` first, then
`16_fx_rate_used.csv` will be updated accordingly.

### 6 — Rebuild and redeploy

```bash
cd /srv/docker/lid && docker compose up --build -d
```

The app title year ranges (e.g. "2015–2024") are hardcoded in markdown headings in
`syndicate_explorer.py` — search for `2015–2024` and update to the new range if needed.
