import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Operating Expenses", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&family=Inter:wght@300;400;500&display=swap');
:root {
    --bg:#0d1117; --surface:#161b22; --border:#21262d;
    --accent:#3fb950; --muted:#8b949e;
    --text:#e6edf3; --text-dim:#c9d1d9;
}
html,body,[data-testid="stAppViewContainer"]{background-color:var(--bg)!important;color:var(--text)!important;}
[data-testid="stSidebar"]{background:var(--surface)!important;}
[data-testid="stHeader"]{background:transparent!important;}
h1,h2,h3{font-family:'Syne',sans-serif!important;color:var(--text)!important;}
p,span,div,td,th{font-family:'Inter',sans-serif!important;color:var(--text-dim)!important;}
.hero-title{font-family:'Syne',sans-serif;font-size:2.4rem;font-weight:800;color:var(--text);letter-spacing:-.03em;line-height:1.1;margin-bottom:.15rem;}
.hero-sub{font-family:'Inter',sans-serif;font-size:.9rem;font-weight:300;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;}
.kpi-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1.2rem 1.4rem;border-left:3px solid var(--accent);}
.kpi-label{font-family:'Inter',sans-serif;font-size:.72rem;font-weight:500;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:.4rem;}
.kpi-value{font-family:'DM Mono',monospace;font-size:1.55rem;font-weight:500;color:var(--text);line-height:1.1;}
.kpi-scenario{font-family:'Inter',sans-serif;font-size:.72rem;color:var(--muted);margin-top:.3rem;}
.kpi-sub{font-family:'DM Mono',monospace;font-size:.85rem;color:var(--muted);margin-top:.25rem;}
.section-hdr{font-family:'Syne',sans-serif;font-size:.7rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.15em;padding:.6rem 0 .3rem 0;border-bottom:1px solid var(--border);margin-bottom:.5rem;}
.divider{border:none;border-top:1px solid var(--border);margin:1.5rem 0;}
.scen-badge{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem;}
.scen-name{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:.5rem;}
.scen-tag{display:inline-block;font-family:'DM Mono',monospace;font-size:.7rem;padding:.15rem .5rem;border-radius:4px;margin:.15rem .1rem 0 0;}
</style>
""", unsafe_allow_html=True)

if "scenarios" not in st.session_state or not st.session_state.scenarios:
    st.markdown('<div class="hero-title">Operating Expenses</div>', unsafe_allow_html=True)
    st.info("No scenarios saved yet. Configure and save scenarios on the Input Data page first.")
    st.stop()

scenarios = st.session_state.scenarios
names     = list(scenarios.keys())
PALETTE   = ["#3fb950","#e6a817","#58a6ff","#f78166","#bc8cff","#79c0ff","#ffa657","#ff7b72"]
cmap      = {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(names)}

def _v(d, k, default=0.0):
    v = d.get(k, default)
    return v if isinstance(v, (int, float)) else default
def fmt(v):  return f"${v:,.0f}"
def fmtd(v): return f"${v:,.2f}"
def fpct(v): return f"{v*100:.4f}%"
def tvc(d):  return _v(d,"Total Raw Material Cost") + _v(d,"Total Chemical Inputs Utilities") - _v(d,"Total Revenue")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">Operating Expenses</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Annual OPEX breakdown — scenario comparison</div>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

if len(names) > 1:
    selected = st.multiselect("Scenarios", names, default=names, label_visibility="collapsed")
    if not selected: selected = names
else:
    selected = names

active = {n: scenarios[n] for n in selected}

# ── Scenario Summary Banner ───────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Scenario Overview</div>', unsafe_allow_html=True)
cols_banner = st.columns(len(active))
for col, (name, d) in zip(cols_banner, active.items()):
    clr  = cmap[name]
    prod = d.get("Product Name", "—")
    unit = d.get("Unit", "")
    cap  = d.get("Capacity", "—")
    trl  = d.get("TRL", "—")
    opex = _v(d, "Total OPEX")
    tvc_v= tvc(d)
    with col:
        st.markdown(f"""
        <div class="scen-badge" style="border-left:4px solid {clr}">
          <div class="scen-name" style="color:{clr}">{name}</div>
          <div style="font-family:'Inter';font-size:.85rem;color:var(--text);margin-bottom:.3rem">{prod}</div>
          <div style="font-family:'DM Mono';font-size:.8rem;color:var(--text-dim);margin-bottom:.4rem">{cap} {unit}/yr</div>
          <span class="scen-tag" style="background:rgba({int(clr[1:3],16)},{int(clr[3:5],16)},{int(clr[5:7],16)},0.15);color:{clr};border:1px solid {clr}33">{trl}</span>
          <div style="font-family:'DM Mono';font-size:.95rem;color:var(--text);margin-top:.6rem;font-weight:500">OPEX: {fmt(opex)}</div>
          <div style="font-family:'Inter';font-size:.72rem;color:var(--muted)">Variable: {fmt(tvc_v)}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Total OPEX per Scenario</div>', unsafe_allow_html=True)
cols_kpi = st.columns(len(active))
for col, (name, d) in zip(cols_kpi, active.items()):
    opex  = _v(d, "Total OPEX")
    tvc_v = tvc(d)
    fc    = _v(d, "Total Fixed Costs")
    with col:
        st.markdown(f"""<div class="kpi-card" style="border-left-color:{cmap[name]}">
            <div class="kpi-label">Total Annual OPEX</div>
            <div class="kpi-value">{fmt(opex)}</div>
            <div class="kpi-scenario" style="color:{cmap[name]};font-weight:500">{name}</div>
            <div class="kpi-sub">{fmt(tvc_v)} variable &nbsp;|&nbsp; {fmt(fc)} fixed</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── OPEX composition + variable components ────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.markdown('<div class="section-hdr">OPEX Composition by Scenario</div>', unsafe_allow_html=True)
    opex_cats = [
        ("Variable Costs",  lambda d: tvc(d)),
        ("Labor",           lambda d: _v(d,"Total Labor Costs")),
        ("Supply & Maint.", lambda d: _v(d,"Supply Maint Costs")),
        ("AFC",             lambda d: _v(d,"AFC Pre Patents")),
        ("Indirect Fixed",  lambda d: _v(d,"Indirect Fixed Costs")),
    ]
    cat_colors = ["#58a6ff","#3fb950","#e6a817","#f78166","#bc8cff"]
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
    fig_stack.update_layout(
        barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8b949e", size=13),
        legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        margin=dict(l=0, r=0, t=40, b=0), height=320,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=11)),
        xaxis=dict(tickfont=dict(family="Syne", size=13, color="#e6edf3")),
    )
    st.plotly_chart(fig_stack, use_container_width=True)

with col_r:
    st.markdown('<div class="section-hdr">Variable Cost Components</div>', unsafe_allow_html=True)
    fig_vc = go.Figure()
    for name in selected:
        d = scenarios[name]
        fig_vc.add_trace(go.Bar(
            name=name,
            x=["Raw Materials","Chem. & Utilities","Credits (-)"],
            y=[_v(d,"Total Raw Material Cost"), _v(d,"Total Chemical Inputs Utilities"), -_v(d,"Total Revenue")],
            text=[fmt(_v(d,"Total Raw Material Cost")), fmt(_v(d,"Total Chemical Inputs Utilities")), fmt(_v(d,"Total Revenue"))],
            textposition="outside",
            textfont=dict(family="DM Mono", size=11, color="#8b949e"),
            marker=dict(color=cmap[name], line_width=0, opacity=0.85),
        ))
    fig_vc.update_layout(
        barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8b949e", size=13),
        legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        margin=dict(l=0, r=0, t=40, b=0), height=320,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=11)),
        xaxis=dict(tickfont=dict(family="Inter", size=12, color="#c9d1d9")),
    )
    st.plotly_chart(fig_vc, use_container_width=True)

# ── Fixed cost donut with selector + key rates ────────────────────────────────
col_don, col_kpis = st.columns([1, 2])

with col_don:
    st.markdown('<div class="section-hdr">Fixed Cost Mix</div>', unsafe_allow_html=True)
    pie_scenario = st.selectbox("Select scenario", selected, key="pie_sel")
    dp = scenarios[pie_scenario]
    cp = cmap[pie_scenario]
    fc_labels = ["Labor","Supply & Maint.","AFC","Indirect Fixed"]
    fc_vals = [_v(dp,"Total Labor Costs"), _v(dp,"Supply Maint Costs"),
               _v(dp,"AFC Pre Patents"),   _v(dp,"Indirect Fixed Costs")]
    fig_pie = go.Figure(go.Pie(
        labels=fc_labels, values=fc_vals, hole=0.55,
        textfont=dict(family="DM Mono", size=12),
        marker=dict(colors=["#3fb950","#e6a817","#58a6ff","#bc8cff"], line=dict(color="#0d1117", width=2)),
        textinfo="percent+label",
    ))
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#8b949e", size=12),
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0), height=270,
        annotations=[dict(text=fmt(_v(dp,"Total Fixed Costs")), x=0.5, y=0.5,
                          font=dict(family="DM Mono", size=13, color="#e6edf3"), showarrow=False)],
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_kpis:
    st.markdown('<div class="section-hdr">Key Rates & Percentages</div>', unsafe_allow_html=True)
    for name in selected:
        d     = scenarios[name]
        opex  = _v(d,"Total OPEX")
        capex = _v(d,"Project CAPEX")
        fc    = _v(d,"Total Fixed Costs")
        vc    = tvc(d)
        st.markdown(f"""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;
                    padding:.8rem 1rem;margin-bottom:.6rem;border-left:3px solid {cmap[name]}">
          <div class="kpi-scenario" style="color:{cmap[name]};font-weight:500;margin-bottom:.4rem">{name}</div>
          <div style="display:flex;gap:2rem;flex-wrap:wrap">
            <div><div class="kpi-label">Fixed / OPEX</div>
              <div style="font-family:'DM Mono';font-size:1rem;color:var(--text)">{fc/opex*100:.1f}%</div></div>
            <div><div class="kpi-label">Variable / OPEX</div>
              <div style="font-family:'DM Mono';font-size:1rem;color:var(--text)">{vc/opex*100:.1f}%</div></div>
            <div><div class="kpi-label">OPEX / CAPEX</div>
              <div style="font-family:'DM Mono';font-size:1rem;color:var(--text)">{opex/capex*100:.1f}%</div></div>
            <div><div class="kpi-label">CAPEX</div>
              <div style="font-family:'DM Mono';font-size:1rem;color:var(--text)">{fmt(capex)}</div></div>
          </div>
        </div>""", unsafe_allow_html=True)

# ── Sankey: Variable Cost Breakdown ───────────────────────────────────────────
st.markdown('<div class="section-hdr">Variable Cost Flow — Sankey</div>', unsafe_allow_html=True)
sk_scenario = st.selectbox("Select scenario for Sankey", selected, key="sk_sel")
ds = scenarios[sk_scenario]

total_opex_v = _v(ds, "Total OPEX")
tvc_v        = tvc(ds)
fc_v         = _v(ds, "Total Fixed Costs")
rm_v         = _v(ds, "Total Raw Material Cost")
cu_v         = _v(ds, "Total Chemical Inputs Utilities")
rev_v        = _v(ds, "Total Revenue")

# Build nodes and links
# Nodes: OPEX | Variable | Fixed | Raw Materials | Chem & Util | Credits | (individual items)
raw_items  = [r for r in (ds.get("Raw Materials") or [])  if r.get("Name") and _v(r,"Rate",0)*_v(r,"Price",0) > 0]
chem_items = [r for r in (ds.get("Chemical Inputs and Utilities") or []) if r.get("Name") and _v(r,"Rate",0)*_v(r,"Price",0) > 0]
wh = _v(ds, "Working Hours per Year", 8000)

def item_cost(r):
    return _v(r,"Rate",0) * _v(r,"Price",0) * wh

node_labels = ["OPEX", "Variable Costs", "Fixed Costs",
               "Raw Materials", "Chem. & Utilities", "Credits (revenue)"]
n_base = len(node_labels)

# Add individual raw material nodes
rm_node_idx = {}
for r in raw_items:
    rm_node_idx[r["Name"]] = len(node_labels)
    node_labels.append(r["Name"])

# Add individual chem/util nodes
cu_node_idx = {}
for r in chem_items:
    cu_node_idx[r["Name"]] = len(node_labels)
    node_labels.append(r["Name"])

# Build links
sources, targets, values, link_labels = [], [], [], []

# OPEX -> Variable & Fixed
sources += [0, 0]
targets += [1, 2]
values  += [tvc_v, fc_v]
link_labels += ["Variable Costs", "Fixed Costs"]

# Variable -> RM, Chem, Credits
if rm_v  > 0: sources.append(1); targets.append(3); values.append(rm_v);  link_labels.append("Raw Materials")
if cu_v  > 0: sources.append(1); targets.append(4); values.append(cu_v);  link_labels.append("Chem & Util")
if rev_v > 0: sources.append(1); targets.append(5); values.append(rev_v); link_labels.append("Credits")

# RM -> individual items
for r in raw_items:
    c = item_cost(r)
    if c > 0:
        sources.append(3); targets.append(rm_node_idx[r["Name"]]); values.append(c)
        link_labels.append(r["Name"])

# Chem -> individual items
for r in chem_items:
    c = item_cost(r)
    if c > 0:
        sources.append(4); targets.append(cu_node_idx[r["Name"]]); values.append(c)
        link_labels.append(r["Name"])

# Fixed -> components
fc_components = [
    (2, "Total Labor Costs",     "Labor"),
    (2, "Supply Maint Costs",    "Supply & Maint."),
    (2, "AFC Pre Patents",       "AFC"),
    (2, "Indirect Fixed Costs",  "Indirect Fixed"),
]
fc_node_start = len(node_labels)
for src_idx, key, lbl in fc_components:
    v = _v(ds, key)
    if v > 0:
        node_labels.append(lbl)
        sources.append(2); targets.append(len(node_labels)-1); values.append(v)
        link_labels.append(lbl)

# Node colors
node_colors = ["#e6a817","#58a6ff","#3fb950"] + ["#58a6ff66","#79c0ff66","#f8514966"]
node_colors += ["#3b7dd833"] * len(rm_node_idx)
node_colors += ["#2ea04366"] * len(cu_node_idx)
fc_colors = ["#3fb950","#e6a817","#f78166","#bc8cff"]
for clr in fc_colors[:len(fc_components)]:
    node_colors.append(clr + "99")

fig_sankey = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        pad=18, thickness=20,
        line=dict(color="#21262d", width=0.5),
        label=node_labels,
        color=node_colors,
        hoverlabel=dict(font=dict(family="DM Mono", size=12)),
    ),
    link=dict(
        source=sources, target=targets, value=values,
        label=link_labels,
        color=["rgba(255,255,255,0.04)"] * len(sources),
        hoverlabel=dict(font=dict(family="DM Mono", size=11)),
    ),
))
fig_sankey.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#c9d1d9", size=12),
    margin=dict(l=0, r=0, t=10, b=0),
    height=480,
)
st.plotly_chart(fig_sankey, use_container_width=True)

# ── Detailed breakdown table ───────────────────────────────────────────────────
with st.expander("Full Detailed Breakdown", expanded=False):
    ROWS = [
        ("H", "VARIABLE COSTS",                    None),
        ("I", "    Raw Materials",                  "Total Raw Material Cost"),
        ("I", "    Chemical Inputs & Utilities",    "Total Chemical Inputs Utilities"),
        ("I", "    Credits & Byproducts (-)",       "Total Revenue"),
        ("S", "  > Total Variable Costs",           "_tvc"),
        ("H", "FIXED COSTS — LABOR",               None),
        ("I", "    OLC",                            "OLC"),
        ("I", "    Lab Charges (%)",                "Lab Charges Pct"),
        ("I", "    Office Labor (%)",               "Office Labor Pct"),
        ("S", "  > Total Labor Costs",              "Total Labor Costs"),
        ("H", "SUPPLY & MAINTENANCE",              None),
        ("I", "    Maintenance & Repairs (%)",      "Maint Pct"),
        ("I", "    Operating Supplies (%)",         "Op Sup Pct"),
        ("S", "  > Supply & Maintenance Costs",     "Supply Maint Costs"),
        ("H", "ADDITIONAL FIXED COSTS (AFC)",      None),
        ("I", "    Admin Overhead (%)",             "Admin Ov Pct"),
        ("I", "    Manufacturing Overhead (%)",     "Mfg Ov Pct"),
        ("I", "    Taxes & Insurance (%)",          "Taxes Ins Pct"),
        ("I", "    Patents & Royalties (%)",        "Patents Pct"),
        ("S", "  > AFC",                            "AFC Pre Patents"),
        ("T", "  = Direct Fixed Costs",             "Direct Fixed Costs"),
        ("H", "INDIRECT FIXED COSTS",              None),
        ("I", "    Administrative Costs (%)",       "Admin Costs Pct"),
        ("I", "    Manufacturing Costs (%)",        "Mfg Costs Pct"),
        ("I", "    Distribution & Selling (%)",     "Dist Sell Pct"),
        ("I", "    Research & Development (%)",     "R D Pct"),
        ("S", "  > Indirect Fixed Costs",           "Indirect Fixed Costs"),
        ("H", "TOTALS",                            None),
        ("S", "  > Total Fixed Costs",             "Total Fixed Costs"),
        ("T", "  = TOTAL OPEX",                    "Total OPEX"),
    ]

    def _cell(rtype, key, d):
        if key is None: return ""
        if key == "_tvc": return fmtd(tvc(d))
        v = d.get(key)
        if v is None: return "—"
        if "Pct" in key: return fpct(v)
        return fmtd(v)

    tbl = {"Line Item": [r[1] for r in ROWS]}
    for name in selected:
        tbl[name] = [_cell(r[0], r[2], scenarios[name]) for r in ROWS]

    st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True,
        column_config={"Line Item": st.column_config.TextColumn("Line Item", width="large")}
        | {n: st.column_config.TextColumn(n, width="medium") for n in selected})
