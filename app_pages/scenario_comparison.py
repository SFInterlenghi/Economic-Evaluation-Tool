"""ISI-Tool — Scenario Comparison page.

Side-by-side financial KPI comparison and overlaid cumulative
discounted cash flow charts across multiple scenarios.
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils.constants import safe_val, fmt_compact, PLOTLY_LAYOUT, PALETTE
from utils.ui import (
    inject_css, page_header, section_header, kpi_card,
    require_scenarios, scenario_filter,
)
from utils.finance import (
    extract_params, build_cf_arrays, compute_indicators,
    solve_price_for_npv, irr_from_cfs,
)

inject_css()

# ── Data guard ────────────────────────────────────────────────────────────────
scenarios, names, cmap = require_scenarios("Scenario Comparison")

if len(names) < 2:
    page_header("Scenario Comparison")
    st.info(
        "At least **2 scenarios** are needed for comparison. "
        "Go to **Input Data** to create more scenarios.",
        icon=":material/info:",
    )
    st.stop()

page_header("Scenario Comparison",
            "Side-by-side financial KPIs and cash flow overlay")

selected = scenario_filter(names)
if len(selected) < 2:
    st.info("Select at least 2 scenarios to compare.")
    st.stop()


# ── Compute indicators for each scenario ─────────────────────────────────────
def _get_price(name, d):
    """Resolve the effective product price for a scenario."""
    _pm = st.session_state.get("cf_price_mode", {}).get(name, {})
    _pm_mode = _pm.get("mode", "MANUAL")
    _input_price = safe_val(d, "Main Product Price", 0.0)
    if _pm_mode != "MANUAL" and _pm.get("solved_price"):
        return float(_pm["solved_price"])
    elif _pm.get("manual_price") is not None:
        return float(_pm["manual_price"])
    return _input_price


results = {}
cf_data = {}

for name in selected:
    d = scenarios[name]
    wif = st.session_state.get("cf_wif", {}).get(name, {})
    fin = st.session_state.get("cf_fin", {}).get(name, {})
    p = extract_params(d, wif, fin)
    price = _get_price(name, d)

    # Auto-compute MSP if no price set
    if price <= 0:
        msp = solve_price_for_npv(p, 0.0)
        price = msp if (msp is not None and msp > 0) else 0.0

    if price > 0:
        ind = compute_indicators(p, price)
        cfs, pvs, acpv = build_cf_arrays(p, price)

        # Also compute lower/upper TIC bounds
        tic_lo_pct = safe_val(d, "TIC Lower Pct", 0.0)
        tic_hi_pct = safe_val(d, "TIC Upper Pct", 0.0)
        has_bounds = (tic_lo_pct != 0 and tic_hi_pct != 0)
        cm_lo = 1.0 + (tic_lo_pct / 100.0) if has_bounds else 0.75
        cm_hi = 1.0 + (tic_hi_pct / 100.0) if has_bounds else 1.40

        _, _, acpv_lo = build_cf_arrays(p, price, cm_lo)
        _, _, acpv_hi = build_cf_arrays(p, price, cm_hi)
    else:
        ind = {
            "NPV": 0.0, "IRR": None, "MSP": None, "Payback": None,
            "TIC": p["capex"] + p["wc"] + p["startup"],
            "MARR": p["marr"], "OPEX": p["opex"],
            "CAPEX": p["capex"], "Capacity": p["capacity"],
        }
        acpv = [0.0]
        acpv_lo = [0.0]
        acpv_hi = [0.0]
        p_total = p.get("total", 1)

    results[name] = ind
    results[name]["price"] = price
    cf_data[name] = {
        "acpv": acpv,
        "acpv_lo": acpv_lo,
        "acpv_hi": acpv_hi,
        "y0": int(d.get("Year of Analysis", 2024)),
        "epc": p["epc_yrs"],
        "total": p["total"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# KPI SUMMARY TABLE
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Financial KPI comparison", "#e6a817")

KPI_ROWS = [
    ("Product Price",     "price",            "currency"),
    ("CAPEX",             "CAPEX",            "currency_M"),
    ("TIC",               "TIC",              "currency_M"),
    ("Total OPEX",        "OPEX",             "currency_M"),
    ("Capacity",          "Capacity",         "number"),
    ("MARR",              "MARR",             "pct"),
    ("NPV",               "NPV",              "currency_M"),
    ("IRR",               "IRR",              "pct"),
    ("MSP",               "MSP",              "currency"),
    ("Payback (op. yrs)", "Payback",          "years"),
    ("Gross Margin",      "Gross Margin",     "pct"),
    ("EBITDA Margin",     "EBITDA Margin",    "pct"),
    ("Net Profit Margin", "Net Profit Margin","pct"),
    ("ROE",               "ROE",              "pct"),
]


def _fmt_kpi(val, fmt_type):
    if val is None:
        return "—"
    if fmt_type == "currency":
        return f"${val:,.2f}"
    if fmt_type == "currency_M":
        return f"${val/1e6:,.1f}M"
    if fmt_type == "pct":
        return f"{val*100:.2f}%"
    if fmt_type == "years":
        return f"{val:.1f}" if isinstance(val, (int, float)) else str(val)
    if fmt_type == "number":
        return f"{val:,.0f}"
    return str(val)


# Build HTML table
scen_headers = "".join(
    f'<th style="padding:.5rem .8rem;text-align:right;font-size:.78rem;'
    f'color:{cmap[n]};border-bottom:2px solid {cmap[n]}44;white-space:nowrap;'
    f'min-width:100px">{n}</th>'
    for n in selected
)

rows_html = ""
for label, key, fmt_type in KPI_ROWS:
    vals = [results[n].get(key) for n in selected]

    # Highlight best value
    numeric_vals = [(i, v) for i, v in enumerate(vals) if v is not None and isinstance(v, (int, float))]
    best_idx = None
    if numeric_vals:
        if key in ("OPEX", "CAPEX", "TIC", "MSP", "Payback"):
            best_idx = min(numeric_vals, key=lambda x: x[1])[0]
        elif key in ("NPV", "IRR", "Capacity", "Gross Margin", "EBITDA Margin",
                     "Net Profit Margin", "ROE"):
            best_idx = max(numeric_vals, key=lambda x: x[1])[0]

    cells = ""
    for i, (n, v) in enumerate(zip(selected, vals)):
        is_best = (i == best_idx) if best_idx is not None else False
        fw = "font-weight:700;" if is_best else ""
        clr = "#3fb950" if is_best else "#c9d1d9"
        cells += (
            f'<td style="padding:.4rem .8rem;text-align:right;'
            f'font-family:DM Mono,monospace;font-size:.8rem;color:{clr};{fw}">'
            f'{_fmt_kpi(v, fmt_type)}</td>'
        )

    rows_html += (
        f'<tr style="border-bottom:1px solid #21262d22">'
        f'<td style="padding:.4rem .8rem;font-size:.82rem;color:#8b949e">{label}</td>'
        f'{cells}</tr>'
    )

st.markdown(f"""
<div style="overflow-x:auto;border:1px solid #21262d;border-radius:6px;background:#161b22">
<table style="width:100%;border-collapse:collapse">
<thead><tr>
  <th style="padding:.5rem .8rem;text-align:left;font-size:.75rem;color:#8b949e;
      border-bottom:2px solid #21262d;min-width:180px">Metric</th>
  {scen_headers}
</tr></thead>
<tbody>{rows_html}</tbody>
</table></div>
""", unsafe_allow_html=True)

st.space("large")

# ═══════════════════════════════════════════════════════════════════════════════
# OVERLAID CUMULATIVE DISCOUNTED CASH FLOW
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Cumulative discounted cash flow — overlay", "#58a6ff")

show_bands = st.toggle("Show TIC accuracy bands", value=True, key="comp_bands")

fig = go.Figure()

for name in selected:
    cd = cf_data[name]
    color = cmap[name]
    cal_yrs = [cd["y0"] + i for i in range(cd["total"])]
    acpv_M = [v / 1e6 for v in cd["acpv"]]

    # Confidence band
    if show_bands:
        acpv_lo_M = [v / 1e6 for v in cd["acpv_lo"]]
        acpv_hi_M = [v / 1e6 for v in cd["acpv_hi"]]
        fig.add_trace(go.Scatter(
            x=cal_yrs + cal_yrs[::-1],
            y=acpv_hi_M + acpv_lo_M[::-1],
            fill="toself",
            fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.06)",
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        ))

    # Main line
    ind = results[name]
    npv_str = f"NPV={ind['NPV']/1e6:.1f}M" if ind.get("NPV") else ""
    fig.add_trace(go.Scatter(
        x=cal_yrs, y=acpv_M,
        mode="lines",
        name=f"{name} ({npv_str})",
        line=dict(color=color, width=2.5),
        hovertemplate=f"{name}<br>%{{x}}: %{{y:.1f}} MMUSD<extra></extra>",
    ))

    # Payback marker
    pb = ind.get("Payback")
    if pb is not None:
        pb_yr = cd["y0"] + (cd["epc"] + 1) + pb
        if pb_yr in cal_yrs:
            pb_idx = cal_yrs.index(pb_yr)
            fig.add_annotation(
                x=pb_yr, y=acpv_M[pb_idx],
                text=f"Payback yr {pb}",
                showarrow=True, arrowhead=2,
                arrowcolor=color, arrowsize=0.7,
                font=dict(size=8, color=color),
            )

fig.add_hline(y=0, line_color="#484f58", line_width=1)

fig.update_layout(
    paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
    font=dict(family="Inter, sans-serif", color="#c9d1d9", size=11),
    margin=dict(l=60, r=20, t=20, b=50),
    height=450,
    xaxis=dict(title="Year", gridcolor="#21262d", linecolor="#30363d",
               tickfont=dict(size=10), showgrid=True),
    yaxis=dict(title="Cumulative discounted cash flow (MMUSD)",
               gridcolor="#21262d", linecolor="#30363d",
               tickfont=dict(size=10, family="DM Mono"), showgrid=True, zeroline=False),
    legend=dict(bgcolor="rgba(13,17,23,0.8)", bordercolor="#30363d",
                borderwidth=1, font=dict(size=10),
                x=0.02, y=0.98, xanchor="left", yanchor="top"),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.space("medium")

# ═══════════════════════════════════════════════════════════════════════════════
# BAR CHART COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Key financial metrics — bar comparison", "#3fb950")

bar_metrics = [
    ("NPV (MMUSD)", "NPV", 1e6),
    ("TIC (MMUSD)", "TIC", 1e6),
    ("OPEX (MMUSD/yr)", "OPEX", 1e6),
]

fig_bars = go.Figure()
for name in selected:
    ind = results[name]
    color = cmap[name]
    fig_bars.add_trace(go.Bar(
        name=name,
        x=[label for label, _, _ in bar_metrics],
        y=[ind.get(key, 0) / scale for _, key, scale in bar_metrics],
        text=[f"{ind.get(key, 0)/scale:,.1f}" for _, key, scale in bar_metrics],
        textposition="outside",
        textfont=dict(family="DM Mono", size=10, color="#8b949e"),
        marker=dict(color=color, line_width=0, opacity=0.85),
    ))

fig_bars.update_layout(
    **{k: v for k, v in PLOTLY_LAYOUT.items() if k != "yaxis"},
    barmode="group",
    yaxis=dict(gridcolor="#21262d", tickformat=",.0f",
               tickfont=dict(family="DM Mono", size=10),
               title="MMUSD"),
    height=320,
)
st.plotly_chart(fig_bars, use_container_width=True)

# IRR comparison
section_header("IRR comparison vs MARR", "#e6a817")
fig_irr = go.Figure()
for name in selected:
    ind = results[name]
    color = cmap[name]
    irr_val = ind.get("IRR")
    marr_val = ind.get("MARR", 0)
    if irr_val is not None:
        fig_irr.add_trace(go.Bar(
            name=name,
            x=[name],
            y=[irr_val * 100],
            text=[f"{irr_val*100:.1f}%"],
            textposition="outside",
            textfont=dict(family="DM Mono", size=11),
            marker=dict(color=color, line_width=0),
        ))

# MARR reference line (use first scenario's MARR)
first_marr = results[selected[0]].get("MARR", 0)
if first_marr:
    fig_irr.add_hline(
        y=first_marr * 100,
        line_color="#e6a817", line_width=2, line_dash="dash",
    )
    fig_irr.add_annotation(
        x=selected[-1], y=first_marr * 100 + 1,
        text=f"MARR = {first_marr*100:.1f}%",
        showarrow=False,
        font=dict(size=10, color="#e6a817"),
    )

fig_irr.update_layout(
    **{k: v for k, v in PLOTLY_LAYOUT.items() if k != "yaxis"},
    yaxis=dict(gridcolor="#21262d", ticksuffix="%",
               tickfont=dict(family="DM Mono", size=10),
               title="IRR (%)"),
    showlegend=False,
    height=280,
)
st.plotly_chart(fig_irr, use_container_width=True)
