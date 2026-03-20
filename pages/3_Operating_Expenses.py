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
.hero-title{font-family:'Syne',sans-serif;font-size:2.4rem;font-weight:800;color:var(--text);letter-spacing:-0.03em;line-height:1.1;margin-bottom:.15rem;}
.hero-sub{font-family:'Inter',sans-serif;font-size:.9rem;font-weight:300;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;}
.kpi-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:1.2rem 1.4rem;border-left:3px solid var(--accent);}
.kpi-label{font-family:'Inter',sans-serif;font-size:.72rem;font-weight:500;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:.4rem;}
.kpi-value{font-family:'DM Mono',monospace;font-size:1.55rem;font-weight:500;color:var(--text);line-height:1.1;}
.kpi-scenario{font-family:'Inter',sans-serif;font-size:.72rem;color:var(--muted);margin-top:.3rem;}
.kpi-sub{font-family:'DM Mono',monospace;font-size:.85rem;color:var(--muted);margin-top:.25rem;}
.section-hdr{font-family:'Syne',sans-serif;font-size:.7rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.15em;padding:.6rem 0 .3rem 0;border-bottom:1px solid var(--border);margin-bottom:.5rem;}
.divider{border:none;border-top:1px solid var(--border);margin:1.5rem 0;}
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

# Header
st.markdown('<div class="hero-title">Operating Expenses</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Annual OPEX breakdown — scenario comparison</div>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

if len(names) > 1:
    selected = st.multiselect("Scenarios", names, default=names, label_visibility="collapsed")
    if not selected: selected = names
else:
    selected = names

active = {n: scenarios[n] for n in selected}

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Total OPEX per Scenario</div>', unsafe_allow_html=True)
cols = st.columns(len(active))
for col, (name, d) in zip(cols, active.items()):
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

# ── Charts ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.markdown('<div class="section-hdr">OPEX Composition by Scenario</div>', unsafe_allow_html=True)
    opex_cats = [
        ("Variable Costs",      lambda d: tvc(d)),
        ("Labor",               lambda d: _v(d,"Total Labor Costs")),
        ("Supply & Maint.",     lambda d: _v(d,"Supply Maint Costs")),
        ("Add. Fixed (AFC)",    lambda d: _v(d,"AFC Pre Patents")),
        ("Indirect Fixed",      lambda d: _v(d,"Indirect Fixed Costs")),
    ]
    cat_colors = ["#58a6ff","#3fb950","#e6a817","#f78166","#bc8cff"]
    fig_stack = go.Figure()
    for (lbl, fn), clr in zip(opex_cats, cat_colors):
        fig_stack.add_trace(go.Bar(
            name=lbl, x=list(active.keys()),
            y=[fn(d) for d in active.values()],
            text=[fmt(fn(d)) for d in active.values()],
            textposition="inside",
            textfont=dict(family="DM Mono", size=10, color="white"),
            marker=dict(color=clr, line_width=0),
        ))
    fig_stack.update_layout(
        barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8b949e"),
        legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=0, r=0, t=40, b=0), height=300,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=9)),
        xaxis=dict(tickfont=dict(family="Syne", size=11, color="#e6edf3")),
    )
    st.plotly_chart(fig_stack, use_container_width=True)

with col_r:
    st.markdown('<div class="section-hdr">Variable Cost Components</div>', unsafe_allow_html=True)
    vc_cats = [
        ("Raw Materials",    lambda d: _v(d,"Total Raw Material Cost")),
        ("Chem. & Utilities",lambda d: _v(d,"Total Chemical Inputs Utilities")),
        ("Credits (−)",      lambda d: -_v(d,"Total Revenue")),
    ]
    vc_colors = ["#58a6ff","#79c0ff","#f85149"]
    fig_vc = go.Figure()
    for name in selected:
        d = scenarios[name]
        fig_vc.add_trace(go.Bar(
            name=name, x=[lbl for lbl, _ in vc_cats],
            y=[fn(d) for _, fn in vc_cats],
            text=[fmt(abs(fn(d))) for _, fn in vc_cats],
            textposition="outside",
            textfont=dict(family="DM Mono", size=9, color="#8b949e"),
            marker=dict(color=cmap[name], line_width=0, opacity=0.85),
        ))
    fig_vc.update_layout(
        barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8b949e"),
        legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=0, r=0, t=40, b=0), height=300,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=9)),
        xaxis=dict(tickfont=dict(family="Inter", size=10, color="#c9d1d9")),
    )
    st.plotly_chart(fig_vc, use_container_width=True)

# ── Fixed cost donut for first scenario ───────────────────────────────────────
col_don, col_kpis = st.columns([1, 2])

with col_don:
    st.markdown(f'<div class="section-hdr">Fixed Cost Mix — {selected[0]}</div>', unsafe_allow_html=True)
    d0 = active[selected[0]]
    fc_labels = ["Labor","Supply & Maint.","AFC","Indirect Fixed"]
    fc_vals = [
        _v(d0,"Total Labor Costs"),
        _v(d0,"Supply Maint Costs"),
        _v(d0,"AFC Pre Patents"),
        _v(d0,"Indirect Fixed Costs"),
    ]
    fig_pie = go.Figure(go.Pie(
        labels=fc_labels, values=fc_vals,
        hole=0.55,
        textfont=dict(family="DM Mono", size=10),
        marker=dict(colors=["#3fb950","#e6a817","#58a6ff","#bc8cff"], line=dict(color="#0d1117", width=2)),
        textinfo="percent",
    ))
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", color="#8b949e"),
        legend=dict(orientation="v", font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=10, b=0), height=250,
        annotations=[dict(text=fmt(_v(d0,"Total Fixed Costs")), x=0.5, y=0.5,
                          font=dict(family="DM Mono", size=13, color="#e6edf3"), showarrow=False)],
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_kpis:
    st.markdown('<div class="section-hdr">Key Rates & Percentages</div>', unsafe_allow_html=True)
    for name in selected:
        d = scenarios[name]
        opex  = _v(d,"Total OPEX")
        capex = _v(d,"Project CAPEX")
        fc    = _v(d,"Total Fixed Costs")
        vc    = tvc(d)
        st.markdown(f"""
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;
                    padding:.8rem 1rem;margin-bottom:.6rem;border-left:3px solid {cmap[name]}">
          <div class="kpi-scenario" style="color:{cmap[name]};font-weight:500;margin-bottom:.4rem">{name}</div>
          <div style="display:flex;gap:2rem;flex-wrap:wrap">
            <div>
              <div class="kpi-label">Fixed / OPEX</div>
              <div style="font-family:'DM Mono';font-size:1rem;color:var(--text)">{fc/opex*100:.1f}%</div>
            </div>
            <div>
              <div class="kpi-label">Variable / OPEX</div>
              <div style="font-family:'DM Mono';font-size:1rem;color:var(--text)">{vc/opex*100:.1f}%</div>
            </div>
            <div>
              <div class="kpi-label">OPEX / CAPEX</div>
              <div style="font-family:'DM Mono';font-size:1rem;color:var(--text)">{opex/capex*100:.1f}%</div>
            </div>
            <div>
              <div class="kpi-label">CAPEX</div>
              <div style="font-family:'DM Mono';font-size:1rem;color:var(--text)">{fmt(capex)}</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

# ── Detailed table ────────────────────────────────────────────────────────────
with st.expander("Full Detailed Breakdown", expanded=False):
    ROWS = [
        ("section","VARIABLE COSTS",None),
        ("item","  Raw Materials","Total Raw Material Cost"),
        ("item","  Chemical Inputs & Utilities","Total Chemical Inputs Utilities"),
        ("item","  Credits & Byproducts (−)","Total Revenue"),
        ("sub","  Total Variable Costs","_tvc"),
        ("section","FIXED COSTS — LABOR",None),
        ("item","  OLC","OLC"),
        ("item","  Lab Charges (%)","Lab Charges Pct"),
        ("item","  Office Labor (%)","Office Labor Pct"),
        ("sub","  Total Labor Costs","Total Labor Costs"),
        ("section","SUPPLY & MAINTENANCE",None),
        ("item","  Maintenance & Repairs (%)","Maint Pct"),
        ("item","  Operating Supplies (%)","Op Sup Pct"),
        ("sub","  Supply & Maintenance Costs","Supply Maint Costs"),
        ("section","ADDITIONAL FIXED COSTS (AFC)",None),
        ("item","  Admin Overhead (%)","Admin Ov Pct"),
        ("item","  Manufacturing Overhead (%)","Mfg Ov Pct"),
        ("item","  Taxes & Insurance (%)","Taxes Ins Pct"),
        ("item","  Patents & Royalties (%)","Patents Pct"),
        ("sub","  AFC","AFC Pre Patents"),
        ("total","  Direct Fixed Costs","Direct Fixed Costs"),
        ("section","INDIRECT FIXED COSTS",None),
        ("item","  Administrative Costs (%)","Admin Costs Pct"),
        ("item","  Manufacturing Costs (%)","Mfg Costs Pct"),
        ("item","  Distribution & Selling (%)","Dist Sell Pct"),
        ("item","  Research & Development (%)","R D Pct"),
        ("sub","  Indirect Fixed Costs","Indirect Fixed Costs"),
        ("section","TOTALS",None),
        ("sub","  Total Fixed Costs","Total Fixed Costs"),
        ("total","  TOTAL OPEX","Total OPEX"),
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
