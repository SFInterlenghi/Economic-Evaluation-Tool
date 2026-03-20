import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Investment Costs", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&family=Inter:wght@300;400;500&display=swap');
:root {
    --bg:#0d1117; --surface:#161b22; --border:#21262d;
    --accent:#e6a817; --accent2:#3fb950; --muted:#8b949e;
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
.section-hdr{font-family:'Syne',sans-serif;font-size:.7rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.15em;padding:.6rem 0 .3rem 0;border-bottom:1px solid var(--border);margin-bottom:.5rem;}
.divider{border:none;border-top:1px solid var(--border);margin:1.5rem 0;}
</style>
""", unsafe_allow_html=True)

if "scenarios" not in st.session_state or not st.session_state.scenarios:
    st.markdown('<div class="hero-title">Investment Costs</div>', unsafe_allow_html=True)
    st.info("No scenarios saved yet. Configure and save scenarios on the Input Data page first.")
    st.stop()

scenarios = st.session_state.scenarios
names     = list(scenarios.keys())
PALETTE   = ["#e6a817","#3fb950","#58a6ff","#f78166","#bc8cff","#79c0ff","#ffa657","#ff7b72"]
cmap      = {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(names)}

def _v(d, k, default=0.0):
    v = d.get(k, default)
    return v if isinstance(v, (int, float)) else default
def fmt(v):  return f"${v:,.0f}"
def fmtd(v): return f"${v:,.2f}"
def fpct(v): return f"{v*100:.2f}%"

# Header
st.markdown('<div class="hero-title">Investment Costs</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Total Investment Cost — scenario comparison</div>', unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

# Scenario filter
if len(names) > 1:
    selected = st.multiselect("Scenarios", names, default=names, label_visibility="collapsed")
    if not selected: selected = names
else:
    selected = names

active = {n: scenarios[n] for n in selected}

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Total Investment Cost per Scenario</div>', unsafe_allow_html=True)
cols = st.columns(len(active))
for col, (name, d) in zip(cols, active.items()):
    tic   = _v(d, "Total Investment")
    capex = _v(d, "Project CAPEX")
    wc    = _v(d, "Working Capital")
    su    = _v(d, "Startup Costs")
    with col:
        st.markdown(f"""<div class="kpi-card" style="border-left-color:{cmap[name]}">
            <div class="kpi-label">Total Investment Cost</div>
            <div class="kpi-value">{fmt(tic)}</div>
            <div class="kpi-scenario" style="color:{cmap[name]};font-weight:500">{name}</div>
            <div class="kpi-scenario">CAPEX {fmt(capex)} &nbsp;|&nbsp; WC {fmt(wc)} &nbsp;|&nbsp; S/U {fmt(su)}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Two charts side by side ───────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    st.markdown('<div class="section-hdr">TIC Composition by Scenario</div>', unsafe_allow_html=True)
    stack_keys = [("CAPEX","Project CAPEX"),("Working Capital","Working Capital"),
                  ("Startup","Startup Costs"),("Additional","Additional Costs")]
    stack_colors = ["#e6a817","#3fb950","#58a6ff","#f78166"]
    fig_stack = go.Figure()
    for (lbl, key), clr in zip(stack_keys, stack_colors):
        fig_stack.add_trace(go.Bar(
            name=lbl, x=list(active.keys()),
            y=[_v(d, key) for d in active.values()],
            text=[fmt(_v(d, key)) for d in active.values()],
            textposition="inside",
            textfont=dict(family="DM Mono", size=10, color="white"),
            marker=dict(color=clr, line_width=0),
        ))
    fig_stack.update_layout(
        barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8b949e"),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=0, r=0, t=30, b=0), height=300,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=9)),
        xaxis=dict(tickfont=dict(family="Syne", size=11, color="#e6edf3")),
    )
    st.plotly_chart(fig_stack, use_container_width=True)

with col_r:
    st.markdown('<div class="section-hdr">CAPEX Components — All Scenarios</div>', unsafe_allow_html=True)
    capex_items = [
        ("Equipment",   "Total Equipment Costs"),
        ("Installation","Total Installation Costs"),
        ("Indirect Field","Total Indirect Field Costs"),
        ("Non-Field",   "Total Non-Field Costs"),
    ]
    fig_capex = go.Figure()
    for name in selected:
        d = scenarios[name]
        fig_capex.add_trace(go.Bar(
            name=name,
            x=[lbl for lbl, _ in capex_items],
            y=[_v(d, key) for _, key in capex_items],
            text=[fmt(_v(d, key)) for _, key in capex_items],
            textposition="outside",
            textfont=dict(family="DM Mono", size=9, color="#8b949e"),
            marker=dict(color=cmap[name], line_width=0, opacity=0.85),
        ))
    fig_capex.update_layout(
        barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8b949e"),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        margin=dict(l=0, r=0, t=30, b=0), height=300,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=9)),
        xaxis=dict(tickfont=dict(family="Inter", size=10, color="#c9d1d9")),
    )
    st.plotly_chart(fig_capex, use_container_width=True)

# ── CAPEX Waterfall for first scenario ────────────────────────────────────────
st.markdown(f'<div class="section-hdr">CAPEX Build-Up — {selected[0]}</div>', unsafe_allow_html=True)
d0 = active[selected[0]]
c0 = cmap[selected[0]]

unscheduled = _v(d0,"Total Equipment Costs") - _v(d0,"Base Equipment Costs")
isbl_val    = _v(d0,"Project Costs ISBL+OSBL")
cont_val    = isbl_val * _v(d0,"Contingency Pct",0)
tuf = _v(d0,"Time Update Factor",1.0); lf = _v(d0,"Location Factor",1.0)
tl_adj = isbl_val * (1 + _v(d0,"Contingency Pct",0)) * (tuf * lf - 1)

wf_x = ["Equip. Acq.","Spare Parts","Setting","Unscheduled","Piping","Civil",
         "Steel","Instruments","Electrical","Insulation","Paint",
         "Field Office","Const. Ind.","Freight","Tax/Permits","Engineering","GA Oh.","Contract",
         "Contingency","Time/Loc.","CAPEX"]
wf_y = [_v(d0,k) for k in ["Equipment Acquisition","Spare Parts","Equipment Setting"]]
wf_y += [unscheduled]
wf_y += [_v(d0,k) for k in ["Piping","Civil","Steel","Instrumentals","Electrical","Insulation","Paint",
                              "Field Office Staff","Construction Indirects",
                              "Freight","Taxes and Permits","Engineering and HO","GA Overheads","Contract Fee"]]
wf_y += [cont_val, tl_adj, _v(d0,"Project CAPEX")]

fig_wf = go.Figure(go.Waterfall(
    orientation="v",
    measure=["relative"]*20 + ["total"],
    x=wf_x, y=wf_y,
    text=[fmt(v) for v in wf_y],
    textposition="outside",
    textfont=dict(family="DM Mono", size=8, color="#8b949e"),
    connector=dict(line=dict(color="#21262d", width=1)),
    increasing=dict(marker=dict(color="#3fb950", line_width=0)),
    decreasing=dict(marker=dict(color="#f85149", line_width=0)),
    totals=dict(marker=dict(color=c0, line_width=0)),
))
fig_wf.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#8b949e"),
    margin=dict(l=0, r=0, t=10, b=0), height=340,
    yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=9)),
    xaxis=dict(tickfont=dict(family="Inter", size=9, color="#c9d1d9"), tickangle=-30),
    showlegend=False,
)
st.plotly_chart(fig_wf, use_container_width=True)

# ── Detailed table ────────────────────────────────────────────────────────────
with st.expander("Full Detailed Breakdown", expanded=False):
    ROWS = [
        ("section","EQUIPMENT COSTS",None),
        ("item","  Equipment Acquisition","Equipment Acquisition"),
        ("item","  Spare Parts","Spare Parts"),
        ("item","  Equipment Setting","Equipment Setting"),
        ("sub","  Base Equipment Costs","Base Equipment Costs"),
        ("item","  Unscheduled Equipment","_unscheduled"),
        ("sub","  Total Equipment Costs","Total Equipment Costs"),
        ("section","INSTALLATION COSTS",None),
        ("item","  Piping","Piping"),("item","  Civil","Civil"),("item","  Steel","Steel"),
        ("item","  Instrumentals","Instrumentals"),("item","  Electrical","Electrical"),
        ("item","  Insulation","Insulation"),("item","  Paint","Paint"),
        ("sub","  Total Installation","Total Installation Costs"),
        ("section","INDIRECT & NON-FIELD",None),
        ("item","  Field Office Staff","Field Office Staff"),
        ("item","  Construction Indirects","Construction Indirects"),
        ("item","  Freight","Freight"),("item","  Taxes & Permits","Taxes and Permits"),
        ("item","  Engineering & HO","Engineering and HO"),
        ("item","  GA Overheads","GA Overheads"),("item","  Contract Fee","Contract Fee"),
        ("section","CAPEX SUMMARY",None),
        ("sub","  Project Costs ISBL+OSBL","Project Costs ISBL+OSBL"),
        ("item","  Contingency (%)","Contingency Pct"),
        ("item","  Time Update Factor","Time Update Factor"),
        ("item","  Location Factor","Location Factor"),
        ("total","  PROJECT CAPEX","Project CAPEX"),
        ("section","TOTAL INVESTMENT",None),
        ("item","  Working Capital","Working Capital"),
        ("item","  Startup Costs","Startup Costs"),
        ("item","  Additional Costs","Additional Costs"),
        ("total","  TOTAL INVESTMENT COST","Total Investment"),
    ]

    def _cell(rtype, key, d):
        if key is None: return ""
        if key == "_unscheduled":
            return fmtd(_v(d,"Total Equipment Costs") - _v(d,"Base Equipment Costs"))
        v = d.get(key)
        if v is None: return "—"
        if key in ("Contingency Pct",): return fpct(v)
        if key in ("Time Update Factor","Location Factor"): return f"{v:.4f}"
        return fmtd(v)

    tbl = {"Line Item": [r[1] for r in ROWS]}
    for name in selected:
        tbl[name] = [_cell(r[0], r[2], scenarios[name]) for r in ROWS]

    st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True,
        column_config={"Line Item": st.column_config.TextColumn("Line Item", width="large")}
        | {n: st.column_config.TextColumn(n, width="medium") for n in selected})
