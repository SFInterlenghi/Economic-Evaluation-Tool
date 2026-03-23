"""ISI-Tool — Cash Flow & Analysis page.

Section 1: Variable cost tables with editable prices + reset buttons (original)
Section 2: Side-by-side base case vs. what-if for TIC, labor, % factors, OPEX
"""
import streamlit as st
import pandas as pd
import math
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
# SESSION STATE
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

# ── Legend ────────────────────────────────────────────────────────────────────
with st.container(border=True):
    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        st.badge("Matches default", icon=":material/check:", color="blue")
    with lc2:
        st.badge("Modified from default", icon=":material/edit:", color="orange")
    with lc3:
        st.badge("Computed result", icon=":material/calculate:", color="green")

st.space("medium")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1: VARIABLE COST TABLES (original layout — HTML tables + reset btns)
# ═════════════════════════════════════════════════════════════════════════════
section_header("Variable costs & credits", "#58a6ff")

working_hours = safe_val(d, "Working Hours per Year", 8000.0)
product_rate = capacity / working_hours if working_hours > 0 else 0.0


def _build_vc_table(table_key: str, is_credit: bool = False):
    """Build and render a variable cost table with editable prices + reset buttons.
    Returns (rows, total_cost)."""
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
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:90px">Rate</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:80px">Rate Unit</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#3fb950;min-width:120px">Cost/year</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#3fb950;min-width:120px">Specific cost</th>
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
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#c9d1d9">{row["rate"]:.4f}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;color:#8b949e">{row["rate_unit"]}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#3fb950;background:#161b22">{smart_fmt(row["line_cost"])}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#3fb950;background:#161b22">{row["spec_cost"]:.4f} USD/{prod_unit}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#3fb950;background:#161b22">{"—" if is_credit else f"{pct:.2f}%"}</td>'
            f'</tr>'
        )
    body_rows.append(
        f'<tr style="border-top:2px solid #21262d;background:#1a2030">'
        f'<td colspan="7" style="padding:.5rem .7rem;color:#e6edf3;font-weight:600">TOTAL</td>'
        f'<td style="padding:.5rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#e6edf3;font-weight:600">{smart_fmt(total_cost)}</td>'
        f'<td style="padding:.5rem .7rem"></td>'
        f'<td style="padding:.5rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#e6edf3;font-weight:600">{"—" if is_credit else "100.00%"}</td>'
        f'</tr>'
    )
    st.markdown(header + "".join(body_rows) + "</tbody></table></div>", unsafe_allow_html=True)

    # Price editors with reset buttons
    st.space("small")
    st.caption("EDIT PRICES — PRESS ↩ TO RESTORE TO DEFAULT")
    changed = False
    for row in rows:
        name = row["name"]
        modified = row["modified"]
        inp_def = row["input_default"]
        wgt_key = f"cf_{scenario_name}_{table_key}_{name}"
        reset_key = f"rst_{scenario_name}_{table_key}_{name}"
        label_color = "#e6a817" if modified else "#8b949e"

        col_lbl, col_inp, col_btn = st.columns([2, 1, 1])
        with col_lbl:
            hint = f"  ← default: {inp_def:.6g}" if modified else ""
            st.markdown(
                f'<p style="font-size:.82rem;color:{label_color};margin:0;padding:.45rem 0">'
                f'{name}<span style="font-size:.72rem;color:#8b949e">{hint}</span></p>',
                unsafe_allow_html=True)
        with col_inp:
            new_val = st.number_input(name, value=float(row["price"]), min_value=0.0,
                                      step=0.001, format="%.6f", key=wgt_key,
                                      label_visibility="collapsed")
            if abs(new_val - row["price"]) > 1e-12:
                wk[table_key][name] = new_val
                changed = True
        with col_btn:
            if st.button(f"↩ {inp_def:.6g}", key=reset_key,
                         help=f"Restore to default: {inp_def:.6g}", disabled=not modified):
                wk[table_key][name] = inp_def
                st.session_state.pop(wgt_key, None)
                changed = True
    if changed:
        st.rerun()
    return rows, total_cost


st.markdown("#### Raw Materials")
rm_rows, rm_total = _build_vc_table("Raw Materials")
st.space("medium")

st.markdown("#### Chemical Inputs & Utilities")
cu_rows, cu_total = _build_vc_table("Chemical Inputs and Utilities")
st.space("medium")

st.markdown("#### Credits & Byproducts")
cb_rows, cb_total = _build_vc_table("Credits and Byproducts", is_credit=True)
st.space("medium")

# Variable costs summary
section_header("Variable costs summary", "#58a6ff")
c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Raw Materials", smart_fmt(rm_total), "#58a6ff")
with c2: kpi_card("Chemical Inputs & Utilities", smart_fmt(cu_total), "#79c0ff")
with c3: kpi_card("Credits & Byproducts", smart_fmt(cb_total), "#3fb950")
tvc_net = rm_total + cu_total - cb_total
with c4: kpi_card("Net Variable Costs", smart_fmt(tvc_net), "#e6a817")

st.space("large")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2: WHAT-IF ANALYSIS — BASE CASE vs. MODIFIED (side-by-side)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### What-If Analysis")
st.caption("Modify parameters below to see how they affect TIC and OPEX. "
           "Base case values (left) come from your saved scenario. "
           "What-if values (right) recalculate all downstream results.")

st.space("medium")


# ── What-if helpers ──────────────────────────────────────────────────────────
def _base(key, default=0.0):
    v = d.get(key, default)
    return v if isinstance(v, (int, float)) else default


def _section_cols():
    c1, c2, c3 = st.columns([3, 2, 2])
    with c2: st.caption("**BASE CASE**")
    with c3: st.caption("**WHAT-IF**")


def _editable_row(label, key, base_val, step=0.01, fmt_fn=None, suffix="",
                  min_value=None, is_int=False):
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
        st.text_input(f"base_{key}", value=f"{fmt_fn(base_val)}{suffix}",
                      disabled=True, label_visibility="collapsed")
    with c3:
        if is_int:
            new_val = st.number_input(label, value=int(current), step=int(step),
                                      min_value=int(min_value) if min_value is not None else None,
                                      key=wk, label_visibility="collapsed")
            if int(new_val) != int(base_val):
                wif[key] = int(new_val)
            elif key in wif:
                del wif[key]
            return int(new_val)
        else:
            new_val = st.number_input(label, value=float(current), step=float(step),
                                      min_value=float(min_value) if min_value is not None else None,
                                      key=wk, label_visibility="collapsed")
            if abs(new_val - float(base_val)) > 1e-9:
                wif[key] = float(new_val)
            elif key in wif:
                del wif[key]
            return float(new_val)


def _result_row(label, base_val, wif_val, is_main=False):
    c1, c2, c3 = st.columns([3, 2, 2])
    color = "#e6a817" if is_main else "#3fb950"
    changed = abs(wif_val - base_val) > 0.01
    delta_str = ""
    if changed and base_val != 0:
        delta_pct = (wif_val - base_val) / abs(base_val) * 100
        delta_str = f"  ({delta_pct:+.1f}%)"
    with c1:
        fw = "600" if is_main else "400"
        st.markdown(f'<p style="margin:0;padding:.35rem 0;font-size:.82rem;'
                    f'color:{color};font-weight:{fw}">{label}</p>', unsafe_allow_html=True)
    with c2:
        st.text_input(f"br_{label}", value=smart_fmt(base_val),
                      disabled=True, label_visibility="collapsed")
    with c3:
        st.text_input(f"wr_{label}", value=f"{smart_fmt(wif_val)}{delta_str}",
                      disabled=True, label_visibility="collapsed")


# ─────────────────────────────────────────────────────────────────────────────
# 2A. CAPACITY & WORKING HOURS
# ─────────────────────────────────────────────────────────────────────────────
section_header("Capacity & operating hours", "#58a6ff")
_section_cols()

base_capacity = _base("Capacity")
base_wh = _base("Working Hours per Year", 8000.0)

wif_capacity = _editable_row("Production capacity", "Capacity", base_capacity,
                              step=100.0, suffix=f" {prod_unit}/yr",
                              fmt_fn=lambda v: f"{v:,.1f}", min_value=0.0)
wif_wh = _editable_row("Working hours per year", "Working Hours per Year", base_wh,
                         step=100.0, suffix=" h/yr",
                         fmt_fn=lambda v: f"{v:,.0f}", min_value=1.0)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 2B. INVESTMENT COSTS (TIC)
# ─────────────────────────────────────────────────────────────────────────────
section_header("Investment costs (TIC)", "#e6a817")
_section_cols()

base_equip = _base("Equipment Acquisition")
base_cont_pct = _base("Contingency Pct")
base_loc_factor = _base("Location Factor", 1.0)

wif_equip = _editable_row("Equipment acquisition", "Equipment Acquisition", base_equip,
                           step=1000.0, fmt_fn=lambda v: smart_fmt(v))
wif_cont_pct = _editable_row("Project contingency (%)", "wif_Contingency_Pct",
                              base_cont_pct * 100, step=1.0, suffix="%",
                              fmt_fn=lambda v: f"{v:.1f}") / 100.0
wif_loc_factor = _editable_row("Location factor", "Location Factor", base_loc_factor,
                                step=0.01, fmt_fn=lambda v: f"{v:.4f}")

# Compute — scale ISBL+OSBL proportionally with equipment
base_isbl_osbl = _base("Project Costs ISBL+OSBL")
equip_ratio = wif_equip / base_equip if base_equip > 0 else 1.0
wif_isbl_osbl = base_isbl_osbl * equip_ratio

base_tuf = _base("Time Update Factor", 1.0)
base_capex = _base("Project CAPEX")
wif_capex = wif_isbl_osbl * (1 + wif_cont_pct) * base_tuf * wif_loc_factor

_result_row("Project Costs ISBL+OSBL", base_isbl_osbl, wif_isbl_osbl)
_result_row("Project CAPEX", base_capex, wif_capex, is_main=True)

# Working Capital
base_wc = _base("Working Capital")
wc_method = d.get("WC Method", "Percentage")
if wc_method == "Percentage":
    base_wc_pct = _base("WC Pct", 5.0)
    wif_wc_pct = _editable_row("Working capital (% of CAPEX)", "WC Pct", base_wc_pct,
                                step=0.5, suffix="%", fmt_fn=lambda v: f"{v:.1f}")
    wif_wc = wif_capex * (wif_wc_pct / 100.0)
else:
    wif_wc = base_wc * (wif_capex / base_capex) if base_capex > 0 else base_wc
_result_row("Working capital", base_wc, wif_wc)

# Startup
base_startup = _base("Startup Costs")
startup_method = d.get("Startup Method", "Multiple Factors")
if startup_method == "Single Factor":
    base_su_pct = _base("Startup Single Pct", 8.0)
    wif_su_pct = _editable_row("Startup costs (% of CAPEX)", "Startup Single Pct", base_su_pct,
                                step=0.5, suffix="%", fmt_fn=lambda v: f"{v:.1f}")
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
# 2C. FIXED COSTS — LABOR
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

wif_n_ops = _editable_row("Operators per shift", "Num Operators", base_n_ops,
                           step=1, is_int=True, min_value=1)
wif_op_sal = _editable_row("Operator salary (USD/month)", "Operator Salary", base_op_sal,
                            step=10.0, min_value=273.0, fmt_fn=lambda v: f"${v:,.2f}")
wif_n_sups = _editable_row("Supervisors per shift", "Num Supervisors", base_n_sups,
                            step=1, is_int=True, min_value=1)
wif_sup_sal = _editable_row("Supervisor salary (USD/month)", "Supervisor Salary", base_sup_sal,
                             step=10.0, min_value=273.0, fmt_fn=lambda v: f"${v:,.2f}")
wif_sal_charges = _editable_row("Salary charges multiplier", "Salary Charges", base_sal_charges,
                                 step=0.05, min_value=1.0, fmt_fn=lambda v: f"{v:.2f}")

wif_olc = (wif_n_ops * wif_op_sal + wif_n_sups * wif_sup_sal) * wif_sal_charges * base_op_team * 12.0
_result_row("Operating Labor Costs (OLC)", base_olc, wif_olc)

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
# 2D. SUPPLY & MAINTENANCE
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
# 2E. ADDITIONAL FIXED COSTS (AFC)
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
# 2F. INDIRECT FIXED COSTS
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
# 2G. OPEX ANALYTICAL SOLVE
# ─────────────────────────────────────────────────────────────────────────────
section_header("OPEX summary", "#e6a817")

# Use the variable cost totals from Section 1 (already computed above)
wif_tvc = tvc_net
base_tvc = (_base("Total Raw Material Cost") + _base("Total Chemical Inputs Utilities")
            - _base("Total Revenue"))

_olc_coeff_w = wif_admin_ov + wif_admin_costs
_capex_coeff_w = wif_mfg_ov + wif_taxes_ins + wif_mfg_costs
_num_w = (wif_tvc + wif_labor + wif_supply_maint
          + _olc_coeff_w * wif_olc + _capex_coeff_w * wif_capex)
_den_w = 1.0 - wif_patents - wif_dist_sell - wif_r_d
wif_opex = _num_w / _den_w if _den_w > 0 else 0.0

wif_afc = (wif_admin_ov * wif_olc + (wif_mfg_ov + wif_taxes_ins) * wif_capex
           + wif_patents * wif_opex)
wif_indirect = (wif_admin_costs * wif_olc + wif_mfg_costs * wif_capex
                + (wif_dist_sell + wif_r_d) * wif_opex)
wif_direct_fixed = wif_labor + wif_supply_maint + wif_afc
wif_total_fixed = wif_direct_fixed + wif_indirect
wif_total_opex = wif_opex

base_afc = _base("AFC Pre Patents")
base_indirect = _base("Indirect Fixed Costs")
base_direct_fixed = _base("Direct Fixed Costs")
base_total_fixed = _base("Total Fixed Costs")
base_opex = _base("Total OPEX")

_result_row("Net variable costs", base_tvc, wif_tvc)
_result_row("Total labor costs", base_labor, wif_labor)
_result_row("Supply & maintenance", base_supply_maint, wif_supply_maint)
_result_row("AFC (Additional Fixed Costs)", base_afc, wif_afc)
_result_row("Direct fixed costs", base_direct_fixed, wif_direct_fixed)
_result_row("Indirect fixed costs", base_indirect, wif_indirect)
_result_row("Total fixed costs", base_total_fixed, wif_total_fixed)
_result_row("TOTAL OPEX", base_opex, wif_total_opex, is_main=True)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# 2H. UNIT ECONOMICS COMPARISON
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
        kpi_card("Operating margin", f"{margin_pct:.1f}%",
                 "#3fb950" if margin > 0 else "#f85149",
                 "At price", f"${main_price:,.2f}/{prod_unit}")
    else:
        kpi_card("Operating margin", "Set price in Input", "#8b949e")
