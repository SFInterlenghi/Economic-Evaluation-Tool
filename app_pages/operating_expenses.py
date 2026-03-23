"""ISI-Tool — Operating Expenses dashboard."""
import streamlit as st
import math
import plotly.graph_objects as go
from utils.constants import safe_val, fmt_compact, smart_fmt, PLOTLY_LAYOUT
from utils.ui import (
    inject_css, page_header, section_header, kpi_card,
    scenario_banner, breakdown_table, require_scenarios, scenario_filter,
)

inject_css()

# ── Data guard ────────────────────────────────────────────────────────────────
scenarios, names, cmap = require_scenarios("Operating Expenses")

def fmt(v):  return f"${v:,.0f}"
def fmtd(v): return f"${v:,.2f}"
def fpct(v): return f"{v * 100:.4f}%"
def tvc(d):  return safe_val(d, "Total Raw Material Cost") + safe_val(d, "Total Chemical Inputs Utilities") - safe_val(d, "Total Revenue")

# ── Header ────────────────────────────────────────────────────────────────────
page_header("Operating Expenses", "Annual OPEX breakdown — scenario comparison")
selected = scenario_filter(names)
active = {n: scenarios[n] for n in selected}

# ── Scenario Overview ─────────────────────────────────────────────────────────
section_header("Scenario overview", "#3fb950")
cols_banner = st.columns(len(active))
for col, (name, d) in zip(cols_banner, active.items()):
    with col:
        scenario_banner(name, d, cmap[name])

st.space("medium")

# ── KPI Cards — with variable/fixed ratio ────────────────────────────────────
section_header("Total OPEX per scenario", "#3fb950")
cols_kpi = st.columns(len(active))
for col, (name, d) in zip(cols_kpi, active.items()):
    opex = safe_val(d, "Total OPEX")
    tvc_v = tvc(d)
    fc = safe_val(d, "Total Fixed Costs")

    # Variable / Fixed ratio
    if opex > 0:
        var_pct = tvc_v / opex * 100
        fix_pct = 100 - var_pct
        ratio_str = f"{var_pct:.0f}% variable / {fix_pct:.0f}% fixed"
    else:
        ratio_str = "—"

    with col:
        kpi_card(
            f"Total Annual OPEX — {name}", fmt(opex), cmap[name],
            "Variable / Fixed",
            f"{fmt_compact(tvc_v)} | {fmt_compact(fc)}",
        )
        st.caption(ratio_str)

st.space("medium")

# ── Unit Economics row ───────────────────────────────────────────────────────
section_header("OPEX per unit product", "#3fb950")
cols_ue = st.columns(len(active))
for col, (name, d) in zip(cols_ue, active.items()):
    opex = safe_val(d, "Total OPEX")
    capacity = safe_val(d, "Capacity")
    unit = d.get("Unit", "unit")
    tvc_v = tvc(d)
    fc = safe_val(d, "Total Fixed Costs")

    with col:
        if capacity > 0:
            opex_per_unit = opex / capacity
            var_per_unit = tvc_v / capacity
            fix_per_unit = fc / capacity
            st.metric(
                f"OPEX per {unit}",
                f"${opex_per_unit:,.2f}",
                border=True,
            )
            st.caption(f"Variable: ${var_per_unit:,.2f} / {unit}  —  Fixed: ${fix_per_unit:,.2f} / {unit}")
        else:
            st.metric(f"OPEX per {unit}", "—", border=True)

st.space("medium")

# ── Charts ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    section_header("OPEX composition by scenario", "#3fb950")
    opex_cats = [
        ("Variable Costs", lambda d: tvc(d)),
        ("Labor", lambda d: safe_val(d, "Total Labor Costs")),
        ("Supply & Maint.", lambda d: safe_val(d, "Supply Maint Costs")),
        ("AFC", lambda d: safe_val(d, "AFC Pre Patents")),
        ("Indirect Fixed", lambda d: safe_val(d, "Indirect Fixed Costs")),
    ]
    cat_colors = ["#58a6ff", "#3fb950", "#e6a817", "#f78166", "#bc8cff"]
    fig_stack = go.Figure()
    for (lbl, fn), clr in zip(opex_cats, cat_colors):
        fig_stack.add_trace(go.Bar(
            name=lbl, x=list(active.keys()),
            y=[fn(d) for d in active.values()],
            text=[fmt(fn(d)) for d in active.values()],
            textposition="inside",
            textfont=dict(family="DM Mono", size=12, color="white"),
            marker=dict(color=clr, line_width=0),
        ))
    fig_stack.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=320)
    st.plotly_chart(fig_stack, use_container_width=True)

with col_r:
    section_header("Variable cost components", "#3fb950")
    fig_vc = go.Figure()
    for name in selected:
        d = scenarios[name]
        fig_vc.add_trace(go.Bar(
            name=name,
            x=["Raw Materials", "Chem. & Utilities", "Credits (-)"],
            y=[safe_val(d, "Total Raw Material Cost"),
               safe_val(d, "Total Chemical Inputs Utilities"),
               -safe_val(d, "Total Revenue")],
            text=[fmt(safe_val(d, "Total Raw Material Cost")),
                  fmt(safe_val(d, "Total Chemical Inputs Utilities")),
                  fmt(safe_val(d, "Total Revenue"))],
            textposition="outside",
            textfont=dict(family="DM Mono", size=11, color="#8b949e"),
            marker=dict(color=cmap[name], line_width=0, opacity=0.85),
        ))
    fig_vc.update_layout(**PLOTLY_LAYOUT, barmode="group", height=320)
    st.plotly_chart(fig_vc, use_container_width=True)

# ── Labor Detail — expandable per scenario ───────────────────────────────────
section_header("Labor cost detail", "#3fb950")

for name in selected:
    d = scenarios[name]
    total_labor = safe_val(d, "Total Labor Costs")
    olc = safe_val(d, "OLC")
    n_ops = d.get("Num Operators", "—")
    n_sups = d.get("Num Supervisors", "—")
    op_sal = d.get("Operator Salary", 0)
    sup_sal = d.get("Supervisor Salary", 0)
    sal_charges = d.get("Salary Charges", 0)
    op_team = d.get("Operating Team Factor", "—")
    lab_pct = d.get("Lab Charges Pct")
    off_pct = d.get("Office Labor Pct")
    whrs = safe_val(d, "Working Hours per Year", 8000)
    daily_h = d.get("Plant Daily Hours", "—")
    weekly_d = d.get("Weekly Op Days", "—")

    with st.expander(
        f"{name} — Labor: {fmt(total_labor)}  (OLC: {fmt(olc)})",
        icon=":material/groups:",
    ):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Workforce**")
            st.caption(f"Operators per shift: **{n_ops}**")
            st.caption(f"Supervisors per shift: **{n_sups}**")
            st.caption(f"Operating team factor: **{op_team}**")
            st.caption(f"Salary charges multiplier: **{sal_charges}**")
        with c2:
            st.markdown("**Salaries (USD/month)**")
            st.caption(f"Operator: **${op_sal:,.2f}**" if isinstance(op_sal, (int, float)) else "Operator: —")
            st.caption(f"Supervisor: **${sup_sal:,.2f}**" if isinstance(sup_sal, (int, float)) else "Supervisor: —")
        with c3:
            st.markdown("**Operating schedule**")
            st.caption(f"Working hours/year: **{whrs:,.0f} h**")
            st.caption(f"Plant daily hours: **{daily_h}** h/day")
            st.caption(f"Weekly operation days: **{weekly_d}** days/week")

        st.space("small")
        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("OLC", fmt(olc), border=True)
        with c5:
            lab_str = f"{lab_pct * 100:.2f}%" if lab_pct is not None else "—"
            st.metric("Lab charges", lab_str, border=True)
        with c6:
            off_str = f"{off_pct * 100:.2f}%" if off_pct is not None else "—"
            st.metric("Office labor", off_str, border=True)

st.space("medium")

# ── Sankey Diagram ────────────────────────────────────────────────────────────
section_header("Cost flow — Sankey diagram", "#3fb950")
sk_scenario = st.selectbox("Select scenario", selected, key="opex_sk_sel",
                           label_visibility="collapsed")
ds = scenarios[sk_scenario]

node_labels = ["OPEX", "Variable", "Fixed"]
sources, targets, values, link_labels = [], [], [], []

tvc_v = tvc(ds)
fc_v = safe_val(ds, "Total Fixed Costs")

if tvc_v > 0:
    sources.append(0); targets.append(1); values.append(tvc_v); link_labels.append("Variable")
if fc_v > 0:
    sources.append(0); targets.append(2); values.append(fc_v); link_labels.append("Fixed")

rm_v = safe_val(ds, "Total Raw Material Cost")
cu_v = safe_val(ds, "Total Chemical Inputs Utilities")
rev_v = safe_val(ds, "Total Revenue")

node_labels += ["Raw Materials", "Chem & Util", "Credits"]

if rm_v > 0:
    sources.append(1); targets.append(3); values.append(rm_v); link_labels.append("Raw Materials")
if cu_v > 0:
    sources.append(1); targets.append(4); values.append(cu_v); link_labels.append("Chem & Util")
if rev_v > 0:
    sources.append(1); targets.append(5); values.append(rev_v); link_labels.append("Credits")

def item_cost(r):
    return float(r.get("Price", 0)) * float(r.get("Rate", 0)) * safe_val(ds, "Working Hours per Year", 8000)

# RM items
raw_items = ds.get("Raw Materials", []) or []
rm_node_idx = {}
for r in raw_items:
    n = r.get("Name", "")
    if n and item_cost(r) > 0:
        node_labels.append(n)
        rm_node_idx[n] = len(node_labels) - 1
        sources.append(3); targets.append(rm_node_idx[n]); values.append(item_cost(r))
        link_labels.append(n)

# Chem items
chem_items = ds.get("Chemical Inputs and Utilities", []) or []
cu_node_idx = {}
for r in chem_items:
    n = r.get("Name", "")
    if n and item_cost(r) > 0:
        node_labels.append(n)
        cu_node_idx[n] = len(node_labels) - 1
        sources.append(4); targets.append(cu_node_idx[n]); values.append(item_cost(r))
        link_labels.append(n)

# Fixed cost components
fc_components = [
    (2, "Total Labor Costs", "Labor"),
    (2, "Supply Maint Costs", "Supply & Maint."),
    (2, "AFC Pre Patents", "AFC"),
    (2, "Indirect Fixed Costs", "Indirect Fixed"),
]
for src_idx, key, lbl in fc_components:
    v = safe_val(ds, key)
    if v > 0:
        node_labels.append(lbl)
        sources.append(2); targets.append(len(node_labels) - 1); values.append(v)
        link_labels.append(lbl)

# Node colors
node_colors = ["#e6a817", "#58a6ff", "#3fb950"]
node_colors += ["rgba(88,166,255,0.35)", "rgba(121,192,255,0.35)", "rgba(248,81,73,0.35)"]
node_colors += ["rgba(59,125,216,0.25)"] * len(rm_node_idx)
node_colors += ["rgba(46,160,67,0.25)"] * len(cu_node_idx)
fc_rgba = ["rgba(63,185,80,0.6)", "rgba(230,168,23,0.6)", "rgba(247,129,102,0.6)", "rgba(188,140,255,0.6)"]
n_fc_added = sum(1 for _, key, _ in fc_components if safe_val(ds, key) > 0)
node_colors += fc_rgba[:n_fc_added]

if values:
    fig_sankey = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18, thickness=20,
            line=dict(color="#21262d", width=0.5),
            label=node_labels, color=node_colors,
        ),
        link=dict(
            source=sources, target=targets, value=values,
            label=link_labels,
            color=["rgba(255,255,255,0.04)"] * len(sources),
        ),
    ))
    fig_sankey.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("yaxis", "xaxis")},
        height=480,
    )
    st.plotly_chart(fig_sankey, use_container_width=True)

# ── Detailed Breakdown Table ──────────────────────────────────────────────────
section_header("Detailed breakdown", "#3fb950")

ROWS = [
    ("H", "VARIABLE COSTS", None),
    ("I", "Raw Materials", "Total Raw Material Cost"),
    ("I", "Chemical Inputs & Utilities", "Total Chemical Inputs Utilities"),
    ("I", "Credits & Byproducts", "Total Revenue"),
    ("S", "Total Variable Costs", "_tvc"),
    ("H", "FIXED COSTS — LABOR", None),
    ("I", "OLC", "OLC"),
    ("I", "Lab Charges (%)", "Lab Charges Pct"),
    ("I", "Office Labor (%)", "Office Labor Pct"),
    ("S", "Total Labor Costs", "Total Labor Costs"),
    ("H", "SUPPLY & MAINTENANCE", None),
    ("I", "Maintenance & Repairs (%)", "Maint Pct"),
    ("I", "Operating Supplies (%)", "Op Sup Pct"),
    ("S", "Supply & Maintenance Costs", "Supply Maint Costs"),
    ("H", "ADDITIONAL FIXED COSTS (AFC)", None),
    ("I", "Admin Overhead (%)", "Admin Ov Pct"),
    ("I", "Manufacturing Overhead (%)", "Mfg Ov Pct"),
    ("I", "Taxes & Insurance (%)", "Taxes Ins Pct"),
    ("I", "Patents & Royalties (%)", "Patents Pct"),
    ("S", "AFC", "AFC Pre Patents"),
    ("T", "Direct Fixed Costs", "Direct Fixed Costs"),
    ("H", "INDIRECT FIXED COSTS", None),
    ("I", "Administrative Costs (%)", "Admin Costs Pct"),
    ("I", "Manufacturing Costs (%)", "Mfg Costs Pct"),
    ("I", "Distribution & Selling (%)", "Dist Sell Pct"),
    ("I", "Research & Development (%)", "R D Pct"),
    ("S", "Indirect Fixed Costs", "Indirect Fixed Costs"),
    ("H", "TOTALS", None),
    ("S", "Total Fixed Costs", "Total Fixed Costs"),
    ("T", "TOTAL OPEX", "Total OPEX"),
]

def _cell(rtype, key, d):
    if key is None: return ""
    if key == "_tvc": return fmtd(tvc(d))
    v = d.get(key)
    if v is None: return "—"
    if "Pct" in key: return fpct(v)
    return fmtd(v)

breakdown_table(ROWS, selected, scenarios, cmap, _cell, accent="#3fb950")
