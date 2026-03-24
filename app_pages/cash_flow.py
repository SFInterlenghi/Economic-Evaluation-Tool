"""ISI-Tool — Cash Flow & Analysis page.

Section 1: Variable cost tables with editable prices + reset buttons (original)
Section 2: Side-by-side base case vs. what-if for TIC, labor, % factors, OPEX
Section 3: Financial Analysis Engine & Price Controls
Section 4: Unified Table & Dashboard
"""
import streamlit as st
import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
from scipy.optimize import brentq

try:
    import numpy_financial as npf
    _HAS_NPF = True
except ImportError:
    _HAS_NPF = False

from utils.constants import (
    safe_val, smart_fmt, fmt_curr, coeff_unit, is_per_year,
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
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
if "cf_selected" not in st.session_state:
    st.session_state.cf_selected = list(scenarios.keys())[0]
if "cf_session_defaults" not in st.session_state:
    st.session_state.cf_session_defaults = {}
if "cf_working" not in st.session_state:
    st.session_state.cf_working = {}
if "cf_wif" not in st.session_state:
    st.session_state.cf_wif = {}    # what-if overrides for TIC/OPEX params

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
        if tbl not in sd:
            sd[tbl] = dict(inp)
        if tbl not in wk:
            wk[tbl] = dict(sd[tbl])

# ── Header ────────────────────────────────────────────────────────────────────
page_header("Cash Flow & Analysis", "Interactive economic analysis — scenario-based")

# ── Scenario selector ─────────────────────────────────────────────────────────
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
        to_pop = [k for k in st.session_state
                  if k.startswith(f"cf_{scenario_name}_") or k.startswith(f"wif_{scenario_name}_")]
        for k in to_pop:
            st.session_state.pop(k, None)
        st.rerun()

# ── Scenario summary KPIs ────────────────────────────────────────────────────
prod_name = d.get("Product Name", "—")
prod_unit = d.get("Unit", "")
capacity = safe_val(d, "Capacity")
tic = safe_val(d, "Total Investment")
opex = safe_val(d, "Total OPEX")

section_header("Scenario summary", "#58a6ff")
c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("Main Product", prod_name, "#e6a817",
             "Capacity", f"{capacity:,.0f} {prod_unit}/year")
with c2:
    kpi_card("Total Investment Cost (TIC)", smart_fmt(tic), "#58a6ff")
with c3:
    kpi_card("Total Annual OPEX", smart_fmt(opex), "#3fb950")

st.space("medium")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1: VARIABLE COST TABLES
# ═════════════════════════════════════════════════════════════════════════════
section_header("Variable costs & credits", "#58a6ff")

working_hours = safe_val(d, "Working Hours per Year", 8000.0)
product_rate = capacity / working_hours if working_hours > 0 else 0.0

def _build_vc_table(table_key: str, is_credit: bool = False):
    items = d.get(table_key, []) or []
    items = [r for r in items if r.get("Name")]
    if not items:
        st.caption("No items defined for this table in the selected scenario.")
        return [], 0.0

    wk = st.session_state.cf_working[scenario_name]
    inp = _input_prices(scenario_name, table_key)
    sd = st.session_state.cf_session_defaults[scenario_name].get(table_key, inp)
    if table_key not in wk:
        wk[table_key] = dict(sd)

    total_cost = 0.0
    rows = []
    for r in items:
        name = r["Name"]
        rate = float(r.get("Rate", 0.0))
        rate_unit = r.get("Rate Unit", "")
        p_unit = r.get("Price Unit", "")
        if is_per_year(rate_unit):
            coeff = rate / capacity if capacity else 0.0
        else:
            coeff = rate / product_rate if product_rate else 0.0
        c_unit = coeff_unit(rate_unit, prod_unit)
        curr_price = wk[table_key].get(name, inp.get(name, 0.0))
        input_def = inp.get(name, 0.0)
        sess_def = sd.get(name, input_def)
        modified = abs(curr_price - input_def) > 1e-9
        spec_cost = curr_price * coeff
        line_cost = curr_price * rate * (1.0 if is_per_year(rate_unit) else working_hours)
        total_cost += line_cost
        rows.append({
            "name": name, "rate": rate, "rate_unit": rate_unit,
            "coeff": coeff, "coeff_unit": c_unit,
            "price": curr_price, "price_unit": p_unit,
            "input_default": input_def, "sess_default": sess_def,
            "modified": modified, "spec_cost": spec_cost, "line_cost": line_cost,
        })

    pct_total = total_cost if total_cost > 0 else 1.0
    header = """
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:.8rem">
    <thead><tr style="border-bottom:2px solid #21262d">
        <th style="padding:.5rem .7rem;text-align:left;color:#8b949e;min-width:160px">Name</th>
        <th style="padding:.5rem .7rem;text-align:center;color:#58a6ff;min-width:130px">Price (editable)</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:90px">Price Unit</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:110px">Tech. Coeff.</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:110px">Coeff. Unit</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#3fb950;min-width:120px">Cost/year</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#3fb950;min-width:60px">%</th>
    </tr></thead><tbody>
    """
    body_rows = []
    for row in rows:
        bg = "#2d2a1a" if row["modified"] else "#1c2d3a"
        bdr = "#e6a817" if row["modified"] else "#58a6ff"
        fc = "#e6a817" if row["modified"] else "#58a6ff"
        pct = row["line_cost"] / pct_total * 100 if not is_credit else 0.0
        body_rows.append(
            f'<tr style="border-bottom:1px solid #21262d22">'
            f'<td style="padding:.4rem .7rem;color:#c9d1d9">{row["name"]}</td>'
            f'<td style="padding:.3rem .7rem;text-align:center;background:{bg};border-left:2px solid {bdr}">'
            f'<span style="font-family:DM Mono,monospace;font-size:.85rem;color:{fc};font-weight:500">'
            f'{row["price"]:.6g}</span></td>'
            f'<td style="padding:.4rem .7rem;text-align:right;color:#8b949e">{row["price_unit"]}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#c9d1d9">{row["coeff"]:.4f}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;color:#8b949e">{row["coeff_unit"]}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#3fb950;background:#161b22">{smart_fmt(row["line_cost"])}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#3fb950;background:#161b22">{"—" if is_credit else f"{pct:.2f}%"}</td>'
            f'</tr>'
        )
    body_rows.append(
        f'<tr style="border-top:2px solid #21262d;background:#1a2030">'
        f'<td colspan="5" style="padding:.5rem .7rem;color:#e6edf3;font-weight:600">TOTAL</td>'
        f'<td style="padding:.5rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#e6edf3;font-weight:600">{smart_fmt(total_cost)}</td>'
        f'<td style="padding:.5rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#e6edf3;font-weight:600">{"—" if is_credit else "100.00%"}</td>'
        f'</tr>'
    )
    st.markdown(header + "".join(body_rows) + "</tbody></table></div>", unsafe_allow_html=True)

    st.space("small")
    changed = False
    for row in rows:
        name = row["name"]; inp_def = row["input_default"]
        wgt_key = f"cf_{scenario_name}_{table_key}_{name}"
        col_lbl, col_inp, col_btn = st.columns([2, 1, 1])
        with col_lbl: st.markdown(f'<p style="font-size:.82rem;color:#8b949e;margin:0;padding:.45rem 0">{name}</p>', unsafe_allow_html=True)
        with col_inp:
            new_val = st.number_input(name, value=float(row["price"]), min_value=0.0, step=0.001, format="%.6f", key=wgt_key, label_visibility="collapsed")
            if abs(new_val - row["price"]) > 1e-12:
                wk[table_key][name] = new_val; changed = True
        with col_btn:
            if st.button(f"↩ {inp_def:.4g}", key=f"rst_{wgt_key}", disabled=not row["modified"]):
                wk[table_key][name] = inp_def; st.session_state.pop(wgt_key, None); changed = True
    if changed: st.rerun()
    return rows, total_cost

st.markdown("#### Raw Materials")
rm_rows, rm_total = _build_vc_table("Raw Materials")
st.markdown("#### Chemical Inputs & Utilities")
cu_rows, cu_total = _build_vc_table("Chemical Inputs and Utilities")
st.markdown("#### Credits & Byproducts")
cb_rows, cb_total = _build_vc_table("Credits and Byproducts", is_credit=True)
tvc_net = rm_total + cu_total - cb_total

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2: WHAT-IF ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### What-If Analysis")
st.caption("Modify parameters below to see how they affect TIC and OPEX.")

def _base(key, default=0.0):
    v = d.get(key, default)
    return v if isinstance(v, (int, float)) else default

def _editable_row(label, key, base_val, step=0.01, fmt_fn=None, suffix="", min_value=None, is_int=False):
    if fmt_fn is None: fmt_fn = lambda v: f"{v:,.2f}"
    wk = f"wif_{scenario_name}_{key}"; current = wif.get(key, base_val)
    modified = key in wif and (abs(float(wif[key]) - float(base_val)) > 1e-9)
    c1, c2, c3 = st.columns([3, 2, 2])
    with c1: st.markdown(f'<p style="margin:0;padding:.35rem 0;font-size:.82rem;color:{"#e6a817" if modified else "#8b949e"}">{label}</p>', unsafe_allow_html=True)
    with c2: st.text_input(f"base_{key}", value=f"{fmt_fn(base_val)}{suffix}", disabled=True, label_visibility="collapsed")
    with c3:
        if is_int:
            new_val = st.number_input(label, value=int(current), step=int(step), min_value=int(min_value) if min_value is not None else None, key=wk, label_visibility="collapsed")
            if int(new_val) != int(base_val): wif[key] = int(new_val)
            elif key in wif: del wif[key]
            return int(new_val)
        else:
            new_val = st.number_input(label, value=float(current), step=float(step), min_value=float(min_value) if min_value is not None else None, key=wk, label_visibility="collapsed")
            if abs(new_val - float(base_val)) > 1e-9: wif[key] = float(new_val)
            elif key in wif: del wif[key]
            return float(new_val)

def _result_row(label, base_val, wif_val, is_main=False):
    c1, c2, c3 = st.columns([3, 2, 2])
    color = "#e6a817" if is_main else "#3fb950"
    delta_str = f"  ({(wif_val-base_val)/abs(base_val)*100:+.1f}%)" if (abs(wif_val-base_val)>0.01 and base_val!=0) else ""
    with c1: st.markdown(f'<p style="margin:0;padding:.35rem 0;font-size:.82rem;color:{color};font-weight:{"600" if is_main else "400"}">{label}</p>', unsafe_allow_html=True)
    with c2: st.text_input(f"br_{label}", value=smart_fmt(base_val), disabled=True, label_visibility="collapsed")
    with c3: st.text_input(f"wr_{label}", value=f"{smart_fmt(wif_val)}{delta_str}", disabled=True, label_visibility="collapsed")

section_header("Capacity & operating hours", "#58a6ff")
base_capacity = _base("Capacity"); base_wh = _base("Working Hours per Year", 8000.0)
wif_capacity = _editable_row("Production capacity", "Capacity", base_capacity, step=100.0, suffix=f" {prod_unit}/yr", min_value=0.0)
wif_wh = _editable_row("Working hours per year", "Working Hours per Year", base_wh, step=100.0, suffix=" h/yr", min_value=1.0)

section_header("Investment costs (TIC)", "#e6a817")
base_equip = _base("Equipment Acquisition"); base_cont_pct = _base("Contingency Pct"); base_loc_factor = _base("Location Factor", 1.0)
wif_equip = _editable_row("Equipment acquisition", "Equipment Acquisition", base_equip, step=1000.0, fmt_fn=lambda v: smart_fmt(v))
wif_cont_pct = _editable_row("Project contingency (%)", "wif_Contingency_Pct", base_cont_pct * 100, step=1.0, suffix="%") / 100.0
wif_loc_factor = _editable_row("Location factor", "Location Factor", base_loc_factor, step=0.01)

base_isbl_osbl = _base("Project Costs ISBL+OSBL"); wif_isbl_osbl = base_isbl_osbl * (wif_equip / base_equip if base_equip > 0 else 1.0)
base_tuf = _base("Time Update Factor", 1.0); base_capex = _base("Project CAPEX")
wif_capex = wif_isbl_osbl * (1 + wif_cont_pct) * base_tuf * wif_loc_factor
_result_row("Project CAPEX", base_capex, wif_capex, is_main=True)

base_wc = _base("Working Capital"); wif_wc = base_wc * (wif_capex / base_capex) if base_capex > 0 else base_wc
base_startup = _base("Startup Costs"); wif_startup = base_startup * (wif_capex / base_capex) if base_capex > 0 else base_startup
wif_tic = wif_capex + wif_wc + wif_startup + _base("Additional Costs")
_result_row("TOTAL INVESTMENT COST", _base("Total Investment"), wif_tic, is_main=True)

section_header("Fixed costs — Labor", "#3fb950")
wif_n_ops = _editable_row("Operators per shift", "Num Operators", d.get("Num Operators", 2), step=1, is_int=True, min_value=1)
wif_op_sal = _editable_row("Operator salary (USD/month)", "Operator Salary", d.get("Operator Salary", 1247.75), step=10.0, min_value=273.0)
wif_sal_charges = _editable_row("Salary charges multiplier", "Salary Charges", d.get("Salary Charges", 2.2), step=0.05, min_value=1.0)
wif_olc = (wif_n_ops * wif_op_sal + d.get("Num Supervisors", 1) * d.get("Supervisor Salary", 1660.155)) * wif_sal_charges * d.get("Operating Team Factor", 5) * 12.0
wif_labor = wif_olc * (1.0 + _base("Lab Charges Pct") + _base("Office Labor Pct"))
_result_row("TOTAL LABOR COSTS", _base("Total Labor Costs"), wif_labor, is_main=True)

section_header("Maintenance & Overhead", "#3fb950")
wif_maint_pct = _editable_row("Maintenance & repairs (% of CAPEX)", "Maint Pct", _base("Maint Pct") * 100, step=0.1, suffix="%") / 100.0
wif_supply_maint = (wif_maint_pct * 1.1) * wif_capex
wif_afc_fixed = (wif_olc * _base("Admin Ov Pct")) + (wif_capex * (_base("Mfg Ov Pct") + _base("Taxes Ins Pct")))
wif_ind_fixed = (wif_olc * _base("Admin Costs Pct")) + (wif_capex * _base("Mfg Costs Pct"))

# OPEX solve analytical
_num = (tvc_net + wif_labor + wif_supply_maint + wif_afc_fixed + wif_ind_fixed)
_den = 1.0 - _base("Patents Pct") - _base("Dist Sell Pct") - _base("R D Pct")
wif_opex = _num / _den if _den > 0 else 0.0
wif_afc = wif_afc_fixed + (wif_opex * _base("Patents Pct"))
wif_indirect = wif_ind_fixed + (wif_opex * (_base("Dist Sell Pct") + _base("R D Pct")))
_result_row("TOTAL OPEX", _base("Total OPEX"), wif_opex, is_main=True)

# ═════════════════════════════════════════════════════════════════════════════
# FINANCIAL ASSUMPTIONS PANEL
# ═════════════════════════════════════════════════════════════════════════════
from utils.constants import CAPEX_DISTRIBUTION, TAXES_BY_COUNTRY, COUNTRY_LIST

if "cf_fin" not in st.session_state: st.session_state.cf_fin = {}
if scenario_name not in st.session_state.cf_fin: st.session_state.cf_fin[scenario_name] = {}
_fin = st.session_state.cf_fin[scenario_name]

def _fin_row(label, key, base_val, step=0.01, fmt=".2f", suffix="", min_val=None, is_int=False, computed_val=None, bold=False):
    mod = key in _fin and not str(key).startswith("_")
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1: st.markdown(f'<p style="margin:0;padding:.32rem 0;font-size:.9rem;color:{"#e6a817" if mod else "#c9d1d9"};{"font-weight:600;" if bold else ""}">{label}</p>', unsafe_allow_html=True)
    if computed_val is not None:
        with c2: st.markdown(f'<p style="margin:0;padding:.32rem 0;font-size:.9rem;font-family:DM Mono,monospace;color:#3fb950;font-weight:600;text-align:right">{computed_val*100:{fmt}}%</p>' if suffix=="%" else f'<p style="margin:0;padding:.32rem 0;font-size:.9rem;font-family:DM Mono,monospace;color:#3fb950;font-weight:600;text-align:right">{computed_val:{fmt}}{suffix}</p>', unsafe_allow_html=True)
        return computed_val
    current = _fin.get(key, base_val)
    wk = f"cffin_{scenario_name}_{key}"
    with c2:
        if is_int:
            new_val = st.number_input(label, value=int(current), min_value=int(min_val) if min_val else None, step=1, key=wk, label_visibility="collapsed")
            if int(new_val) != int(base_val): _fin[key] = int(new_val)
            elif key in _fin: del _fin[key]
        else:
            dv = float(current)*100.0 if suffix=="%" else float(current)
            new_disp = st.number_input(label, value=dv, step=float(step), format=f"%{fmt}", key=wk, label_visibility="collapsed")
            new_val = new_disp/100.0 if suffix=="%" else new_disp
            if abs(new_val - float(base_val)) > 1e-9: _fin[key] = new_val
            elif key in _fin: del _fin[key]
    with c3:
        if st.button("↩", key=f"rst_{wk}", disabled=not mod):
            _fin.pop(key, None); st.session_state.pop(wk, None); st.rerun()
    return _fin.get(key, base_val)

with st.expander("**Financial Assumptions**", expanded=False, icon=":material/settings:"):
    st.markdown("---")
    col_l, col_m, col_r = st.columns(3)
    with col_l:
        section_header("Land & Depreciation", "#e6a817")
        fa_land_opt = st.radio("Land option", ["Buy", "Rent"], index=0 if _fin.get("Land Option", "Buy")=="Buy" else 1, horizontal=True)
        _fin["Land Option"] = fa_land_opt
        fa_land_buy = (wif_isbl_osbl * _fin_row("Land purchase (% of ISBL)", "Land Buy Pct", 2.0, suffix="%") / 100.0) if fa_land_opt=="Buy" else 0.0
        fa_land_rent = (wif_isbl_osbl * _fin_row("Land rent (% of ISBL/yr)", "Land Rent Pct", 0.2, suffix="%") / 100.0) if fa_land_opt=="Rent" else 0.0
        fa_dep_yrs = _fin_row("Depreciation period (years)", "Depreciation Years", 10, is_int=True, min_val=1)
        fa_resid_pct = _fin_row("Residual value (% of CAPEX)", "Residual Value Pct", 20.0, suffix="%") / 100.0
    with col_m:
        section_header("Project Timeline", "#58a6ff")
        fa_op_yrs = _fin_row("Project lifetime (years)", "Project Lifetime", 20, is_int=True, min_val=1)
        fa_epc_yrs = _fin_row("EPC time (years)", "EPC Years", 3, is_int=True, min_val=1)
        _ref_fracs = list(CAPEX_DISTRIBUTION[str(fa_epc_yrs)].values)[:fa_epc_yrs]
        _fa_capex_fracs = _ref_fracs # Simplified for stability
        fa_tax = _fin_row("Tax rate", "Tax Rate", 0.34, suffix="%")
    with col_r:
        section_header("Financial Parameters", "#58a6ff")
        fa_cbr = _fin_row("Central Bank Rate", "CBR", 5.45, suffix="%")
        fa_cs = _fin_row("Credit Spread", "CS", 2.94, suffix="%")
        fa_cod = (fa_cbr + fa_cs) * (1 - fa_tax) / 100.0
        _fin_row("Cost of Debt (COD)", "_cod", fa_cod, computed_val=fa_cod, bold=True)
        fa_marr = _fin_row("MARR (%)", "MARR", 10.0, suffix="%", bold=True) / 100.0

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: CALCULATION ENGINE & PRICE CONTROLS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
section_header("Financial Analysis Controls", "#58a6ff")

# Shared Engine for Solvers, Table, and Dashboard
def _get_project_data(price, capex_mult=1.0):
    _c = wif_capex * capex_mult
    _w = wif_wc * capex_mult
    _s = wif_startup * capex_mult
    _l = fa_land_buy * capex_mult
    _dep_ann = -(_c * (1 - fa_resid_pct)) / fa_dep_yrs if fa_dep_yrs > 0 else 0.0
    
    total_yrs = fa_epc_yrs + fa_op_yrs
    cfs = []; acc_pv = 0.0; acc_list = []
    
    for i in range(total_yrs):
        oi = i - fa_epc_yrs
        is_epc = i < fa_epc_yrs
        
        # Investment
        inv = -_c * _fa_capex_fracs[i] if is_epc else 0.0
        if i == fa_epc_yrs - 1: inv -= _w
        if oi == fa_op_yrs - 1: inv += _w
        if oi == 0: inv -= _s
        if i == 0: inv -= _l

        # Financing
        f_int = 0.0; f_amort = 0.0
        if d.get("Financing Type") != "None":
            _tot_d = _c * d.get("Debt Ratio Pct", 50.0)/100.0
            f_int = -_tot_d * fa_cod
            if oi >= 0 and oi < 10: f_amort = -(_tot_d / 10) # Simplified

        if is_epc:
            cf = inv + f_int + f_amort
            pv = cf / (1 + fa_marr) ** i
            acc_pv += pv
            cfs.append(cf); acc_list.append(acc_pv)
            continue

        # Operations
        cp = 1.0; fp = 1.0 # Simplified factors for dashboard sync
        rev = (price * wif_capacity * cp) + cb_total
        if oi == fa_op_yrs - 1: rev += (_c * fa_resid_pct)
        costs = -(rm_total + cu_total + wif_labor + (wif_maint_pct * _c))
        if fa_land_opt == "Rent": costs -= fa_land_rent

        ebt = rev + costs + _dep_ann + f_int
        tax = -max(0.0, ebt) * fa_tax
        # CF = Net Profit + Dep (add-back) + Amort + Inv
        cf = (ebt + tax) - _dep_ann + f_amort + inv
        pv = cf / (1 + fa_marr) ** i
        acc_pv += pv
        cfs.append(cf); acc_list.append(acc_pv)
        
    return cfs, acc_list

def _solve_for_npv(target_mm):
    try: return brentq(lambda p: _get_project_data(p)[1][-1] - (target_mm * 1e6), 0.01, 1e7, xtol=0.01)
    except: return None

# Price Synchronization
price_key = f"active_price_{scenario_name}"
if price_key not in st.session_state:
    input_p = safe_val(d, "Main Product Price", 0.0)
    if input_p <= 0:
        res = _solve_for_npv(0.0)
        st.session_state[price_key] = res if res else 100.0
    else:
        st.session_state[price_key] = input_p

c1, c2, c3, c4 = st.columns([2.5, 2, 2, 2])
with c1:
    eff_price = st.number_input(f"Selling Price ({prod_unit})", key=price_key, step=1.0)
with c2:
    if st.button("Calculate MSP (NPV=0)", type="primary", use_container_width=True):
        res = _solve_for_npv(0.0)
        if res: st.session_state[price_key] = res; st.rerun()
with c3:
    t_irr = st.number_input("Target IRR (%)", value=15.0, step=0.5)
    if st.button("Solve for IRR", use_container_width=True):
        if _HAS_NPF:
            res = brentq(lambda p: npf.irr(_get_project_data(p)[0]) - t_irr/100, 0.01, 1e7, xtol=0.01)
            if res: st.session_state[price_key] = res; st.rerun()
with c4:
    t_npv = st.number_input("Target NPV (MMUSD)", value=0.0, step=10.0)
    if st.button("Solve for NPV", use_container_width=True):
        res = _solve_for_npv(t_npv)
        if res: st.session_state[price_key] = res; st.rerun()

# Data Generation
cfs_main, acc_main = _get_project_data(eff_price)

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4: FINANCIAL DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
section_header("Financial Dashboard", "#58a6ff")

_tic_lo_m = 1.0 + (safe_val(d, "TIC Lower Pct", -25.0)/100.0)
_tic_hi_m = 1.0 + (safe_val(d, "TIC Upper Pct", 40.0)/100.0)
_, acc_lo = _get_project_data(eff_price, _tic_lo_m)
_, acc_hi = _get_project_data(eff_price, _tic_hi_m)

g_col, k_col = st.columns([3, 1])
with g_col:
    cal_yrs = [int(d.get("Year of Analysis", 2024)) + i for i in range(fa_epc_yrs + fa_op_yrs)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cal_yrs + cal_yrs[::-1], y=[v/1e6 for v in acc_hi] + [v/1e6 for v in acc_lo][::-1], fill='toself', fillcolor='rgba(88,166,255,0.08)', line=dict(color='rgba(0,0,0,0)'), name='TIC Sensitivity'))
    fig.add_trace(go.Scatter(x=cal_yrs, y=[v/1e6 for v in acc_main], name="Base Case", line=dict(color='#58a6ff', width=3)))
    
    pb_idx = next((i for i, v in enumerate(acc_main) if v >= 0), None)
    if pb_idx: fig.add_trace(go.Scatter(x=[cal_yrs[pb_idx]], y=[0], mode='markers', name="Payback", marker=dict(color='#e6a817', size=12, symbol='diamond')))
    
    peak_v = min(acc_main); peak_idx = acc_main.index(peak_v)
    fig.add_trace(go.Scatter(x=[cal_yrs[peak_idx]], y=[peak_v/1e6], mode='markers', name="Peak Debt", marker=dict(color='#f85149', size=10)))
    
    fig.add_vline(x=cal_yrs[fa_epc_yrs-1], line_dash="dash", line_color="#6e7681")
    fig.update_layout(template="plotly_dark", height=450, yaxis_title="MMUSD", hovermode="x unified", legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    fig.add_hline(y=0, line_color="white", opacity=0.2)
    st.plotly_chart(fig, use_container_width=True)

with k_col:
    section_header("Key Metrics", "#e6a817")
    kpi_card("Project NPV", smart_fmt(acc_main[-1]), "#58a6ff")
    irr_val = npf.irr(cfs_main) if _HAS_NPF else 0
    kpi_card("Project IRR", f"{irr_val*100:.2f}%", "#3fb950")
    kpi_card("Payback Point", f"{pb_idx - fa_epc_yrs if pb_idx else 'N/A'} yrs", "#e6a817")
    kpi_card("Peak Investment", smart_fmt(abs(peak_v)), "#f85149")
