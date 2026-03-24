import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="Lloyd's Insight and Syndicate Analyses", layout="wide", page_icon="🏦")

components.html("""
<script>
(function() {
    var doc = window.parent.document;

    function applySticky() {
        var tabBar = doc.querySelector('[data-baseweb="tab-list"]');
        if (!tabBar) return;

        // Walk up the ACTUAL parent chain and unset any overflow that blocks sticky
        var el = tabBar.parentElement;
        while (el && el !== doc.body) {
            var cs = window.parent.getComputedStyle(el);
            if (/hidden|auto|scroll/.test(cs.overflow) ||
                /hidden|auto|scroll/.test(cs.overflowY)) {
                el.style.setProperty('overflow',   'visible', 'important');
                el.style.setProperty('overflow-y', 'visible', 'important');
            }
            el = el.parentElement;
        }

        // Apply sticky positioning to the tab bar
        tabBar.style.setProperty('position',         'sticky',                      'important');
        tabBar.style.setProperty('top',              '2.875rem',                    'important');
        tabBar.style.setProperty('z-index',          '999',                         'important');
        tabBar.style.setProperty('background-color', 'white',                       'important');
        tabBar.style.setProperty('padding-bottom',   '4px',                         'important');
        tabBar.style.setProperty('box-shadow',       '0 2px 6px rgba(0,0,0,0.10)', 'important');
    }

    // Run after Streamlit finishes rendering
    setTimeout(applySticky, 400);
    setTimeout(applySticky, 1200);

    // Debounced observer — reapply after tab switches / re-renders
    var timer;
    new MutationObserver(function() {
        clearTimeout(timer);
        timer = setTimeout(applySticky, 150);
    }).observe(doc.body, { childList: true, subtree: true });
})();
</script>
""", height=1)

st.markdown("""
<style>
h1 { border-bottom: 2px solid #d0d0d0; padding-bottom: 0.3rem; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    kpi  = pd.read_csv(os.path.join(DATA_DIR, "07_whole_account_kpis.csv"))
    seg  = pd.read_csv(os.path.join(DATA_DIR, "08_segmental_kpis.csv"))
    mkt  = pd.read_csv(os.path.join(DATA_DIR, "09_market_annual_summary.csv"))
    lob  = pd.read_csv(os.path.join(DATA_DIR, "11_lob_market_share_by_year.csv"))
    rnk  = pd.read_csv(os.path.join(DATA_DIR, "12_syndicate_percentile_rankings.csv"))
    losses  = pd.read_csv(os.path.join(DATA_DIR, "13_major_loss_events.csv"))
    drivers = pd.read_csv(os.path.join(DATA_DIR, "14_lloyds_loss_drivers.csv"))
    return kpi, seg, mkt, lob, rnk, losses, drivers

kpi, seg, mkt, lob, rnk, losses, drivers = load_data()

year_min, year_max = int(kpi["year"].min()), int(kpi["year"].max())
ALL_YEARS   = list(range(year_min, year_max + 1))
XAXIS_YEARS = dict(tickmode="array", tickvals=ALL_YEARS)

all_agents = sorted(kpi["managing_agent"].dropna().unique())
all_synd   = sorted(kpi["syndicate"].unique())
_synd_set  = set(all_synd)

# ── Initialise session state from query params (once per browser session) ─────
if "qp_initialized" not in st.session_state:
    qp = st.query_params
    st.session_state["nav_view"] = (
        "Syndicate" if qp.get("view", "").lower() == "syndicate" else "Market"
    )
    if "synd" in qp:
        raw = [int(s) for s in str(qp["synd"]).split(",") if s.strip().lstrip("-").isdigit()]
        st.session_state["filter_synd"]  = [s for s in raw if s in _synd_set]
        st.session_state["nav_search"]   = "Syndicate Number"
    else:
        st.session_state["filter_synd"]  = []
        st.session_state["nav_search"]   = "Managing Agent"
    try:
        yr_lo = max(year_min, int(qp.get("yr_min", year_min)))
        yr_hi = min(year_max, int(qp.get("yr_max", year_max)))
    except (ValueError, TypeError):
        yr_lo, yr_hi = year_min, year_max
    st.session_state["filter_yr"]    = (yr_lo, yr_hi)
    st.session_state["filter_agents"] = []
    st.session_state["qp_initialized"] = True

def _sync_qp():
    """Keep the URL in sync with the current filter state."""
    view  = st.session_state.get("nav_view", "Market")
    synds = st.session_state.get("filter_synd", [])
    yr    = st.session_state.get("filter_yr", (year_min, year_max))
    st.query_params["view"] = view.lower()
    if synds:
        st.query_params["synd"] = ",".join(str(s) for s in sorted(synds))
    elif "synd" in st.query_params:
        del st.query_params["synd"]
    if yr[0] != year_min:
        st.query_params["yr_min"] = str(yr[0])
    elif "yr_min" in st.query_params:
        del st.query_params["yr_min"]
    if yr[1] != year_max:
        st.query_params["yr_max"] = str(yr[1])
    elif "yr_max" in st.query_params:
        del st.query_params["yr_max"]

# ── Sidebar navigation ────────────────────────────────────────────────────────
st.sidebar.title("Navigation")
view_mode = st.sidebar.radio("View", ["Market", "Syndicate"],
                             key="nav_view", on_change=_sync_qp)

# ── SIDEBAR FILTERS (always visible; greyed out in Market view) ───────────────
_market = view_mode == "Market"

st.sidebar.divider()
st.sidebar.markdown("**Filters**")
if _market:
    st.sidebar.caption("_Filters apply to Syndicate view only._")

search_mode = st.sidebar.radio("Search by", ["Managing Agent", "Syndicate Number"],
                               key="nav_search", disabled=_market, on_change=_sync_qp)

if search_mode == "Managing Agent":
    sel_agents = st.sidebar.multiselect("Managing Agent(s)", all_agents,
                                        key="filter_agents", disabled=_market,
                                        on_change=_sync_qp)
    if sel_agents:
        avail_synd = sorted(kpi[kpi["managing_agent"].isin(sel_agents)]["syndicate"].unique())
    else:
        avail_synd = all_synd
    sel_synd = st.sidebar.multiselect("Syndicate(s)", avail_synd,
                                      default=avail_synd if sel_agents else [],
                                      key="filter_synd", disabled=_market,
                                      on_change=_sync_qp)
else:
    sel_synd = st.sidebar.multiselect("Syndicate(s)", all_synd,
                                      key="filter_synd", disabled=_market,
                                      on_change=_sync_qp)

yr_range = st.sidebar.slider("Year Range", year_min, year_max,
                             key="filter_yr", disabled=_market, on_change=_sync_qp)

# ── MARKET VIEW ───────────────────────────────────────────────────────────────
if view_mode == "Market":
    st.title("Lloyd's Insight and Syndicate Analyses")
    st.header("Market View")

    def _parse_loss_bn(s):
        """Parse insured loss string to USD billions (midpoint for ranges)."""
        import re
        if pd.isna(s):
            return 0.0
        s = str(s).lower().replace("~", "").replace(",", "")
        matches = re.findall(r"([\d.]+)\s*(billion|million)", s)
        if not matches:
            return 0.0
        values = [float(n) / 1000 if u == "million" else float(n) for n, u in matches]
        return sum(values) / len(values)  # midpoint for ranges

    st.markdown("""
    <style>
    [data-testid="stExpander"] summary p {
        font-size: 1.15rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    def _html_table(headers, rows_html, max_height=380):
        """Render a styled scrollable HTML table."""
        th_cells = "".join(
            f"<th style='text-align:{align};padding:8px 12px;border-bottom:2px solid #ddd;white-space:nowrap'>{label}</th>"
            for label, align in headers
        )
        return f"""
        <div style='max-height:{max_height}px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px'>
        <table style='width:100%;border-collapse:collapse;font-size:0.875rem'>
          <thead><tr style='position:sticky;top:0;background:#f7f7f7;z-index:1'>{th_cells}</tr></thead>
          <tbody>{rows_html}</tbody>
        </table></div>"""

    # ── Major loss events table ────────────────────────────────────────────────
    with st.expander("Major Industry Loss Events (2015–2024)", expanded=False):
        st.caption("Source: [reinsurancene.ws](https://www.reinsurancene.ws/insurance-industry-losses-events-data/) · Industry insured loss estimates at time of reporting")

        loss_years = sorted(losses[losses["year"].between(year_min, year_max)]["year"].unique(), reverse=True)
        sel_loss_year = st.selectbox(
            "Filter by Year", options=["All years"] + [int(y) for y in loss_years],
            key="loss_yr_filter"
        )

        loss_tbl = (
            losses[losses["year"].isin(loss_years if sel_loss_year == "All years" else [sel_loss_year])]
            .copy()
            [["year", "loss_name", "loss_type", "industry_loss", "economic_loss", "month_year"]]
            .rename(columns={
                "year":           "Year",
                "loss_name":      "Event",
                "loss_type":      "Type",
                "industry_loss":  "Insured Loss",
                "economic_loss":  "Economic Loss",
                "month_year":     "Date",
            })
            .assign(_loss_sort=lambda d: d["Insured Loss"].apply(_parse_loss_bn))
            .sort_values(["Year", "_loss_sort"], ascending=[False, False])
            .drop(columns="_loss_sort")
            .reset_index(drop=True)
        )

        rows = ""
        for _, r in loss_tbl.iterrows():
            rows += (
                f"<tr>"
                f"<td style='text-align:center;white-space:nowrap'>{int(r['Year'])}</td>"
                f"<td style='text-align:center;white-space:nowrap'>{r['Date']}</td>"
                f"<td style='text-align:center;white-space:nowrap'>{r['Type']}</td>"
                f"<td>{r['Event']}</td>"
                f"<td style='white-space:nowrap'>{r['Insured Loss']}</td>"
                f"<td style='white-space:nowrap'>{r['Economic Loss'] if pd.notna(r['Economic Loss']) else '—'}</td>"
                f"</tr>"
            )
        st.markdown(_html_table(
            [("Year","center"),("Month/Year of Loss","center"),("Type","center"),
             ("Event","left"),("Insured Loss","left"),("Economic Loss","left")],
            rows
        ), unsafe_allow_html=True)

    # ── Lloyd's loss drivers table ─────────────────────────────────────────────
    with st.expander("Lloyd's Loss Drivers (2015–2024)", expanded=False):
        st.caption("Source: Lloyd's Annual Reports · GBP figures are Lloyd's net estimates where available")

        driver_years = sorted(drivers[drivers["year"].between(year_min, year_max)]["year"].unique(), reverse=True)
        sel_driver_year = st.selectbox(
            "Filter by Year", options=["All years"] + [int(y) for y in driver_years],
            key="driver_yr_filter"
        )

        driver_tbl = (
            drivers[drivers["year"].isin(driver_years if sel_driver_year == "All years" else [sel_driver_year])]
            .copy()
            .sort_values(["year", "rank"], ascending=[False, True])
            .reset_index(drop=True)
        )

        rows = ""
        for _, r in driver_tbl.iterrows():
            lloyds_loss = f"£{r['lloyds_loss_gbp_m']:,.0f}m" if pd.notna(r["lloyds_loss_gbp_m"]) else "—"
            mkt_loss    = f"${r['total_market_loss_usd_bn']:,.1f}bn" if pd.notna(r["total_market_loss_usd_bn"]) else "—"
            rows += (
                f"<tr>"
                f"<td style='text-align:center;white-space:nowrap'>{int(r['year'])}</td>"
                f"<td style='text-align:center'>{int(r['rank'])}</td>"
                f"<td>{r['driver_name']}</td>"
                f"<td style='text-align:center;white-space:nowrap'>{r['driver_type']}</td>"
                f"<td style='white-space:nowrap'>{r['primary_lob']}</td>"
                f"<td style='text-align:center;white-space:nowrap'>{lloyds_loss}</td>"
                f"<td style='text-align:center;white-space:nowrap'>{mkt_loss}</td>"
                f"<td style='font-size:0.8rem;color:#555'>{r['notes'] if pd.notna(r['notes']) else ''}</td>"
                f"</tr>"
            )
        st.markdown(_html_table(
            [("Year","center"),("Rank","center"),("Driver","left"),("Type","center"),
             ("Primary LOB","left"),("Lloyd's Loss (GBP)","center"),("Market Loss (USD)","center"),("Notes","left")],
            rows, max_height=420
        ), unsafe_allow_html=True)

    st.divider()

    # ── Combined ratio + GWP trends ───────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Market-Wide Combined Ratio**")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=mkt["year"], y=mkt["market_combined_ratio"],
                             marker_color=[
                                 "salmon" if v > 100 else "steelblue"
                                 for v in mkt["market_combined_ratio"]
                             ], name="Combined Ratio"))
        fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Break-even")
        fig.update_layout(height=360, yaxis_title="Combined Ratio (%)",
                          xaxis=XAXIS_YEARS, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("**Market GWP & Pre-tax Margin**")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=mkt["year"], y=mkt["gross_written_premium"] / 1e6,
                             name="GWP (£bn)", marker_color="steelblue", opacity=0.7,
                             yaxis="y1"))
        fig.add_trace(go.Scatter(x=mkt["year"], y=mkt["market_pretax_margin"],
                                 name="Pre-tax Margin (%)", mode="lines+markers",
                                 line=dict(color="darkorange", width=2), yaxis="y2"))
        fig.add_hline(y=0, line_dash="dash", line_color="grey", yref="y2")
        fig.update_layout(
            height=360, xaxis=XAXIS_YEARS,
            yaxis=dict(title="GWP (£bn)"),
            yaxis2=dict(title="Pre-tax Margin (%)", overlaying="y", side="right",
                        showgrid=False),
            legend=dict(font_size=10)
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Loss vs Expense ratio trend ───────────────────────────────────────────
    st.markdown("**Loss Ratio vs Expense Ratio (Market)**")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=mkt["year"], y=mkt["market_loss_ratio"],
                         name="Loss Ratio", marker_color="steelblue"))
    fig.add_trace(go.Bar(x=mkt["year"], y=mkt["market_expense_ratio"],
                         name="Expense Ratio", marker_color="lightsteelblue"))
    fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100%")
    fig.update_layout(barmode="stack", height=340, yaxis_title="Ratio (%)",
                      xaxis=XAXIS_YEARS, legend=dict(font_size=10))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Scatter: Profitability vs Volatility ─────────────────────────────────
    st.markdown("### Syndicate Profitability vs Volatility (Net Basis)")
    st.caption("Y = avg net pre-tax margin (higher = more profitable). "
               "X = volatility (std dev of net combined ratio, high → left, low → right). "
               "Top-right = best performers.")

    scatter_yr_min, scatter_yr_max = st.select_slider(
        "Year range for scatter",
        options=ALL_YEARS,
        value=(year_min, year_max),
        key="scatter_yr"
    )

    sc = kpi[kpi["year"].between(scatter_yr_min, scatter_yr_max)].copy()
    sc_agg = sc.groupby(["syndicate","managing_agent"]).agg(
        avg_combined_ratio = ("combined_ratio",       "mean"),
        std_combined_ratio = ("combined_ratio",       "std"),
        avg_loss_ratio     = ("net_loss_ratio",        "mean"),
        avg_expense_ratio  = ("expense_ratio",         "mean"),
        avg_pretax_margin  = ("pretax_margin",         "mean"),
        std_pretax_margin  = ("pretax_margin",         "std"),
        avg_gwp_m          = ("gross_written_premium", lambda x: x.mean() / 1000),
        n_years            = ("year",                  "count"),
    ).reset_index()

    sc_agg = sc_agg[sc_agg["n_years"] >= 2].dropna(subset=["std_combined_ratio","avg_pretax_margin"])
    sc_agg = sc_agg.sort_values("managing_agent")
    sc_agg["label"] = sc_agg["syndicate"].astype(str) + " – " + sc_agg["managing_agent"]

    mkt_filt       = mkt[mkt["year"].between(scatter_yr_min, scatter_yr_max)]
    mkt_avg_margin = mkt_filt["market_pretax_margin"].mean()
    mkt_avg_std    = sc_agg["std_combined_ratio"].median()

    fig = px.scatter(
        sc_agg,
        x="std_combined_ratio",
        y="avg_pretax_margin",
        color="managing_agent",
        hover_name="label",
        hover_data={
            "avg_pretax_margin":   ":.1f",
            "std_pretax_margin":   ":.1f",
            "avg_combined_ratio":  ":.1f",
            "std_combined_ratio":  ":.1f",
            "avg_loss_ratio":      ":.1f",
            "avg_expense_ratio":   ":.1f",
            "avg_gwp_m":           ":.0f",
            "managing_agent":      False,
        },
        labels={
            "std_combined_ratio": "Volatility — Std Dev of Net Combined Ratio (%) →",
            "avg_pretax_margin":  "Avg Net Pre-tax Margin (%)",
            "avg_gwp_m":          "Avg GWP (£m)",
            "managing_agent":     "Managing Agent",
        },
        color_discrete_sequence=px.colors.qualitative.Plotly,
    )
    fig.update_traces(marker=dict(size=10))

    # Reference lines
    fig.add_hline(y=0, line_dash="dash", line_color="red",
                  annotation_text="Break-even", annotation_position="right")
    fig.add_hline(y=mkt_avg_margin, line_dash="dot", line_color="grey",
                  annotation_text=f"Market avg ({mkt_avg_margin:.1f}%)", annotation_position="right")
    fig.add_vline(x=mkt_avg_std, line_dash="dot", line_color="grey",
                  annotation_text=f"Median vol ({mkt_avg_std:.1f}%)", annotation_position="top")

    # Quadrant labels — x-axis reversed so low vol = right, high vol = left
    x_low  = sc_agg["std_combined_ratio"].quantile(0.10)
    x_high = sc_agg["std_combined_ratio"].quantile(0.85)
    y_high = sc_agg["avg_pretax_margin"].quantile(0.85)
    y_low  = sc_agg["avg_pretax_margin"].quantile(0.15)
    fig.add_annotation(x=x_low,  y=y_high, text="Low vol / High profit",
                       showarrow=False, font=dict(color="green", size=14))
    fig.add_annotation(x=x_high, y=y_low,  text="High vol / Low profit",
                       showarrow=False, font=dict(color="red",   size=14))

    # Default zoom: cover the central bulk of data (5th–95th percentile),
    # excluding extreme outliers. Users can zoom/pan to see the full range.
    x_default_max = sc_agg["std_combined_ratio"].quantile(0.90)   # ~35
    y_default_lo  = sc_agg["avg_pretax_margin"].quantile(0.05)    # ~-30
    y_default_hi  = sc_agg["avg_pretax_margin"].quantile(0.95)    # ~40

    fig.update_layout(
        height=680,
        legend=dict(
            font_size=12,
            title="Managing Agent",
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
        ),
        xaxis=dict(
            tickmode="array", tickvals=list(range(0, 51, 5)),
            range=[35, 0],
        ),
        yaxis=dict(
            range=[y_default_lo * 1.1, y_default_hi * 1.1],
        ),
    )
    st.caption("_Default view shows the central 90% of syndicates. Use the chart toolbar to zoom out and reveal outliers._")
    st.plotly_chart(fig, use_container_width=True)

    st.stop()

# ── SYNDICATE VIEW ────────────────────────────────────────────────────────────
if not sel_synd:
    st.title("Lloyd's Insight and Syndicate Analyses")
    st.header("Syndicate View")
    st.info("Select one or more syndicates (or a managing agent) in the sidebar to get started.")
    st.stop()

df   = kpi[(kpi["syndicate"].isin(sel_synd)) & (kpi["year"].between(*yr_range))].copy()
dseg = seg[(seg["syndicate"].isin(sel_synd)) & (seg["year"].between(*yr_range))].copy()

multi = len(sel_synd) > 1

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("Lloyd's Insight and Syndicate Analyses")
if multi:
    st.header(f"Syndicate View — {len(sel_synd)} syndicates selected")
else:
    row   = df.iloc[-1] if not df.empty else None
    title = f"Syndicate {sel_synd[0]}"
    if row is not None:
        title += f" — {row['managing_agent']}"
    st.header(f"Syndicate View — {title}")

# ── Latest-year KPI cards ─────────────────────────────────────────────────────
latest_yr = df["year"].max()
latest    = df[df["year"] == latest_yr]

snap = latest.agg({
    "gross_written_premium": "sum",
    "net_written_premium":   "sum",
    "net_earned_premium":    "sum",
    "result_before_tax":     "sum",
    "combined_ratio":        "mean",
    "net_loss_ratio":        "mean",
    "expense_ratio":         "mean",
    "pretax_margin":         "mean",
})

def fmt_gbp(v):
    if abs(v) >= 1_000_000:
        return f"£{v/1_000_000:.1f}bn"
    if abs(v) >= 1_000:
        return f"£{v/1_000:.0f}m"
    return f"£{v:.0f}k"

st.markdown(f"### {latest_yr} Snapshot")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("GWP",            fmt_gbp(snap["gross_written_premium"]))
c2.metric("NEP",            fmt_gbp(snap["net_earned_premium"]))
c3.metric("Pre-tax Result", fmt_gbp(snap["result_before_tax"]))
c4.metric("Combined Ratio", f"{snap['combined_ratio']:.1f}%")
c5.metric("Loss Ratio",     f"{snap['net_loss_ratio']:.1f}%")
c6.metric("Pre-tax Margin", f"{snap['pretax_margin']:.1f}%")

st.divider()

# ── Tab layout ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Performance Trends", "Underwriting Ratios", "LOB Breakdown", "Balance Sheet", "Raw Data"
])

COLOR_MAP = {s: px.colors.qualitative.Plotly[i % 10] for i, s in enumerate(sel_synd)}

# ── Tab 1: Performance Trends ─────────────────────────────────────────────────
with tab1:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**GWP vs NEP (£m)**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Bar(x=d["year"], y=d["gross_written_premium"] / 1000,
                                 name=f"GWP {lbl}", marker_color=COLOR_MAP[s], opacity=0.8))
            fig.add_trace(go.Scatter(x=d["year"], y=d["net_earned_premium"] / 1000,
                                     name=f"NEP {lbl}",
                                     line=dict(color=COLOR_MAP[s], dash="dot"),
                                     mode="lines+markers"))
        fig.update_layout(barmode="group", height=380, legend=dict(font_size=10),
                          yaxis_title="£m", xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("**Pre-tax Result (£m)**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            colors = ["green" if v >= 0 else "red" for v in d["result_before_tax"]]
            if multi:
                fig.add_trace(go.Scatter(x=d["year"], y=d["result_before_tax"] / 1000,
                                         name=lbl, mode="lines+markers",
                                         line=dict(color=COLOR_MAP[s])))
            else:
                fig.add_trace(go.Bar(x=d["year"], y=d["result_before_tax"] / 1000,
                                     name=lbl, marker_color=colors))
        fig.add_hline(y=0, line_dash="dash", line_color="grey")
        fig.update_layout(height=380, legend=dict(font_size=10),
                          yaxis_title="£m", xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Pre-tax Margin vs Market (by year)**")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=mkt["year"], y=mkt["market_pretax_margin"],
                         name="Market Avg", marker_color="lightblue", opacity=0.6))
    for s in sel_synd:
        d   = df[df["syndicate"] == s]
        lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
        fig.add_trace(go.Scatter(x=d["year"], y=d["pretax_margin"], name=lbl,
                                 mode="lines+markers", line=dict(color=COLOR_MAP[s])))
    fig.add_hline(y=0, line_dash="dash", line_color="grey")
    fig.update_layout(height=350, yaxis_title="Pre-tax Margin (%)",
                      legend=dict(font_size=10), xaxis=XAXIS_YEARS)
    st.plotly_chart(fig, use_container_width=True)

    # ── Percentile bucket grid ────────────────────────────────────────────────
    st.markdown("**Market Percentile Ranking by Year**")

    with st.expander("How to read this chart"):
        st.markdown("""
**What this chart shows**

Each dot represents this syndicate's position in the Lloyd's market for a given year.
The vertical axis is divided into six performance tiers — from **Top 10%** (best) at the top
down to **Bottom 10%** (worst) at the bottom. A dot in the Top 10% row means the syndicate
ranked among the most profitable 10% of all active Lloyd's syndicates that year.

**How the ranking is calculated**

Syndicates are ranked each year by their **net pre-tax margin** — that is, profit before tax
expressed as a percentage of net earned premium. This is a size-neutral measure, so a small
syndicate with a strong margin competes on equal footing with a large one.

The full market of active syndicates for that year is then divided into six tiers based on
where each syndicate's margin falls relative to its peers:

| Tier | What it means |
|---|---|
| **Top 10%** | Among the most profitable 10% of syndicates that year |
| **P75–P90** | Better than 75% of the market, but not quite top 10% |
| **P50–P75** | Above the median — performing better than half the market |
| **P25–P50** | Below the median — in the lower half of the market |
| **P10–P25** | Underperforming — worse than 75% of peers |
| **Bottom 10%** | Among the least profitable 10% of syndicates that year |

**Tips for reading the chart**

- A dot **staying in the upper rows** year after year signals consistent outperformance.
- A dot that **moves up over time** suggests improving underwriting discipline or favourable reserve development.
- A dot that **drops sharply** in a single year often reflects a large loss event or reserve strengthening.
- Compare the trajectory against years with known market events — 2017 (hurricanes Harvey, Irma, Maria),
  2020 (COVID-19), and 2022 (Ukraine conflict & inflation) were particularly challenging years for the market.
        """)


    BUCKET_ORDER = ["Top 10%", "P75-P90", "P50-P75", "P25-P50", "P10-P25", "Bottom 10%"]
    BUCKET_COLORS = {
        "Top 10%":    "#1a7f37",
        "P75-P90":    "#57ab5a",
        "P50-P75":    "#aad7b0",
        "P25-P50":    "#f5c9a0",
        "P10-P25":    "#e07b39",
        "Bottom 10%": "#c0392b",
    }

    drnk = rnk[(rnk["syndicate"].isin(sel_synd)) & (rnk["year"].between(*yr_range))].copy()

    fig = go.Figure()

    # Light alternating band per bucket row
    for i, bucket in enumerate(BUCKET_ORDER):
        fig.add_hrect(
            y0=i - 0.5, y1=i + 0.5,
            fillcolor="rgba(210,210,210,0.8)" if i % 2 == 0 else "rgba(255,255,255,0)",
            line_width=0, layer="below"
        )

    for s in sel_synd:
        d   = drnk[drnk["syndicate"] == s].sort_values("year")
        if d.empty:
            continue
        lbl = f"{s} – {d['managing_agent'].iloc[-1]}"

        # Map bucket to y-position (numeric so lines connect vertically)
        y_pos    = d["percentile_bucket"].map({b: i for i, b in enumerate(BUCKET_ORDER)})
        dot_cols = d["percentile_bucket"].map(BUCKET_COLORS)

        # Line connecting the dots
        fig.add_trace(go.Scatter(
            x=d["year"], y=y_pos,
            mode="lines",
            line=dict(color=COLOR_MAP[s], width=1.5, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))
        # Dots coloured by bucket
        fig.add_trace(go.Scatter(
            x=d["year"], y=y_pos,
            mode="markers",
            name=lbl,
            marker=dict(
                color=dot_cols,
                size=14,
                line=dict(color=COLOR_MAP[s], width=2),
            ),
            customdata=d[["percentile_bucket","pretax_margin","percentile_rank"]].values,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Year: %{x}<br>"
                "Bucket: %{customdata[0]}<br>"
                "Percentile rank: %{customdata[2]:.1f}<br>"
                "Pre-tax margin: %{customdata[1]:.1f}%"
                "<extra></extra>"
            ),
            text=[lbl] * len(d),
        ))

    fig.update_layout(
        height=380,
        xaxis=XAXIS_YEARS,
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(len(BUCKET_ORDER))),
            ticktext=BUCKET_ORDER,
            range=[-0.5, len(BUCKET_ORDER) - 0.5],
            autorange="reversed",
        ),
        legend=dict(font_size=10),
        plot_bgcolor="white",
        yaxis_gridcolor="rgba(200,200,200,0.5)",
        xaxis_gridcolor="rgba(200,200,200,0.5)",
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Underwriting Ratios ────────────────────────────────────────────────
with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Combined Ratio vs Market**")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=mkt["year"], y=mkt["market_combined_ratio"],
                             name="Market Avg", marker_color="lightblue", opacity=0.6))
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["combined_ratio"], name=lbl,
                                     mode="lines+markers", line=dict(color=COLOR_MAP[s])))
        fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100%")
        fig.update_layout(height=380, yaxis_title="Combined Ratio (%)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("**Loss Ratio vs Expense Ratio**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s].sort_values("year")
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Bar(x=d["year"], y=d["net_loss_ratio"],
                                 name=f"Loss {lbl}", marker_color=COLOR_MAP[s], opacity=0.85,
                                 offsetgroup=str(s)))
            fig.add_trace(go.Bar(x=d["year"], y=d["expense_ratio"],
                                 name=f"Expense {lbl}", marker_color=COLOR_MAP[s], opacity=0.4,
                                 offsetgroup=str(s), base=d["net_loss_ratio"].values))
        fig.update_layout(barmode="group", height=380, yaxis_title="Ratio (%)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("**Loss Ratio vs Market**")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=mkt["year"], y=mkt["market_loss_ratio"],
                             name="Market Avg", marker_color="lightblue", opacity=0.6))
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["net_loss_ratio"], name=lbl,
                                     mode="lines+markers", line=dict(color=COLOR_MAP[s])))
        fig.update_layout(height=340, yaxis_title="Loss Ratio (%)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.markdown("**Expense Ratio vs Market**")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=mkt["year"], y=mkt["market_expense_ratio"],
                             name="Market Avg", marker_color="lightblue", opacity=0.6))
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["expense_ratio"], name=lbl,
                                     mode="lines+markers", line=dict(color=COLOR_MAP[s])))
        fig.update_layout(height=340, yaxis_title="Expense Ratio (%)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    col_e, col_f = st.columns(2)

    with col_e:
        st.markdown("**RI Cession Rate**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["ri_cession_rate"], name=lbl,
                                     mode="lines+markers", line=dict(color=COLOR_MAP[s])))
        fig.update_layout(height=320, yaxis_title="RI Cession Rate (%)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    with col_f:
        st.markdown("**Reserve Ratio (Claims Outstanding / NEP)**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["reserve_ratio"], name=lbl,
                                     mode="lines+markers", line=dict(color=COLOR_MAP[s])))
        fig.update_layout(height=320, yaxis_title="Reserve Ratio (%)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

# ── Tab 3: LOB Breakdown ──────────────────────────────────────────────────────
with tab3:
    if dseg.empty:
        st.info("No segmental data available for this selection.")
    else:
        year_options = ["All Years"] + sorted(dseg["year"].unique(), reverse=True)
        yr_sel   = st.selectbox("Year", year_options, key="lob_yr")
        dseg_yr  = dseg if yr_sel == "All Years" else dseg[dseg["year"] == yr_sel]
        yr_label = yr_sel

        col_a, col_b = st.columns(2)
        with col_a:
            if yr_sel == "All Years":
                st.markdown("**GWP by LOB (All Years — 100% stacked)**")
                lob_yr_grp = dseg.groupby(["year","aggregate_lob"])["gross_written_premium"].sum().reset_index()
                lob_yr_grp = lob_yr_grp[lob_yr_grp["gross_written_premium"] > 0]
                yr_totals  = lob_yr_grp.groupby("year")["gross_written_premium"].transform("sum")
                lob_yr_grp["pct"] = lob_yr_grp["gross_written_premium"] / yr_totals * 100
                fig = go.Figure()
                for lob_name in lob_yr_grp["aggregate_lob"].unique():
                    d = lob_yr_grp[lob_yr_grp["aggregate_lob"] == lob_name]
                    fig.add_trace(go.Bar(x=d["year"], y=d["pct"], name=lob_name))
                fig.update_layout(barmode="stack", height=380, yaxis_ticksuffix="%",
                                  yaxis_title="GWP Share (%)", legend=dict(font_size=10),
                                  xaxis=XAXIS_YEARS)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown(f"**GWP by LOB ({yr_label})**")
                lob_grp = dseg_yr.groupby("aggregate_lob")["gross_written_premium"].sum().reset_index()
                lob_grp = lob_grp[lob_grp["gross_written_premium"] > 0]
                fig = px.pie(lob_grp, values="gross_written_premium", names="aggregate_lob",
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Plotly)
                fig.update_layout(height=380)
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            if yr_sel != "All Years":
                st.markdown(f"**Gross Combined Ratio by LOB ({yr_label})**")
                lob_kpi = dseg_yr.groupby("aggregate_lob").agg(
                    gwp=("gross_written_premium","sum"),
                    gep=("gross_earned_premium","sum"),
                    inc=("gross_incurred","sum"),
                    exp=("operating_expenses","sum"),
                ).reset_index()
                lob_kpi["loss_ratio"]    = lob_kpi["inc"] / lob_kpi["gep"] * -100
                lob_kpi["expense_ratio"] = lob_kpi["exp"] / lob_kpi["gep"] * -100
                lob_kpi["combined"]      = lob_kpi["loss_ratio"] + lob_kpi["expense_ratio"]
                lob_kpi = lob_kpi.replace([float("inf"), float("-inf")], float("nan")).dropna(subset=["combined"])
                fig = go.Figure()
                fig.add_trace(go.Bar(x=lob_kpi["aggregate_lob"], y=lob_kpi["loss_ratio"], name="Loss Ratio"))
                fig.add_trace(go.Bar(x=lob_kpi["aggregate_lob"], y=lob_kpi["expense_ratio"], name="Expense Ratio"))
                fig.add_hline(y=100, line_dash="dash", line_color="red")
                fig.update_layout(barmode="stack", height=380, yaxis_title="Ratio (%)")
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("**LOB GWP**")
        lob_trend = dseg.groupby(["year","aggregate_lob"])["gross_written_premium"].sum().reset_index()
        lob_trend["gwp_m"] = lob_trend["gross_written_premium"] / 1000
        fig = px.bar(lob_trend, x="year", y="gwp_m", color="aggregate_lob",
                     barmode="group", labels={"gwp_m": "GWP (£m)", "aggregate_lob": "LOB"})
        fig.update_layout(height=350, yaxis_title="GWP (£m)", xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Loss Ratio & Expense Ratio by LOB Over Years**")
        ratio_trend = dseg.groupby(["year","aggregate_lob"]).agg(
            gep=("gross_earned_premium","sum"),
            inc=("gross_incurred","sum"),
            exp=("operating_expenses","sum"),
        ).reset_index()
        ratio_trend["loss_ratio"]    = (ratio_trend["inc"] / ratio_trend["gep"] * -100).replace([float("inf"), float("-inf")], float("nan"))
        ratio_trend["expense_ratio"] = (ratio_trend["exp"] / ratio_trend["gep"] * -100).replace([float("inf"), float("-inf")], float("nan"))

        col_c, col_d = st.columns(2)
        with col_c:
            st.markdown("*Loss Ratio by LOB*")
            fig = px.line(ratio_trend, x="year", y="loss_ratio", color="aggregate_lob",
                          markers=True, labels={"loss_ratio": "Loss Ratio (%)", "aggregate_lob": "LOB"})
            fig.update_layout(height=340, legend=dict(font_size=10), xaxis=XAXIS_YEARS)
            st.plotly_chart(fig, use_container_width=True)

        with col_d:
            st.markdown("*Expense Ratio by LOB*")
            fig = px.line(ratio_trend, x="year", y="expense_ratio", color="aggregate_lob",
                          markers=True, labels={"expense_ratio": "Expense Ratio (%)", "aggregate_lob": "LOB"})
            fig.update_layout(height=340, legend=dict(font_size=10), xaxis=XAXIS_YEARS)
            st.plotly_chart(fig, use_container_width=True)

        stats = ratio_trend.groupby("aggregate_lob").agg(
            avg_loss_ratio   =("loss_ratio",   "mean"),
            min_loss_ratio   =("loss_ratio",   "min"),
            max_loss_ratio   =("loss_ratio",   "max"),
            avg_expense_ratio=("expense_ratio","mean"),
            min_expense_ratio=("expense_ratio","min"),
            max_expense_ratio=("expense_ratio","max"),
        ).round(1).reset_index()
        stats.columns = ["LOB","Avg Loss Ratio","Min Loss Ratio","Max Loss Ratio",
                               "Avg Expense Ratio","Min Expense Ratio","Max Expense Ratio"]
        st.markdown("*Summary Stats (all available years)*")
        st.dataframe(stats, use_container_width=True, hide_index=True)

        st.markdown("**Segmental Detail**")
        cols_show = ["year","syndicate","managing_agent","aggregate_lob","harmonised_lob",
                     "gross_written_premium","gross_loss_ratio","gross_expense_ratio",
                     "gross_combined_ratio","net_uw_margin"]
        st.dataframe(dseg[cols_show].sort_values(["year","aggregate_lob"]),
                     use_container_width=True, hide_index=True)

# ── Tab 4: Balance Sheet ──────────────────────────────────────────────────────
with tab4:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Total Assets (£m)**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["total_assets"] / 1000, name=lbl,
                                     mode="lines+markers", line=dict(color=COLOR_MAP[s])))
        fig.update_layout(height=350, yaxis_title="Total Assets (£m)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("**Return on Assets (%)**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["roa"], name=lbl,
                                     mode="lines+markers", line=dict(color=COLOR_MAP[s])))
        fig.add_hline(y=0, line_dash="dash", line_color="grey")
        fig.update_layout(height=350, yaxis_title="ROA (%)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("**RI Assets as % of Total Assets**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["ri_to_total_assets"], name=lbl,
                                     mode="lines+markers", line=dict(color=COLOR_MAP[s])))
        fig.update_layout(height=320, yaxis_title="RI Assets / Total Assets (%)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.markdown("**Claims Outstanding (£m)**")
        fig = go.Figure()
        for s in sel_synd:
            d   = df[df["syndicate"] == s]
            lbl = f"{s} – {d['managing_agent'].iloc[-1]}" if not d.empty else str(s)
            fig.add_trace(go.Scatter(x=d["year"], y=d["claims_outstanding"].abs() / 1000,
                                     name=lbl, mode="lines+markers",
                                     line=dict(color=COLOR_MAP[s])))
        fig.update_layout(height=320, yaxis_title="Claims Outstanding (£m)",
                          legend=dict(font_size=10), xaxis=XAXIS_YEARS)
        st.plotly_chart(fig, use_container_width=True)

# ── Tab 5: Raw Data ───────────────────────────────────────────────────────────
with tab5:
    st.markdown("**Whole Account KPIs**")
    disp_cols = ["year","syndicate","managing_agent","gross_written_premium","net_earned_premium",
                 "result_before_tax","net_loss_ratio","expense_ratio","combined_ratio",
                 "pretax_margin","ri_cession_rate","reserve_ratio","total_assets"]
    st.dataframe(
        df[disp_cols].sort_values(["syndicate","year"]).style.format({
            c: "{:.1f}" for c in ["net_loss_ratio","expense_ratio","combined_ratio",
                                   "pretax_margin","ri_cession_rate","reserve_ratio"]
        }),
        use_container_width=True, hide_index=True
    )
    st.download_button("Download filtered data (CSV)", df.to_csv(index=False),
                       file_name="filtered_syndicates.csv", mime="text/csv")
