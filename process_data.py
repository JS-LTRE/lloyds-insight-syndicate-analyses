"""
Data processing script: regenerates CSV files 01-12 from the new Excel file.
Run from /srv/docker/lid after placing the new Excel file in this directory.
"""
import pandas as pd
import numpy as np
import os

EXCEL_FILE = '/srv/docker/lid/Longtail_ICMRData_2015-2025_2026-04-15.xlsx'
OUT_DIR = '/srv/docker/lid'

print("Loading Excel file...")
xl = pd.ExcelFile(EXCEL_FILE)

# ---------------------------------------------------------------------------
# 01 — Whole Account GBPk
# ---------------------------------------------------------------------------
print("Processing 01_whole_account_gbpk.csv ...")
df_wa = pd.read_excel(xl, sheet_name='Whole Account GBPk')

# Column renames: new Excel → old CSV convention
df_wa = df_wa.rename(columns={
    'net_claims_incurred': 'net_claims_incrred',        # preserve legacy typo
    'ri_share_claims_outstanding': 'ri_assets',
    'ri_unearned_premium': 'unearned_premium',
    'total_liabilities_capital_and_reserves': 'total_liabilities',
})

CSV01_COLS = [
    'syndicate', 'year', 'managing_agent',
    'gross_written_premium', 'outward_reinsurance_premium', 'net_written_premium',
    'net_earned_premium', 'other_technical_income', 'technical_investment_income',
    'gross_claims_paid', 'gross_change_in_provision_for_claims',
    'ri_share_claims_paid', 'ri_share_change_in_provision_for_claims',
    'net_claims_incrred', 'operating_expenses', 'balance_on_technical_account',
    'profit_loss_on_exchange', 'other_non_technical_income', 'result_before_tax',
    'financial_investments', 'ri_assets', 'unearned_premium', 'other_assets',
    'total_assets', 'provisions_for_unearned_premium', 'claims_outstanding',
    'other_liabilities', 'total_liabilities', 'currency', 'unit',
]
df01 = df_wa[CSV01_COLS].copy()
df01.to_csv(os.path.join(OUT_DIR, '01_whole_account_gbpk.csv'), index=False)
print(f"  Rows: {len(df01)}, Years: {sorted(df01['year'].unique())}")

# ---------------------------------------------------------------------------
# 02 — Whole Account original currency
# ---------------------------------------------------------------------------
print("Processing 02_whole_account_orig_ccy.csv ...")
df_wao = pd.read_excel(xl, sheet_name='Whole Account original currency')

df_wao = df_wao.rename(columns={
    'net_claims_incurred': 'net_claims_incrred',
    'ri_share_claims_outstanding': 'ri_assets',
    'ri_unearned_premium': 'unearned_premium',
    'total_liabilities_capital_and_reserves': 'total_liabilities',
    'reporting_currency': 'reporting_currency',
    'reporting_unit': 'reporting_unit',
})

CSV02_COLS = [
    'year', 'syndicate', 'reporting_currency', 'reporting_unit',
    'gross_written_premium', 'outward_reinsurance_premium', 'net_written_premium',
    'net_earned_premium', 'other_technical_income', 'technical_investment_income',
    'gross_claims_paid', 'gross_change_in_provision_for_claims',
    'ri_share_claims_paid', 'ri_share_change_in_provision_for_claims',
    'net_claims_incrred', 'operating_expenses', 'balance_on_technical_account',
    'profit_loss_on_exchange', 'other_non_technical_income', 'result_before_tax',
    'financial_investments', 'ri_assets', 'unearned_premium', 'other_assets',
    'total_assets', 'provisions_for_unearned_premium', 'claims_outstanding',
    'total_liabilities', 'other_liabilities', 'source',
]
df02 = df_wao[CSV02_COLS].copy()
df02.to_csv(os.path.join(OUT_DIR, '02_whole_account_orig_ccy.csv'), index=False)
print(f"  Rows: {len(df02)}, Years: {sorted(df02['year'].unique())}")

# ---------------------------------------------------------------------------
# 03 — Segmental GBPk
# ---------------------------------------------------------------------------
print("Processing 03_segmental_gbpk.csv ...")
df03 = pd.read_excel(xl, sheet_name='Segmental GBPk')
CSV03_COLS = [
    'year', 'syndicate', 'managing_agent', 'syndicate_cob', 'harmonised_lob',
    'aggregate_lob', 'gross_written_premium', 'gross_earned_premium', 'gross_incurred',
    'operating_expenses', 'gross_uw_result', 'net_uw_result', 'unit', 'currency',
]
df03 = df03[CSV03_COLS].copy()
df03.to_csv(os.path.join(OUT_DIR, '03_segmental_gbpk.csv'), index=False)
print(f"  Rows: {len(df03)}, Years: {sorted(df03['year'].unique())}")

# ---------------------------------------------------------------------------
# 04 — Segmental original currency
# ---------------------------------------------------------------------------
print("Processing 04_segmental_orig_ccy.csv ...")
df04 = pd.read_excel(xl, sheet_name='Segmental original currency')
CSV04_COLS = [
    'year', 'syndicate', 'reporting_currency', 'reporting_unit', 'syndicate_cob',
    'gross_written_premium', 'gross_earned_premium', 'gross_claims_incurred',
    'operating_expenses', 'ri_balance', 'source',
]
df04 = df04[CSV04_COLS].copy()
df04.to_csv(os.path.join(OUT_DIR, '04_segmental_orig_ccy.csv'), index=False)
print(f"  Rows: {len(df04)}, Years: {sorted(df04['year'].unique())}")

# ---------------------------------------------------------------------------
# 05 — Exchange rates
# ---------------------------------------------------------------------------
print("Processing 05_exchange_rates.csv ...")
df_fx = pd.read_excel(xl, sheet_name='Exchange rates')

# New Excel only has Average period; pivot to get average_fx per currency/year
df_avg = df_fx[df_fx['Period'] == 'Average'][['Currency', 'Year', 'Fx', 'Market Bulletin']].copy()
df_avg = df_avg.rename(columns={
    'Currency': 'currency',
    'Year': 'year',
    'Fx': 'average_fx',
    'Market Bulletin': 'market_bulletin',
})
df_avg['year_end_fx'] = np.nan  # not available in new Excel format

# Bring in year_end_fx from existing CSV05 where available
existing_05 = pd.read_csv(os.path.join(OUT_DIR, '05_exchange_rates.csv'))
ye_map = existing_05.set_index(['currency', 'year'])['year_end_fx'].to_dict()
df_avg['year_end_fx'] = df_avg.apply(
    lambda r: ye_map.get((r['currency'], r['year']), np.nan), axis=1
)

df05 = df_avg[['currency', 'year', 'average_fx', 'year_end_fx', 'market_bulletin']].copy()
df05 = df05.sort_values(['currency', 'year']).reset_index(drop=True)
df05.to_csv(os.path.join(OUT_DIR, '05_exchange_rates.csv'), index=False)
print(f"  Rows: {len(df05)}")
print(df05.to_string())

# ---------------------------------------------------------------------------
# 06 — LOB Mapping
# ---------------------------------------------------------------------------
print("Processing 06_lob_mapping.csv ...")
df06 = pd.read_excel(xl, sheet_name='LOB Mapping')
df06.to_csv(os.path.join(OUT_DIR, '06_lob_mapping.csv'), index=False)
print(f"  Rows: {len(df06)}")

# ---------------------------------------------------------------------------
# 07 — Whole Account KPIs (derived from 01)
# ---------------------------------------------------------------------------
print("Processing 07_whole_account_kpis.csv ...")
df07 = df01.copy()

nep = df07['net_earned_premium']
gwp = df07['gross_written_premium']

# Ratios — guard against divide-by-zero
df07['net_loss_ratio'] = (df07['net_claims_incrred'].abs() / nep.replace(0, np.nan) * 100).round(2)
df07['expense_ratio'] = (df07['operating_expenses'].abs() / nep.replace(0, np.nan) * 100).round(2)
df07['combined_ratio'] = (df07['net_loss_ratio'] + df07['expense_ratio']).round(2)
df07['ri_cession_rate'] = (df07['outward_reinsurance_premium'].abs() / gwp.replace(0, np.nan) * 100).round(2)
df07['net_retention_rate'] = (df07['net_written_premium'] / gwp.replace(0, np.nan) * 100).round(2)
df07['technical_account_margin'] = (df07['balance_on_technical_account'] / nep.replace(0, np.nan) * 100).round(2)
df07['pretax_margin'] = (df07['result_before_tax'] / nep.replace(0, np.nan) * 100).round(2)
df07['roa'] = (df07['result_before_tax'] / df07['total_assets'].replace(0, np.nan) * 100).round(2)
df07['ri_to_total_assets'] = (df07['ri_assets'] / df07['total_assets'].replace(0, np.nan) * 100).round(2)
df07['reserve_ratio'] = (df07['claims_outstanding'].abs() / nep.replace(0, np.nan) * 100).round(2)

# GWP size bucket (GBP thousands)
def gwp_bucket(g):
    if pd.isna(g):
        return np.nan
    if g < 50_000:
        return 'Micro (<50m)'
    elif g < 200_000:
        return 'Small (50-200m)'
    elif g < 500_000:
        return 'Mid (200-500m)'
    elif g < 1_000_000:
        return 'Large (500m-1bn)'
    else:
        return 'XL (>1bn)'

df07['gwp_size_bucket'] = df07['gross_written_premium'].apply(gwp_bucket)

df07.to_csv(os.path.join(OUT_DIR, '07_whole_account_kpis.csv'), index=False)
print(f"  Rows: {len(df07)}, Years: {sorted(df07['year'].unique())}")

# ---------------------------------------------------------------------------
# 08 — Segmental KPIs (derived from 03)
# ---------------------------------------------------------------------------
print("Processing 08_segmental_kpis.csv ...")
df08 = df03.copy()

gep = df08['gross_earned_premium']
df08['gross_loss_ratio'] = (df08['gross_incurred'].abs() / gep.replace(0, np.nan) * 100).round(2)
df08['gross_expense_ratio'] = (df08['operating_expenses'].abs() / gep.replace(0, np.nan) * 100).round(2)
df08['gross_combined_ratio'] = (df08['gross_loss_ratio'] + df08['gross_expense_ratio']).round(2)
df08['net_uw_margin'] = (df08['net_uw_result'] / gep.replace(0, np.nan) * 100).round(2)

CSV08_COLS = [
    'year', 'syndicate', 'managing_agent', 'syndicate_cob', 'harmonised_lob',
    'aggregate_lob', 'gross_written_premium', 'gross_earned_premium', 'gross_incurred',
    'operating_expenses', 'gross_uw_result', 'net_uw_result', 'unit', 'currency',
    'gross_loss_ratio', 'gross_expense_ratio', 'gross_combined_ratio', 'net_uw_margin',
]
df08 = df08[CSV08_COLS]
df08.to_csv(os.path.join(OUT_DIR, '08_segmental_kpis.csv'), index=False)
print(f"  Rows: {len(df08)}, Years: {sorted(df08['year'].unique())}")

# ---------------------------------------------------------------------------
# 09 — Market Annual Summary (aggregate from 01, GBP only)
# ---------------------------------------------------------------------------
print("Processing 09_market_annual_summary.csv ...")
df_gbp = df01[df01['currency'] == 'GBP'].copy()

agg = df_gbp.groupby('year').agg(
    syndicates=('syndicate', 'count'),
    gross_written_premium=('gross_written_premium', 'sum'),
    net_written_premium=('net_written_premium', 'sum'),
    net_earned_premium=('net_earned_premium', 'sum'),
    net_claims_incurred=('net_claims_incrred', 'sum'),
    operating_expenses=('operating_expenses', 'sum'),
    balance_tech_account=('balance_on_technical_account', 'sum'),
    result_before_tax=('result_before_tax', 'sum'),
    total_assets=('total_assets', 'sum'),
    claims_outstanding=('claims_outstanding', 'sum'),
).reset_index()

nep = agg['net_earned_premium']
agg['market_loss_ratio'] = (agg['net_claims_incurred'].abs() / nep * 100).round(2)
agg['market_expense_ratio'] = (agg['operating_expenses'].abs() / nep * 100).round(2)
agg['market_combined_ratio'] = (agg['market_loss_ratio'] + agg['market_expense_ratio']).round(2)
agg['market_pretax_margin'] = (agg['result_before_tax'] / nep * 100).round(2)

agg.to_csv(os.path.join(OUT_DIR, '09_market_annual_summary.csv'), index=False)
print(f"  Rows: {len(agg)}, Years: {sorted(agg['year'].unique())}")

# ---------------------------------------------------------------------------
# 10 — Managing Agent GWP Pivot (from 01, GBP only)
# ---------------------------------------------------------------------------
print("Processing 10_managing_agent_gwp_pivot.csv ...")
df_gbp2 = df01[df01['currency'] == 'GBP'].copy()
pivot = df_gbp2.groupby(['managing_agent', 'year'])['gross_written_premium'].sum().unstack('year')
pivot.columns = [str(c) for c in pivot.columns]
pivot = pivot.reset_index()
pivot.to_csv(os.path.join(OUT_DIR, '10_managing_agent_gwp_pivot.csv'), index=False)
print(f"  Rows: {len(pivot)}, Year columns: {[c for c in pivot.columns if c != 'managing_agent']}")

# ---------------------------------------------------------------------------
# 11 — LOB Market Share by Year (from 03)
# ---------------------------------------------------------------------------
print("Processing 11_lob_market_share_by_year.csv ...")
lob_agg = df03.groupby(['year', 'aggregate_lob'])['gross_written_premium'].sum().reset_index()
market_tot = lob_agg.groupby('year')['gross_written_premium'].sum().rename('market_total')
lob_agg = lob_agg.join(market_tot, on='year')
lob_agg['market_share_pct'] = (lob_agg['gross_written_premium'] / lob_agg['market_total'] * 100).round(2)
lob_agg.to_csv(os.path.join(OUT_DIR, '11_lob_market_share_by_year.csv'), index=False)
print(f"  Rows: {len(lob_agg)}, Years: {sorted(lob_agg['year'].unique())}")

# ---------------------------------------------------------------------------
# 12 — Syndicate Percentile Rankings (from 07)
# ---------------------------------------------------------------------------
print("Processing 12_syndicate_percentile_rankings.csv ...")
df12_cols = ['year', 'syndicate', 'managing_agent', 'gross_written_premium',
             'net_earned_premium', 'result_before_tax', 'pretax_margin',
             'net_loss_ratio', 'expense_ratio', 'combined_ratio']
df12 = df07[df12_cols].copy()

# Rank within each year (ascending = lowest margin gets rank 1)
year_sizes = df12.groupby('year')['year'].transform('count')
year_ranks = df12.groupby('year')['pretax_margin'].rank(
    ascending=True, method='average', na_option='keep'
)
df12['percentile_rank'] = (year_ranks / year_sizes * 100).round(1)

def pct_bucket(r):
    if pd.isna(r):
        return np.nan
    if r >= 90:
        return 'Top 10%'
    elif r >= 75:
        return 'P75-P90'
    elif r >= 50:
        return 'P50-P75'
    elif r >= 25:
        return 'P25-P50'
    elif r >= 10:
        return 'P10-P25'
    else:
        return 'Bottom 10%'

df12['percentile_bucket'] = df12['percentile_rank'].apply(pct_bucket)
df12 = df12.sort_values(['year', 'percentile_rank'], ascending=[True, False]).reset_index(drop=True)
df12.to_csv(os.path.join(OUT_DIR, '12_syndicate_percentile_rankings.csv'), index=False)
print(f"  Rows: {len(df12)}, Years: {sorted(df12['year'].unique())}")

print("\nDone. All CSV files updated.")
