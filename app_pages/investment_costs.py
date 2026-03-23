"""ISI-Tool — Investment Costs dashboard."""
import streamlit as st
import plotly.graph_objects as go
from utils.constants import safe_val, fmt_compact, smart_fmt, PLOTLY_LAYOUT
from utils.ui import (
    inject_css, page_header, section_header, kpi_card,
    scenario_banner, breakdown_table, require_scenarios, scenario_filter,
)

inject_css()

# ── Data guard ────────────────────────────────────────────────────────────────
scenarios, names, cmap = require_scenarios("Investment Costs")

def fmt(v):  return f"${v:,.0f}"
def fmtd(v): return f"${v:,.2f}"
def fpct(v): return f"{v * 100:.2f}%"

# ── Header ────────────────────────────────────────────────────────────────────
page_header("Investment Costs", "Total Investment Cost — scenario comparison")
selected = scenario_filter(names)
active = {n: scenarios[n] for n in selected}

# ── Scenario Overview ─────────────────────────────────────────────────────────
section_header("Scenario overview", "#e6a817")
cols_banner = st.columns(len(active))
for col, (name, d) in zip(cols_banner, active.items()):
    with col:
        scenario_banner(name, d, cmap[name])

st.space("medium")

# ── KPI Cards — TIC with accuracy bounds ─────────────────────────────────────
section_header("Total Investment Cost per scenario", "#e6a817")
cols_kpi = st.columns(len(active))
for col, (name, d) in zip(cols_kpi, active.items()):
    tic = safe_val(d, "Total Investment")
    capex = safe_val(d, "Project CAPEX")
    wc = safe_val(d, "Working Capital")
    su = safe_val(d, "Startup Costs")

    # TIC accuracy bounds
    tic_lo_pct = d.get("TIC Lower Pct")
    tic_hi_pct = d.get("TIC Upper Pct")
    if tic_lo_pct is not None and tic_hi_pct is not None and tic > 0:
        tic_lo = tic * (1 + tic_lo_pct / 100.0)
        tic_hi = tic * (1 + tic_hi_pct / 100.0)
        range_str = f"Range: {fmt_compact(tic_lo)} to {fmt_compact(tic_hi)}  ({tic_lo_pct:+.0f}% / {tic_hi_pct:+.0f}%)"
    else:
        range_str = "Accuracy bounds: N/A"

    with col:
        kpi_card(
            f"Total Investment — {name}", fmt(tic), cmap[name],
            "CAPEX / WC / S-U",
            f"{fmt_compact(capex)} | {fmt_compact(wc)} | {fmt_compact(su)}",
        )
        st.caption(range_str)

st.space("medium")

# ── Unit Economics + ISBL/OSBL row ───────────────────────────────────────────
section_header("Unit economics & cost structure", "#e6a817")
cols_ue = st.columns(len(active))
for col, (name, d) in zip(cols_ue, active.items()):
    tic = safe_val(d, "Total Investment")
    capex = safe_val(d, "Project CAPEX")
    capacity = safe_val(d, "Capacity")
    unit = d.get("Unit", "unit")
    isbl_pct = safe_val(d, "ISBL Contribution (%)", 100.0)
    osbl_pct = 100.0 - isbl_pct

    with col:
        # Unit economics
        if capacity > 0:
            tic_per_unit = tic / capacity
            capex_per_unit = capex / capacity
            st.metric(
                f"TIC per {unit}/yr",
                f"${tic_per_unit:,.2f}",
                border=True,
            )
            st.caption(f"CAPEX: ${capex_per_unit:,.2f} / {unit}/yr")
        else:
            st.metric(f"TIC per {unit}/yr", "—", border=True)

        # ISBL / OSBL split
        fig_isbl = go.Figure(go.Pie(
            labels=["ISBL", "OSBL"],
            values=[isbl_pct, osbl_pct],
            hole=0.6,
            textinfo="label+percent",
            textfont=dict(size=11, color="#c9d1d9"),
            marker=dict(colors=[cmap[name], "#21262d"], line=dict(color="#0d1117", width=2)),
            hoverinfo="label+percent",
        ))
        fig_isbl.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=5, r=5, t=5, b=5), height=130,
            showlegend=False,
            annotations=[dict(
                text=f"{isbl_pct:.0f}%<br>ISBL",
                x=0.5, y=0.5, font=dict(size=12, color="#8b949e"),
                showarrow=False,
            )],
        )
        st.plotly_chart(fig_isbl, use_container_width=True)

st.space("medium")

# ── TIC Accuracy — visual range chart ────────────────────────────────────────
has_bounds = any(
    d.get("TIC Lower Pct") is not None and d.get("TIC Upper Pct") is not None
    for d in active.values()
)
if has_bounds:
    section_header("TIC accuracy range", "#e6a817")
    fig_range = go.Figure()
    for name in selected:
        d = scenarios[name]
        tic = safe_val(d, "Total Investment")
        lo_pct = d.get("TIC Lower Pct")
        hi_pct = d.get("TIC Upper Pct")
        if lo_pct is not None and hi_pct is not None and tic > 0:
            lo_val = tic * (1 + lo_pct / 100.0)
            hi_val = tic * (1 + hi_pct / 100.0)
            fig_range.add_trace(go.Bar(
                name=name, x=[name], y=[tic],
                text=[fmt(tic)], textposition="inside",
                textfont=dict(family="DM Mono", size=12, color="white"),
                marker=dict(color=cmap[name], line_width=0),
                error_y=dict(
                    type="data", symmetric=False,
                    array=[hi_val - tic], arrayminus=[tic - lo_val],
                    color="#8b949e", thickness=2, width=8,
                ),
            ))
    fig_range.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k != "yaxis"},
        height=280, showlegend=False,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f",
                   tickfont=dict(family="DM Mono", size=11)),
    )
    st.plotly_chart(fig_range, use_container_width=True)
    st.space("medium")

# ── Charts — TIC composition + CAPEX components ─────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    section_header("TIC composition by scenario", "#e6a817")
    stack_keys = [
        ("CAPEX", "Project CAPEX"), ("Working Capital", "Working Capital"),
        ("Startup", "Startup Costs"), ("Additional", "Additional Costs"),
    ]
    stack_colors = ["#e6a817", "#3fb950", "#58a6ff", "#f78166"]
    fig_stack = go.Figure()
    for (lbl, key), clr in zip(stack_keys, stack_colors):
        fig_stack.add_trace(go.Bar(
            name=lbl, x=list(active.keys()),
            y=[safe_val(d, key) for d in active.values()],
            text=[fmt(safe_val(d, key)) for d in active.values()],
            textposition="inside",
            textfont=dict(family="DM Mono", size=12, color="white"),
            marker=dict(color=clr, line_width=0),
        ))
    fig_stack.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=320)
    st.plotly_chart(fig_stack, use_container_width=True)

with col_r:
    section_header("CAPEX components — all scenarios", "#e6a817")
    capex_items = [
        ("Equipment", "Total Equipment Costs"), ("Installation", "Total Installation Costs"),
        ("Indirect Field", "Total Indirect Field Costs"), ("Non-Field", "Total Non-Field Costs"),
    ]
    fig_capex = go.Figure()
    for name in selected:
        d = scenarios[name]
        fig_capex.add_trace(go.Bar(
            name=name,
            x=[lbl for lbl, _ in capex_items],
            y=[safe_val(d, key) for _, key in capex_items],
            text=[fmt(safe_val(d, key)) for _, key in capex_items],
            textposition="outside",
            textfont=dict(family="DM Mono", size=10, color="#8b949e"),
            marker=dict(color=cmap[name], line_width=0, opacity=0.85),
        ))
    fig_capex.update_layout(**PLOTLY_LAYOUT, barmode="group", height=320)
    st.plotly_chart(fig_capex, use_container_width=True)

# ── CAPEX Waterfall ───────────────────────────────────────────────────────────
section_header("CAPEX build-up", "#e6a817")
wf_scenario = st.selectbox("Select scenario for build-up chart", selected, key="wf_sel",
                           label_visibility="collapsed")
d0 = scenarios[wf_scenario]
c0 = cmap[wf_scenario]

unscheduled = safe_val(d0, "Total Equipment Costs") - safe_val(d0, "Base Equipment Costs")
isbl_val = safe_val(d0, "Project Costs ISBL+OSBL")
cont_val = isbl_val * safe_val(d0, "Contingency Pct", 0)
tuf = safe_val(d0, "Time Update Factor", 1.0)
lf = safe_val(d0, "Location Factor", 1.0)
tl_adj = isbl_val * (1 + safe_val(d0, "Contingency Pct", 0)) * (tuf * lf - 1)

wf_x = [
    "Equip. Acq.", "Spare Parts", "Setting", "Unscheduled",
    "Piping", "Civil", "Steel", "Instruments", "Electrical", "Insulation", "Paint",
    "Field Office", "Const. Ind.",
    "Freight", "Tax/Permits", "Engineering", "GA Oh.", "Contract",
    "Contingency", "Time/Loc.", "CAPEX",
]
wf_y = [safe_val(d0, k) for k in ["Equipment Acquisition", "Spare Parts", "Equipment Setting"]]
wf_y += [unscheduled]
wf_y += [safe_val(d0, k) for k in [
    "Piping", "Civil", "Steel", "Instrumentals", "Electrical", "Insulation", "Paint",
    "Field Office Staff", "Construction Indirects",
    "Freight", "Taxes and Permits", "Engineering and HO", "GA Overheads", "Contract Fee",
]]
wf_y += [cont_val, tl_adj, safe_val(d0, "Project CAPEX")]

fig_wf = go.Figure(go.Waterfall(
    orientation="v",
    measure=["relative"] * 20 + ["total"],
    x=wf_x, y=wf_y,
    text=[fmt(v) for v in wf_y],
    textposition="outside",
    textfont=dict(family="DM Mono", size=10, color="#8b949e"),
    connector=dict(line=dict(color="#21262d", width=1)),
    increasing=dict(marker=dict(color="#3fb950", line_width=0)),
    decreasing=dict(marker=dict(color="#f85149", line_width=0)),
    totals=dict(marker=dict(color=c0, line_width=0)),
))
fig_wf.update_layout(
    **{k: v for k, v in PLOTLY_LAYOUT.items() if k != "xaxis"},
    height=360, showlegend=False,
    xaxis=dict(tickfont=dict(family="DM Sans", size=10, color="#c9d1d9"), tickangle=-30),
)
st.plotly_chart(fig_wf, use_container_width=True)

# ── Detailed Breakdown Table ──────────────────────────────────────────────────
section_header("Detailed breakdown", "#e6a817")

ROWS = [
    ("H", "EQUIPMENT COSTS", None),
    ("I", "Equipment Acquisition", "Equipment Acquisition"),
    ("I", "Spare Parts", "Spare Parts"),
    ("I", "Equipment Setting", "Equipment Setting"),
    ("S", "Base Equipment Costs", "Base Equipment Costs"),
    ("I", "Unscheduled Equipment", "_unscheduled"),
    ("S", "Total Equipment Costs", "Total Equipment Costs"),
    ("H", "INSTALLATION COSTS", None),
    ("I", "Piping", "Piping"), ("I", "Civil", "Civil"), ("I", "Steel", "Steel"),
    ("I", "Instrumentals", "Instrumentals"), ("I", "Electrical", "Electrical"),
    ("I", "Insulation", "Insulation"), ("I", "Paint", "Paint"),
    ("S", "Total Installation Costs", "Total Installation Costs"),
    ("H", "INDIRECT & NON-FIELD", None),
    ("I", "Field Office Staff", "Field Office Staff"),
    ("I", "Construction Indirects", "Construction Indirects"),
    ("I", "Freight", "Freight"), ("I", "Taxes & Permits", "Taxes and Permits"),
    ("I", "Engineering & HO", "Engineering and HO"),
    ("I", "GA Overheads", "GA Overheads"), ("I", "Contract Fee", "Contract Fee"),
    ("H", "CAPEX SUMMARY", None),
    ("S", "Project Costs ISBL+OSBL", "Project Costs ISBL+OSBL"),
    ("I", "ISBL Contribution", "ISBL Contribution (%)"),
    ("I", "Contingency", "Contingency Pct"),
    ("I", "Time Update Factor", "Time Update Factor"),
    ("I", "Location Factor", "Location Factor"),
    ("T", "PROJECT CAPEX", "Project CAPEX"),
    ("H", "TOTAL INVESTMENT", None),
    ("I", "Working Capital", "Working Capital"),
    ("I", "Startup Costs", "Startup Costs"),
    ("I", "Additional Costs", "Additional Costs"),
    ("T", "TOTAL INVESTMENT COST", "Total Investment"),
]

def _cell(rtype, key, d):
    if key is None: return ""
    if key == "_unscheduled":
        return fmtd(safe_val(d, "Total Equipment Costs") - safe_val(d, "Base Equipment Costs"))
    v = d.get(key)
    if v is None: return "—"
    if key == "Contingency Pct": return fpct(v)
    if key == "ISBL Contribution (%)": return f"{v:.1f}%"
    if key in ("Time Update Factor", "Location Factor"): return f"{v:.4f}"
    return fmtd(v)

breakdown_table(ROWS, selected, scenarios, cmap, _cell, accent="#e6a817")
