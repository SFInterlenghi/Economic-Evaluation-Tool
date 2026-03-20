import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Investment Costs", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&family=Inter:wght@300;400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
:root {
    --bg:#0d1117; --surface:#161b22; --border:#21262d;
    --accent:#e6a817; --muted:#8b949e;
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
.section-hdr{font-family:'Syne',sans-serif;font-size:.7rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.15em;padding:.6rem 0 .3rem 0;border-bottom:1px solid var(--border);margin-bottom:.5rem;}
.divider{border:none;border-top:1px solid var(--border);margin:1.5rem 0;}
/* Hide sidebar collapse toggle — icon font sometimes renders as raw text */
[data-testid="collapsedControl"] { display: none !important; }
button[data-testid="baseButton-headerNoPadding"] { display: none !important; }
.scen-badge{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem;height:100%;}
.scen-name{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:var(--text);margin-bottom:.5rem;}
.scen-tag{display:inline-block;font-family:'DM Mono',monospace;font-size:.7rem;padding:.15rem .5rem;border-radius:4px;margin:.15rem .1rem 0 0;}
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

# ── Header ────────────────────────────────────────────────────────────────────
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

# ── Scenario Summary Banner ───────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Scenario Overview</div>', unsafe_allow_html=True)
cols_banner = st.columns(len(active))
for col, (name, d) in zip(cols_banner, active.items()):
    clr    = cmap[name]
    prod   = d.get("Product Name", "—")
    unit   = d.get("Unit", "")
    cap    = d.get("Capacity", "—")
    trl    = d.get("TRL", "—")
    sev    = d.get("Process Severity", "—")
    mat    = d.get("Material Handled", "—")
    tic    = _v(d, "Total Investment")
    with col:
        st.markdown(f"""
        <div class="scen-badge" style="border-left:4px solid {clr}">
          <div class="scen-name" style="color:{clr}">{name}</div>
          <div style="font-family:'Inter';font-size:.85rem;color:var(--text);margin-bottom:.4rem">
            {prod}
          </div>
          <div style="font-family:'DM Mono';font-size:.8rem;color:var(--text-dim);margin-bottom:.5rem">
            {cap} {unit}/yr
          </div>
          <div>
            <span class="scen-tag" style="background:rgba({int(clr[1:3],16)},{int(clr[3:5],16)},{int(clr[5:7],16)},0.15);color:{clr};border:1px solid {clr}33">{trl}</span>
            <span class="scen-tag" style="background:#21262d;color:var(--muted)">{sev}</span>
            <span class="scen-tag" style="background:#21262d;color:var(--muted)">{mat}</span>
          </div>
          <div style="font-family:'DM Mono';font-size:.95rem;color:var(--text);margin-top:.6rem;font-weight:500">
            TIC: {fmt(tic)}
          </div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Total Investment Cost per Scenario</div>', unsafe_allow_html=True)
cols_kpi = st.columns(len(active))
for col, (name, d) in zip(cols_kpi, active.items()):
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
            textfont=dict(family="DM Mono", size=13, color="white"),
            marker=dict(color=clr, line_width=0),
        ))
    fig_stack.update_layout(
        barmode="stack", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8b949e", size=13),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        margin=dict(l=0, r=0, t=40, b=0), height=320,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=11)),
        xaxis=dict(tickfont=dict(family="Syne", size=13, color="#e6edf3")),
    )
    st.plotly_chart(fig_stack, use_container_width=True)

with col_r:
    st.markdown('<div class="section-hdr">CAPEX Components — All Scenarios</div>', unsafe_allow_html=True)
    capex_items = [
        ("Equipment",     "Total Equipment Costs"),
        ("Installation",  "Total Installation Costs"),
        ("Indirect Field","Total Indirect Field Costs"),
        ("Non-Field",     "Total Non-Field Costs"),
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
            textfont=dict(family="DM Mono", size=11, color="#8b949e"),
            marker=dict(color=cmap[name], line_width=0, opacity=0.85),
        ))
    fig_capex.update_layout(
        barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#8b949e", size=13),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
        margin=dict(l=0, r=0, t=40, b=0), height=320,
        yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=11)),
        xaxis=dict(tickfont=dict(family="Inter", size=12, color="#c9d1d9")),
    )
    st.plotly_chart(fig_capex, use_container_width=True)

# ── CAPEX Waterfall with scenario selector ────────────────────────────────────
st.markdown('<div class="section-hdr">CAPEX Build-Up</div>', unsafe_allow_html=True)
wf_scenario = st.selectbox("Select scenario for build-up chart", selected, key="wf_sel")
d0 = scenarios[wf_scenario]
c0 = cmap[wf_scenario]

unscheduled = _v(d0,"Total Equipment Costs") - _v(d0,"Base Equipment Costs")
isbl_val    = _v(d0,"Project Costs ISBL+OSBL")
cont_val    = isbl_val * _v(d0,"Contingency Pct", 0)
tuf = _v(d0,"Time Update Factor",1.0)
lf  = _v(d0,"Location Factor",1.0)
tl_adj = isbl_val * (1 + _v(d0,"Contingency Pct",0)) * (tuf * lf - 1)

wf_x = ["Equip. Acq.","Spare Parts","Setting","Unscheduled",
         "Piping","Civil","Steel","Instruments","Electrical","Insulation","Paint",
         "Field Office","Const. Ind.",
         "Freight","Tax/Permits","Engineering","GA Oh.","Contract",
         "Contingency","Time/Loc.","CAPEX"]
wf_y  = [_v(d0,k) for k in ["Equipment Acquisition","Spare Parts","Equipment Setting"]]
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
    textfont=dict(family="DM Mono", size=10, color="#8b949e"),
    connector=dict(line=dict(color="#21262d", width=1)),
    increasing=dict(marker=dict(color="#3fb950", line_width=0)),
    decreasing=dict(marker=dict(color="#f85149", line_width=0)),
    totals=dict(marker=dict(color=c0, line_width=0)),
))
fig_wf.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#8b949e", size=12),
    margin=dict(l=0, r=0, t=20, b=0), height=360,
    yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono", size=10)),
    xaxis=dict(tickfont=dict(family="Inter", size=10, color="#c9d1d9"), tickangle=-30),
    showlegend=False,
)
st.plotly_chart(fig_wf, use_container_width=True)

# ── Detailed breakdown table ───────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Detailed Breakdown</div>', unsafe_allow_html=True)

ROWS = [
    ("H", "EQUIPMENT COSTS",              None),
    ("I", "Equipment Acquisition",        "Equipment Acquisition"),
    ("I", "Spare Parts",                  "Spare Parts"),
    ("I", "Equipment Setting",            "Equipment Setting"),
    ("S", "Base Equipment Costs",         "Base Equipment Costs"),
    ("I", "Unscheduled Equipment",        "_unscheduled"),
    ("S", "Total Equipment Costs",        "Total Equipment Costs"),
    ("H", "INSTALLATION COSTS",           None),
    ("I", "Piping",                       "Piping"),
    ("I", "Civil",                        "Civil"),
    ("I", "Steel",                        "Steel"),
    ("I", "Instrumentals",                "Instrumentals"),
    ("I", "Electrical",                   "Electrical"),
    ("I", "Insulation",                   "Insulation"),
    ("I", "Paint",                        "Paint"),
    ("S", "Total Installation Costs",     "Total Installation Costs"),
    ("H", "INDIRECT & NON-FIELD",         None),
    ("I", "Field Office Staff",           "Field Office Staff"),
    ("I", "Construction Indirects",       "Construction Indirects"),
    ("I", "Freight",                      "Freight"),
    ("I", "Taxes & Permits",              "Taxes and Permits"),
    ("I", "Engineering & HO",             "Engineering and HO"),
    ("I", "GA Overheads",                 "GA Overheads"),
    ("I", "Contract Fee",                 "Contract Fee"),
    ("H", "CAPEX SUMMARY",                None),
    ("S", "Project Costs ISBL+OSBL",      "Project Costs ISBL+OSBL"),
    ("I", "Contingency",                  "Contingency Pct"),
    ("I", "Time Update Factor",           "Time Update Factor"),
    ("I", "Location Factor",              "Location Factor"),
    ("T", "PROJECT CAPEX",                "Project CAPEX"),
    ("H", "TOTAL INVESTMENT",             None),
    ("I", "Working Capital",              "Working Capital"),
    ("I", "Startup Costs",                "Startup Costs"),
    ("I", "Additional Costs",             "Additional Costs"),
    ("T", "TOTAL INVESTMENT COST",        "Total Investment"),
]

def _cell(rtype, key, d):
    if key is None: return ""
    if key == "_unscheduled":
        return fmtd(_v(d,"Total Equipment Costs") - _v(d,"Base Equipment Costs"))
    v = d.get(key)
    if v is None: return "—"
    if key == "Contingency Pct": return fpct(v)
    if key in ("Time Update Factor","Location Factor"): return f"{v:.4f}"
    return fmtd(v)

# Build HTML table
_scen_headers = "".join(
    f'<th style="padding:.5rem .9rem;text-align:right;font-family:Syne,sans-serif;'
    f'font-size:.75rem;color:{cmap[n]};border-bottom:2px solid {cmap[n]}44;white-space:nowrap">{n}</th>'
    for n in selected
)
html_rows = []
for rtype, label, key in ROWS:
    if rtype == "H":
        row_html = (
            f'<tr><td colspan="{len(selected)+1}" style="padding:.6rem .9rem .2rem;'
            f'font-family:Syne,sans-serif;font-size:.65rem;font-weight:700;'
            f'color:#e6a817;text-transform:uppercase;letter-spacing:.12em;'
            f'background:#0d1117;border-top:1px solid #21262d">{label}</td></tr>'
        )
    else:
        is_total = rtype == "T"
        is_sub   = rtype == "S"
        indent   = "0" if is_total else ("1rem" if is_sub else "2rem")
        bg       = "#1a2030" if is_total else ("#161b22" if is_sub else "transparent")
        fw       = "600" if (is_total or is_sub) else "400"
        fc       = "#e6edf3" if is_total else ("#c9d1d9" if is_sub else "#8b949e")
        cells    = "".join(
            f'<td style="padding:.4rem .9rem;text-align:right;font-family:DM Mono,monospace;'
            f'font-size:.8rem;color:{fc};white-space:nowrap">{_cell(rtype, key, scenarios[n])}</td>'
            for n in selected
        )
        row_html = (
            f'<tr style="background:{bg};border-bottom:1px solid #21262d22">'
            f'<td style="padding:.4rem .9rem .4rem {indent};font-family:Inter,sans-serif;'
            f'font-size:.82rem;font-weight:{fw};color:{fc}">{label}</td>'
            f'{cells}</tr>'
        )
    html_rows.append(row_html)

html_table = f"""
<div style="overflow-x:auto;border:1px solid #21262d;border-radius:8px;background:#161b22">
<table style="width:100%;border-collapse:collapse">
<thead><tr>
  <th style="padding:.5rem .9rem;text-align:left;font-family:Syne,sans-serif;
      font-size:.75rem;color:#8b949e;border-bottom:2px solid #21262d;min-width:220px">
      Line Item</th>
  {_scen_headers}
</tr></thead>
<tbody>{"".join(html_rows)}</tbody>
</table>
</div>
"""
st.markdown(html_table, unsafe_allow_html=True)
