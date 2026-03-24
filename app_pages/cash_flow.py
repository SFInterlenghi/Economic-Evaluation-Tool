"""ISI-Tool — Cash Flow & Analysis page.

Section 1: Variable cost tables with editable prices (original)
Section 2: What-If Analysis for TIC & OPEX
Section 3: Financial Analysis Engine & Solvers (Fixed State Logic)
Section 4: Unified Table & Dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go

# Safety check for mathematical solvers
try:
    from scipy.optimize import brentq
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

try:
    import numpy_financial as npf
    _HAS_NPF = True
except ImportError:
    _HAS_NPF = False

from utils.constants import (
    safe_val, smart_fmt, fmt_curr, coeff_unit, is_per_year,
) #
from utils.ui import inject_css, page_header, section_header, kpi_card #

inject_css()

# ── Guard ─────────────────────────────────────────────────────────────────────
if "scenarios" not in st.session_state or not st.session_state.scenarios:
    page_header("Cash Flow & Analysis") #
    st.info("No scenarios saved yet — go to **Input Data** to configure and save a scenario first.",
            icon=":material/info:")
    st.stop()

scenarios = st.session_state.scenarios

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE & SCENARIO SETUP
# ─────────────────────────────────────────────────────────────────────────────
if "cf_selected" not in st.session_state:
    st.session_state.cf_selected = list(scenarios.keys())[0]
if "cf_session_defaults" not in st.session_state:
    st.session_state.cf_session_defaults = {}
if "cf_working" not in st.session_state:
    st.session_state.cf_working = {}
if "cf_wif" not in st.session_state:
    st.session_state.cf_wif = {}

def _input_prices(scenario_name, table_key):
    items = scenarios[scenario_name].get(table_key, []) or []
    return {r["Name"]: float(r.get("Price", 0.0)) for r in items if r.get("Name")}

def _ensure_scenario(scenario_name):
    if scenario_name not in st.session_state.cf_session_defaults:
        st.session_state.cf_session_defaults[scenario_name] = {}
    if scenario_name not in st.session_state.cf_working:
        st.session_state.cf_working[scenario_name] = {}
    if scenario_name not in st.session_state.cf_wif:
        st.session_state.cf_wif[scenario_name] = {}
    for tbl in ["Raw Materials", "Chemical Inputs and Utilities", "Credits and Byproducts"]:
        inp = _input_prices(scenario_name, tbl)
        sd = st.session_state.cf_session_defaults[scenario_name]
        wk = st.session_state.cf_working[scenario_name]
        if tbl not in sd: sd[tbl] = dict(inp)
        if tbl not in wk: wk[tbl] = dict(sd[tbl])

# ── Header & Selector ─────────────────────────────────────────────────────────
page_header("Cash Flow & Analysis", "Interactive economic analysis — scenario-based") #

col_sel, col_reset = st.columns([3, 1])
with col_sel:
    prev_scenario = st.session_state.cf_selected
    chosen = st.selectbox("Select scenario", list(scenarios.keys()),
                          index=list(scenarios.keys()).index(st.session_state.cf_selected),
                          label_visibility="collapsed", key="cf_scenario_sel")
if chosen != prev_scenario:
    st.session_state.cf_selected = chosen
    _ensure_scenario(chosen)
    sd = st.session_state.cf_session_defaults.get(chosen, {})
    st.session_state.cf_working[chosen] = {tbl: dict(prices) for tbl, prices in sd.items()}
    st.rerun()

scenario_name = st.session_state.cf_selected
_ensure_scenario(scenario_name)
d = scenarios[scenario_name]
wif = st.session_state.cf_wif[scenario_name]

with col_reset:
    if st.button("↺  Reset all to base case", type="secondary", use_container_width=True):
        sd = st.session_state.cf_session_defaults.get(scenario_name, {})
        st.session_state.cf_working[scenario_name] = {tbl: dict(p) for tbl, p in sd.items()}
        st.session_state.cf_wif[scenario_name] = {}
        to_pop = [k for k in st.session_state if k.startswith(f"cf_{scenario_name}_") or k.startswith(f"wif_{scenario_name}_")]
        for k in to_pop: st.session_state.pop(k, None)
        st.rerun()

# ── Initial KPIs ─────────────────────────────────────────────────────────────
prod_name = d.get("Product Name", "—")
prod_unit = d.get("Unit", "")
capacity = safe_val(d, "Capacity") #
tic = safe_val(d, "Total Investment") #
opex = safe_val(d, "Total OPEX") #

section_header("Scenario summary", "#58a6ff") #
c1, c2, c3 = st.columns(3)
with c1: kpi_card("Main Product", prod_name, "#e6a817", "Capacity", f"{capacity:,.0f} {prod_unit}/year") #
with c2: kpi_card("Total Investment Cost (TIC)", smart_fmt(tic), "#58a6ff") #
with c3: kpi_card("Total Annual OPEX", smart_fmt(opex), "#3fb950") #

st.space("medium")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1: VARIABLE COST TABLES
# ═════════════════════════════════════════════════════════════════════════════
section_header("Variable costs & credits", "#58a6ff") #

working_hours = safe_val(d, "Working Hours per Year", 8000.0) #
product_rate = capacity / working_hours if working_hours > 0 else 0.0

def _build_vc_table(table_key: str, is_credit: bool = False):
    items = [r for r in d.get(table_key, []) if r.get("Name")]
    if not items:
        st.caption("No items defined for this table.")
        return [], 0.0

    wk = st.session_state.cf_working[scenario_name]
    inp = _input_prices(scenario_name, table_key)
    sd = st.session_state.cf_session_defaults[scenario_name].get(table_key, inp)
    if table_key not in wk: wk[table_key] = dict(sd)

    total_cost = 0.0
    rows = []
    for r in items:
        name = r["Name"]; rate = float(r.get("Rate", 0.0)); rate_unit = r.get("Rate Unit", "")
        p_unit = r.get("Price Unit", ""); curr_price = wk[table_key].get(name, inp.get(name, 0.0))
        coeff = (rate / capacity) if is_per_year(rate_unit) else (rate / product_rate if product_rate else 0.0) #
        line_cost = curr_price * rate * (1.0 if is_per_year(rate_unit) else working_hours) #
        total_cost += line_cost
        rows.append({"name": name, "rate": rate, "rate_unit": rate_unit, "coeff": coeff, "coeff_unit": coeff_unit(rate_unit, prod_unit), "price": curr_price, "price_unit": p_unit, "input_def": inp.get(name, 0.0), "modified": abs(curr_price - inp.get(name, 0.0)) > 1e-9, "line_cost": line_cost}) #

    header = '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.8rem"><thead><tr style="border-bottom:2px solid #21262d"><th style="padding:.5rem .7rem;text-align:left;color:#8b949e">Name</th><th style="padding:.5rem .7rem;text-align:center;color:#58a6ff">Price</th><th style="padding:.5rem .7rem;text-align:right;color:#8b949e">Unit</th><th style="padding:.5rem .7rem;text-align:right;color:#3fb950">Cost/year</th><th style="padding:.5rem .7rem;text-align:right;color:#3fb950">%</th></tr></thead><tbody>'
    body = ""
    for r in rows:
        pct = (r["line_cost"] / total_cost * 100) if total_cost and not is_credit else 0.0
        bg = "#2d2a1a" if r["modified"] else "transparent"
        body += f'<tr style="background:{bg};border-bottom:1px solid #21262d22"><td style="padding:.4rem .7rem;color:#c9d1d9">{r["name"]}</td><td style="padding:.4rem .7rem;text-align:center;color:{"#e6a817" if r["modified"] else "#58a6ff"}">{r["price"]:.6g}</td><td style="padding:.4rem .7rem;text-align:right;color:#8b949e">{r["price_unit"]}</td><td style="padding:.4rem .7rem;text-align:right;color:#3fb950">{smart_fmt(r["line_cost"])}</td><td style="padding:.4rem .7rem;text-align:right;color:#3fb950">{"—" if is_credit else f"{pct:.1f}%"}</td></tr>' #
    
    st.markdown(header + body + f'<tr style="border-top:2px solid #21262d;background:#1a2030"><td colspan="3" style="padding:.5rem .7rem;color:#e6edf3;font-weight:600">TOTAL</td><td style="padding:.5rem .7rem;text-align:right;color:#e6edf3;font-weight:600">{smart_fmt(total_cost)}</td><td></td></tr></tbody></table></div>', unsafe_allow_html=True) #

    changed = False
    for r in rows:
        col_l, col_i, col_b = st.columns([2, 1, 1])
        with col_i:
            nv = st.number_input(r["name"], value=float(r["price"]), format="%.6f", key=f"inp_{scenario_name}_{table_key}_{r['name']}", label_visibility="collapsed")
            if abs(nv - r["price"]) > 1e-12: wk[table_key][r["name"]] = nv; changed = True
        with col_b:
            if st.button("↩", key=f"rst_{scenario_name}_{table_key}_{r['name']}", disabled=not r["modified"]):
                wk[table_key][r["name"]] = r["input_def"]; changed = True
    if changed: st.rerun()
    return total_cost

st.markdown("#### Raw Materials")
rm_total = _build_vc_table("Raw Materials")
st.markdown("#### Chemical Inputs & Utilities")
cu_total = _build_vc_table("Chemical Inputs and Utilities")
st.markdown("#### Credits & Byproducts")
cb_total = _build_vc_table("Credits and Byproducts", is_credit=True)
tvc_net = rm_total + cu_total - cb_total

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2: WHAT-IF ANALYSIS (TIC & OPEX)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
section_header("What-If Analysis", "#58a6ff") #

def _base(k, dft=0.0):
    v = d.get(k, dft)
    return float(v) if isinstance(v, (int, float)) else dft

def _edit_row(label, key, base_v, step=0.01, suffix=""):
    wk = f"wif_{scenario_name}_{key}"; current = wif.get(key, base_v)
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1: st.markdown(f'<p style="margin:0;padding:.35rem 0;font-size:.82rem;color:{"#e6a817" if key in wif else "#8b949e"}">{label}</p>', unsafe_allow_html=True)
    with c2: st.text_input(f"b_{key}", value=f"{base_v:,.2f}{suffix}", disabled=True, label_visibility="collapsed")
    with c3:
        nv = st.number_input(label, value=float(current), step=float(step), key=wk, label_visibility="collapsed")
        if abs(nv - base_v) > 1e-9: wif[key] = nv
        elif key in wif: del wif[key]
        return nv

wif_capacity = _edit_row("Production capacity", "Capacity", _base("Capacity"), step=100.0)
wif_wh = _edit_row("Working hours per year", "Working Hours per Year", _base("Working Hours per Year", 8000.0), step=100.0)

section_header("Investment costs (TIC)", "#e6a817") #
wif_equip = _edit_row("Equipment acquisition", "Equipment Acquisition", _base("Equipment Acquisition"), step=1000.0)
wif_cont = _edit_row("Project contingency (%)", "wif_Contingency_Pct", _base("Contingency Pct") * 100, step=1.0) / 100.0
wif_loc = _edit_row("Location factor", "Location Factor", _base("Location Factor", 1.0), step=0.01)

wif_isbl = _base("Project Costs ISBL+OSBL") * (wif_equip / _base("Equipment Acquisition") if _base("Equipment Acquisition") > 0 else 1.0)
wif_capex = wif_isbl * (1 + wif_cont) * _base("Time Update Factor", 1.0) * wif_loc
wif_wc = _base("Working Capital") * (wif_capex / _base("Project CAPEX") if _base("Project CAPEX") > 0 else 1.0)
wif_startup = _base("Startup Costs") * (wif_capex / _base("Project CAPEX") if _base("Project CAPEX") > 0 else 1.0)
wif_tic = wif_capex + wif_wc + wif_startup + _base("Additional Costs")

kpi_c1, kpi_c2 = st.columns(2)
with kpi_c1: kpi_card("Modified CAPEX", smart_fmt(wif_capex), "#e6a817") #
with kpi_c2: kpi_card("Modified TIC", smart_fmt(wif_tic), "#58a6ff") #

# ═════════════════════════════════════════════════════════════════════════════
# FINANCIAL ASSUMPTIONS PANEL (Land, Taxes, MARR)
# ═════════════════════════════════════════════════════════════════════════════
from utils.constants import CAPEX_DISTRIBUTION

if "cf_fin" not in st.session_state: st.session_state.cf_fin = {}
if scenario_name not in st.session_state.cf_fin: st.session_state.cf_fin[scenario_name] = {}
_fin = st.session_state.cf_fin[scenario_name]

def _fin_input(label, key, base_v, step=0.01, suffix=""):
    wk = f"fin_{scenario_name}_{key}"; current = _fin.get(key, base_v)
    col1, col2 = st.columns([3, 2])
    with col1: st.markdown(f'<p style="font-size:.9rem;color:{"#e6a817" if key in _fin else "#c9d1d9"}">{label}</p>', unsafe_allow_html=True)
    with col2:
        val = st.number_input(label, value=float(current), step=float(step), key=wk, label_visibility="collapsed")
        if abs(val - base_v) > 1e-9: _fin[key] = val
        elif key in _fin: del _fin[key]
    return val

with st.expander("**Financial Assumptions**", expanded=False):
    st.markdown("---")
    fl, fm, fr = st.columns(3)
    with fl:
        section_header("Land", "#e6a817") #
        fa_land_opt = st.radio("Option", ["Buy", "Rent"], index=0 if _fin.get("Land Option", "Buy")=="Buy" else 1, horizontal=True)
        _fin["Land Option"] = fa_land_opt
        fa_land_buy = (wif_isbl * _fin_input("Land purchase (%)", "Land Buy Pct", 2.0, suffix="%") / 100.0) if fa_land_opt=="Buy" else 0.0
        fa_land_rent = (wif_isbl * _fin_input("Land rent (%/yr)", "Land Rent Pct", 0.2, suffix="%") / 100.0) if fa_land_opt=="Rent" else 0.0
    with fm:
        section_header("Timeline", "#58a6ff") #
        fa_op_yrs = int(_fin_input("Project lifetime (yrs)", "Project Lifetime", 20, step=1))
        fa_epc_yrs = int(_fin_input("EPC time (yrs)", "EPC Years", 3, step=1))
        fa_tax = _fin_input("Tax rate (%)", "Tax Rate", 34.0, suffix="%") / 100.0
    with fr:
        section_header("Financials", "#58a6ff") #
        fa_marr = _fin_input("MARR (%)", "MARR", 10.0, suffix="%") / 100.0
        fa_resid = _fin_input("Residual value (%)", "Residual Value Pct", 20.0, suffix="%") / 100.0

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3: CORE CALCULATION ENGINE & SOLVERS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
section_header("Economic Dashboard", "#58a6ff") #

def _get_project_arrays(price, tic_mult=1.0):
    """Central math engine for calculating year-by-year cash flows."""
    _c = wif_capex * tic_mult; _w = wif_wc * tic_mult; _s = wif_startup * tic_mult; _l = fa_land_buy * tic_mult
    _dep_ann = -(_c * (1 - fa_resid)) / 10 if 10 > 0 else 0.0 # Standard 10yr dep
    
    total_yrs = fa_epc_yrs + fa_op_yrs
    _fracs = list(CAPEX_DISTRIBUTION[str(fa_epc_yrs)].values)[:fa_epc_yrs] if str(fa_epc_yrs) in CAPEX_DISTRIBUTION else [1.0/fa_epc_yrs]*fa_epc_yrs
    
    cfs = []; acc_pv = 0.0; acc_list = []
    
    for i in range(total_yrs):
        oi = i - fa_epc_yrs; is_epc = i < fa_epc_yrs
        inv = -_c * _fracs[i] if is_epc else 0.0
        if i == fa_epc_yrs - 1: inv -= _w
        if oi == fa_op_yrs - 1: inv += _w
        if oi == 0: inv -= _s
        if i == 0: inv -= _l

        if is_epc:
            cf = inv; pv = cf / (1 + fa_marr) ** i
            acc_pv += pv; cfs.append(cf); acc_list.append(acc_pv)
            continue

        rev = (price * wif_capacity) + cb_total
        if oi == fa_op_yrs - 1: rev += (_c * fa_resid)
        costs = -(rm_total + cu_total + _base("Total Labor Costs") + (0.03 * _c)) 
        if fa_land_opt == "Rent": costs -= fa_land_rent

        ebt = rev + costs + _dep_ann
        tax = -max(0.0, ebt) * fa_tax
        # Cash Flow = Net Profit + Dep (add-back) + Investment
        cf = (ebt + tax) - _dep_ann + inv
        pv = cf / (1 + fa_marr) ** i
        acc_pv += pv; cfs.append(cf); acc_list.append(acc_pv)
    return cfs, acc_list

def _solve_msp():
    if not _HAS_SCIPY: return None
    try: return brentq(lambda p: _get_project_arrays(p)[1][-1], 0.01, 1e7, xtol=0.01)
    except: return None

# Fixed Price Logic: Store in a state key separate from the widget key
price_state_key = f"p_state_{scenario_name}"

if price_state_key not in st.session_state:
    ip = safe_val(d, "Main Product Price", 0.0) #
    if ip <= 0:
        with st.spinner("Calculating Initial MSP..."):
            res = _solve_msp()
            st.session_state[price_state_key] = res if res else 100.0
    else:
        st.session_state[price_state_key] = ip

# Control Row
c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    # Use 'value' pointing to state, NOT 'key' to avoid API error
    eff_p = st.number_input(f"Selling Price ({prod_unit})", value=float(st.session_state[price_state_key]), step=1.0)
    st.session_state[price_state_key] = eff_p
with c2:
    if st.button("Calculate MSP (NPV=0)", type="primary", use_container_width=True):
        if _HAS_SCIPY:
            st.session_state[price_state_key] = _solve_msp()
            st.rerun()
        else: st.error("Scipy not installed.")
with c3:
    if st.button("Reset to Input Price", use_container_width=True):
        st.session_state[price_state_key] = safe_val(d, "Main Product Price", 0.0); st.rerun() #

# Data Generation
cfs_main, acc_main = _get_project_arrays(st.session_state[price_state_key])

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4: FINANCIAL DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
_t_lo = 1.0 + (safe_val(d, "TIC Lower Pct", -25.0)/100.0) #
_t_hi = 1.0 + (safe_val(d, "TIC Upper Pct", 40.0)/100.0) #
_, acc_lo = _get_project_arrays(st.session_state[price_state_key], _t_lo)
_, acc_hi = _get_project_arrays(st.session_state[price_state_key], _t_hi)

g_col, k_col = st.columns([3, 1])
with g_col:
    cal_yrs = [int(d.get("Year of Analysis", 2024)) + i for i in range(fa_epc_yrs + fa_op_yrs)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cal_yrs + cal_yrs[::-1], y=[v/1e6 for v in acc_hi] + [v/1e6 for v in acc_lo][::-1], fill='toself', fillcolor='rgba(88,166,255,0.1)', line=dict(color='rgba(0,0,0,0)'), name='TIC Sensitivity'))
    fig.add_trace(go.Scatter(x=cal_yrs, y=[v/1e6 for v in acc_main], name="Base Case", line=dict(color='#58a6ff', width=3)))
    
    pb_idx = next((i for i, v in enumerate(acc_main) if v >= 0), None)
    if pb_idx:
        fig.add_trace(go.Scatter(x=[cal_yrs[pb_idx]], y=[0], mode='markers', name="Payback", marker=dict(color='#e6a817', size=12, symbol='diamond')))
    
    pk_v = min(acc_main); pk_idx = acc_main.index(pk_v)
    fig.add_trace(go.Scatter(x=[cal_yrs[pk_idx]], y=[pk_v/1e6], mode='markers', name="Peak Debt", marker=dict(color='#f85149', size=10)))
    
    fig.add_vline(x=cal_yrs[fa_epc_yrs-1], line_dash="dash", line_color="#6e7681")
    fig.update_layout(template="plotly_dark", height=450, yaxis_title="MMUSD", hovermode="x unified")
    fig.add_hline(y=0, line_color="white", opacity=0.2)
    st.plotly_chart(fig, use_container_width=True)

with k_col:
    section_header("Key Metrics", "#e6a817") #
    kpi_card("Project NPV", smart_fmt(acc_main[-1]), "#58a6ff") #
    irr_v = npf.irr(cfs_main) if _HAS_NPF else 0.0
    kpi_card("Project IRR", f"{irr_v*100:.2f}%" if irr_v else "N/A", "#3fb950") #
    kpi_card("Payback Period", f"{pb_idx - fa_epc_yrs if pb_idx else 'N/A'} yrs", "#e6a817") #
    kpi_card("Peak Investment", smart_fmt(abs(pk_v)), "#f85149") #
