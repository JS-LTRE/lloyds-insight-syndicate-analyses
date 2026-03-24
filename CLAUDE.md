# Lloyd's Syndicate Explorer — Docker Deployment

## Project Overview

A Streamlit web application for interactive analysis of Lloyd's of London syndicate
historical performance data (2015–2024). Covers 156 syndicates across 10 years with
P&L, balance sheet, segmental line-of-business, and market benchmarking views.

The app runs entirely from pre-generated CSV files — no database required.

---

## Instructions for Claude Code

When you read this file, execute the following steps in order. Do not skip steps.
All commands should be run from the directory containing this file.

### Step 1 — Confirm required files are present

The following files must exist in this directory before proceeding:

**Application**
- `syndicate_explorer.py` — main Streamlit app

**Data files (CSV)**
- `07_whole_account_kpis.csv`
- `08_segmental_kpis.csv`
- `09_market_annual_summary.csv`
- `11_lob_market_share_by_year.csv`
- `12_syndicate_percentile_rankings.csv`

**Docker config (created by this deployment)**
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`

If any Docker config files are missing, create them using the exact content in the
sections below before continuing.

---

### Step 2 — Create `requirements.txt` if missing

```
streamlit==1.55.0
pandas==2.3.3
plotly==6.6.0
openpyxl==3.1.5
```

---

### Step 3 — Create `Dockerfile` if missing

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    streamlit==1.55.0 \
    pandas==2.3.3 \
    plotly==6.6.0 \
    openpyxl==3.1.5

COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "syndicate_explorer.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
```

---

### Step 4 — Create `docker-compose.yml` if missing

```yaml
version: "3.9"

services:
  syndicate-explorer:
    build: .
    container_name: lloyds-syndicate-explorer
    ports:
      - "8501:8501"
    restart: unless-stopped
```

---

### Step 5 — Build and start the container

Run this command:

```bash
docker-compose up --build -d
```

This will:
1. Build the Docker image using `python:3.11-slim` as base
2. Install all pinned Python dependencies
3. Copy all application and data files into the image
4. Start the container in detached mode on port `8501`
5. Configure the container to restart automatically unless explicitly stopped

---

### Step 6 — Verify the deployment

Run these verification commands and confirm they succeed:

```bash
# Check container is running
docker ps --filter "name=lloyds-syndicate-explorer"

# Check health endpoint (may take 10–15s on first start)
curl -f http://localhost:8501/_stcore/health
```

Expected output from health check: `ok`

If the health check fails after 30 seconds, run:
```bash
docker logs lloyds-syndicate-explorer
```
and investigate any errors before retrying.

---

### Step 7 — Report success

Once the container is healthy, confirm to the user:
- Container name: `lloyds-syndicate-explorer`
- URL: `http://<server-ip>:8501`
- Status: running / healthy

---

## Useful management commands

```bash
# Stop the app
docker-compose down

# View live logs
docker logs -f lloyds-syndicate-explorer

# Rebuild after updating syndicate_explorer.py or CSV files
docker-compose up --build -d

# Remove the container and image entirely
docker-compose down --rmi all
```

---

## Data dictionary

| CSV file | Contents | Rows |
|---|---|---|
| `07_whole_account_kpis.csv` | P&L + balance sheet + derived ratios per syndicate/year | 979 |
| `08_segmental_kpis.csv` | Underwriting data by line of business | 4,940 |
| `09_market_annual_summary.csv` | Market-wide annual aggregates | 10 |
| `11_lob_market_share_by_year.csv` | LOB market share % by year | 61 |
| `12_syndicate_percentile_rankings.csv` | Annual net profit percentile bucket per syndicate | ~979 |
| `13_major_loss_events.csv` | Major global insured loss events (1988–2025) sourced from reinsurancene.ws | 158 |
| `14_lloyds_loss_drivers.csv` | Top Lloyd's-specific loss drivers per year (2015–2024), sourced from Lloyd's Annual Reports | 46 |

All monetary values are in **GBP thousands** unless otherwise noted.
Years covered: **2015–2024**.

---

## Annual refresh guide

When new Lloyd's data becomes available (typically Q2 of the following year), update the
analysis by repeating the steps below for the new year (e.g. replacing "2025" as appropriate).

### 1 — Update syndicate underwriting data (files 07–12)

These are generated from the Lloyd's Annual Report Excel data extract. Replace the existing
CSVs with new versions that include the additional year's rows. The app will automatically
detect the new year range from `07_whole_account_kpis.csv`.

### 2 — Update market annual summary (file 09)

Add one row to `09_market_annual_summary.csv` for the new year with market-wide combined
ratio, GWP, and pre-tax margin figures from the Lloyd's Annual Report.

### 3 — Update major loss events (file 13)

Visit [reinsurancene.ws/insurance-industry-losses-events-data](https://www.reinsurancene.ws/insurance-industry-losses-events-data/)
and scrape or copy any new loss events for the new year. Append them to
`13_major_loss_events.csv` using the same column format:

```
loss_name, month_year, industry_loss, economic_loss, loss_type, notes, year
```

### 4 — Update Lloyd's loss drivers (file 14)

Once the Lloyd's Annual Report is published, add up to 5 rows to `14_lloyds_loss_drivers.csv`
for the new year, one row per major loss driver ranked by severity. Use the same column format:

```
year, rank, driver_name, driver_type, primary_lob, lloyds_loss_gbp_m,
total_market_loss_usd_bn, notes, source
```

- `driver_type` values in use: `Natural Catastrophe`, `Man-made Event`, `Attritional & Pricing`,
  `Reserve Strengthening`, `Investment Loss`
- `lloyds_loss_gbp_m` and `total_market_loss_usd_bn` may be left blank if not disclosed

### 5 — Rebuild and redeploy

After updating any CSV files, rebuild the container:

```bash
cd /srv/docker/lid && docker compose up --build -d
```

The app title ranges (e.g. "2015–2024") are hardcoded in the markdown headings in
`syndicate_explorer.py` — search for `2015–2024` and update to the new range if needed.
