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
# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3: FINANCIAL ANALYSIS — DETAILED CASH FLOW TABLE
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Financial Analysis")
st.caption(
    "Detailed year-by-year cash flow table. "
    "All values in USD — outflows shown as (negative), inflows as positive. "
    "What-if overrides are applied wherever available."
)
st.space("medium")

from utils.constants import CAPEX_DISTRIBUTION

# ─────────────────────────────────────────────────────────────────────────────
# WHAT-IF AWARE DATA RESOLVER
# Prefers what-if override values over saved scenario values.
# For keys that are never overridable (e.g. EPC Years, depreciation method),
# always reads from the saved scenario dict d.
# ─────────────────────────────────────────────────────────────────────────────
def _wv(key, fallback=0.0):
    """Return what-if override if present, else saved scenario value, else fallback."""
    if key in wif:
        return wif[key]
    v = d.get(key, fallback)
    return v if isinstance(v, (int, float)) else fallback

# ── Project timeline (never overridable — always from saved scenario) ─────────
epc_years        = int(safe_val(d, "EPC Years", 3))
op_years         = int(safe_val(d, "Project Lifetime", 20))
total_years      = epc_years + op_years
year_of_analysis = int(d.get("Year of Analysis", 2024))

# ── Investment values (what-if aware) ────────────────────────────────────────
capex_val       = _wv("Project CAPEX",    safe_val(d, "Project CAPEX"))
wc_val          = _wv("Working Capital",  safe_val(d, "Working Capital"))
startup_val     = _wv("Startup Costs",    safe_val(d, "Startup Costs"))
isbl_osbl_val   = safe_val(d, "Project Costs ISBL+OSBL")  # not overridable

land_option_val = d.get("Land Option", "Buy")
if land_option_val == "Buy":
    land_buy_pct  = safe_val(d, "Land Buy Pct", 0.0)
    land_cost_val = isbl_osbl_val * (land_buy_pct / 100.0)
    land_rent_yr  = 0.0
else:
    land_cost_val = 0.0
    land_rent_pct = safe_val(d, "Land Rent Pct", 0.0)
    land_rent_yr  = isbl_osbl_val * (land_rent_pct / 100.0)

# ── CAPEX distribution fractions ────────────────────────────────────────────
_epc_col      = str(epc_years)
_capex_series = CAPEX_DISTRIBUTION[_epc_col]
_capex_fracs  = list(_capex_series.values)[:epc_years]
_frac_sum     = sum(_capex_fracs)
if _frac_sum > 0:
    _capex_fracs = [f / _frac_sum for f in _capex_fracs]

# ── Revenue inputs (what-if aware) ──────────────────────────────────────────
prod_unit_val   = d.get("Unit", "")
wif_cap         = _wv("Capacity",              safe_val(d, "Capacity"))
wif_wh          = _wv("Working Hours per Year", safe_val(d, "Working Hours per Year", 8000.0))
main_price_val  = safe_val(d, "Main Product Price", 0.0)  # selling price — from input only

# Byproduct base revenue at full capacity, op year 0 (no growth yet)
# Recompute from scenario items using what-if capacity
_cb_items = d.get("Credits and Byproducts", []) or []
_bp_base_rev = 0.0
for _r in _cb_items:
    if not _r.get("Name"):
        continue
    _rate  = float(_r.get("Rate", 0.0))
    _price = float(_r.get("Price", 0.0))
    _ru    = _r.get("Rate Unit", "")
    # Use working hours scaling consistent with the rest of the tool
    if is_per_year(_ru):
        _bp_base_rev += _price * _rate
    else:
        _bp_base_rev += _price * _rate * wif_wh

# ── Capacity / fixed-cost schedule ──────────────────────────────────────────
# 3-bucket: first op year / intermediate / last op year (as fractions 0–1)
cap_first = safe_val(d, "Capacity First Year",       100.0) / 100.0
cap_inter = safe_val(d, "Capacity Intermediate",     100.0) / 100.0
cap_last  = safe_val(d, "Capacity Last Year",        100.0) / 100.0
fc_first  = safe_val(d, "Fixed Costs First Year",    100.0) / 100.0
fc_inter  = safe_val(d, "Fixed Costs Intermediate",  100.0) / 100.0
fc_last   = safe_val(d, "Fixed Costs Last Year",     100.0) / 100.0

def _cap_pct(op_idx):
    if op_idx == 0:              return cap_first
    elif op_idx == op_years - 1: return cap_last
    else:                        return cap_inter

def _fc_pct(op_idx):
    if op_idx == 0:              return fc_first
    elif op_idx == op_years - 1: return fc_last
    else:                        return fc_inter

# ── Annual growth rates ──────────────────────────────────────────────────────
g_main   = safe_val(d, "Growth Main Price",        0.0) / 100.0
g_byprod = safe_val(d, "Growth Byproduct Price",   0.0) / 100.0
g_rm     = safe_val(d, "Growth Raw Materials",     0.0) / 100.0
g_cu     = safe_val(d, "Growth Chem Utilities",    0.0) / 100.0
g_fc     = safe_val(d, "Growth Fixed Costs",       0.0) / 100.0

# ── Depreciation (never overridable) ────────────────────────────────────────
dep_method        = d.get("Depreciation Method", "Straight Line")
dep_years         = int(safe_val(d, "Depreciation Years", 10))
# Residual value: always recomputed from what-if CAPEX × saved residual_value_pct.
# Applies to both Straight Line and MACRS — method only affects the depreciation
# schedule (handled in the depreciation module), not the terminal residual value.
residual_val_pct = safe_val(d, "Residual Value Pct", 20.0) / 100.0
residual_val_usd = capex_val * residual_val_pct   # capex_val is already what-if aware

# ── OPEX components (what-if aware) — used in expenses module ───────────────
# Variable cost base at full capacity (from tvc_net computed in Section 1)
# Split RM and CU proportionally from saved totals
_rm_saved  = safe_val(d, "Total Raw Material Cost",         0.0)
_cu_saved  = safe_val(d, "Total Chemical Inputs Utilities", 0.0)
_tvc_saved = _rm_saved + _cu_saved
# Scale to what-if capacity if capacity was overridden
_cap_ratio = wif_cap / safe_val(d, "Capacity", wif_cap) if safe_val(d, "Capacity", 1.0) > 0 else 1.0
_rm_base   = _rm_saved * _cap_ratio
_cu_base   = _cu_saved * _cap_ratio

# Fixed cost components — what-if aware
_labor_base   = wif_labor        # from Section 2 what-if solve
_sm_base      = wif_supply_maint
_afc_base     = wif_afc
_indirect_base= wif_indirect

# ── Financing (never overridable) ───────────────────────────────────────────
financing_type  = d.get("Financing Type", "None")
is_leveraged    = financing_type == "Straight Line"
debt_ratio_val  = safe_val(d, "Debt Ratio", 0.0)
total_debt      = capex_val * debt_ratio_val
amort_years     = int(safe_val(d, "Amortization Years", 13))
grace_years     = int(safe_val(d, "Grace Period Years",  5))
cod_val         = safe_val(d, "COD", 0.0) / 100.0  # already fraction? check
# COD is stored as fraction in scenario (e.g. 0.0742), verify
if cod_val > 1.0:
    cod_val = cod_val / 100.0  # safety: convert if stored as %

# ─────────────────────────────────────────────────────────────────────────────
# YEAR INDEX ARRAYS
# ─────────────────────────────────────────────────────────────────────────────
calendar_years  = [year_of_analysis + i for i in range(total_years)]
proj_year_idx   = list(range(total_years))
op_year_labels  = ["—"] * epc_years + list(range(1, op_years + 1))

col_calendar  = [str(y) for y in calendar_years]
col_proj_year = [str(i) for i in proj_year_idx]
col_op_year   = [str(v) for v in op_year_labels]

# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING HELPERS (shared across all modules)
# ─────────────────────────────────────────────────────────────────────────────
def _fmt_val(v):
    if v == 0.0:
        return "—"
    abs_v = abs(v)
    if abs_v >= 1_000_000:
        s = f"{abs_v / 1_000_000:.3f}M"
    elif abs_v >= 1_000:
        s = f"{abs_v / 1_000:.1f}k"
    else:
        s = f"{abs_v:,.2f}"
    return f"({s})" if v < 0 else s

def _fmt_col(values):
    return [_fmt_val(v) for v in values]

def _cell_color(val_str):
    if val_str == "—":
        return "#30363d"
    if val_str.startswith("("):
        return "#f85149"
    return "#3fb950"

def _html_cf_table(headers, col_arrays, epc_count, total_col_idx=None, accent_col_idxs=None):
    """Shared styled HTML cash flow table renderer."""
    accent_col_idxs = accent_col_idxs or []
    th_base = (
        "padding:.45rem .8rem;font-size:.74rem;letter-spacing:.04em;"
        "white-space:nowrap;border-bottom:2px solid #21262d;background:#0d1117;"
    )
    head_cells = []
    for j, h in enumerate(headers):
        align = "left" if j < 3 else "right"
        head_cells.append(
            f'<th style="{th_base}text-align:{align};color:#8b949e;">{h}</th>'
        )

    rows_html = []
    for i in range(total_years):
        is_epc = i < epc_count
        bg     = "#0d1117" if is_epc else "#161b22"
        cells_html = []
        for j, col in enumerate(col_arrays):
            val        = col[i]
            is_total   = total_col_idx is not None and j == total_col_idx
            is_accent  = j in accent_col_idxs
            if j < 3:
                color = "#484f58" if is_epc else "#6e7681"
                align = "left" if j == 0 else "center"
                td    = (
                    f"padding:.3rem .8rem;text-align:{align};"
                    f"font-size:.78rem;color:{color};"
                )
            else:
                color = _cell_color(str(val))
                fw    = "font-weight:600;" if (is_total or is_accent) else ""
                bdr   = "border-left:1px solid #21262d;" if is_total else ""
                td    = (
                    f"padding:.3rem .8rem;text-align:right;"
                    f"font-family:DM Mono,monospace;font-size:.78rem;"
                    f"color:{color};{fw}{bdr}"
                )
            cells_html.append(f'<td style="{td}">{val}</td>')

        rows_html.append(
            f'<tr style="background:{bg};border-bottom:1px solid #1c2128;">'
            + "".join(cells_html) + "</tr>"
        )

    return (
        '<div style="overflow-x:auto;max-height:540px;overflow-y:auto;'
        'border:1px solid #21262d;border-radius:6px;">'
        "<table style='width:100%;border-collapse:collapse;'>"
        "<thead style='position:sticky;top:0;z-index:2;'>"
        f"<tr>{''.join(head_cells)}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table></div>"
    )

def _footer_totals(col_names, col_values):
    """Render a row of column-total KPI chips."""
    cols_ui = st.columns(len(col_names))
    for col_ui, lbl, val in zip(cols_ui, col_names, col_values):
        with col_ui:
            color = "#f85149" if val < 0 else ("#3fb950" if val > 0 else "#8b949e")
            st.markdown(
                f'<div style="text-align:center;padding:.4rem;'
                f'background:#161b22;border-radius:4px;">'
                f'<p style="font-size:.68rem;color:#6e7681;margin:0 0 .15rem 0">{lbl}</p>'
                f'<p style="font-size:.86rem;font-family:DM Mono,monospace;'
                f'color:{color};font-weight:600;margin:0">{_fmt_val(val)}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1: INVESTMENT
# ─────────────────────────────────────────────────────────────────────────────
inv_capex, inv_wc, inv_startup, inv_land, inv_total = [], [], [], [], []

for i in range(total_years):
    op_idx     = i - epc_years
    capex_row  = -capex_val * _capex_fracs[i] if i < epc_years else 0.0
    if i == epc_years - 1:
        wc_row = -wc_val
    elif op_idx == op_years - 1:
        wc_row = +wc_val
    else:
        wc_row = 0.0
    startup_row = -startup_val if op_idx == 0 else 0.0
    land_row    = -land_cost_val if i == 0 else 0.0
    inv_capex.append(capex_row); inv_wc.append(wc_row)
    inv_startup.append(startup_row); inv_land.append(land_row)
    inv_total.append(capex_row + wc_row + startup_row + land_row)

section_header("Module 1 — Investment", "#e6a817")
k1, k2, k3, k4 = st.columns(4)
with k1: kpi_card("Project CAPEX",   smart_fmt(capex_val),   "#58a6ff", f"Over {epc_years} EPC yr(s)", "CAPEX table")
with k2: kpi_card("Working Capital", smart_fmt(wc_val),      "#79c0ff", "Recovery", f"Op. year {op_years}")
with k3: kpi_card("Start-up Costs",  smart_fmt(startup_val), "#3fb950", "Timing",   "Op. year 1")
with k4:
    if land_option_val == "Buy":
        kpi_card("Land Purchase", smart_fmt(land_cost_val), "#e6a817", "Timing", "Year 0")
    else:
        kpi_card("Land", "Rent", "#8b949e", "Expense", "in expenses module")

st.space("small")
if st.toggle("Show investment detail", key="tog_inv"):
    st.markdown(
        _html_cf_table(
            ["Calendar Year", "Proj. Year", "Op. Year",
             "CAPEX", "Working Capital", "Start-up", "Land Purchase", "TOTAL"],
            [col_calendar, col_proj_year, col_op_year,
             _fmt_col(inv_capex), _fmt_col(inv_wc),
             _fmt_col(inv_startup), _fmt_col(inv_land), _fmt_col(inv_total)],
            epc_years, total_col_idx=7
        ), unsafe_allow_html=True,
    )
    st.space("small")
    st.caption("Column totals")
    _footer_totals(
        ["CAPEX", "Working Capital", "Start-up", "Land", "TOTAL"],
        [sum(inv_capex), sum(inv_wc), sum(inv_startup), sum(inv_land), sum(inv_total)]
    )

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2: REVENUE
# ─────────────────────────────────────────────────────────────────────────────
rev_main, rev_byprod, rev_carbon, rev_residual, rev_total = [], [], [], [], []

for i in range(total_years):
    op_idx = i - epc_years
    if i < epc_years:
        rev_main.append(0.0); rev_byprod.append(0.0)
        rev_carbon.append(0.0); rev_residual.append(0.0); rev_total.append(0.0)
        continue

    cp              = _cap_pct(op_idx)
    g_main_f        = (1 + g_main)   ** op_idx
    g_byprod_f      = (1 + g_byprod) ** op_idx

    main_rev        = main_price_val * wif_cap * cp * g_main_f
    byprod_rev      = _bp_base_rev * cp * g_byprod_f
    carbon_rev      = 0.0                  # future-proof placeholder
    # Residual value: last operational year
    if op_idx == op_years - 1:
        resid_rev   = residual_val_usd
    else:
        resid_rev   = 0.0
    total_rev       = main_rev + byprod_rev + carbon_rev + resid_rev

    rev_main.append(main_rev); rev_byprod.append(byprod_rev)
    rev_carbon.append(carbon_rev); rev_residual.append(resid_rev)
    rev_total.append(total_rev)

section_header("Module 2 — Revenue", "#3fb950")
r1, r2, r3 = st.columns(3)
with r1: kpi_card("Main Product Price", f"${main_price_val:,.2f}/{prod_unit_val}" if main_price_val else "Not set", "#3fb950")
with r2: kpi_card("Total Revenue (undiscounted)", smart_fmt(sum(rev_total)), "#58a6ff")
with r3: kpi_card("Residual Value",  smart_fmt(residual_val_usd), "#e6a817", "Method", dep_method)

st.space("small")
if not main_price_val:
    st.warning("Main product selling price is not set. Set it in **Input Data → Other Premises** to see revenue.", icon=":material/warning:")

if st.toggle("Show revenue detail", key="tog_rev"):
    st.markdown(
        _html_cf_table(
            ["Calendar Year", "Proj. Year", "Op. Year",
             "Main Product", "Byproducts", "Carbon Credits", "Residual Value", "TOTAL"],
            [col_calendar, col_proj_year, col_op_year,
             _fmt_col(rev_main), _fmt_col(rev_byprod),
             _fmt_col(rev_carbon), _fmt_col(rev_residual), _fmt_col(rev_total)],
            epc_years, total_col_idx=7
        ), unsafe_allow_html=True,
    )
    st.space("small")
    st.caption("Column totals")
    _footer_totals(
        ["Main Product", "Byproducts", "Carbon Credits", "Residual Value", "TOTAL"],
        [sum(rev_main), sum(rev_byprod), sum(rev_carbon), sum(rev_residual), sum(rev_total)]
    )

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3: EXPENSES
# ─────────────────────────────────────────────────────────────────────────────
exp_rm, exp_cu, exp_labor, exp_sm, exp_afc, exp_ifc = [], [], [], [], [], []
exp_rent, exp_total_exp = [], []

for i in range(total_years):
    op_idx = i - epc_years
    if i < epc_years:
        for lst in [exp_rm, exp_cu, exp_labor, exp_sm, exp_afc, exp_ifc, exp_rent, exp_total_exp]:
            lst.append(0.0)
        continue

    cp   = _cap_pct(op_idx)
    fp   = _fc_pct(op_idx)
    g_rm_f  = (1 + g_rm) ** op_idx
    g_cu_f  = (1 + g_cu) ** op_idx
    g_fc_f  = (1 + g_fc) ** op_idx

    rm_yr    = -(_rm_base    * cp * g_rm_f)
    cu_yr    = -(_cu_base    * cp * g_cu_f)
    labor_yr = -(_labor_base * fp * g_fc_f)
    sm_yr    = -(_sm_base    * fp * g_fc_f)
    afc_yr   = -(_afc_base   * fp * g_fc_f)
    ifc_yr   = -(_indirect_base * fp * g_fc_f)
    rent_yr  = -(land_rent_yr   * g_fc_f) if land_option_val == "Rent" else 0.0
    total_yr = rm_yr + cu_yr + labor_yr + sm_yr + afc_yr + ifc_yr + rent_yr

    exp_rm.append(rm_yr); exp_cu.append(cu_yr); exp_labor.append(labor_yr)
    exp_sm.append(sm_yr); exp_afc.append(afc_yr); exp_ifc.append(ifc_yr)
    exp_rent.append(rent_yr); exp_total_exp.append(total_yr)

# Build column list conditionally (land rent only if relevant)
_exp_headers = ["Calendar Year", "Proj. Year", "Op. Year",
                "Raw Materials", "Chem. Inputs & Util.", "Carbon Costs",
                "Labor", "Supply & Maint.", "AFC", "Indirect Fixed Costs"]
_exp_cols    = [col_calendar, col_proj_year, col_op_year,
                _fmt_col(exp_rm), _fmt_col(exp_cu),
                _fmt_col([0.0]*total_years),   # carbon costs — always 0 for now
                _fmt_col(exp_labor), _fmt_col(exp_sm),
                _fmt_col(exp_afc), _fmt_col(exp_ifc)]
_exp_footer_names  = ["Raw Materials", "Chem. Inputs", "Carbon", "Labor", "S&M", "AFC", "Indirect"]
_exp_footer_values = [sum(exp_rm), sum(exp_cu), 0.0, sum(exp_labor), sum(exp_sm), sum(exp_afc), sum(exp_ifc)]

if land_option_val == "Rent":
    _exp_headers.append("Land Rent")
    _exp_cols.append(_fmt_col(exp_rent))
    _exp_footer_names.append("Land Rent")
    _exp_footer_values.append(sum(exp_rent))

_exp_headers.append("TOTAL")
_exp_cols.append(_fmt_col(exp_total_exp))
_exp_footer_names.append("TOTAL")
_exp_footer_values.append(sum(exp_total_exp))
_total_exp_col_idx = len(_exp_cols) - 1

section_header("Module 3 — Expenses", "#f85149")
e1, e2, e3 = st.columns(3)
with e1: kpi_card("Total Expenses (undiscounted)", smart_fmt(abs(sum(exp_total_exp))), "#f85149")
with e2: kpi_card("Variable Cost Base", smart_fmt(abs(sum(exp_rm) + sum(exp_cu))), "#ff7b72")
with e3: kpi_card("Fixed Cost Base", smart_fmt(abs(sum(exp_labor)+sum(exp_sm)+sum(exp_afc)+sum(exp_ifc))), "#ffa657")

st.space("small")
if st.toggle("Show expenses detail", key="tog_exp"):
    st.markdown(
        _html_cf_table(_exp_headers, _exp_cols, epc_years, total_col_idx=_total_exp_col_idx),
        unsafe_allow_html=True,
    )
    st.space("small")
    st.caption("Column totals")
    _footer_totals(_exp_footer_names, _exp_footer_values)

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4: FINANCING
# ─────────────────────────────────────────────────────────────────────────────
fin_debt, fin_amort, fin_accum, fin_interest, fin_total_fin = [], [], [], [], []

if is_leveraged:
    # Debt drawn during EPC proportional to CAPEX fractions
    debt_drawn_epc = [total_debt * f for f in _capex_fracs]
    annual_repay   = total_debt / amort_years if amort_years > 0 else 0.0
    accumulated    = 0.0

    for i in range(total_years):
        op_idx  = i - epc_years
        debt_i  = debt_drawn_epc[i] if i < epc_years else 0.0
        accumulated += debt_i

        # Amortization after grace period, for amort_years
        if op_idx >= grace_years and (op_idx - grace_years) < amort_years:
            amort_i = -annual_repay
        else:
            amort_i = 0.0

        # Interest on balance before this year's repayment
        interest_i = -(accumulated) * cod_val

        accumulated += amort_i  # reduce balance after repayment

        fin_debt.append(debt_i); fin_amort.append(amort_i)
        fin_accum.append(accumulated); fin_interest.append(interest_i)
        fin_total_fin.append(amort_i + interest_i)

_fin_default_open = not is_leveraged   # hidden by default if not leveraged

section_header("Module 4 — Financing", "#8b949e" if not is_leveraged else "#58a6ff")

if not is_leveraged:
    st.info("No financing configured (Financing Type = None). Module hidden by default.", icon=":material/info:")
    _show_fin = st.toggle("Show financing module anyway", key="tog_fin")
else:
    f1, f2, f3 = st.columns(3)
    with f1: kpi_card("Total Debt", smart_fmt(total_debt), "#58a6ff",
                      "Ratio", f"{safe_val(d,'Debt Ratio Pct'):.1f}% of CAPEX")
    with f2: kpi_card("Amortization", f"{amort_years} years", "#79c0ff",
                      "Grace period", f"{grace_years} years")
    with f3: kpi_card("Cost of Debt (COD)", f"{cod_val*100:.2f}%", "#e6a817")
    _show_fin = st.toggle("Show financing detail", key="tog_fin", value=True)

if _show_fin and is_leveraged:
    st.markdown(
        _html_cf_table(
            ["Calendar Year", "Proj. Year", "Op. Year",
             "Debt Drawdown", "Amortization", "Accum. Debt", "Interest", "TOTAL"],
            [col_calendar, col_proj_year, col_op_year,
             _fmt_col(fin_debt), _fmt_col(fin_amort),
             _fmt_col(fin_accum), _fmt_col(fin_interest), _fmt_col(fin_total_fin)],
            epc_years, total_col_idx=7, accent_col_idxs=[5]
        ), unsafe_allow_html=True,
    )
    st.space("small")
    st.caption("Column totals")
    _footer_totals(
        ["Debt Drawn", "Amortization", "Interest", "TOTAL (cash out)"],
        [sum(fin_debt), sum(fin_amort), sum(fin_interest), sum(fin_total_fin)]
    )

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 5: CASH FLOW
# ─────────────────────────────────────────────────────────────────────────────

# ── Depreciation schedule ─────────────────────────────────────────────────────
dep_method_val = d.get("Depreciation Method", "Straight Line")
dep_years_val  = int(safe_val(d, "Depreciation Years", 10))
dep_annual_sl  = -(capex_val - residual_val_usd) / dep_years_val if dep_years_val > 0 else 0.0

# MACRS reference table — IRS GDS half-year convention
# Key = recovery period (years), value = list of annual rates (index 0 = recovery year 1)
_MACRS_TABLE = {
    3:  [0.3333, 0.4445, 0.1481, 0.0741],
    5:  [0.2000, 0.3200, 0.1920, 0.1152, 0.1152, 0.0576],
    7:  [0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446],
    10: [0.1000, 0.1800, 0.1440, 0.1152, 0.0922, 0.0737, 0.0655, 0.0655,
         0.0656, 0.0655, 0.0328],
    15: [0.0500, 0.0950, 0.0855, 0.0770, 0.0693, 0.0623, 0.0590, 0.0590,
         0.0591, 0.0590, 0.0591, 0.0590, 0.0591, 0.0590, 0.0591, 0.0295],
    20: [0.0375, 0.0722, 0.0668, 0.0618, 0.0571, 0.0528, 0.0489, 0.0452,
         0.0446, 0.0446, 0.0446, 0.0446, 0.0446, 0.0446, 0.0446, 0.0446,
         0.0446, 0.0446, 0.0446, 0.0446, 0.0223],
}
_macrs_key   = min(_MACRS_TABLE.keys(), key=lambda k: abs(k - dep_years_val))
_macrs_rates = _MACRS_TABLE[_macrs_key]

def _dep(op_idx):
    """Depreciation for operational year op_idx (0-based). Returns negative value (expense)."""
    if dep_method_val == "Straight Line":
        return dep_annual_sl if op_idx < dep_years_val else 0.0
    else:  # MACRS
        return (-capex_val * _macrs_rates[op_idx]) if op_idx < len(_macrs_rates) else 0.0

# ── Tax rate and MARR ─────────────────────────────────────────────────────────
tax_rate_val = safe_val(d, "Tax Rate", 0.34)
if tax_rate_val > 1.0:
    tax_rate_val /= 100.0

marr_val = safe_val(d, "MARR", 0.12)
if marr_val > 1.0:
    marr_val /= 100.0

# ── Build cash flow arrays ────────────────────────────────────────────────────
cf_revenue     = []
cf_var_labor   = []
cf_gross_profit= []
cf_fixed       = []
cf_ebitda      = []
cf_depreciation= []
cf_ebit        = []
cf_fin_int_col = []
cf_ebt         = []
cf_taxes       = []
cf_net_profit  = []
cf_amortization= []
cf_proj_inv    = []
cf_cashflow    = []
cf_pv_cf       = []
cf_accum_pv    = []

_accum_pv = 0.0

for i in range(total_years):
    op_idx = i - epc_years
    is_epc = i < epc_years

    # Always-active columns from other modules
    proj_inv_i = inv_total[i]
    fin_int_i  = fin_interest[i] if is_leveraged else 0.0
    amort_i    = fin_amort[i]    if is_leveraged else 0.0

    if is_epc:
        # EPC: only investment + financing + cash flow columns are populated
        cf_revenue.append(None);      cf_var_labor.append(None)
        cf_gross_profit.append(None); cf_fixed.append(None)
        cf_ebitda.append(None);       cf_depreciation.append(None)
        cf_ebit.append(None);         cf_ebt.append(None)
        cf_taxes.append(None);        cf_net_profit.append(None)

        cf_fin_int_col.append(fin_int_i)
        cf_amortization.append(amort_i)
        cf_proj_inv.append(proj_inv_i)

        cash_flow_i = proj_inv_i + fin_int_i + amort_i
        pv_i        = cash_flow_i / (1 + marr_val) ** i
        _accum_pv  += pv_i

        cf_cashflow.append(cash_flow_i)
        cf_pv_cf.append(pv_i)
        cf_accum_pv.append(_accum_pv)
        continue

    # ── Operational rows ──────────────────────────────────────────────────────
    # Revenue (already computed in module 2, index aligned)
    rev_i  = rev_total[i]

    # Variable & Labor = RM + CU + Carbon (0) + Labor  (all negative)
    var_i  = exp_rm[i] + exp_cu[i] + 0.0 + exp_labor[i]

    # Fixed Costs = S&M + AFC + IFC + Land Rent  (all negative)
    fix_i  = exp_sm[i] + exp_afc[i] + exp_ifc[i] + exp_rent[i]

    # Income statement chain
    gp_i      = rev_i + var_i
    ebitda_i  = gp_i  + fix_i
    dep_i     = _dep(op_idx)
    ebit_i    = ebitda_i + dep_i
    ebt_i     = ebit_i   + fin_int_i
    tax_i     = -max(0.0, ebt_i) * tax_rate_val   # 0 on losses, negative outflow otherwise
    np_i      = ebt_i    + tax_i

    # Cash Flow = Net Profit + Amortization (debt repayment) + Project Investment
    cash_flow_i = np_i + amort_i + proj_inv_i
    pv_i        = cash_flow_i / (1 + marr_val) ** i
    _accum_pv  += pv_i

    cf_revenue.append(rev_i);          cf_var_labor.append(var_i)
    cf_gross_profit.append(gp_i);      cf_fixed.append(fix_i)
    cf_ebitda.append(ebitda_i);        cf_depreciation.append(dep_i)
    cf_ebit.append(ebit_i);            cf_fin_int_col.append(fin_int_i)
    cf_ebt.append(ebt_i);              cf_taxes.append(tax_i)
    cf_net_profit.append(np_i);        cf_amortization.append(amort_i)
    cf_proj_inv.append(proj_inv_i);    cf_cashflow.append(cash_flow_i)
    cf_pv_cf.append(pv_i);             cf_accum_pv.append(_accum_pv)

npv_val = _accum_pv   # final accumulated PV = NPV

# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING FOR TABLE — None values (EPC non-applicable) display as "—"
# ─────────────────────────────────────────────────────────────────────────────
def _fmt_cf_col(values):
    """Format cash flow column — None → '—', 0 → '—', else ±accounting notation."""
    out = []
    for v in values:
        if v is None:
            out.append("—")
        else:
            out.append(_fmt_val(v))
    return out

# ── Summary KPIs ──────────────────────────────────────────────────────────────
section_header("Module 5 — Cash Flow", "#58a6ff")

npv_color = "#3fb950" if npv_val >= 0 else "#f85149"
k1, k2, k3, k4 = st.columns(4)
with k1:
    kpi_card("NPV", smart_fmt(npv_val), npv_color,
             "Discount rate", f"MARR = {marr_val*100:.2f}%")
with k2:
    # IRR approximation note — full IRR requires scipy, flag for next iteration
    kpi_card("Depreciation Method", dep_method_val, "#8b949e",
             "Period", f"{dep_years_val} years")
with k3:
    kpi_card("Tax Rate", f"{tax_rate_val*100:.1f}%", "#8b949e",
             "Country", d.get("Tax Country", "—"))
with k4:
    _peak_inv = min(inv_total)   # most negative investment year
    kpi_card("Peak Investment Year", smart_fmt(abs(_peak_inv)), "#e6a817",
             "Yr", str(inv_total.index(_peak_inv)))

st.space("small")

# ── Detail table ──────────────────────────────────────────────────────────────
if st.toggle("Show cash flow detail", key="tog_cf", value=True):
    _cf_headers = [
        "Calendar Year", "Proj. Year", "Op. Year",
        "Revenue", "Var. & Labor", "Gross Profit",
        "Fixed Costs", "EBITDA", "Depreciation",
        "EBIT", "Fin. Interest", "EBT",
        "Taxes", "Net Profit", "Amortization",
        "Proj. Investment", "Cash Flow", "Present CF", "Accum. PV CF"
    ]
    _cf_col_arrays = [
        col_calendar, col_proj_year, col_op_year,
        _fmt_cf_col(cf_revenue),      _fmt_cf_col(cf_var_labor),
        _fmt_cf_col(cf_gross_profit), _fmt_cf_col(cf_fixed),
        _fmt_cf_col(cf_ebitda),       _fmt_cf_col(cf_depreciation),
        _fmt_cf_col(cf_ebit),         _fmt_cf_col(cf_fin_int_col),
        _fmt_cf_col(cf_ebt),          _fmt_cf_col(cf_taxes),
        _fmt_cf_col(cf_net_profit),   _fmt_cf_col(cf_amortization),
        _fmt_cf_col(cf_proj_inv),     _fmt_cf_col(cf_cashflow),
        _fmt_cf_col(cf_pv_cf),        _fmt_cf_col(cf_accum_pv),
    ]

    # Highlight key result columns
    _accent_idxs = [
        _cf_headers.index("EBITDA")       - 0,   # col index offset by 0 (headers include index cols)
        _cf_headers.index("Net Profit")   - 0,
        _cf_headers.index("Cash Flow")    - 0,
        _cf_headers.index("Accum. PV CF") - 0,
    ]

    st.markdown(
        _html_cf_table(
            _cf_headers, _cf_col_arrays, epc_years,
            total_col_idx=_cf_headers.index("Cash Flow"),
            accent_col_idxs=_accent_idxs
        ),
        unsafe_allow_html=True,
    )

    st.space("small")
    st.caption("Key column totals (operational years only)")
    _op_slice = slice(epc_years, total_years)
    _footer_totals(
        ["Revenue", "Var.+Labor", "Fixed", "EBITDA", "Net Profit", "Cash Flow", "NPV"],
        [
            sum(v for v in cf_revenue[_op_slice]     if v is not None),
            sum(v for v in cf_var_labor[_op_slice]   if v is not None),
            sum(v for v in cf_fixed[_op_slice]       if v is not None),
            sum(v for v in cf_ebitda[_op_slice]      if v is not None),
            sum(v for v in cf_net_profit[_op_slice]  if v is not None),
            sum(v for v in cf_cashflow[_op_slice]    if v is not None),
            npv_val,
        ]
    )

st.space("medium")


