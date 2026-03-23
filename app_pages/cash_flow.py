"""ISI-Tool — Cash Flow & Analysis page.

Side-by-side base case vs. what-if analysis with full recalculation engine.
"""
import streamlit as st
import pandas as pd
import math
from utils.constants import (
    safe_val, smart_fmt, coeff_unit, is_per_year, fmt_curr,
    UNSCHED_FACTORS, PROJECT_CONTINGENCY, LAB_CHARGES, OFFICE_LABOR,
    MAINTENANCE_REPAIRS, OPERATING_SUPPLIES, ADMIN_OVERHEAD, MFG_OVERHEAD,
    TAXES_INSURANCE, PATENTS_ROYALTIES, DIST_SELLING, R_AND_D,
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
# SESSION STATE — what-if overrides
# ─────────────────────────────────────────────────────────────────────────────
# cf_wif[scenario_name] = {key: value}  — only stores CHANGED values
# If a key is absent from cf_wif, the base case value is used.

if "cf_selected" not in st.session_state:
    st.session_state.cf_selected = list(scenarios.keys())[0]
if "cf_wif" not in st.session_state:
    st.session_state.cf_wif = {}
if "cf_vc_prices" not in st.session_state:
    st.session_state.cf_vc_prices = {}  # {scenario: {table: {item: price}}}


def _wif(scenario_name: str) -> dict:
    """Return the what-if override dict for a scenario (creates if needed)."""
    if scenario_name not in st.session_state.cf_wif:
        st.session_state.cf_wif[scenario_name] = {}
    return st.session_state.cf_wif[scenario_name]


def _vc_prices(scenario_name: str) -> dict:
    """Return the variable cost price overrides for a scenario."""
    if scenario_name not in st.session_state.cf_vc_prices:
        st.session_state.cf_vc_prices[scenario_name] = {}
    return st.session_state.cf_vc_prices[scenario_name]


# ── Header ────────────────────────────────────────────────────────────────────
page_header("Cash Flow & Analysis", "What-if analysis — base case vs. modified")

# ── Scenario selector ─────────────────────────────────────────────────────────
col_sel, col_reset = st.columns([3, 1])
with col_sel:
    prev = st.session_state.cf_selected
    chosen = st.selectbox("Select scenario", list(scenarios.keys()),
                          index=list(scenarios.keys()).index(st.session_state.cf_selected),
                          label_visibility="collapsed", key="cf_scenario_sel")
if chosen != prev:
    st.session_state.cf_selected = chosen
    st.rerun()

scenario_name = st.session_state.cf_selected
d = scenarios[scenario_name]  # base case data
wif = _wif(scenario_name)     # what-if overrides

with col_reset:
    if st.button("↺  Reset all to base case", type="secondary", use_container_width=True):
        st.session_state.cf_wif[scenario_name] = {}
        st.session_state.cf_vc_prices[scenario_name] = {}
        # Pop all widget keys for this scenario
        to_pop = [k for k in st.session_state if k.startswith(f"wif_{scenario_name}_")]
        for k in to_pop:
            st.session_state.pop(k, None)
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — side-by-side display
# ─────────────────────────────────────────────────────────────────────────────
def _get(key: str, default=0.0):
    """Get what-if value if overridden, else base case value."""
    if key in wif:
        return wif[key]
    v = d.get(key, default)
    return v if isinstance(v, (int, float)) else default


def _base(key: str, default=0.0):
    """Get base case value only."""
    v = d.get(key, default)
    return v if isinstance(v, (int, float)) else default


def _is_modified(key: str) -> bool:
    return key in wif


def _editable_row(label: str, key: str, base_val, step=0.01,
                  fmt_fn=None, suffix="", min_value=None, is_int=False):
    """
    Render a side-by-side row: Base Case (read-only) | What-If (editable).
    Returns the what-if value.
    """
    if fmt_fn is None:
        fmt_fn = lambda v: f"{v:,.2f}"

    wk = f"wif_{scenario_name}_{key}"
    current = wif.get(key, base_val)
    modified = key in wif and (
        (is_int and int(wif[key]) != int(base_val)) or
        (not is_int and abs(float(wif[key]) - float(base_val)) > 1e-9)
    )

    c1, c2, c3 = st.columns([3, 2, 2])
    with c1:
        color = "#e6a817" if modified else "#8b949e"
        st.markdown(f'<p style="margin:0;padding:.35rem 0;font-size:.82rem;color:{color}">{label}</p>',
                    unsafe_allow_html=True)
    with c2:
        # Base case — read only
        st.text_input(f"base_{key}", value=f"{fmt_fn(base_val)}{suffix}",
                      disabled=True, label_visibility="collapsed")
    with c3:
        # What-if — editable
        if is_int:
            new_val = st.number_input(
                label, value=int(current), step=int(step),
                min_value=int(min_value) if min_value is not None else None,
                key=wk, label_visibility="collapsed",
            )
            if int(new_val) != int(base_val):
                wif[key] = int(new_val)
            elif key in wif:
                del wif[key]
            return int(new_val)
        else:
            new_val = st.number_input(
                label, value=float(current), step=float(step),
                min_value=float(min_value) if min_value is not None else None,
                key=wk, label_visibility="collapsed",
            )
            if abs(new_val - float(base_val)) > 1e-9:
                wif[key] = float(new_val)
            elif key in wif:
                del wif[key]
            return float(new_val)


def _result_row(label: str, base_val: float, wif_val: float, is_main=False):
    """Render a computed result row: Base Case | What-If (both read-only)."""
    c1, c2, c3 = st.columns([3, 2, 2])
    color = "#3fb950" if not is_main else "#e6a817"
    changed = abs(wif_val - base_val) > 0.01
    delta_str = ""
    if changed and base_val != 0:
        delta_pct = (wif_val - base_val) / abs(base_val) * 100
        delta_str = f"  ({delta_pct:+.1f}%)"

    with c1:
        fw = "600" if is_main else "400"
        st.markdown(f'<p style="margin:0;padding:.35rem 0;font-size:.82rem;'
                    f'color:{color};font-weight:{fw}">{label}</p>',
                    unsafe_allow_html=True)
    with c2:
        st.text_input(f"br_{label}", value=smart_fmt(base_val),
                      disabled=True, label_visibility="collapsed")
    with c3:
        display = f"{smart_fmt(wif_val)}{delta_str}"
        st.text_input(f"wr_{label}", value=display,
                      disabled=True, label_visibility="collapsed")


def _section_cols():
    """Render the Base Case | What-If column headers."""
    c1, c2, c3 = st.columns([3, 2, 2])
    with c2:
        st.caption("**BASE CASE**")
    with c3:
        st.caption("**WHAT-IF**")


# ─────────────────────────────────────────────────────────────────────────────
# LEGEND
# ─────────────────────────────────────────────────────────────────────────────
with st.container(border=True):
    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        st.badge("Editable input", icon=":material/edit:", color="blue")
    with lc2:
        st.badge("Modified from base", icon=":material/change_circle:", color="orange")
    with lc3:
        st.badge("Computed result", icon=":material/calculate:", color="green")

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 1. CAPACITY & WORKING HOURS
# ─────────────────────────────────────────────────────────────────────────────
section_header("Capacity & operating hours", "#58a6ff")
_section_cols()

base_capacity = _base("Capacity")
base_wh = _base("Working Hours per Year", 8000.0)
prod_unit = d.get("Unit", "unit")

wif_capacity = _editable_row("Production capacity", "Capacity",
                              base_capacity, step=100.0, suffix=f" {prod_unit}/yr",
                              fmt_fn=lambda v: f"{v:,.1f}", min_value=0.0)
wif_wh = _editable_row("Working hours per year", "Working Hours per Year",
                         base_wh, step=100.0, suffix=" h/yr",
                         fmt_fn=lambda v: f"{v:,.0f}", min_value=1.0)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 2. INVESTMENT COSTS (TIC)
# ─────────────────────────────────────────────────────────────────────────────
section_header("Investment costs (TIC)", "#e6a817")
_section_cols()

# Editable
base_equip = _base("Equipment Acquisition")
base_cont_pct = _base("Contingency Pct")
base_loc_factor = _base("Location Factor", 1.0)

wif_equip = _editable_row("Equipment acquisition", "Equipment Acquisition",
                           base_equip, step=1000.0, fmt_fn=lambda v: smart_fmt(v))
wif_cont_pct = _editable_row("Project contingency (%)", "Contingency Pct",
                              base_cont_pct * 100, step=1.0, suffix="%",
                              fmt_fn=lambda v: f"{v:.1f}") / 100.0
wif_loc_factor = _editable_row("Location factor", "Location Factor",
                                base_loc_factor, step=0.01,
                                fmt_fn=lambda v: f"{v:.4f}")

# Computed — rebuild CAPEX from base structure ratios
# Use ratio of new equip / old equip to scale all costs proportionally
base_total_equip = _base("Total Equipment Costs")
equip_ratio = wif_equip / base_equip if base_equip > 0 else 1.0

base_isbl_osbl = _base("Project Costs ISBL+OSBL")
wif_isbl_osbl = base_isbl_osbl * equip_ratio

base_tuf = _base("Time Update Factor", 1.0)
base_capex = _base("Project CAPEX")
wif_capex = wif_isbl_osbl * (1 + wif_cont_pct) * base_tuf * wif_loc_factor

_result_row("Project Costs ISBL+OSBL", base_isbl_osbl, wif_isbl_osbl)
_result_row("Project CAPEX", base_capex, wif_capex, is_main=True)

st.space("small")

# Working Capital
base_wc = _base("Working Capital")
wc_method = d.get("WC Method", "Percentage")

if wc_method == "Percentage":
    base_wc_pct = _base("WC Pct", 5.0)
    wif_wc_pct = _editable_row("Working capital (% of CAPEX)", "WC Pct",
                                base_wc_pct, step=0.5, suffix="%",
                                fmt_fn=lambda v: f"{v:.1f}")
    wif_wc = wif_capex * (wif_wc_pct / 100.0)
else:
    wif_wc = base_wc * (wif_capex / base_capex) if base_capex > 0 else base_wc

_result_row("Working capital", base_wc, wif_wc)

# Startup Costs
base_startup = _base("Startup Costs")
startup_method = d.get("Startup Method", "Multiple Factors")
if startup_method == "Single Factor":
    base_su_pct = _base("Startup Single Pct", 8.0)
    wif_su_pct = _editable_row("Startup costs (% of CAPEX)", "Startup Single Pct",
                                base_su_pct, step=0.5, suffix="%",
                                fmt_fn=lambda v: f"{v:.1f}")
    wif_startup = wif_capex * (wif_su_pct / 100.0)
else:
    wif_startup = base_startup * (wif_capex / base_capex) if base_capex > 0 else base_startup

_result_row("Startup costs", base_startup, wif_startup)

base_additional = _base("Additional Costs")
base_tic = _base("Total Investment")
wif_tic = wif_capex + wif_wc + wif_startup + base_additional

_result_row("TOTAL INVESTMENT COST", base_tic, wif_tic, is_main=True)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 3. VARIABLE COSTS
# ─────────────────────────────────────────────────────────────────────────────
section_header("Variable costs", "#58a6ff")

vc_prices = _vc_prices(scenario_name)


def _build_vc_section(table_key: str, is_credit: bool = False):
    """Build variable cost table with editable prices. Returns total cost."""
    items = d.get(table_key, []) or []
    items = [r for r in items if r.get("Name")]
    if not items:
        st.caption("No items defined.")
        return 0.0

    if table_key not in vc_prices:
        vc_prices[table_key] = {}

    _section_cols()
    total_base = 0.0
    total_wif = 0.0

    for r in items:
        name = r["Name"]
        rate = float(r.get("Rate", 0.0))
        rate_unit = r.get("Rate Unit", "")
        p_unit = r.get("Price Unit", "")
        base_price = float(r.get("Price", 0.0))
        curr_price = vc_prices[table_key].get(name, base_price)

        multiplier = 1.0 if is_per_year(rate_unit) else wif_wh
        base_cost = base_price * rate * (1.0 if is_per_year(rate_unit) else base_wh)
        wif_cost = curr_price * rate * multiplier

        total_base += base_cost
        total_wif += wif_cost

        modified = abs(curr_price - base_price) > 1e-9
        wk = f"wif_{scenario_name}_vc_{table_key}_{name}"

        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            color = "#e6a817" if modified else "#8b949e"
            st.markdown(f'<p style="margin:0;padding:.35rem 0;font-size:.82rem;color:{color}">'
                        f'{name} <span style="color:#555;font-size:.7rem">({p_unit})</span></p>',
                        unsafe_allow_html=True)
        with c2:
            st.text_input(f"bvc_{table_key}_{name}", value=f"{base_price:.6g} → {smart_fmt(base_cost)}/yr",
                          disabled=True, label_visibility="collapsed")
        with c3:
            new_price = st.number_input(
                name, value=float(curr_price), min_value=0.0,
                step=0.001, format="%.6f", key=wk, label_visibility="collapsed",
            )
            if abs(new_price - base_price) > 1e-9:
                vc_prices[table_key][name] = new_price
            elif name in vc_prices[table_key]:
                del vc_prices[table_key][name]

    _result_row(f"Total {'revenue' if is_credit else 'cost'}", total_base, total_wif)
    return total_wif


st.markdown("##### Raw Materials")
wif_rm_total = _build_vc_section("Raw Materials")
st.space("small")

st.markdown("##### Chemical Inputs & Utilities")
wif_cu_total = _build_vc_section("Chemical Inputs and Utilities")
st.space("small")

st.markdown("##### Credits & Byproducts")
wif_cb_total = _build_vc_section("Credits and Byproducts", is_credit=True)

wif_tvc = wif_rm_total + wif_cu_total - wif_cb_total
base_tvc = (_base("Total Raw Material Cost") + _base("Total Chemical Inputs Utilities")
            - _base("Total Revenue"))

st.space("small")
_result_row("NET VARIABLE COSTS", base_tvc, wif_tvc, is_main=True)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 4. FIXED COSTS — LABOR
# ─────────────────────────────────────────────────────────────────────────────
section_header("Fixed costs — Labor", "#3fb950")
_section_cols()

base_n_ops = d.get("Num Operators", 2)
base_op_sal = d.get("Operator Salary", 1247.75)
base_n_sups = d.get("Num Supervisors", 1)
base_sup_sal = d.get("Supervisor Salary", 1660.155)
base_sal_charges = d.get("Salary Charges", 2.2)
base_op_team = d.get("Operating Team Factor", 5)
base_olc = _base("OLC")

wif_n_ops = _editable_row("Operators per shift", "Num Operators",
                           base_n_ops, step=1, is_int=True, min_value=1)
wif_op_sal = _editable_row("Operator salary (USD/month)", "Operator Salary",
                            base_op_sal, step=10.0, min_value=273.0,
                            fmt_fn=lambda v: f"${v:,.2f}")
wif_n_sups = _editable_row("Supervisors per shift", "Num Supervisors",
                            base_n_sups, step=1, is_int=True, min_value=1)
wif_sup_sal = _editable_row("Supervisor salary (USD/month)", "Supervisor Salary",
                             base_sup_sal, step=10.0, min_value=273.0,
                             fmt_fn=lambda v: f"${v:,.2f}")
wif_sal_charges = _editable_row("Salary charges multiplier", "Salary Charges",
                                 base_sal_charges, step=0.05, min_value=1.0,
                                 fmt_fn=lambda v: f"{v:.2f}")

# Compute OLC — use base operating team factor (schedule-dependent, not editable here)
wif_olc = (wif_n_ops * wif_op_sal + wif_n_sups * wif_sup_sal) * wif_sal_charges * base_op_team * 12.0
_result_row("Operating Labor Costs (OLC)", base_olc, wif_olc)

# Lab charges & Office labor
base_lab_pct = _base("Lab Charges Pct")
base_off_pct = _base("Office Labor Pct")

wif_lab_pct = _editable_row("Laboratory charges (% of OLC)", "Lab Charges Pct",
                              base_lab_pct * 100, step=0.1, suffix="%",
                              fmt_fn=lambda v: f"{v:.2f}") / 100.0
wif_off_pct = _editable_row("Office labor (% of OLC)", "Office Labor Pct",
                              base_off_pct * 100, step=0.1, suffix="%",
                              fmt_fn=lambda v: f"{v:.2f}") / 100.0

base_labor = _base("Total Labor Costs")
wif_labor = wif_olc * (1.0 + wif_lab_pct + wif_off_pct)
_result_row("TOTAL LABOR COSTS", base_labor, wif_labor, is_main=True)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 5. FIXED COSTS — SUPPLY & MAINTENANCE
# ─────────────────────────────────────────────────────────────────────────────
section_header("Fixed costs — Supply & maintenance", "#3fb950")
_section_cols()

base_maint_pct = _base("Maint Pct")
base_op_sup_pct = _base("Op Sup Pct")

wif_maint_pct = _editable_row("Maintenance & repairs (% of CAPEX)", "Maint Pct",
                                base_maint_pct * 100, step=0.1, suffix="%",
                                fmt_fn=lambda v: f"{v:.2f}") / 100.0
wif_op_sup_pct = _editable_row("Operating supplies (% of Maint)", "Op Sup Pct",
                                 base_op_sup_pct * 100, step=0.1, suffix="%",
                                 fmt_fn=lambda v: f"{v:.2f}") / 100.0

base_supply_maint = _base("Supply Maint Costs")
wif_supply_maint = (wif_maint_pct + wif_maint_pct * wif_op_sup_pct) * wif_capex
_result_row("SUPPLY & MAINTENANCE", base_supply_maint, wif_supply_maint, is_main=True)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 6. ADDITIONAL FIXED COSTS (AFC)
# ─────────────────────────────────────────────────────────────────────────────
section_header("Additional fixed costs (AFC)", "#3fb950")
_section_cols()

base_admin_ov = _base("Admin Ov Pct")
base_mfg_ov = _base("Mfg Ov Pct")
base_taxes_ins = _base("Taxes Ins Pct")
base_patents = _base("Patents Pct")

wif_admin_ov = _editable_row("Administrative overhead (% of OLC)", "Admin Ov Pct",
                               base_admin_ov * 100, step=0.1, suffix="%",
                               fmt_fn=lambda v: f"{v:.2f}") / 100.0
wif_mfg_ov = _editable_row("Manufacturing overhead (% of CAPEX)", "Mfg Ov Pct",
                             base_mfg_ov * 100, step=0.01, suffix="%",
                             fmt_fn=lambda v: f"{v:.4f}") / 100.0
wif_taxes_ins = _editable_row("Taxes & insurance (% of CAPEX)", "Taxes Ins Pct",
                                base_taxes_ins * 100, step=0.01, suffix="%",
                                fmt_fn=lambda v: f"{v:.4f}") / 100.0
wif_patents = _editable_row("Patents & royalties (% of OPEX)", "Patents Pct",
                              base_patents * 100, step=0.1, suffix="%",
                              fmt_fn=lambda v: f"{v:.2f}") / 100.0

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 7. INDIRECT FIXED COSTS
# ─────────────────────────────────────────────────────────────────────────────
section_header("Indirect fixed costs", "#3fb950")
_section_cols()

base_admin_costs = _base("Admin Costs Pct")
base_mfg_costs = _base("Mfg Costs Pct")
base_dist_sell = _base("Dist Sell Pct")
base_r_d = _base("R D Pct")

wif_admin_costs = _editable_row("Administrative costs (% of OLC)", "Admin Costs Pct",
                                  base_admin_costs * 100, step=0.1, suffix="%",
                                  fmt_fn=lambda v: f"{v:.2f}") / 100.0
wif_mfg_costs = _editable_row("Manufacturing costs (% of CAPEX)", "Mfg Costs Pct",
                                base_mfg_costs * 100, step=0.01, suffix="%",
                                fmt_fn=lambda v: f"{v:.4f}") / 100.0
wif_dist_sell = _editable_row("Distribution & selling (% of OPEX)", "Dist Sell Pct",
                                base_dist_sell * 100, step=0.1, suffix="%",
                                fmt_fn=lambda v: f"{v:.2f}") / 100.0
wif_r_d = _editable_row("Research & development (% of OPEX)", "R D Pct",
                          base_r_d * 100, step=0.1, suffix="%",
                          fmt_fn=lambda v: f"{v:.2f}") / 100.0

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 8. OPEX CALCULATION — analytical solve (same formula as input_data)
# ─────────────────────────────────────────────────────────────────────────────
section_header("OPEX summary", "#e6a817")

# What-if OPEX solve
_olc_coeff_w = wif_admin_ov + wif_admin_costs
_capex_coeff_w = wif_mfg_ov + wif_taxes_ins + wif_mfg_costs
_num_w = (wif_tvc + wif_labor + wif_supply_maint
          + _olc_coeff_w * wif_olc + _capex_coeff_w * wif_capex)
_den_w = 1.0 - wif_patents - wif_dist_sell - wif_r_d
wif_opex = _num_w / _den_w if _den_w > 0 else 0.0

wif_afc = (wif_admin_ov * wif_olc
           + (wif_mfg_ov + wif_taxes_ins) * wif_capex
           + wif_patents * wif_opex)
wif_indirect = (wif_admin_costs * wif_olc
                + wif_mfg_costs * wif_capex
                + (wif_dist_sell + wif_r_d) * wif_opex)
wif_direct_fixed = wif_labor + wif_supply_maint + wif_afc
wif_total_fixed = wif_direct_fixed + wif_indirect
wif_total_opex = wif_opex

# Base case values
base_afc = _base("AFC Pre Patents")
base_indirect = _base("Indirect Fixed Costs")
base_direct_fixed = _base("Direct Fixed Costs")
base_total_fixed = _base("Total Fixed Costs")
base_opex = _base("Total OPEX")

_result_row("AFC (Additional Fixed Costs)", base_afc, wif_afc)
_result_row("Direct fixed costs", base_direct_fixed, wif_direct_fixed)
_result_row("Indirect fixed costs", base_indirect, wif_indirect)
_result_row("Total fixed costs", base_total_fixed, wif_total_fixed)
_result_row("TOTAL OPEX", base_opex, wif_total_opex, is_main=True)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 9. UNIT ECONOMICS COMPARISON
# ─────────────────────────────────────────────────────────────────────────────
section_header("Unit economics comparison", "#e6a817")

col1, col2, col3, col4 = st.columns(4)
with col1:
    if wif_capacity > 0:
        kpi_card("TIC per unit", f"${wif_tic / wif_capacity:,.2f}/{prod_unit}/yr", "#e6a817",
                 "Base", f"${base_tic / base_capacity:,.2f}" if base_capacity > 0 else "—")
    else:
        kpi_card("TIC per unit", "—", "#e6a817")
with col2:
    if wif_capacity > 0:
        kpi_card("OPEX per unit", f"${wif_total_opex / wif_capacity:,.2f}/{prod_unit}", "#3fb950",
                 "Base", f"${base_opex / base_capacity:,.2f}" if base_capacity > 0 else "—")
    else:
        kpi_card("OPEX per unit", "—", "#3fb950")
with col3:
    if wif_total_opex > 0:
        var_pct = wif_tvc / wif_total_opex * 100
        kpi_card("Variable cost share", f"{var_pct:.0f}%", "#58a6ff",
                 "Base", f"{base_tvc / base_opex * 100:.0f}%" if base_opex > 0 else "—")
    else:
        kpi_card("Variable cost share", "—", "#58a6ff")
with col4:
    main_price = d.get("Main Product Price", 0) or 0
    if main_price > 0 and wif_capacity > 0:
        revenue = main_price * wif_capacity
        margin = revenue - wif_total_opex
        margin_pct = margin / revenue * 100 if revenue > 0 else 0
        kpi_card("Operating margin", f"{margin_pct:.1f}%", "#3fb950" if margin > 0 else "#f85149",
                 "At price", f"${main_price:,.2f}/{prod_unit}")
    else:
        kpi_card("Operating margin", "Set price in Input", "#8b949e")
