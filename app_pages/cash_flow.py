"""ISI-Tool — Cash Flow & Analysis page.

Section 1: Variable cost tables with editable prices
Section 2: What-If Analysis for TIC & OPEX
Financial Assumptions: Land, Taxes, MARR, EPC, etc.
Section 3: Financial Analysis (Unified Table) & Price Solvers
Section 4: Financial Dashboard (Graph & KPIs)
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
    CAPEX_DISTRIBUTION, TAXES_BY_COUNTRY, COUNTRY_LIST
)
from utils.ui import inject_css, page_header, section_header, kpi_card

inject_css()

# ── Guard ─────────────────────────────────────────────────────────────────────
if "scenarios" not in st.session_state or not st.session_state.scenarios:
    page_header("Cash Flow & Analysis")
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
if "cf_fin" not in st.session_state:
    st.session_state.cf_fin = {}

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
    if scenario_name not in st.session_state.cf_fin:
        st.session_state.cf_fin[scenario_name] = {}
    for tbl in ["Raw Materials", "Chemical Inputs and Utilities", "Credits and Byproducts"]:
        inp = _input_prices(scenario_name, tbl)
        sd = st.session_state.cf_session_defaults[scenario_name]
        wk = st.session_state.cf_working[scenario_name]
        if tbl not in sd: sd[tbl] = dict(inp)
        if tbl not in wk: wk[tbl] = dict(sd[tbl])

# ── Header & Selector ─────────────────────────────────────────────────────────
page_header("Cash Flow & Analysis", "Interactive economic analysis — scenario-based")

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
_fin = st.session_state.cf_fin[scenario_name]

with col_reset:
    if st.button("↺  Reset all to base case", type="secondary", use_container_width=True):
        sd = st.session_state.cf_session_defaults.get(scenario_name, {})
        st.session_state.cf_working[scenario_name] = {tbl: dict(p) for tbl, p in sd.items()}
        st.session_state.cf_wif[scenario_name] = {}
        st.session_state.cf_fin[scenario_name] = {}
        to_pop = [k for k in st.session_state if k.startswith(f"cf_{scenario_name}_") or k.startswith(f"wif_{scenario_name}_") or k.startswith(f"fin_{scenario_name}_")]
        for k in to_pop: st.session_state.pop(k, None)
        st.rerun()

# ── Initial KPIs ─────────────────────────────────────────────────────────────
prod_name = d.get("Product Name", "—")
prod_unit = d.get("Unit", "")
capacity = safe_val(d, "Capacity")
tic_base = safe_val(d, "Total Investment")
opex_base = safe_val(d, "Total OPEX")

section_header("Scenario summary", "#58a6ff")
c1, c2, c3 = st.columns(3)
with c1: kpi_card("Main Product", prod_name, "#e6a817", "Capacity", f"{capacity:,.0f} {prod_unit}/year")
with c2: kpi_card("Base TIC", smart_fmt(tic_base), "#58a6ff")
with c3: kpi_card("Base Annual OPEX", smart_fmt(opex_base), "#3fb950")

st.space("medium")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1: VARIABLE COST TABLES
# ═════════════════════════════════════════════════════════════════════════════
section_header("Variable costs & credits", "#58a6ff")

working_hours = safe_val(d, "Working Hours per Year", 8000.0)
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
        coeff = (rate / capacity) if is_per_year(rate_unit) else (rate / product_rate if product_rate else 0.0)
        line_cost = curr_price * rate * (1.0 if is_per_year(rate_unit) else working_hours)
        total_cost += line_cost
        rows.append({"name": name, "rate": rate, "rate_unit": rate_unit, "coeff": coeff, "coeff_unit": coeff_unit(rate_unit, prod_unit), "price": curr_price, "price_unit": p_unit, "input_def": inp.get(name, 0.0), "modified": abs(curr_price - inp.get(name, 0.0)) > 1e-9, "line_cost": line_cost})

    header = '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:.8rem"><thead><tr style="border-bottom:2px solid #21262d"><th style="padding:.5rem .7rem;text-align:left;color:#8b949e">Name</th><th style="padding:.5rem .7rem;text-align:center;color:#58a6ff">Price</th><th style="padding:.5rem .7rem;text-align:right;color:#8b949e">Unit</th><th style="padding:.5rem .7rem;text-align:right;color:#3fb950">Cost/year</th><th style="padding:.5rem .7rem;text-align:right;color:#3fb950">%</th></tr></thead><tbody>'
    body = ""
    for r in rows:
        pct = (r["line_cost"] / total_cost * 100) if total_cost and not is_credit else 0.0
        bg = "#2d2a1a" if r["modified"] else "transparent"
        body += f'<tr style="background:{bg};border-bottom:1px solid #21262d22"><td style="padding:.4rem .7rem;color:#c9d1d9">{r["name"]}</td><td style="padding:.4rem .7rem;text-align:center;color:{"#e6a817" if r["modified"] else "#58a6ff"}">{r["price"]:.6g}</td><td style="padding:.4rem .7rem;text-align:right;color:#8b949e">{r["price_unit"]}</td><td style="padding:.4rem .7rem;text-align:right;color:#3fb950">{smart_fmt(r["line_cost"])}</td><td style="padding:.4rem .7rem;text-align:right;color:#3fb950">{"—" if is_credit else f"{pct:.1f}%"}</td></tr>'
    
    st.markdown(header + body + f'<tr style="border-top:2px solid #21262d;background:#1a2030"><td colspan="3" style="padding:.5rem .7rem;color:#e6edf3;font-weight:600">TOTAL</td><td style="padding:.5rem .7rem;text-align:right;color:#e6edf3;font-weight:600">{smart_fmt(total_cost)}</td><td></td></tr></tbody></table></div>', unsafe_allow_html=True)

    changed = False
    for r in rows:
        col_l, col_i, col_b = st.columns([2, 1, 1])
        with col_l: st.markdown(f'<p style="font-size:.82rem;color:#8b949e;margin:0;padding:.45rem 0">{r["name"]}</p>', unsafe_allow_html=True)
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
tvc_net_current = rm_total + cu_total - cb_total

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2: WHAT-IF ANALYSIS (TIC & OPEX)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
section_header("What-If Analysis", "#58a6ff")

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

section_header("Capacity & operating hours", "#58a6ff")
wif_capacity = _edit_row("Production capacity", "Capacity", _base("Capacity"), step=100.0)
wif_wh = _edit_row("Working hours per year", "Working Hours per Year", _base("Working Hours per Year", 8000.0), step=100.0)

section_header("Investment costs (TIC)", "#e6a817")
wif_equip = _edit_row("Equipment acquisition", "Equipment Acquisition", _base("Equipment Acquisition"), step=1000.0)
wif_cont = _edit_row("Project contingency (%)", "wif_Contingency_Pct", _base("Contingency Pct") * 100, step=1.0) / 100.0
wif_loc = _edit_row("Location factor", "Location Factor", _base("Location Factor", 1.0), step=0.01)

wif_isbl = _base("Project Costs ISBL+OSBL") * (wif_equip / _base("Equipment Acquisition") if _base("Equipment Acquisition") > 0 else 1.0)
wif_capex = wif_isbl * (1 + wif_cont) * _base("Time Update Factor", 1.0) * wif_loc
wif_wc = _base("Working Capital") * (wif_capex / _base("Project CAPEX") if _base("Project CAPEX") > 0 else 1.0)
wif_startup = _base("Startup Costs") * (wif_capex / _base("Project CAPEX") if _base("Project CAPEX") > 0 else 1.0)
wif_tic = wif_capex + wif_wc + wif_startup + _base("Additional Costs")

kpi_c1, kpi_c2 = st.columns(2)
with kpi_c1: kpi_card("Modified CAPEX", smart_fmt(wif_capex), "#e6a817")
with kpi_c2: kpi_card("Modified TIC", smart_fmt(wif_tic), "#58a6ff")

section_header("Labor & Fixed Costs", "#3fb950")
wif_n_ops = _edit_row("Operators per shift", "Num Operators", d.get("Num Operators", 2), step=1)
wif_op_sal = _edit_row("Operator salary (USD/mo)", "Operator Salary", d.get("Operator Salary", 1247.75), step=10.0)
wif_sal_charges = _edit_row("Salary charges multiplier", "Salary Charges", d.get("Salary Charges", 2.2), step=0.05)
wif_olc = (wif_n_ops * wif_op_sal + d.get("Num Supervisors", 1) * d.get("Supervisor Salary", 1660.155)) * wif_sal_charges * d.get("Operating Team Factor", 5) * 12.0
wif_labor = wif_olc * (1.0 + _base("Lab Charges Pct") + _base("Office Labor Pct"))
wif_maint_pct = _edit_row("Maintenance & repairs (% of CAPEX)", "Maint Pct", _base("Maint Pct") * 100, step=0.1) / 100.0
wif_supply_maint = (wif_maint_pct * 1.1) * wif_capex

# ═════════════════════════════════════════════════════════════════════════════
# FINANCIAL ASSUMPTIONS PANEL
# ═════════════════════════════════════════════════════════════════════════════
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
        section_header("Land", "#e6a817")
        fa_land_opt = st.radio("Option", ["Buy", "Rent"], index=0 if _fin.get("Land Option", "Buy")=="Buy" else 1, horizontal=True)
        _fin["Land Option"] = fa_land_opt
        fa_land_buy = (wif_isbl * _fin_input("Land purchase (%)", "Land Buy Pct", 2.0, suffix="%") / 100.0) if fa_land_opt=="Buy" else 0.0
        fa_land_rent = (wif_isbl * _fin_input("Land rent (%/yr)", "Land Rent Pct", 0.2, suffix="%") / 100.0) if fa_land_opt=="Rent" else 0.0
    with fm:
        section_header("Timeline & Taxes", "#58a6ff")
        fa_op_yrs = int(_fin_input("Project lifetime (yrs)", "Project Lifetime", 20, step=1))
        fa_epc_yrs = int(_fin_input("EPC time (yrs)", "EPC Years", 3, step=1))
        fa_tax = _fin_input("Tax rate (%)", "Tax Rate", 34.0, suffix="%") / 100.0
    with fr:
        section_header("Finance & Depr", "#58a6ff")
        fa_marr = _fin_input("MARR (%)", "MARR", 10.0, suffix="%") / 100.0
        fa_resid = _fin_input("Residual value (%)", "Residual Value Pct", 20.0, suffix="%") / 100.0
        fa_dep_yrs = int(_fin_input("Depreciation yrs", "Depr Years", 10, step=1))

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3: CALCULATION ENGINE & PRICE CONTROLS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
section_header("Economic Engine & Solvers", "#58a6ff")

def _get_project_arrays(price, tic_mult=1.0):
    """Central math engine for everything on this page."""
    _c = wif_capex * tic_mult; _w = wif_wc * tic_mult; _s = wif_startup * tic_mult; _l = fa_land_buy * tic_mult
    _dep_ann = -(_c * (1 - fa_resid)) / fa_dep_yrs if fa_dep_yrs > 0 else 0.0
    
    total_yrs = fa_epc_yrs + fa_op_yrs
    _fracs = list(CAPEX_DISTRIBUTION[str(fa_epc_yrs)].values)[:fa_epc_yrs] if str(fa_epc_yrs) in CAPEX_DISTRIBUTION else [1.0/fa_epc_yrs]*fa_epc_yrs
    
    cfs = []; acc_pv = 0.0; acc_list = []; rev_list = []; opex_list = []; tax_list = []; dep_list = []
    
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
            rev_list.append(0.0); opex_list.append(0.0); tax_list.append(0.0); dep_list.append(0.0)
            continue

        rev = (price * wif_capacity) + cb_total
        if oi == fa_op_yrs - 1: rev += (_c * fa_resid)
        costs = -(rm_total + cu_total + wif_labor + (wif_maint_pct * _c))
        if fa_land_opt == "Rent": costs -= fa_land_rent

        ebt = rev + costs + _dep_ann
        tax = -max(0.0, ebt) * fa_tax
        # Cash Flow = (EBT + Tax) - Depreciation (Add Back) + Investment
        cf = (ebt + tax) - _dep_ann + inv
        pv = cf / (1 + fa_marr) ** i
        acc_pv += pv; cfs.append(cf); acc_list.append(acc_pv)
        rev_list.append(rev); opex_list.append(costs); tax_list.append(tax); dep_list.append(_dep_ann)
        
    return {
        "cfs": cfs, "acc_list": acc_list, "rev": rev_list, 
        "opex": opex_list, "tax": tax_list, "dep": dep_list
    }

def _solve_msp():
    if not _HAS_SCIPY: return None
    try: return brentq(lambda p: _get_project_arrays(p)["acc_list"][-1], 0.01, 1e7, xtol=0.01)
    except: return None

# Fixed Price Sync Logic
price_state_key = f"p_state_{scenario_name}"
if price_state_key not in st.session_state:
    ip = safe_val(d, "Main Product Price", 0.0)
    if ip <= 0:
        with st.spinner("Solving MSP..."):
            res = _solve_msp()
            st.session_state[price_state_key] = res if res else 100.0
    else: st.session_state[price_state_key] = ip

c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
with c1:
    eff_p = st.number_input(f"Selling Price ({prod_unit})", value=float(st.session_state[price_state_key]), step=1.0)
    st.session_state[price_state_key] = eff_p
with c2:
    if st.button("Calculate MSP (NPV=0)", type="primary", use_container_width=True):
        st.session_state[price_state_key] = _solve_msp(); st.rerun()
with c3:
    if st.button("Solve for 15% IRR", use_container_width=True):
        if _HAS_SCIPY and _HAS_NPF:
            res = brentq(lambda p: npf.irr(_get_project_arrays(p)["cfs"]) - 0.15, 0.01, 1e7, xtol=0.01)
            st.session_state[price_state_key] = res; st.rerun()
with c4:
    if st.button("Reset Price", use_container_width=True):
        st.session_state[price_state_key] = safe_val(d, "Main Product Price", 0.0); st.rerun()

# Generate Result Data
results = _get_project_arrays(st.session_state[price_state_key])

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4: UNIFIED CASH FLOW TABLE
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
section_header("Unified Cash Flow Table", "#58a6ff")

cal_yrs = [int(d.get("Year of Analysis", 2024)) + i for i in range(fa_epc_yrs + fa_op_yrs)]
df_table = pd.DataFrame({
    "Year": cal_yrs,
    "Revenue (M$)": [v/1e6 for v in results["rev"]],
    "OPEX (M$)": [v/1e6 for v in results["opex"]],
    "Taxes (M$)": [v/1e6 for v in results["tax"]],
    "Cash Flow (M$)": [v/1e6 for v in results["cfs"]],
    "Accum. NPV (M$)": [v/1e6 for v in results["acc_list"]]
})
st.dataframe(df_table.style.format("{:.3f}"), use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5: FINANCIAL DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
section_header("Financial Dashboard", "#58a6ff")

_t_lo = 1.0 + (safe_val(d, "TIC Lower Pct", -25.0)/100.0)
_t_hi = 1.0 + (safe_val(d, "TIC Upper Pct", 40.0)/100.0)
acc_lo = _get_project_arrays(eff_p, _t_lo)["acc_list"]
acc_hi = _get_project_arrays(eff_p, _t_hi)["acc_list"]

g_col, k_col = st.columns([3, 1])
with g_col:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cal_yrs + cal_yrs[::-1], y=[v/1e6 for v in acc_hi] + [v/1e6 for v in acc_lo][::-1], fill='toself', fillcolor='rgba(88,166,255,0.08)', line=dict(color='rgba(0,0,0,0)'), name='TIC Sensitivity'))
    fig.add_trace(go.Scatter(x=cal_yrs, y=[v/1e6 for v in results["acc_list"]], name="Base Case", line=dict(color='#58a6ff', width=3)))
    
    pb_idx = next((i for i, v in enumerate(results["acc_list"]) if v >= 0), None)
    if pb_idx: fig.add_trace(go.Scatter(x=[cal_yrs[pb_idx]], y=[0], mode='markers', name="Payback", marker=dict(color='#e6a817', size=12, symbol='diamond')))
    
    pk_v = min(results["acc_list"]); pk_idx = results["acc_list"].index(pk_v)
    fig.add_trace(go.Scatter(x=[cal_yrs[pk_idx]], y=[pk_v/1e6], mode='markers', name="Peak Debt", marker=dict(color='#f85149', size=10)))
    
    fig.add_vline(x=cal_yrs[fa_epc_yrs-1], line_dash="dash", line_color="#6e7681")
    fig.update_layout(template="plotly_dark", height=450, yaxis_title="MMUSD", hovermode="x unified")
    fig.add_hline(y=0, line_color="white", opacity=0.2)
    st.plotly_chart(fig, use_container_width=True)

with k_col:
    section_header("Key Metrics", "#e6a817")
    kpi_card("Project NPV", smart_fmt(results["acc_list"][-1]), "#58a6ff")
    irr_v = npf.irr(results["cfs"]) if _HAS_NPF else 0.0
    kpi_card("Project IRR", f"{irr_v*100:.2f}%", "#3fb950")
    kpi_card("Payback Point", f"{pb_idx - fa_epc_yrs if pb_idx else 'N/A'} yrs", "#e6a817")
    kpi_card("Peak Investment", smart_fmt(abs(pk_v)), "#f85149")
