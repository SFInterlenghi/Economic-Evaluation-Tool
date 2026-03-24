"""ISI-Tool — Cash Flow & Analysis page.

Section 1: Variable cost tables with editable prices + reset buttons
Section 2: Side-by-side base case vs. what-if analysis engine
Section 3: Financial assumptions panel
Section 4: Unified cash flow table
Section 5: Financial dashboard
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

section_header("Variable costs summary", "#58a6ff")
c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Raw Materials", smart_fmt(rm_total), "#58a6ff")
with c2: kpi_card("Chemical Inputs & Utilities", smart_fmt(cu_total), "#79c0ff")
with c3: kpi_card("Credits & Byproducts", smart_fmt(cb_total), "#3fb950")
tvc_net = rm_total + cu_total - cb_total
with c4: kpi_card("Net Variable Costs", smart_fmt(tvc_net), "#e6a817")

st.space("large")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2: WHAT-IF ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### What-If Analysis")
st.caption("Modify parameters below to see how they affect TIC and OPEX. "
           "Base case values (left) come from your saved scenario. "
           "What-if values (right) recalculate all downstream results.")

st.space("medium")


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


# 2A. CAPACITY & WORKING HOURS
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

# 2B. INVESTMENT COSTS
section_header("Investment costs (TIC)", "#e6a817")
_section_cols()

base_equip = _base("Equipment Acquisition")
base_cont_pct = _base("Contingency Pct")
base_loc_factor = _base("Location Factor", 1.0)

wif_equip = _editable_row("Equipment acquisition", "Equipment Acquisition", base_equip,
                           step=1000.0, fmt_fn=lambda v: smart_fmt(v))
wif_cont_pct = _editable_row("Project contingency (%)", "Contingency Pct",
                              base_cont_pct * 100, step=1.0, suffix="%",
                              fmt_fn=lambda v: f"{v:.1f}") / 100.0
wif_loc_factor = _editable_row("Location factor", "Location Factor", base_loc_factor,
                                step=0.01, fmt_fn=lambda v: f"{v:.4f}")

base_isbl_osbl = _base("Project Costs ISBL+OSBL")
equip_ratio = wif_equip / base_equip if base_equip > 0 else 1.0
wif_isbl_osbl = base_isbl_osbl * equip_ratio

base_tuf = _base("Time Update Factor", 1.0)
base_capex = _base("Project CAPEX")
wif_capex = wif_isbl_osbl * (1 + wif_cont_pct) * base_tuf * wif_loc_factor

_result_row("Project Costs ISBL+OSBL", base_isbl_osbl, wif_isbl_osbl)
_result_row("Project CAPEX", base_capex, wif_capex, is_main=True)

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

# 2C. LABOR
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

# 2D. SUPPLY & MAINTENANCE
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

# 2E. AFC
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

# 2F. INDIRECT
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

# 2G. OPEX SOLVE
section_header("OPEX summary", "#e6a817")

wif_tvc_for_opex = tvc_net
base_tvc_saved = (_base("Total Raw Material Cost") + _base("Total Chemical Inputs Utilities")
                  - _base("Total Revenue"))

_olc_coeff_w = wif_admin_ov + wif_admin_costs
_capex_coeff_w = wif_mfg_ov + wif_taxes_ins + wif_mfg_costs
_num_w = (wif_tvc_for_opex + wif_labor + wif_supply_maint
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

_result_row("Net variable costs", base_tvc_saved, wif_tvc_for_opex)
_result_row("Total labor costs", base_labor, wif_labor)
_result_row("Supply & maintenance", base_supply_maint, wif_supply_maint)
_result_row("AFC (Additional Fixed Costs)", base_afc, wif_afc)
_result_row("Direct fixed costs", base_direct_fixed, wif_direct_fixed)
_result_row("Indirect fixed costs", base_indirect, wif_indirect)
_result_row("Total fixed costs", base_total_fixed, wif_total_fixed)
_result_row("TOTAL OPEX", base_opex, wif_total_opex, is_main=True)

st.space("medium")

# 2H. UNIT ECONOMICS
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
        var_pct = wif_tvc_for_opex / wif_total_opex * 100
        kpi_card("Variable cost share", f"{var_pct:.0f}%", "#58a6ff",
                 "Base", f"{base_tvc_saved / base_opex * 100:.0f}%" if base_opex > 0 else "—")
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

st.space("large")

# ═════════════════════════════════════════════════════════════════════════════
# FINANCIAL ASSUMPTIONS PANEL
# ═════════════════════════════════════════════════════════════════════════════
from utils.constants import CAPEX_DISTRIBUTION, TAXES_BY_COUNTRY, COUNTRY_LIST

# ── State init ────────────────────────────────────────────────────────────────
if "cf_fin" not in st.session_state:
    st.session_state.cf_fin = {}
if scenario_name not in st.session_state.cf_fin:
    st.session_state.cf_fin[scenario_name] = {}

_fin = st.session_state.cf_fin[scenario_name]

def _fget(key, fallback=0.0):
    if key in _fin:
        return _fin[key]
    v = d.get(key, fallback)
    return v if isinstance(v, (int, float)) else fallback

def _fset(key, val, base_val, is_int=False):
    if is_int:
        if int(val) != int(base_val):
            _fin[key] = int(val)
        elif key in _fin:
            del _fin[key]
    else:
        if abs(float(val) - float(base_val)) > 1e-9:
            _fin[key] = float(val)
        elif key in _fin:
            del _fin[key]

def _modified(key):
    return key in _fin and not str(key).startswith("_")

def _fin_row(label, key, base_val, step=0.01, fmt=".2f", suffix="",
             min_val=None, is_int=False, computed_val=None, bold=False):
    """Editable assumption row with per-field reset. Returns current value."""
    mod = _modified(key)
    c1, c2, c3 = st.columns([3, 2, 1])
    label_color = "#e6a817" if mod else "#c9d1d9"
    fw = "font-weight:600;" if bold else ""
    with c1:
        st.markdown(
            f'<p style="margin:0;padding:.32rem 0;font-size:.9rem;'
            f'color:{label_color};{fw}">{label}</p>',
            unsafe_allow_html=True)
    if computed_val is not None:
        with c2:
            disp = (f"{computed_val*100:{fmt}}%" if suffix == "%"
                    else f"{computed_val:{fmt}}{suffix}")
            st.markdown(
                f'<p style="margin:0;padding:.32rem 0;font-size:.9rem;'
                f'font-family:DM Mono,monospace;color:#3fb950;font-weight:600;'
                f'text-align:right">{disp}</p>', unsafe_allow_html=True)
        with c3:
            st.markdown("")
        return computed_val

    current = _fin.get(key, base_val)
    wk = f"cffin_{scenario_name}_{key}"
    rk = f"cffinrst_{scenario_name}_{key}"
    hint = (f"{float(base_val)*100:{fmt}}%" if suffix == "%"
            else f"{base_val:{fmt}}{suffix}" if not is_int
            else str(int(base_val)))

    with c2:
        if is_int:
            new_val = st.number_input(
                label, value=int(current),
                min_value=int(min_val) if min_val is not None else None,
                step=1, key=wk, label_visibility="collapsed")
            _fset(key, int(new_val), base_val, is_int=True)
        else:
            disp_val = float(current) * 100.0 if suffix == "%" else float(current)
            mv = (float(min_val) * 100.0 if (min_val is not None and suffix == "%")
                  else float(min_val) if min_val is not None else None)
            new_disp = st.number_input(
                label, value=disp_val, min_value=mv,
                step=float(step), format=f"%{fmt}",
                key=wk, label_visibility="collapsed")
            new_val = new_disp / 100.0 if suffix == "%" else new_disp
            _fset(key, new_val, base_val)

    with c3:
        # Bug fix: reset button must be rendered here, AFTER the input, not after return
        if st.button("↩", key=rk, help=f"Reset to: {hint}",
                     disabled=not mod, use_container_width=True):
            _fin.pop(key, None)
            st.session_state.pop(wk, None)
            st.rerun()

    return int(new_val) if is_int else _fin.get(key, base_val)

def _display_row(label, value, fmt=".4f", suffix="", bold=False, color="#6e7681"):
    c1, c2, _ = st.columns([3, 2, 1])
    fw = "font-weight:600;" if bold else ""
    if isinstance(value, float):
        disp = f"{value*100:{fmt}}%" if suffix == "%" else f"{value:{fmt}}{suffix}"
    else:
        disp = f"{value}{suffix}"
    with c1:
        st.markdown(
            f'<p style="margin:0;padding:.32rem 0;font-size:.9rem;'
            f'color:{color};{fw}">{label}</p>', unsafe_allow_html=True)
    with c2:
        st.markdown(
            f'<p style="margin:0;padding:.32rem 0;font-size:.9rem;'
            f'font-family:DM Mono,monospace;color:{color};text-align:right;{fw}">'
            f'{disp}</p>', unsafe_allow_html=True)

def _section_label(text, color="#58a6ff"):
    st.markdown(
        f'<p style="font-size:.72rem;letter-spacing:.07em;color:{color};'
        f'font-weight:600;margin:.7rem 0 .1rem 0;text-transform:uppercase">{text}</p>',
        unsafe_allow_html=True)

def _reset_key(key):
    """Pop both the fin override and the widget key."""
    _fin.pop(key, None)
    st.session_state.pop(f"cffin_{scenario_name}_{key}", None)

# ── Expander ──────────────────────────────────────────────────────────────────
with st.expander(
    "**Financial Assumptions**  —  click to edit before running analysis",
    expanded=False, icon=":material/settings:"
):
    _n_overrides = sum(1 for k in _fin if not k.startswith("_"))
    hdr_c1, hdr_c2 = st.columns([4, 1])
    with hdr_c1:
        if _n_overrides:
            st.badge(f"{_n_overrides} assumption(s) modified",
                     icon=":material/edit:", color="orange")
        else:
            st.badge("All values match scenario defaults",
                     icon=":material/check_circle:", color="blue")
    with hdr_c2:
        if st.button("↺ Reset all", key="fin_reset_all",
                     disabled=(_n_overrides == 0), use_container_width=True):
            keys_to_pop = [k for k in st.session_state
                           if k.startswith(f"cffin_{scenario_name}_")
                           or k.startswith(f"cffinrst_{scenario_name}_")]
            for k in keys_to_pop:
                st.session_state.pop(k, None)
            st.session_state.cf_fin[scenario_name] = {}
            st.rerun()

    st.markdown("---")
    col_left, col_mid, col_right = st.columns(3)

    # ─────────────────────────────────────────────────────────────────────────
    # LEFT COLUMN
    # ─────────────────────────────────────────────────────────────────────────
    with col_left:

        # LAND
        _section_label("Land assumptions", "#e6a817")
        _land_base    = d.get("Land Option", "Buy")
        _land_wk      = f"cffin_{scenario_name}_Land Option"
        _land_options = ["Buy", "Rent"]
        _land_idx     = _land_options.index(_fin.get("Land Option", _land_base))
        _land_changed = _modified("Land Option")
        _lo_label_color = "#e6a817" if _land_changed else "#c9d1d9"
        st.markdown(
            f'<p style="margin:0;padding:.2rem 0 .1rem 0;font-size:.9rem;'
            f'color:{_lo_label_color}">Land option</p>', unsafe_allow_html=True)
        _land_sel = st.radio(
            "Land option", _land_options, index=_land_idx,
            horizontal=True, key=_land_wk, label_visibility="collapsed")
        if _land_sel != _land_base:
            _fin["Land Option"] = _land_sel
        elif "Land Option" in _fin:
            del _fin["Land Option"]
        fa_land_opt = _land_sel

        _isbl_val = safe_val(d, "Project Costs ISBL+OSBL")
        _display_row("ISBL+OSBL", _isbl_val / 1_000_000,
                     fmt=".3f", suffix=" M USD")
        if fa_land_opt == "Rent":
            _lrp_base     = safe_val(d, "Land Rent Pct", 0.2) / 100.0
            fa_land_pct   = _fin_row("Land factor (% of ISBL+OSBL)", "Land Rent Pct",
                                     _lrp_base, step=0.01, fmt=".3f", suffix="%")
            fa_land_rent_yr_val = _isbl_val * fa_land_pct / 100.0
            _display_row("Land rent (M USD/yr)",
                         fa_land_rent_yr_val / 1_000_000,
                         fmt=".3f", suffix=" M USD/yr", color="#3fb950")
            fa_land_buy_cost = 0.0
        else:
            _lbp_base        = safe_val(d, "Land Buy Pct", 2.0) / 100.0
            fa_land_pct      = _fin_row("Land purchase (% of ISBL+OSBL)", "Land Buy Pct",
                                        _lbp_base, step=0.01, fmt=".3f", suffix="%")
            fa_land_buy_cost = _isbl_val * fa_land_pct / 100.0
            _display_row("Land cost (M USD)",
                         fa_land_buy_cost / 1_000_000,
                         fmt=".3f", suffix=" M USD", color="#3fb950")
            fa_land_rent_yr_val = 0.0

        # DEPRECIATION
        _section_label("Depreciation", "#e6a817")
        _dep_m_base    = d.get("Depreciation Method", "Straight Line")
        _dep_m_wk      = f"cffin_{scenario_name}_Depreciation Method"
        _dep_m_opts    = ["Straight Line", "MACRS"]
        _dep_m_idx     = _dep_m_opts.index(_fin.get("Depreciation Method", _dep_m_base))
        _dep_m_changed = _modified("Depreciation Method")
        st.markdown(
            f'<p style="margin:0;padding:.2rem 0 .1rem 0;font-size:.9rem;'
            f'color:{"#e6a817" if _dep_m_changed else "#c9d1d9"}">Depreciation method</p>',
            unsafe_allow_html=True)
        _dep_m_sel = st.radio(
            "Depreciation method", _dep_m_opts, index=_dep_m_idx,
            horizontal=True, key=_dep_m_wk, label_visibility="collapsed")
        if _dep_m_sel != _dep_m_base:
            _fin["Depreciation Method"] = _dep_m_sel
        elif "Depreciation Method" in _fin:
            del _fin["Depreciation Method"]
        fa_dep_method = _dep_m_sel

        fa_dep_yrs = _fin_row(
            "Depreciation period (years)", "Depreciation Years",
            int(safe_val(d, "Depreciation Years", 10)),
            step=1, fmt="d", is_int=True, min_val=1)
        fa_resid_pct = _fin_row(
            "Residual value (% of CAPEX)", "Residual Value Pct",
            safe_val(d, "Residual Value Pct", 20.0),
            step=0.5, fmt=".1f", suffix="%")

        # FIXED COSTS
        _section_label("Fixed costs distribution", "#3fb950")
        st.markdown('<p style="font-size:.72rem;color:#6e7681;margin:0 0 .1rem 0">'
                    '% of annual fixed costs</p>', unsafe_allow_html=True)
        fa_fc_first = _fin_row("1st year", "Fixed Costs First Year",
                               safe_val(d, "Fixed Costs First Year", 100.0),
                               step=1.0, fmt=".1f", suffix="%")
        fa_fc_inter = _fin_row("Intermediate years", "Fixed Costs Intermediate",
                               safe_val(d, "Fixed Costs Intermediate", 100.0),
                               step=1.0, fmt=".1f", suffix="%")
        fa_fc_last  = _fin_row("Last year", "Fixed Costs Last Year",
                               safe_val(d, "Fixed Costs Last Year", 100.0),
                               step=1.0, fmt=".1f", suffix="%")

        # PRODUCTION CAPACITY
        _section_label("Production capacity", "#3fb950")
        st.markdown('<p style="font-size:.72rem;color:#6e7681;margin:0 0 .1rem 0">'
                    '% of total capacity</p>', unsafe_allow_html=True)
        fa_cap_first = _fin_row("1st year", "Capacity First Year",
                                safe_val(d, "Capacity First Year", 100.0),
                                step=1.0, fmt=".1f", suffix="%")
        fa_cap_inter = _fin_row("Intermediate years", "Capacity Intermediate",
                                safe_val(d, "Capacity Intermediate", 100.0),
                                step=1.0, fmt=".1f", suffix="%")
        fa_cap_last  = _fin_row("Last year", "Capacity Last Year",
                                safe_val(d, "Capacity Last Year", 100.0),
                                step=1.0, fmt=".1f", suffix="%")

    # ─────────────────────────────────────────────────────────────────────────
    # MIDDLE COLUMN
    # ─────────────────────────────────────────────────────────────────────────
    with col_mid:

        # PROJECT LIFETIME
        _section_label("Project lifetime", "#58a6ff")
        fa_op_yrs  = _fin_row("Project lifetime (years)", "Project Lifetime",
                              int(safe_val(d, "Project Lifetime", 20)),
                              step=1, fmt="d", is_int=True, min_val=1)
        fa_epc_yrs = _fin_row("EPC time (years)", "EPC Years",
                              int(safe_val(d, "EPC Years", 3)),
                              step=1, fmt="d", is_int=True, min_val=1)
        _display_row("Total (years)", fa_op_yrs + fa_epc_yrs,
                     fmt="d", bold=True, color="#3fb950")

        # CAPEX DISTRIBUTION
        _section_label("Distribution of CAPEX", "#e6a817")
        st.markdown('<p style="font-size:.72rem;color:#6e7681;margin:0 0 .15rem 0">'
                    'EPC year fractions (last year = 1 − others)</p>',
                    unsafe_allow_html=True)

        # Detect EPC count change → reset fractions to reference table
        _prev_epc_key = f"_epc_for_fracs"
        _prev_epc     = _fin.get(_prev_epc_key)
        if _prev_epc != fa_epc_yrs:
            # EPC count changed — wipe stored fractions and reseed from ref table
            for _ki in range(10):
                _reset_key(f"capex_frac_{_ki}")
            _fin[_prev_epc_key] = fa_epc_yrs

        _ref_fracs = list(CAPEX_DISTRIBUTION[str(fa_epc_yrs)].values)[:fa_epc_yrs]
        _ord       = ["1st","2nd","3rd","4th","5th","6th","7th","8th","9th","10th"]
        _editable_fracs = []

        # Header
        st.markdown(
            '<div style="display:flex;gap:.4rem;margin-bottom:.15rem">'
            '<span style="flex:1.2;font-size:.7rem;color:#6e7681">EPC year</span>'
            '<span style="flex:2;font-size:.7rem;color:#6e7681;text-align:right">'
            '% of CAPEX</span>'
            '<span style="flex:.5"></span></div>',
            unsafe_allow_html=True)

        for _ki in range(fa_epc_yrs - 1):
            _frac_base = _ref_fracs[_ki] if _ki < len(_ref_fracs) else 0.0
            _frac_key  = f"capex_frac_{_ki}"
            _frac_wk   = f"cffin_{scenario_name}_{_frac_key}"
            _frac_rk   = f"cffinrst_{scenario_name}_{_frac_key}"
            _frac_cur  = _fin.get(_frac_key, _frac_base)
            _frac_mod  = _modified(_frac_key)

            fc1, fc2, fc3 = st.columns([1.2, 2, 0.5])
            with fc1:
                st.markdown(
                    f'<p style="margin:0;padding:.32rem 0;font-size:.8rem;'
                    f'color:{"#e6a817" if _frac_mod else "#c9d1d9"}">'
                    f'{_ord[_ki]}</p>', unsafe_allow_html=True)
            with fc2:
                _new_frac_pct = st.number_input(
                    f"frac_{_ki}", value=float(_frac_cur) * 100.0,
                    min_value=0.0, max_value=100.0,
                    step=1.0, format="%.2f",
                    key=_frac_wk, label_visibility="collapsed")
                _new_frac = _new_frac_pct / 100.0
                if abs(_new_frac - _frac_base) > 1e-9:
                    _fin[_frac_key] = _new_frac
                elif _frac_key in _fin:
                    del _fin[_frac_key]
                _editable_fracs.append(_new_frac)
            with fc3:
                if st.button("↩", key=_frac_rk, help=f"Reset to {_frac_base*100:.2f}%",
                             disabled=not _frac_mod, use_container_width=True):
                    _reset_key(_frac_key)
                    st.rerun()

        # Last year — computed, read-only
        _last_frac = max(0.0, 1.0 - sum(_editable_fracs))
        fl1, fl2, fl3 = st.columns([1.2, 2, 0.5])
        with fl1:
            st.markdown(
                f'<p style="margin:0;padding:.32rem 0;font-size:.8rem;'
                f'color:#6e7681">{_ord[fa_epc_yrs-1]}</p>', unsafe_allow_html=True)
        with fl2:
            _last_color = "#f85149" if _last_frac < 0 else "#3fb950"
            st.markdown(
                f'<p style="margin:0;padding:.32rem 0;font-size:.8rem;'
                f'font-family:DM Mono,monospace;color:{_last_color};text-align:right">'
                f'{_last_frac*100:.2f}%</p>', unsafe_allow_html=True)
        # Warning if fractions overshoot
        if sum(_editable_fracs) > 1.0:
            st.warning("Fractions exceed 100% — last year clamped to 0%.",
                       icon=":material/warning:")

        # Store final fracs for table consumption
        _fa_capex_fracs = _editable_fracs + [_last_frac]

        # TAXES
        _section_label("Taxes", "#58a6ff")
        _tax_country_base = d.get("Tax Country", "Brazil")
        _tax_country_cur  = _fin.get("Tax Country", _tax_country_base)
        _tc_wk            = f"cffin_{scenario_name}_Tax Country"
        _tc_changed       = _modified("Tax Country")
        st.markdown(
            f'<p style="margin:0;padding:.2rem 0 .1rem 0;font-size:.9rem;'
            f'color:{"#e6a817" if _tc_changed else "#c9d1d9"}">Country</p>',
            unsafe_allow_html=True)
        _tc_idx = COUNTRY_LIST.index(_tax_country_cur) if _tax_country_cur in COUNTRY_LIST else 0
        _tc_sel = st.selectbox("Tax country", COUNTRY_LIST, index=_tc_idx,
                               key=_tc_wk, label_visibility="collapsed")

        # Auto-update tax rate whenever country selection changes from previous render
        _prev_country = _fin.get("_tax_country_prev", _tax_country_base)
        if _tc_sel != _prev_country:
            # Country changed — seed Tax Rate from reference table and clear widget key
            _auto_tax = TAXES_BY_COUNTRY.get(_tc_sel, 0.34)
            _fin["Tax Rate"] = _auto_tax
            _fin["_tax_country_prev"] = _tc_sel
            st.session_state.pop(f"cffin_{scenario_name}_Tax Rate", None)

        if _tc_sel != _tax_country_base:
            _fin["Tax Country"] = _tc_sel
        elif "Tax Country" in _fin:
            del _fin["Tax Country"]

        _tax_base_val = safe_val(d, "Tax Rate", 0.34)
        if _tax_base_val > 1.0: _tax_base_val /= 100.0
        # Use the auto-seeded Tax Rate if present, else scenario default
        _tax_cur_val = _fin.get("Tax Rate", _tax_base_val)

        fa_tax_rate = _fin_row(
            "Tax rate", "Tax Rate",
            _tax_cur_val,
            step=0.1, fmt=".1f", suffix="%")

        # FINANCING
        _section_label("Financial leverage", "#58a6ff")
        _fin_t_base = d.get("Financing Type", "None")
        _fin_t_wk   = f"cffin_{scenario_name}_Financing Type"
        _fin_t_opts = ["None", "Straight Line"]
        _fin_t_idx  = _fin_t_opts.index(_fin.get("Financing Type", _fin_t_base))
        _fin_t_chg  = _modified("Financing Type")
        st.markdown(
            f'<p style="margin:0;padding:.2rem 0 .1rem 0;font-size:.9rem;'
            f'color:{"#e6a817" if _fin_t_chg else "#c9d1d9"}">Financing type</p>',
            unsafe_allow_html=True)
        _fin_t_sel = st.radio(
            "Financing type", _fin_t_opts, index=_fin_t_idx,
            horizontal=True, key=_fin_t_wk, label_visibility="collapsed")
        if _fin_t_sel != _fin_t_base:
            _fin["Financing Type"] = _fin_t_sel
        elif "Financing Type" in _fin:
            del _fin["Financing Type"]
        fa_fin_type = _fin_t_sel
        fa_leveraged = fa_fin_type == "Straight Line"

        if fa_leveraged:
            fa_debt_ratio = _fin_row(
                "Debt ratio (% of CAPEX)", "Debt Ratio Pct",
                safe_val(d, "Debt Ratio Pct", 50.0),
                step=1.0, fmt=".1f", suffix="%")
            fa_amort_yrs = _fin_row(
                "Amortization period (years)", "Amortization Years",
                int(safe_val(d, "Amortization Years", 13)),
                step=1, fmt="d", is_int=True, min_val=1)
            fa_grace_yrs = _fin_row(
                "Grace period (years)", "Grace Period Years",
                int(safe_val(d, "Grace Period Years", 5)),
                step=1, fmt="d", is_int=True, min_val=0)
        else:
            for _lbl in ["Debt ratio (% of CAPEX)",
                         "Amortization period (years)", "Grace period (years)"]:
                _display_row(_lbl, "—")
            fa_debt_ratio = 0.0
            fa_amort_yrs  = int(safe_val(d, "Amortization Years", 13))
            fa_grace_yrs  = int(safe_val(d, "Grace Period Years",  5))

    # ─────────────────────────────────────────────────────────────────────────
    # RIGHT COLUMN
    # ─────────────────────────────────────────────────────────────────────────
    with col_right:

        # MARR
        _section_label("MARR", "#58a6ff")
        fa_cbr = _fin_row("Central bank interest rate (rB)", "Central Bank Rate",
                          safe_val(d, "Central Bank Rate", 5.45),
                          step=0.01, fmt=".2f", suffix="%")
        fa_cs  = _fin_row("Credit spread (Scu)", "Credit Spread",
                          safe_val(d, "Credit Spread", 2.94),
                          step=0.01, fmt=".2f", suffix="%")

        _fa_tax_frac = _fin.get("Tax Rate", _tax_base_val if '_tax_base_val' in dir() else 0.34)
        if _fa_tax_frac > 1.0: _fa_tax_frac /= 100.0
        fa_cod = (fa_cbr / 100.0 + fa_cs / 100.0) * (1.0 - _fa_tax_frac)
        _fin_row("Cost of debt (COD)", "_cod", fa_cod,
                 computed_val=fa_cod, bold=True)

        fa_ubeta = _fin_row("Unlevered/Asset beta (βu)", "Unlevered Beta",
                            safe_val(d, "Unlevered Beta", 1.0),
                            step=0.01, fmt=".2f")
        _dr_frac = (fa_debt_ratio / 100.0) if fa_leveraged else 0.0
        _lev_f   = ((1.0 - _fa_tax_frac) * _dr_frac / (1.0 - _dr_frac)
                    if _dr_frac < 1.0 else 0.0)
        fa_lbeta = fa_ubeta * (1.0 + _lev_f)
        _fin_row("Levered/Equity beta (βl)", "_lbeta", fa_lbeta,
                 computed_val=fa_lbeta)

        fa_rm = _fin_row("Market return (rM)", "Market Return",
                         safe_val(d, "Market Return", 8.63),
                         step=0.01, fmt=".2f", suffix="%")
        fa_rf = _fin_row("Risk-free rate (rf)", "Risk Free Rate",
                         safe_val(d, "Risk Free Rate", 1.94),
                         step=0.01, fmt=".2f", suffix="%")
        fa_prm = fa_lbeta * (fa_rm - fa_rf) / 100.0
        _fin_row("Market risk premium (PRM)", "_prm", fa_prm,
                 computed_val=fa_prm, bold=True)

        fa_prp   = _fin_row("Country risk premium (PRP)", "Country Risk Premium",
                            safe_val(d, "Country Risk Premium", 3.63),
                            step=0.01, fmt=".2f", suffix="%")
        fa_uscpi = _fin_row("U.S. CPI (IUSA)", "US CPI",
                            safe_val(d, "US CPI", 2.46),
                            step=0.01, fmt=".2f", suffix="%")
        fa_ccpi  = _fin_row("Country's CPI (Icountry)", "Country CPI",
                            safe_val(d, "Country CPI", 4.65),
                            step=0.01, fmt=".2f", suffix="%")

        _rfr_f   = fa_rf    / 100.0
        _ccpi_f  = fa_ccpi  / 100.0
        _uscpi_f = fa_uscpi / 100.0
        fa_coe   = ((1 + _rfr_f) * (1 + _ccpi_f) / (1 + _uscpi_f) - 1) + fa_prm + fa_prp / 100.0
        _fin_row("Cost of equity (COE)", "_coe", fa_coe,
                 computed_val=fa_coe, bold=True)

        _marr_formula = (_dr_frac * fa_cod + (1 - _dr_frac) * fa_coe) if fa_leveraged else fa_coe
        fa_marr = _fin_row("MARR", "MARR", _marr_formula,
                           step=0.01, fmt=".2f", suffix="%", bold=True)
        # Persist computed intermediates (not user-editable, prefixed with _)
        _fin["_cod_computed"]  = fa_cod
        _fin["_coe_computed"]  = fa_coe
        _fin["_marr_final"]    = fa_marr if "MARR" in _fin else _marr_formula

        # MARKET ASSUMPTIONS
        _section_label("Market assumptions (per year)", "#3fb950")
        st.markdown('<p style="font-size:.72rem;color:#6e7681;margin:0 0 .1rem 0">'
                    'Annual growth rate (%)</p>', unsafe_allow_html=True)
        fa_g_main = _fin_row("Main product",       "Growth Main Price",
                             safe_val(d, "Growth Main Price",      0.0),
                             step=0.1, fmt=".1f", suffix="%")
        fa_g_bp   = _fin_row("Byproducts",         "Growth Byproduct Price",
                             safe_val(d, "Growth Byproduct Price", 0.0),
                             step=0.1, fmt=".1f", suffix="%")
        fa_g_rm   = _fin_row("Raw materials",      "Growth Raw Materials",
                             safe_val(d, "Growth Raw Materials",   0.0),
                             step=0.1, fmt=".1f", suffix="%")
        fa_g_cu   = _fin_row("Chem. inputs & util.","Growth Chem Utilities",
                             safe_val(d, "Growth Chem Utilities",  0.0),
                             step=0.1, fmt=".1f", suffix="%")
        fa_g_fc   = _fin_row("Fixed costs",        "Growth Fixed Costs",
                             safe_val(d, "Growth Fixed Costs",     0.0),
                             step=0.1, fmt=".1f", suffix="%")

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# EXPOSE _fa_* VARIABLES FOR THE UNIFIED TABLE
# All variables below are consumed by financial_unified.py
# ─────────────────────────────────────────────────────────────────────────────
def _fa(key, fallback=0.0):
    if key in _fin and not str(key).startswith("_"):
        return _fin[key]
    v = d.get(key, fallback)
    return v if isinstance(v, (int, float)) else fallback

# Structural
_fa_epc_yrs     = fa_epc_yrs
_fa_op_yrs      = fa_op_yrs
_fa_capex_fracs = _fa_capex_fracs      # list of fracs, len == fa_epc_yrs
_fa_land_opt    = fa_land_opt
_fa_land_rent_yr= fa_land_rent_yr_val
_fa_land_buy    = fa_land_buy_cost
_fa_fin_type    = fa_fin_type
_fa_leveraged   = fa_leveraged

# Depreciation
_fa_dep_method  = fa_dep_method
_fa_dep_yrs     = fa_dep_yrs
_fa_resid_pct   = fa_resid_pct / 100.0

# Schedules
_fa_cap_first   = fa_cap_first  / 100.0
_fa_cap_inter   = fa_cap_inter  / 100.0
_fa_cap_last    = fa_cap_last   / 100.0
_fa_fc_first    = fa_fc_first   / 100.0
_fa_fc_inter    = fa_fc_inter   / 100.0
_fa_fc_last     = fa_fc_last    / 100.0

# Financial
_fa_tax         = fa_tax_rate if fa_tax_rate <= 1.0 else fa_tax_rate / 100.0
_fa_debt_ratio  = (fa_debt_ratio / 100.0) if fa_leveraged else 0.0
_fa_amort_yrs   = fa_amort_yrs
_fa_grace_yrs   = fa_grace_yrs
_fa_cod         = fa_cod
_fa_marr_raw    = _fin.get("_marr_final", _marr_formula)
_fa_marr        = _fa_marr_raw / 100.0 if _fa_marr_raw > 1.0 else _fa_marr_raw

# Growth
_fa_g_main      = fa_g_main  / 100.0
_fa_g_byprod    = fa_g_bp    / 100.0
_fa_g_rm        = fa_g_rm    / 100.0
_fa_g_cu        = fa_g_cu    / 100.0
_fa_g_fc        = fa_g_fc    / 100.0

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3: FINANCIAL ANALYSIS — UNIFIED CASH FLOW TABLE
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Financial Analysis")
st.caption(
    "Year-by-year cash flow table. Outflows shown as (negative), inflows positive. "
    "What-if overrides applied where available."
)
st.space("medium")

from utils.constants import CAPEX_DISTRIBUTION

# ─────────────────────────────────────────────────────────────────────────────
# WHAT-IF AWARE RESOLVER
# ─────────────────────────────────────────────────────────────────────────────
def _wv(key, fallback=0.0):
    """Prefer what-if override, then saved scenario value, then fallback."""
    if key in wif:
        return wif[key]
    v = d.get(key, fallback)
    return v if isinstance(v, (int, float)) else fallback

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT TIMELINE  (structural — never overridable)
# ─────────────────────────────────────────────────────────────────────────────
_epc   = _fa_epc_yrs
_op    = _fa_op_yrs
_total = _epc + _op
_y0    = int(d.get("Year of Analysis", 2024))

# ─────────────────────────────────────────────────────────────────────────────
# INVESTMENT INPUTS  (what-if aware)
# ─────────────────────────────────────────────────────────────────────────────
_capex   = _wv("Project CAPEX",   safe_val(d, "Project CAPEX"))
_wc      = _wv("Working Capital", safe_val(d, "Working Capital"))
_startup = _wv("Startup Costs",   safe_val(d, "Startup Costs"))
_isbl    = safe_val(d, "Project Costs ISBL+OSBL")

_land_opt = _fa_land_opt
if _land_opt == "Buy":
    _land_buy = _fa_land_buy
    _land_rent_yr = 0.0
else:
    _land_buy = 0.0
    _land_rent_yr = _fa_land_rent_yr

_epc_col    = str(_epc)
_cap_fracs  = _fa_capex_fracs

# ─────────────────────────────────────────────────────────────────────────────
# REVENUE INPUTS  (what-if aware)
# ─────────────────────────────────────────────────────────────────────────────
_prod_unit   = d.get("Unit", "")
_wif_cap     = _wv("Capacity",               safe_val(d, "Capacity"))
_wif_wh      = _wv("Working Hours per Year", safe_val(d, "Working Hours per Year", 8000.0))

# ── Effective product price — shared with dashboard ───────────────────────────
# Read from price mode state if available, fall back to saved scenario value.
# This ensures the revenue table and NPV graph always use the same price.
_input_price_raw = safe_val(d, "Main Product Price", 0.0)
_pm_state = (st.session_state
             .get("cf_price_mode", {})
             .get(scenario_name, {}))
_pm_mode  = _pm_state.get("mode", "MANUAL")
if _pm_mode != "MANUAL" and _pm_state.get("solved_price"):
    _main_price = float(_pm_state["solved_price"])
elif _pm_state.get("manual_price") is not None:
    _main_price = float(_pm_state["manual_price"])
else:
    _main_price = _input_price_raw

_bp_base = 0.0
for _r in (d.get("Credits and Byproducts", []) or []):
    if not _r.get("Name"): continue
    _rate = float(_r.get("Rate", 0.0)); _price = float(_r.get("Price", 0.0))
    _bp_base += _price * _rate * (1.0 if is_per_year(_r.get("Rate Unit","")) else _wif_wh)

_cap_first = _fa_cap_first
_cap_inter = _fa_cap_inter
_cap_last  = _fa_cap_last
_fc_first  = _fa_fc_first
_fc_inter  = _fa_fc_inter
_fc_last   = _fa_fc_last

def _cpct(oi):
    return _cap_first if oi==0 else (_cap_last if oi==_op-1 else _cap_inter)
def _fpct(oi):
    return _fc_first  if oi==0 else (_fc_last  if oi==_op-1 else _fc_inter)

_g_main   = _fa_g_main
_g_byprod = _fa_g_byprod
_g_rm     = _fa_g_rm
_g_cu     = _fa_g_cu
_g_fc     = _fa_g_fc

# ─────────────────────────────────────────────────────────────────────────────
# RESIDUAL VALUE & DEPRECIATION
# ─────────────────────────────────────────────────────────────────────────────
_resid_pct  = _fa_resid_pct
_resid_usd  = _capex * _resid_pct
_dep_method = _fa_dep_method
_dep_yrs    = _fa_dep_yrs
_dep_sl     = -(_capex - _resid_usd) / _dep_yrs if _dep_yrs > 0 else 0.0

_MACRS = {
    3:  [0.3333,0.4445,0.1481,0.0741],
    5:  [0.2000,0.3200,0.1920,0.1152,0.1152,0.0576],
    7:  [0.1429,0.2449,0.1749,0.1249,0.0893,0.0892,0.0893,0.0446],
    10: [0.1000,0.1800,0.1440,0.1152,0.0922,0.0737,0.0655,0.0655,0.0656,0.0655,0.0328],
    15: [0.0500,0.0950,0.0855,0.0770,0.0693,0.0623,0.0590,0.0590,0.0591,0.0590,
         0.0591,0.0590,0.0591,0.0590,0.0591,0.0295],
    20: [0.0375,0.0722,0.0668,0.0618,0.0571,0.0528,0.0489,0.0452,0.0446,0.0446,
         0.0446,0.0446,0.0446,0.0446,0.0446,0.0446,0.0446,0.0446,0.0446,0.0446,0.0223],
}
_mk   = min(_MACRS.keys(), key=lambda k: abs(k - _dep_yrs))
_mrat = _MACRS[_mk]

def _dep(oi):
    if _dep_method == "Straight Line":
        return _dep_sl if oi < _dep_yrs else 0.0
    return (-_capex * _mrat[oi]) if oi < len(_mrat) else 0.0

# ─────────────────────────────────────────────────────────────────────────────
# OPEX COMPONENTS  (what-if aware — pull from Section 2 computed values)
# ─────────────────────────────────────────────────────────────────────────────
_cap_ratio = _wif_cap / safe_val(d, "Capacity", _wif_cap) if safe_val(d, "Capacity", 1.0) > 0 else 1.0
_rm_base   = safe_val(d, "Total Raw Material Cost",         0.0) * _cap_ratio
_cu_base   = safe_val(d, "Total Chemical Inputs Utilities", 0.0) * _cap_ratio
_lab_base  = wif_labor
_sm_base   = wif_supply_maint
_afc_base  = wif_afc
_ifc_base  = wif_indirect

# ─────────────────────────────────────────────────────────────────────────────
# FINANCING  (structural — never overridable)
# ─────────────────────────────────────────────────────────────────────────────
_fin_type   = _fa_fin_type
_leveraged  = _fa_leveraged
_debt_ratio = _fa_debt_ratio
_tot_debt   = _capex * _debt_ratio
_amort_yrs  = _fa_amort_yrs
_grace_yrs  = _fa_grace_yrs
_cod        = safe_val(d, "COD", 0.0)
if _cod > 1.0: _cod /= 100.0
_ann_repay  = _tot_debt / _amort_yrs if (_leveraged and _amort_yrs > 0) else 0.0

# ─────────────────────────────────────────────────────────────────────────────
# TAX & MARR
# ─────────────────────────────────────────────────────────────────────────────
_tax  = _fa_tax
_marr = _fa_marr

# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE ALL COLUMNS  (single pass)
# ─────────────────────────────────────────────────────────────────────────────
# Index
T_cal  = [str(_y0 + i) for i in range(_total)]
T_proj = [str(i)       for i in range(_total)]
T_op   = ["—"] * _epc + [str(j) for j in range(1, _op + 1)]

# Module arrays — None = not applicable (EPC row for income statement cols)
I_capex=[]; I_wc=[]; I_su=[]; I_land=[]; I_tot=[]
R_main=[]; R_bp=[]; R_cc=[]; R_resid=[]; R_tot=[]
E_rm=[]; E_cu=[]; E_carb=[]; E_lab=[]; E_sm=[]; E_afc=[]; E_ifc=[]; E_rent=[]; E_tot=[]
F_debt=[]; F_amort=[]; F_accum=[]; F_int=[]; F_tot=[]
C_rev=[]; C_vl=[]; C_gp=[]; C_fix=[]; C_ebitda=[]; C_dep=[]
C_ebit=[]; C_fint=[]; C_ebt=[]; C_tax=[]; C_np=[]
C_amort=[]; C_inv=[]; C_cf=[]; C_pvcf=[]; C_acpv=[]

_accum_debt = 0.0
_accum_pv   = 0.0

for i in range(_total):
    oi = i - _epc       # operational index (negative during EPC)
    epc = i < _epc

    # ── INVESTMENT ──────────────────────────────────────────────────────────
    i_cap  = -_capex * _cap_fracs[i] if epc else 0.0
    i_wc   = (-_wc if i == _epc - 1
               else (+_wc if oi == _op - 1 else 0.0))
    i_su   = -_startup if oi == 0 else 0.0
    i_land = -_land_buy if i == 0 else 0.0
    i_tot  = i_cap + i_wc + i_su + i_land
    I_capex.append(i_cap); I_wc.append(i_wc); I_su.append(i_su)
    I_land.append(i_land); I_tot.append(i_tot)

    # ── FINANCING ────────────────────────────────────────────────────────────
    f_debt  = (_tot_debt * _cap_fracs[i]) if (epc and _leveraged) else 0.0
    _accum_debt += f_debt
    f_int   = -_accum_debt * _cod if _leveraged else 0.0
    f_amort = (-_ann_repay
               if (_leveraged and oi >= _grace_yrs
                   and (oi - _grace_yrs) < _amort_yrs)
               else 0.0)
    _accum_debt += f_amort
    f_accum = _accum_debt
    f_tot   = f_amort + f_int
    F_debt.append(f_debt); F_amort.append(f_amort); F_accum.append(f_accum)
    F_int.append(f_int);   F_tot.append(f_tot)

    if epc:
        # Revenue & Expenses — not applicable during EPC
        for lst in [R_main,R_bp,R_cc,R_resid,R_tot]: lst.append(None)
        for lst in [E_rm,E_cu,E_carb,E_lab,E_sm,E_afc,E_ifc,E_rent,E_tot]: lst.append(None)
        # Cash Flow income statement — not applicable during EPC
        for lst in [C_rev,C_vl,C_gp,C_fix,C_ebitda,C_dep,
                    C_ebit,C_ebt,C_tax,C_np]: lst.append(None)
        C_fint.append(f_int); C_amort.append(f_amort); C_inv.append(i_tot)
        cf_i  = i_tot + f_int + f_amort
        pv_i  = cf_i / (1 + _marr) ** i
        _accum_pv += pv_i
        C_cf.append(cf_i); C_pvcf.append(pv_i); C_acpv.append(_accum_pv)
        continue

    # ── REVENUE ──────────────────────────────────────────────────────────────
    cp = _cpct(oi)
    r_main  =  _main_price * _wif_cap * cp * (1 + _g_main)   ** oi
    r_bp    =  _bp_base    * cp        * (1 + _g_byprod) ** oi
    r_cc    =  0.0                       # carbon credits — future-proof
    r_resid =  _resid_usd if oi == _op - 1 else 0.0
    r_tot   =  r_main + r_bp + r_cc + r_resid
    R_main.append(r_main); R_bp.append(r_bp); R_cc.append(r_cc)
    R_resid.append(r_resid); R_tot.append(r_tot)

    # ── EXPENSES ─────────────────────────────────────────────────────────────
    fp = _fpct(oi)
    g_rm_f = (1+_g_rm)**oi; g_cu_f = (1+_g_cu)**oi; g_fc_f = (1+_g_fc)**oi
    e_rm   = -(_rm_base  * cp * g_rm_f)
    e_cu   = -(_cu_base  * cp * g_cu_f)
    e_carb = 0.0
    e_lab  = -(_lab_base * fp * g_fc_f)
    e_sm   = -(_sm_base  * fp * g_fc_f)
    e_afc  = -(_afc_base * fp * g_fc_f)
    e_ifc  = -(_ifc_base * fp * g_fc_f)
    e_rent = -(_land_rent_yr * g_fc_f) if _land_opt == "Rent" else 0.0
    e_tot  = e_rm+e_cu+e_carb+e_lab+e_sm+e_afc+e_ifc+e_rent
    E_rm.append(e_rm); E_cu.append(e_cu); E_carb.append(e_carb)
    E_lab.append(e_lab); E_sm.append(e_sm); E_afc.append(e_afc)
    E_ifc.append(e_ifc); E_rent.append(e_rent); E_tot.append(e_tot)

    # ── CASH FLOW INCOME STATEMENT ────────────────────────────────────────────
    c_rev    = r_tot
    c_vl     = e_rm + e_cu + e_carb + e_lab
    c_gp     = c_rev + c_vl
    c_fix    = e_sm + e_afc + e_ifc + e_rent
    c_ebitda = c_gp + c_fix
    c_dep    = _dep(oi)
    c_ebit   = c_ebitda + c_dep
    c_fint   = f_int
    c_ebt    = c_ebit + c_fint
    c_tax    = -max(0.0, c_ebt) * _tax
    c_np     = c_ebt + c_tax
    c_amort  = f_amort
    c_inv    = i_tot
    cf_i     = c_np + c_amort + c_inv
    pv_i     = cf_i / (1 + _marr) ** i
    _accum_pv += pv_i

    C_rev.append(c_rev); C_vl.append(c_vl); C_gp.append(c_gp)
    C_fix.append(c_fix); C_ebitda.append(c_ebitda); C_dep.append(c_dep)
    C_ebit.append(c_ebit); C_fint.append(c_fint); C_ebt.append(c_ebt)
    C_tax.append(c_tax); C_np.append(c_np); C_amort.append(c_amort)
    C_inv.append(c_inv); C_cf.append(cf_i); C_pvcf.append(pv_i)
    C_acpv.append(_accum_pv)

_npv = _accum_pv

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN REGISTRY — maps module → list of (header, array, is_subtotal)
# ─────────────────────────────────────────────────────────────────────────────
_INV_COLS = [
    ("CAPEX",           I_capex, False),
    ("Working Capital", I_wc,    False),
    ("Start-up",        I_su,    False),
    ("Land Purchase",   I_land,  False),
    ("Inv. Total",      I_tot,   True),
]
_REV_COLS = [
    ("Main Product",    R_main,  False),
    ("Byproducts",      R_bp,    False),
    ("Carbon Credits",  R_cc,    False),
    ("Residual Value",  R_resid, False),
    ("Rev. Total",      R_tot,   True),
]
_EXP_COLS = [
    ("Raw Materials",   E_rm,    False),
    ("Chem. & Util.",   E_cu,    False),
    ("Carbon Costs",    E_carb,  False),
    ("Labor",           E_lab,   False),
    ("Supply & Maint.", E_sm,    False),
    ("AFC",             E_afc,   False),
    ("Indirect Fixed",  E_ifc,   False),
    ("Land Rent",       E_rent,  False),
    ("Exp. Total",      E_tot,   True),
]
_FIN_COLS = [
    ("Debt Drawdown",   F_debt,  False),
    ("Amortization",    F_amort, False),
    ("Accum. Debt",     F_accum, False),
    ("Interest",        F_int,   False),
    ("Fin. Total",      F_tot,   True),
]
_CF_COLS = [
    ("Revenue",         C_rev,    False),
    ("Var. & Labor",    C_vl,     False),
    ("Gross Profit",    C_gp,     True),
    ("Fixed Costs",     C_fix,    False),
    ("EBITDA",          C_ebitda, True),
    ("Depreciation",    C_dep,    False),
    ("EBIT",            C_ebit,   True),
    ("Fin. Interest",   C_fint,   False),
    ("EBT",             C_ebt,    True),
    ("Taxes",           C_tax,    False),
    ("Net Profit",      C_np,     True),
    ("Amortization",    C_amort,  False),
    ("Proj. Investment",C_inv,    False),
    ("Cash Flow",       C_cf,     True),
    ("Present CF",      C_pvcf,   False),
    ("Accum. PV CF",    C_acpv,   True),
]

_MODULE_MAP = {
    "Investment": _INV_COLS,
    "Revenue":    _REV_COLS,
    "Expenses":   _EXP_COLS,
    "Financing":  _FIN_COLS,
    "Cash Flow":  _CF_COLS,
}
_MODULE_COLORS = {
    "Investment": "#e6a817",
    "Revenue":    "#3fb950",
    "Expenses":   "#f85149",
    "Financing":  "#58a6ff",
    "Cash Flow":  "#58a6ff",
}

# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _fv(v):
    """Format a single value. None → '—'. 0 → '—'. Neg → (x). Pos → x."""
    if v is None or v == 0.0:
        return "—"
    a = abs(v)
    s = (f"{a/1_000_000:.3f}M" if a >= 1_000_000
         else f"{a/1_000:.1f}k" if a >= 1_000
         else f"{a:,.2f}")
    return f"({s})" if v < 0 else s

def _cc(vs):
    """Cell color from formatted string."""
    if vs in ("—", ""): return "#30363d"
    return "#f85149" if vs.startswith("(") else "#3fb950"

# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# COLUMN SELECTOR — st.pills
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("#### Detailed Cash Flow Table")
st.caption("Select modules to display as column groups. Index columns always visible.")

_all_modules = ["Investment", "Revenue", "Expenses", "Financing", "Cash Flow"]

# Hide Financing pill if not leveraged
_available = [m for m in _all_modules if not (m == "Financing" and not _leveraged)]

_selected = st.pills(
    "Visible modules",
    options=_available,
    selection_mode="multi",
    default=["Cash Flow"],
    key="fin_module_pills",
    label_visibility="collapsed",
)

if not _selected:
    st.info("Select at least one module above to display the table.", icon=":material/table:")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# BUILD SELECTED COLUMN LIST
# ─────────────────────────────────────────────────────────────────────────────
_active_cols = []   # list of (header, formatted_array, is_subtotal, module_name)
for mod in _all_modules:
    if mod not in _selected:
        continue
    for (hdr, arr, is_sub) in _MODULE_MAP[mod]:
        _active_cols.append((hdr, [_fv(v) for v in arr], is_sub, mod))

# ─────────────────────────────────────────────────────────────────────────────
# HTML TABLE RENDERER — unified, sticky index, colored module headers
# ─────────────────────────────────────────────────────────────────────────────
def _render_unified_table(active_cols, epc_count, total_rows):
    # ── Column header row with module color bands ─────────────────────────────
    th_idx = (
        "padding:.5rem .9rem;font-size:.73rem;letter-spacing:.04em;"
        "white-space:nowrap;border-bottom:2px solid #21262d;background:#0d1117;"
        "text-align:left;color:#8b949e;position:sticky;left:0;z-index:3;"
    )
    th_val_base = (
        "padding:.5rem .8rem;font-size:.73rem;letter-spacing:.04em;"
        "white-space:nowrap;border-bottom:2px solid #21262d;background:#0d1117;"
        "text-align:right;color:#8b949e;"
    )

    # Group header row (module color bands)
    _prev_mod   = None
    _mod_spans  = []   # (module_name, col_count)
    for _, _, _, mod in active_cols:
        if mod != _prev_mod:
            _mod_spans.append([mod, 1])
            _prev_mod = mod
        else:
            _mod_spans[-1][1] += 1

    grp_cells = (
        f'<th colspan="3" style="{th_idx}border-bottom:1px solid #21262d;'
        f'color:#484f58;font-size:.68rem"></th>'
    )
    for mod_name, span in _mod_spans:
        mc = _MODULE_COLORS.get(mod_name, "#8b949e")
        grp_cells += (
            f'<th colspan="{span}" style="padding:.3rem .8rem;font-size:.68rem;'
            f'text-align:center;background:#0d1117;color:{mc};'
            f'border-bottom:1px solid {mc};border-left:2px solid {mc};'
            f'letter-spacing:.06em;white-space:nowrap;">'
            f'{mod_name.upper()}</th>'
        )

    # Column header row
    idx_hdrs = ["Calendar Year", "Proj. Year", "Op. Year"]
    col_cells = ""
    for h in idx_hdrs:
        col_cells += f'<th style="{th_idx}">{h}</th>'
    for j, (hdr, _, is_sub, mod) in enumerate(active_cols):
        mc   = _MODULE_COLORS.get(mod, "#8b949e")
        fw   = "font-weight:600;" if is_sub else ""
        bdr  = f"border-left:2px solid {mc};" if (j == 0 or active_cols[j-1][3] != mod) else ""
        col_cells += (
            f'<th style="{th_val_base}{fw}{bdr}">{hdr}</th>'
        )

    # ── Data rows ──────────────────────────────────────────────────────────────
    rows_html = []
    for i in range(total_rows):
        is_epc = i < epc_count
        bg     = "#0d1117" if is_epc else "#161b22"

        # Index cells — sticky left
        idx_vals = [T_cal[i], T_proj[i], T_op[i]]
        idx_color = "#484f58" if is_epc else "#6e7681"
        row_cells = ""
        for j, v in enumerate(idx_vals):
            align = "left" if j == 0 else "center"
            sticky = ("position:sticky;left:0;z-index:1;"
                      f"background:{bg};" if j == 0 else "")
            row_cells += (
                f'<td style="padding:.3rem .9rem;font-size:.77rem;'
                f'text-align:{align};color:{idx_color};{sticky}">{v}</td>'
            )

        # Value cells
        for j, (hdr, fmt_arr, is_sub, mod) in enumerate(active_cols):
            vs   = fmt_arr[i]
            mc   = _MODULE_COLORS.get(mod, "#8b949e")
            fc   = _cc(vs)
            fw   = "font-weight:600;" if is_sub else ""
            bdr  = f"border-left:2px solid {mc}22;" if (j == 0 or active_cols[j-1][3] != mod) else ""
            row_cells += (
                f'<td style="padding:.3rem .8rem;text-align:right;'
                f'font-family:DM Mono,monospace;font-size:.77rem;'
                f'color:{fc};{fw}{bdr}">{vs}</td>'
            )

        rows_html.append(
            f'<tr style="background:{bg};border-bottom:1px solid #1c2128;">'
            + row_cells + "</tr>"
        )

    return (
        '<div style="overflow-x:auto;max-height:580px;overflow-y:auto;'
        'border:1px solid #21262d;border-radius:6px;">'
        "<table style='width:100%;border-collapse:collapse;'>"
        "<thead style='position:sticky;top:0;z-index:2;'>"
        f"<tr>{grp_cells}</tr>"
        f"<tr>{col_cells}</tr>"
        "</thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table></div>"
    )

st.markdown(
    _render_unified_table(_active_cols, _epc, _total),
    unsafe_allow_html=True,
)

# ── Footer totals for selected columns ────────────────────────────────────────
st.space("small")
st.caption("Column totals — operational years only")
_op_totals_names  = []
_op_totals_values = []
for (hdr, arr, _, mod) in _active_cols:
    raw = _MODULE_MAP[mod]
    raw_arr = next(a for (h,a,_) in raw if h == hdr)
    val = sum(v for v in raw_arr[_epc:] if v is not None)
    _op_totals_names.append(hdr)
    _op_totals_values.append(val)

# Render in rows of 6 to avoid overcrowding
_chunk = 6
for start in range(0, len(_op_totals_names), _chunk):
    _ns = _op_totals_names[start:start+_chunk]
    _vs = _op_totals_values[start:start+_chunk]
    cols_ui = st.columns(len(_ns))
    for col_ui, lbl, val in zip(cols_ui, _ns, _vs):
        with col_ui:
            color = "#f85149" if val < 0 else ("#3fb950" if val > 0 else "#8b949e")
            st.markdown(
                f'<div style="text-align:center;padding:.35rem .2rem;'
                f'background:#161b22;border-radius:4px;">'
                f'<p style="font-size:.66rem;color:#6e7681;margin:0 0 .1rem 0;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{lbl}</p>'
                f'<p style="font-size:.84rem;font-family:DM Mono,monospace;'
                f'color:{color};font-weight:600;margin:0">{_fv(val)}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.space("medium")

# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL ANALYSIS OVERVIEW — below the table
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
section_header("Financial Analysis — Overview", "#58a6ff")

with st.expander("**Investment**", expanded=False, icon=":material/account_balance:"):
    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi_card("Project CAPEX",   smart_fmt(_capex),   "#58a6ff", f"Over {_epc} EPC yr(s)", "distributed")
    with k2: kpi_card("Working Capital", smart_fmt(_wc),      "#79c0ff", "Recovery", f"Op. year {_op}")
    with k3: kpi_card("Start-up Costs",  smart_fmt(_startup), "#3fb950", "Timing",   "Op. year 1")
    with k4:
        if _land_opt == "Buy":
            kpi_card("Land Purchase", smart_fmt(_land_buy), "#e6a817", "Timing", "Year 0")
        else:
            kpi_card("Land Rent", smart_fmt(_land_rent_yr)+"/yr", "#8b949e", "In", "Expenses")

with st.expander("**Revenue**", expanded=False, icon=":material/trending_up:"):
    r1,r2,r3 = st.columns(3)
    with r1: kpi_card("Main Product Price",
                      f"${_main_price:,.2f}/{_prod_unit}" if _main_price else "Not set", "#3fb950")
    with r2: kpi_card("Total Revenue (undiscounted)",
                      smart_fmt(sum(v for v in R_tot if v)), "#58a6ff")
    with r3: kpi_card("Residual Value", smart_fmt(_resid_usd), "#e6a817", "Method", _dep_method)
    if not _main_price:
        st.warning("Main product price not set — set it in Input Data → Other Premises.",
                   icon=":material/warning:")

with st.expander("**Expenses**", expanded=False, icon=":material/payments:"):
    e1,e2,e3 = st.columns(3)
    with e1: kpi_card("Total Expenses (undiscounted)",
                      smart_fmt(abs(sum(v for v in E_tot if v is not None))), "#f85149")
    with e2: kpi_card("Variable Cost Base",
                      smart_fmt(abs(sum(v for v in E_rm if v is not None)
                                  + sum(v for v in E_cu if v is not None))), "#ff7b72")
    with e3: kpi_card("Fixed Cost Base",
                      smart_fmt(abs(sum(v for v in E_sm if v is not None)
                                  + sum(v for v in E_afc if v is not None)
                                  + sum(v for v in E_ifc if v is not None))), "#ffa657")

with st.expander("**Financing**", expanded=False, icon=":material/credit_card:"):
    if not _leveraged:
        st.info("No financing configured (Financing Type = None).", icon=":material/info:")
    else:
        f1,f2,f3 = st.columns(3)
        with f1: kpi_card("Total Debt",     smart_fmt(_tot_debt),       "#58a6ff",
                          "Ratio", f"{_fa_debt_ratio*100:.1f}% of CAPEX")
        with f2: kpi_card("Amortization",   f"{_amort_yrs} years",      "#79c0ff",
                          "Grace", f"{_grace_yrs} years")
        with f3: kpi_card("Cost of Debt",   f"{_fa_cod*100:.2f}%",      "#e6a817")

with st.expander("**Cash Flow**", expanded=True, icon=":material/account_balance_wallet:"):
    npv_color = "#3fb950" if _npv >= 0 else "#f85149"
    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("NPV", smart_fmt(_npv), npv_color,
                      "MARR", f"{_marr*100:.2f}%")
    with c2: kpi_card("Depreciation", _dep_method, "#8b949e",
                      "Period", f"{_dep_yrs} yrs")
    with c3: kpi_card("Tax Rate", f"{_tax*100:.1f}%", "#8b949e",
                      "Country", _fin.get("Tax Country", d.get("Tax Country", "—")))
    with c4:
        _peak_i = I_tot.index(min(I_tot))
        kpi_card("Peak Investment", smart_fmt(abs(min(I_tot))), "#e6a817",
                 "Year", str(_peak_i))

st.space("medium")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4: FINANCIAL DASHBOARD
# NPV curve, MSP/NPV/IRR controls, scenario summary, KPI tables
# ═════════════════════════════════════════════════════════════════════════════
import numpy as np
import plotly.graph_objects as go

try:
    import numpy_financial as npf
    _HAS_NPF = True
except ImportError:
    _HAS_NPF = False

try:
    from scipy.optimize import brentq
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

st.markdown("---")
st.markdown("### Financial Dashboard")

# ─────────────────────────────────────────────────────────────────────────────
# CORE CF ENGINE — recomputes full CF for any product price & TIC multiplier
# All parameters come from _fa_* and wif variables already in scope
# ─────────────────────────────────────────────────────────────────────────────

def _build_cf_arrays(product_price, capex_mult=1.0):
    """
    Full year-by-year cash flow given a product price and a TIC multiplier.
    Returns (cf_list, accum_pv_list, calendar_years).
    """
    _c   = _capex   * capex_mult
    _lc_wc  = _wc      * capex_mult
    _lc_su  = _startup * capex_mult
    _dep_sl_v = -(_c - _c * _fa_resid_pct) / _fa_dep_yrs if _fa_dep_yrs > 0 else 0.0

    _fracs = _fa_capex_fracs   # already normalised, len == _fa_epc_yrs

    cfs = []; accum_pv = 0.0; pv_list = []; accum_list = []

    for i in range(_total):
        oi      = i - _epc
        is_epc  = i < _epc

        # Investment
        inv = -_c * _fracs[i] if is_epc else 0.0
        if i == _epc - 1:    inv += -_lc_wc
        if oi == _op - 1:    inv += +_lc_wc
        if oi == 0:          inv += -_lc_su
        if i == 0:           inv += -(_fa_land_buy * capex_mult
                                       if _fa_land_opt == "Buy" else 0.0)

        # Financing
        f_int   = 0.0
        f_amort = 0.0
        if _fa_leveraged:
            _tot_d = _c * _fa_debt_ratio
            _accum_d_i = _tot_d  # simplified: use total debt for interest calc
            f_int = -_accum_d_i * _fa_cod
            _ann_r = _tot_d / _fa_amort_yrs if _fa_amort_yrs > 0 else 0.0
            if oi >= _fa_grace_yrs and (oi - _fa_grace_yrs) < _fa_amort_yrs:
                f_amort = -_ann_r

        if is_epc:
            cf = inv + f_int + f_amort
            pv = cf / (1 + _fa_marr) ** i
            accum_pv += pv
            cfs.append(cf); pv_list.append(pv); accum_list.append(accum_pv)
            continue

        cp = _cpct(oi); fp = _fpct(oi)
        g_main_f = (1 + _fa_g_main)   ** oi
        g_bp_f   = (1 + _fa_g_byprod) ** oi
        g_rm_f   = (1 + _fa_g_rm)     ** oi
        g_cu_f   = (1 + _fa_g_cu)     ** oi
        g_fc_f   = (1 + _fa_g_fc)     ** oi

        # Revenue
        main_rev   = product_price * _wif_cap * cp * g_main_f
        byprod_rev = _bp_base * cp * g_bp_f
        resid_rev  = _c * _fa_resid_pct if oi == _op - 1 else 0.0
        rev        = main_rev + byprod_rev + resid_rev

        # Costs
        rm   = -(_rm_base  * cp * g_rm_f)
        cu   = -(_cu_base  * cp * g_cu_f)
        lab  = -(_lab_base * fp * g_fc_f)
        sm   = -(_sm_base  * fp * g_fc_f)
        afc  = -(_afc_base * fp * g_fc_f)
        ifc  = -(_ifc_base * fp * g_fc_f)
        rent = -(_fa_land_rent_yr * g_fc_f) if _fa_land_opt == "Rent" else 0.0
        var  = rm + cu + lab
        fix  = sm + afc + ifc + rent

        dep  = (_dep_sl_v if oi < _fa_dep_yrs else 0.0) if _dep_method == "Straight Line" \
               else (-_c * _MACRS[min(_MACRS.keys(), key=lambda k: abs(k-_fa_dep_yrs))][oi]
                     if oi < len(_MACRS[min(_MACRS.keys(), key=lambda k: abs(k-_fa_dep_yrs))]) else 0.0)

        ebt  = rev + var + fix + dep + f_int
        tax  = -max(0.0, ebt) * _fa_tax
        np_  = ebt + tax
        cf   = np_ + f_amort + inv
        pv   = cf / (1 + _fa_marr) ** i
        accum_pv += pv
        cfs.append(cf); pv_list.append(pv); accum_list.append(accum_pv)

    return cfs, pv_list, accum_list


def _npv_at_price(price, capex_mult=1.0):
    _, _, accum = _build_cf_arrays(price, capex_mult)
    return accum[-1]


def _irr_from_cfs(cfs):
    if not _HAS_NPF:
        return None
    try:
        v = npf.irr(cfs)
        return None if (v is None or np.isnan(v) or np.isinf(v)) else float(v)
    except Exception:
        return None


def _solve_price_for_npv(target_npv, capex_mult=1.0):
    """Find product price such that NPV = target_npv."""
    if not _HAS_SCIPY:
        return None
    try:
        return brentq(lambda p: _npv_at_price(p, capex_mult) - target_npv,
                      0.001, 1_000_000.0, xtol=0.01, maxiter=200)
    except Exception:
        return None


def _solve_price_for_irr(target_irr, capex_mult=1.0):
    """Find product price such that IRR = target_irr."""
    if not _HAS_SCIPY or not _HAS_NPF:
        return None
    def irr_err(p):
        cfs, _, _ = _build_cf_arrays(p, capex_mult)
        v = _irr_from_cfs(cfs)
        return (v - target_irr) if v is not None else -target_irr
    # Scan for bracket
    scan = [100, 500, 1000, 2000, 5000, 10000, 50000]
    irrs = [(p, irr_err(p)) for p in scan]
    lo = [p for p, e in irrs if e < 0]
    hi = [p for p, e in irrs if e > 0]
    if not lo or not hi:
        return None
    try:
        return brentq(irr_err, max(lo), min(hi) * 2, xtol=0.01, maxiter=200)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TIC BOUNDS
# ─────────────────────────────────────────────────────────────────────────────
_tic_lo_pct = safe_val(d, "TIC Lower Pct", None)   # e.g. -25.0
_tic_hi_pct = safe_val(d, "TIC Upper Pct", None)   # e.g. 40.0
_has_bounds = (_tic_lo_pct is not None and _tic_hi_pct is not None
               and _tic_lo_pct != 0 and _tic_hi_pct != 0)
_cm_lo = 1.0 + (_tic_lo_pct / 100.0) if _has_bounds else 0.75
_cm_hi = 1.0 + (_tic_hi_pct / 100.0) if _has_bounds else 1.40

# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT PRICE STATE
# Modes: MANUAL (user types price) | USE_MSP | SET_NPV | SET_IRR
# Stored per-scenario in st.session_state.cf_price_mode[scenario]
# ─────────────────────────────────────────────────────────────────────────────
if "cf_price_mode" not in st.session_state:
    st.session_state.cf_price_mode = {}
if scenario_name not in st.session_state.cf_price_mode:
    st.session_state.cf_price_mode[scenario_name] = {
        "mode": "MANUAL",
        "npv_target": 0.0,
        "irr_target": _fa_marr * 100.0,
        "solved_price": None,
        "manual_price": None,   # user-typed override
        "msp_initialised": False,
    }

_pm = st.session_state.cf_price_mode[scenario_name]

_input_price = safe_val(d, "Main Product Price", 0.0)   # from saved scenario

# ── Auto-initialise: if no input price and MSP not yet computed, solve MSP ──
if _input_price <= 0 and not _pm.get("msp_initialised") and _HAS_SCIPY:
    with st.spinner("No selling price set — calculating MSP automatically…"):
        _auto_msp = _solve_price_for_npv(0.0)
    if _auto_msp and _auto_msp > 0:
        _pm["mode"]           = "USE_MSP"
        _pm["solved_price"]   = _auto_msp
        _pm["msp_initialised"]= True
    else:
        _pm["msp_initialised"] = True   # mark even if failed to avoid infinite retry

# ── Determine effective price ──────────────────────────────────────────────
# Priority: solved_price (any non-MANUAL mode) > manual_price override > input_price
if _pm["mode"] != "MANUAL":
    _eff_price = _pm.get("solved_price") or _input_price
else:
    _eff_price = _pm.get("manual_price") if _pm.get("manual_price") is not None else _input_price

# ─────────────────────────────────────────────────────────────────────────────
# CONTROL ROW
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("#### Price & NPV Controls")
_price_unit = d.get("Unit", "")

# ── Pending price: solvers write here BEFORE rendering, widget reads it ───────
# Pattern: store solved price in _pm BEFORE st.rerun(). On next render,
# _eff_price reads from _pm — no widget key conflict possible.
_ctrl_cols = st.columns([2, 3, 3, 3])

with _ctrl_cols[0]:
    st.markdown('<p style="font-size:.85rem;color:#8b949e;margin:.3rem 0 .1rem 0">'
                'Main product selling price</p>', unsafe_allow_html=True)

    # Determine the value to show in the widget
    # Priority: solved_price (solver modes) > manual_price > input_price
    if _pm["mode"] != "MANUAL" and _pm.get("solved_price"):
        _widget_val = float(_pm["solved_price"])
    elif _pm.get("manual_price") is not None:
        _widget_val = float(_pm["manual_price"])
    else:
        _widget_val = float(_input_price) if _input_price > 0 else 0.0

    # No key= on this widget — value is fully controlled by _pm state.
    # on_change fires only when user edits, switching to MANUAL mode.
    _new_price = st.number_input(
        "Product price",
        value=_widget_val,
        min_value=0.0, step=1.0, format="%.2f",
        label_visibility="collapsed",
        help=f"USD / {_price_unit}",
    )

    # Detect user edit: if rendered value differs from what we showed, go MANUAL
    if abs(_new_price - _widget_val) > 0.005:
        _pm["mode"]         = "MANUAL"
        _pm["solved_price"] = None
        _pm["manual_price"] = _new_price
        _eff_price          = _new_price
    else:
        _eff_price = _widget_val

    st.markdown(f'<p style="font-size:.75rem;color:#6e7681;margin:.1rem 0 0 0">'
                f'USD / {_price_unit}</p>', unsafe_allow_html=True)

    _mode_colors = {"USE_MSP": "green", "SET_NPV": "blue", "SET_IRR": "orange", "MANUAL": "gray"}
    _mode_labels = {"USE_MSP": "MSP", "SET_NPV": "Set NPV", "SET_IRR": "Set IRR", "MANUAL": "Manual"}
    st.badge(_mode_labels.get(_pm["mode"], "Manual"),
             icon=":material/auto_fix_high:" if _pm["mode"] != "MANUAL" else ":material/edit:",
             color=_mode_colors.get(_pm["mode"], "gray"))

with _ctrl_cols[1]:
    st.markdown('<p style="font-size:.85rem;color:#3fb950;margin:.3rem 0 .1rem 0">'
                '① Minimum Selling Price</p>', unsafe_allow_html=True)
    st.caption("Price at which NPV = 0")
    _use_msp = st.button("Calculate MSP", key="btn_use_msp",
                          type="primary" if _pm["mode"] == "USE_MSP" else "secondary",
                          use_container_width=True, disabled=not _HAS_SCIPY)
    if _use_msp:
        with st.spinner("Solving for MSP…"):
            _msp_val = _solve_price_for_npv(0.0)
        if _msp_val is not None and _msp_val > 0:
            _pm["mode"]         = "USE_MSP"
            _pm["solved_price"] = _msp_val
            _pm["manual_price"] = None
            st.rerun()
        else:
            st.error("Could not solve MSP — check inputs.")

with _ctrl_cols[2]:
    st.markdown('<p style="font-size:.85rem;color:#58a6ff;margin:.3rem 0 .1rem 0">'
                '② Set NPV target</p>', unsafe_allow_html=True)
    _npv_target_input = st.number_input(
        "Target NPV (MMUSD)", value=float(_pm.get("npv_target", 0.0)),
        step=1.0, format="%.1f", key=f"npv_target_{scenario_name}",
        label_visibility="collapsed")
    _pm["npv_target"] = _npv_target_input
    _set_npv = st.button("Apply →", key="btn_set_npv",
                          type="primary" if _pm["mode"] == "SET_NPV" else "secondary",
                          use_container_width=True, disabled=not _HAS_SCIPY)
    if _set_npv:
        _target_usd = _npv_target_input * 1_000_000.0
        with st.spinner(f"Solving for NPV = {_npv_target_input:.1f} MMUSD…"):
            _p_npv = _solve_price_for_npv(_target_usd)
        if _p_npv is not None and _p_npv > 0:
            _pm["mode"]         = "SET_NPV"
            _pm["solved_price"] = _p_npv
            _pm["manual_price"] = None
            st.rerun()
        else:
            st.error("Could not solve — target NPV may be unreachable.")
    if _pm["mode"] == "SET_NPV" and _pm.get("solved_price"):
        st.caption(f"→ Price = ${_pm['solved_price']:,.2f} / {_price_unit}")

with _ctrl_cols[3]:
    st.markdown('<p style="font-size:.85rem;color:#e6a817;margin:.3rem 0 .1rem 0">'
                '③ Set IRR target</p>', unsafe_allow_html=True)
    _irr_target_input = st.number_input(
        "Target IRR (%)", value=float(_pm.get("irr_target", _fa_marr * 100)),
        step=0.1, format="%.2f", key=f"irr_target_{scenario_name}",
        label_visibility="collapsed")
    _pm["irr_target"] = _irr_target_input
    _set_irr = st.button("Apply →", key="btn_set_irr",
                          type="primary" if _pm["mode"] == "SET_IRR" else "secondary",
                          use_container_width=True,
                          disabled=(not _HAS_SCIPY or not _HAS_NPF))
    if _set_irr:
        with st.spinner(f"Solving for IRR = {_irr_target_input:.2f}%…"):
            _p_irr = _solve_price_for_irr(_irr_target_input / 100.0)
        if _p_irr is not None and _p_irr > 0:
            _pm["mode"]         = "SET_IRR"
            _pm["solved_price"] = _p_irr
            _pm["manual_price"] = None
            st.rerun()
        else:
            st.error("Could not solve — target IRR may be unreachable.")
    if _pm["mode"] == "SET_IRR" and _pm.get("solved_price"):
        st.caption(f"→ Price = ${_pm['solved_price']:,.2f} / {_price_unit}")

st.space("small")

# ─────────────────────────────────────────────────────────────────────────────
# GUARD — need a valid price to compute curves
# ─────────────────────────────────────────────────────────────────────────────
if not _eff_price or _eff_price <= 0:
    st.warning("Enter a selling price above, or click 'Calculate MSP'.",
               icon=":material/warning:")
    st.stop()

_cfs_base, _pvs_base, _acpv_base = _build_cf_arrays(_eff_price, 1.0)
_cfs_lo,   _pvs_lo,   _acpv_lo   = _build_cf_arrays(_eff_price, _cm_lo)
_cfs_hi,   _pvs_hi,   _acpv_hi   = _build_cf_arrays(_eff_price, _cm_hi)

_cal_yrs = [_y0 + i for i in range(_total)]

# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL INDICATORS — base, lower TIC, upper TIC
# ─────────────────────────────────────────────────────────────────────────────
def _indicators(cfs, acpv, capex_mult=1.0):
    _c   = _capex * capex_mult
    _tic = (_c + _wc * capex_mult + _startup * capex_mult
            + (_fa_land_buy * capex_mult if _fa_land_opt == "Buy" else 0.0))
    npv_ = acpv[-1]
    irr_ = _irr_from_cfs(cfs)

    # MSP for this TIC scenario
    msp_ = _solve_price_for_npv(0.0, capex_mult) if _HAS_SCIPY else None

    # Payback: first project year where acpv >= 0
    payback_ = next((i for i, v in enumerate(acpv) if v >= 0), None)
    payback_op = (payback_ - _epc) if payback_ is not None else None

    # Break-even period = payback (same definition confirmed by user)
    breakeven_yr = payback_op

    # Average annual net profit (operational years only)
    op_cfs = cfs[_epc:]
    avg_np = np.mean(op_cfs) if op_cfs else 0.0

    # ROI = (sum Net Profit + sum Investment) / project_lifetime
    sum_inv = sum(cfs[:_epc]) + (-_wc * capex_mult) + (-_startup * capex_mult)
    roi_val = (sum(op_cfs) + sum(cfs[:_epc])) / _op if _op > 0 else 0.0

    # Average revenues / OPEX for margin metrics (steady-state year, full capacity)
    # Use year _epc + 2 (3rd op year, full capacity, no startup) as representative
    _ss_i = min(_epc + 2, _total - 1)
    oi_ss = _ss_i - _epc
    cp    = _cpct(oi_ss); fp = _fpct(oi_ss)
    rev_ss = ((_eff_price * _wif_cap * cp * (1+_fa_g_main)**oi_ss)
              + (_bp_base * cp * (1+_fa_g_byprod)**oi_ss))
    var_ss = ((_rm_base  * cp * (1+_fa_g_rm)**oi_ss)
              + (_cu_base * cp * (1+_fa_g_cu)**oi_ss)
              + (_lab_base* fp * (1+_fa_g_fc)**oi_ss))
    fix_ss = ((_sm_base  * fp * (1+_fa_g_fc)**oi_ss)
              + (_afc_base* fp * (1+_fa_g_fc)**oi_ss)
              + (_ifc_base* fp * (1+_fa_g_fc)**oi_ss))
    dep_ss = -(_c - _c*_fa_resid_pct)/_fa_dep_yrs if oi_ss < _fa_dep_yrs else 0.0
    gp_ss  = rev_ss - var_ss
    ebitda_ss = gp_ss - fix_ss
    ebit_ss   = ebitda_ss + dep_ss
    ebt_ss    = ebit_ss
    np_ss     = ebt_ss * (1 - _fa_tax)
    equity_ss = _tic

    gm_   = gp_ss    / rev_ss if rev_ss else 0.0
    em_   = ebitda_ss/ rev_ss if rev_ss else 0.0
    ebit_ = ebit_ss  / rev_ss if rev_ss else 0.0
    npm_  = np_ss    / rev_ss if rev_ss else 0.0
    roe_  = np_ss    / equity_ss if equity_ss else 0.0
    roa_  = np_ss    / _tic if _tic else 0.0

    # Average annual values for summary table
    avg_ebitda = np.mean([cf for cf in op_cfs]) if op_cfs else 0.0

    return {
        "NPV": npv_, "IRR": irr_, "MSP": msp_,
        "Payback": payback_op, "Breakeven": breakeven_yr,
        "ROI": roi_val, "TIC": _tic,
        "MARR": _fa_marr,
        "Gross Margin": gm_, "EBITDA Margin": em_,
        "EBIT Margin": ebit_, "Net Profit Margin": npm_,
        "ROE": roe_, "ROA": roa_,
        "Avg EBITDA": avg_ebitda, "Avg Net Profit": avg_np,
    }

_ind_base = _indicators(_cfs_base, _acpv_base, 1.0)
_ind_lo   = _indicators(_cfs_lo,   _acpv_lo,   _cm_lo)
_ind_hi   = _indicators(_cfs_hi,   _acpv_hi,   _cm_hi)

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT: graph left, scenario summary right
# ─────────────────────────────────────────────────────────────────────────────
graph_col, summary_col = st.columns([3, 1])

with summary_col:
    section_header("Scenario summary", "#58a6ff")

    def _kv(label, val_lo, val_base, val_hi, unit="", fmt=".3f", pct=False):
        """3-column KPI row: Lower | Result | Upper."""
        def _f(v):
            if v is None: return "—"
            if pct: return f"{v*100:.2f}%"
            if abs(v) >= 1e6: return f"{v/1e6:{fmt}}M"
            return f"{v:{fmt}}"
        c1,c2,c3 = st.columns(3)
        with c1: st.markdown(f'<p style="font-size:.7rem;color:#8b949e;margin:0">{_f(val_lo)}</p>', unsafe_allow_html=True)
        with c2: st.markdown(f'<p style="font-size:.8rem;color:#c9d1d9;font-weight:600;text-align:center;margin:0">{_f(val_base)}</p>', unsafe_allow_html=True)
        with c3: st.markdown(f'<p style="font-size:.7rem;color:#8b949e;text-align:right;margin:0">{_f(val_hi)}</p>', unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:.7rem;color:#484f58;margin:0 0 .3rem 0">{label} {unit}</p>', unsafe_allow_html=True)

    # Header
    hc1,hc2,hc3 = st.columns(3)
    for col,txt,clr in [(hc1,"Lower TIC","#8b949e"),(hc2,"Result","#c9d1d9"),(hc3,"Upper TIC","#8b949e")]:
        with col: st.markdown(f'<p style="font-size:.68rem;color:{clr};font-weight:600;margin:0 0 .2rem 0">{txt}</p>', unsafe_allow_html=True)

    _prod_name_disp = d.get("Product Name","—")
    st.markdown(f'<p style="font-size:.75rem;color:#6e7681;margin:.3rem 0 .1rem 0">Product</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:.82rem;color:#c9d1d9;font-weight:600;margin:0 0 .4rem 0">{_prod_name_disp}</p>', unsafe_allow_html=True)

    _tic_lo_usd = _capex*_cm_lo + _wc*_cm_lo + _startup*_cm_lo
    _tic_hi_usd = _capex*_cm_hi + _wc*_cm_hi + _startup*_cm_hi
    _kv("CAPEX (MMUSD)", _capex*_cm_lo/1e6, _capex/1e6, _capex*_cm_hi/1e6, fmt=".3f")
    _kv("Working Capital (MMUSD)", _wc*_cm_lo/1e6, _wc/1e6, _wc*_cm_hi/1e6, fmt=".3f")
    _kv("Start-up (MMUSD)", _startup*_cm_lo/1e6, _startup/1e6, _startup*_cm_hi/1e6, fmt=".3f")
    _kv("TIC (MMUSD)", _tic_lo_usd/1e6, (_capex+_wc+_startup)/1e6, _tic_hi_usd/1e6, fmt=".3f")
    _kv("OPEX (MMUSD/yr)", None, sum(abs(v) for v in [_sm_base,_afc_base,_ifc_base,_lab_base,_rm_base,_cu_base])/1e6, None, fmt=".3f")

    st.markdown("---")
    section_header("Financial indicators", "#e6a817")
    hc1,hc2,hc3 = st.columns(3)
    for col,txt in [(hc1,"Lower"),(hc2,"Result"),(hc3,"Upper")]:
        with col: st.markdown(f'<p style="font-size:.68rem;color:#8b949e;font-weight:600;margin:0 0 .2rem 0">{txt}</p>', unsafe_allow_html=True)

    _kv("MARR (%/yr)", None, _fa_marr, None, pct=True)
    _kv("MSP (USD/unit)", _ind_lo["MSP"], _ind_base["MSP"], _ind_hi["MSP"], fmt=",.2f")
    _kv("NPV (MMUSD)", _ind_lo["NPV"]/1e6, _ind_base["NPV"]/1e6, _ind_hi["NPV"]/1e6, fmt=".3f")
    _kv("IRR (%/yr)", _ind_lo["IRR"], _ind_base["IRR"], _ind_hi["IRR"], pct=True)
    _kv("Payback (years)", _ind_lo["Payback"], _ind_base["Payback"], _ind_hi["Payback"], fmt=".1f")
    _kv("Break-even (years)", _ind_lo["Breakeven"], _ind_base["Breakeven"], _ind_hi["Breakeven"], fmt=".1f")
    _kv("ROI (USD/yr)", _ind_lo["ROI"]/1e6, _ind_base["ROI"]/1e6, _ind_hi["ROI"]/1e6, fmt=".3f")

# ─────────────────────────────────────────────────────────────────────────────
# NPV GRAPH
# ─────────────────────────────────────────────────────────────────────────────
with graph_col:
    section_header("Cumulative discounted cash flow", "#58a6ff")

    # Convert to MMUSD for display
    _acpv_b_M  = [v/1e6 for v in _acpv_base]
    _acpv_lo_M = [v/1e6 for v in _acpv_lo]
    _acpv_hi_M = [v/1e6 for v in _acpv_hi]

    fig = go.Figure()

    # Shaded band between bounds
    fig.add_trace(go.Scatter(
        x=_cal_yrs + _cal_yrs[::-1],
        y=_acpv_hi_M + _acpv_lo_M[::-1],
        fill='toself', fillcolor='rgba(88,166,255,0.06)',
        line=dict(color='rgba(0,0,0,0)'), showlegend=False, hoverinfo='skip'
    ))

    # Upper TIC bound (red dashed)
    _lo_lbl = f"Upper bound (+{_tic_hi_pct:.0f}% of TIC)" if _has_bounds else "Upper bound (+40%)"
    fig.add_trace(go.Scatter(
        x=_cal_yrs, y=_acpv_hi_M,
        mode='lines', name=_lo_lbl,
        line=dict(color='#f85149', dash='dash', width=1.5),
        hovertemplate='%{x}: %{y:.1f} MMUSD<extra>Upper TIC</extra>'
    ))

    # Lower TIC bound (green dashed)
    _hi_lbl = f"Lower bound ({_tic_lo_pct:.0f}% of TIC)" if _has_bounds else "Lower bound (-25%)"
    fig.add_trace(go.Scatter(
        x=_cal_yrs, y=_acpv_lo_M,
        mode='lines', name=_hi_lbl,
        line=dict(color='#3fb950', dash='dash', width=1.5),
        hovertemplate='%{x}: %{y:.1f} MMUSD<extra>Lower TIC</extra>'
    ))

    # Base case (solid blue)
    _npv_lbl = f"NPV = {_ind_base['NPV']/1e6:.1f} MMUSD"
    fig.add_trace(go.Scatter(
        x=_cal_yrs, y=_acpv_b_M,
        mode='lines', name=f"Base case ({_npv_lbl})",
        line=dict(color='#58a6ff', width=2.5),
        hovertemplate='%{x}: %{y:.1f} MMUSD<extra>Base case</extra>'
    ))

    # Zero line
    fig.add_hline(y=0, line_color='#484f58', line_width=1)

    # EPC end annotation
    _epc_end_yr = _y0 + _epc - 1
    fig.add_vline(x=_epc_end_yr, line_dash='dot', line_color='#6e7681', line_width=1)
    fig.add_annotation(x=_epc_end_yr, y=min(_acpv_b_M)*0.6,
                       text="EPC", showarrow=False,
                       font=dict(size=10, color='#6e7681'))

    # Payback annotation
    _pb = _ind_base["Payback"]
    if _pb is not None:
        _pb_yr = _y0 + _epc + _pb
        if _pb_yr in _cal_yrs:
            _pb_idx = _cal_yrs.index(_pb_yr)
            fig.add_annotation(
                x=_pb_yr, y=_acpv_b_M[_pb_idx] + max(_acpv_b_M)*0.05,
                text=f"Payback<br>(Op. yr {_pb})",
                showarrow=True, arrowhead=2, arrowcolor='#e6a817',
                font=dict(size=9, color='#e6a817'), arrowsize=0.8
            )

    # NPV endpoint annotation
    fig.add_annotation(
        x=_cal_yrs[-1], y=_acpv_b_M[-1],
        text=_npv_lbl, showarrow=True,
        arrowhead=2, arrowcolor='#58a6ff',
        font=dict(size=10, color='#58a6ff'),
        xanchor='right', yanchor='bottom'
    )

    # Layout
    fig.update_layout(
        paper_bgcolor='#0d1117', plot_bgcolor='#161b22',
        font=dict(family='Inter, sans-serif', color='#c9d1d9', size=11),
        margin=dict(l=60, r=20, t=20, b=50),
        height=420,
        xaxis=dict(
            title='Year', gridcolor='#21262d', linecolor='#30363d',
            tickfont=dict(size=10), showgrid=True,
        ),
        yaxis=dict(
            title='Cumulative discounted cash flow (MMUSD)',
            gridcolor='#21262d', linecolor='#30363d',
            tickfont=dict(size=10), showgrid=True, zeroline=False,
        ),
        legend=dict(
            bgcolor='rgba(13,17,23,0.8)', bordercolor='#30363d',
            borderwidth=1, font=dict(size=10),
            x=0.02, y=0.98, xanchor='left', yanchor='top'
        ),
        hovermode='x unified',
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MARGIN KPI TABLE — 3×3 grid of Lower/Result/Upper per metric
# ─────────────────────────────────────────────────────────────────────────────
st.space("small")
st.markdown("#### Profitability Metrics")

_metrics = [
    ("Gross margin",       "Gross Margin"),
    ("EBITDA margin",      "EBITDA Margin"),
    ("EBIT margin",        "EBIT Margin"),
    ("Net profit margin",  "Net Profit Margin"),
    ("Return on equity (ROE)", "ROE"),
    ("Return on assets (ROA)", "ROA"),
]

def _metric_card(title, lo, base, hi):
    def _fp(v): return f"{v*100:.2f}%" if v is not None else "—"
    c = "#3fb950" if (base or 0) >= 0 else "#f85149"
    st.markdown(
        f'<div style="background:#161b22;border:1px solid #21262d;'
        f'border-radius:6px;padding:.6rem .8rem;margin:.2rem 0">'
        f'<p style="font-size:.7rem;color:#8b949e;margin:0 0 .3rem 0;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:.05em">{title}</p>'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
        f'<span style="font-size:.75rem;color:#6e7681">{_fp(lo)}</span>'
        f'<span style="font-size:1rem;color:{c};font-weight:700;'
        f'font-family:DM Mono,monospace">{_fp(base)}</span>'
        f'<span style="font-size:.75rem;color:#6e7681">{_fp(hi)}</span>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between">'
        f'<span style="font-size:.62rem;color:#484f58">Lower</span>'
        f'<span style="font-size:.62rem;color:#484f58">Result</span>'
        f'<span style="font-size:.62rem;color:#484f58">Upper</span>'
        f'</div></div>',
        unsafe_allow_html=True
    )

_mcols = st.columns(len(_metrics))
for col, (title, key) in zip(_mcols, _metrics):
    with col:
        _metric_card(
            title,
            _ind_lo.get(key),
            _ind_base.get(key),
            _ind_hi.get(key),
        )

st.space("medium")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5: PROJECT COST & REVENUE COMPOSITION
# Per-unit breakdown at steady-state, single Sankey diagram
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Project Cost & Revenue Composition")
st.caption(
    "Per-unit breakdown at steady-state (full capacity, no growth effects). "
    f"Functional unit: 1 {_prod_unit} of {d.get('Product Name','product')}."
)

# ─────────────────────────────────────────────────────────────────────────────
# STEADY-STATE YEAR — op index 2 (3rd operational year, full capacity)
# ─────────────────────────────────────────────────────────────────────────────
_ss_oi  = min(2, _op - 1)   # op index (0-based)
_ss_cap = _cpct(_ss_oi)     # capacity fraction (should be 1.0 at steady state)
_ss_fp  = _fpct(_ss_oi)     # fixed cost fraction

# Annual production at steady state
_ss_prod = _wif_cap * _ss_cap   # units/year

if _ss_prod <= 0:
    st.warning("Annual production is zero — check capacity inputs.", icon=":material/warning:")
    st.stop()

# ── Per-unit cost components (USD/unit) ───────────────────────────────────────
# Variable costs — scale with capacity
_u_rm    = _rm_base  * _ss_cap / _ss_prod * _ss_prod / _wif_cap  # = _rm_base / _wif_cap
_u_cu    = _cu_base  * _ss_cap / _ss_prod * _ss_prod / _wif_cap
# Simplified: per-unit = annual_cost_at_full_cap / annual_production
_u_rm    = _rm_base  / _wif_cap   # USD/unit
_u_cu    = _cu_base  / _wif_cap

# Fixed costs — per unit = annual_fixed / annual_production_at_ss
_u_lab   = _lab_base * _ss_fp / _ss_prod
_u_sm    = _sm_base  * _ss_fp / _ss_prod
_u_afc   = _afc_base * _ss_fp / _ss_prod
_u_ifc   = _ifc_base * _ss_fp / _ss_prod

# Taxes per unit — from steady-state CF calculation
_ss_rev     = _eff_price * _wif_cap * _ss_cap + _bp_base * _ss_cap
_ss_var     = -(_rm_base * _ss_cap + _cu_base * _ss_cap + _lab_base * _ss_fp)
_ss_fix     = -(_sm_base * _ss_fp + _afc_base * _ss_fp + _ifc_base * _ss_fp)
_ss_dep     = -(_capex - _capex * _fa_resid_pct) / _fa_dep_yrs if _ss_oi < _fa_dep_yrs else 0.0
_ss_ebt     = _ss_rev + _ss_var + _ss_fix + _ss_dep
_ss_tax_yr  = max(0.0, _ss_ebt) * _fa_tax
_u_tax      = _ss_tax_yr / _ss_prod

# ROI per unit = (TIC × MARR) / annual production
_ss_tic     = _capex + _wc + _startup + (_fa_land_buy if _fa_land_opt == "Buy" else 0.0)
_u_roi      = (_ss_tic * _fa_marr) / _ss_prod

# Carbon costs — always 0 for now (future-proof)
_u_carbon_cost = 0.0

# Total cost per unit
_u_total_cost = (_u_rm + _u_cu + _u_lab + _u_sm + _u_afc
                 + _u_ifc + _u_tax + _u_roi + _u_carbon_cost)

# ── Per-unit revenue components (USD/unit) ────────────────────────────────────
_u_main    = _eff_price                         # main product
_u_byprod  = _bp_base / _wif_cap                # byproducts per unit
_u_carbon_rev = 0.0                             # carbon credits
_u_fin_rev = 0.0                                # financial revenue (not shown if no financing)

_u_total_rev = _u_main + _u_byprod + _u_carbon_rev + _u_fin_rev

# Net margin per unit (surplus above cost of capital)
_u_net_margin = max(0.0, _u_total_rev - _u_total_cost)

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT: left summary table | right Sankey
# ─────────────────────────────────────────────────────────────────────────────
_tbl_col, _snk_col = st.columns([1, 2])

with _tbl_col:
    def _tbl_row(label, value, bold=False, color="#c9d1d9", indent=False):
        fw = "font-weight:700;" if bold else ""
        pad = "padding-left:1rem;" if indent else ""
        val_str = f"{value:,.2f}" if value != 0 else "—"
        val_color = "#e6a817" if bold else color
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:.25rem .5rem;border-bottom:1px solid #21262d22;">'
            f'<span style="font-size:.82rem;color:{color};{fw}{pad}">{label}</span>'
            f'<span style="font-size:.82rem;font-family:DM Mono,monospace;'
            f'color:{val_color};{fw}">{val_str}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    def _tbl_header(label, unit_label=""):
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:.3rem .5rem;background:#1f2937;margin-top:.3rem;">'
            f'<span style="font-size:.78rem;color:#58a6ff;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.05em">{label}</span>'
            f'<span style="font-size:.75rem;color:#8b949e">{unit_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _prod_name = d.get("Product Name", "Product")
    _cap_label = f"{_wif_cap:,.2f} {_prod_unit}/year"

    _tbl_header("Annual capacity", _prod_unit + "/year")
    _tbl_row(_prod_name, _wif_cap)

    _tbl_header("Project costs", f"USD/{_prod_unit}")
    _tbl_row("Raw materials",        _u_rm,    indent=True, color="#8b949e")
    _tbl_row("Chemical inputs & util.", _u_cu, indent=True, color="#8b949e")
    _tbl_row("Labor",                _u_lab,   indent=True, color="#8b949e")
    _tbl_row("Supply & maintenance", _u_sm,    indent=True, color="#8b949e")
    _tbl_row("Additional fixed costs",_u_afc,  indent=True, color="#8b949e")
    _tbl_row("Indirect fixed costs", _u_ifc,   indent=True, color="#8b949e")
    _tbl_row("Carbon emission",      _u_carbon_cost, indent=True, color="#8b949e")
    _tbl_row("Taxes",                _u_tax,   indent=True, color="#8b949e")
    _tbl_row("Project costs",        _u_total_cost, bold=True)
    _tbl_row("Return on investment", _u_roi,   bold=True)

    _tbl_header("Project revenue", f"USD/{_prod_unit}")
    _tbl_row("Main product",         _u_main,    indent=True, color="#8b949e")
    _tbl_row("Byproducts",           _u_byprod,  indent=True, color="#8b949e")
    _tbl_row("Carbon capture",       _u_carbon_rev, indent=True, color="#8b949e")
    if _fa_leveraged:
        _tbl_row("Financial revenue", _u_fin_rev, indent=True, color="#8b949e")
    _tbl_row("Project revenue",      _u_total_rev, bold=True)

# ─────────────────────────────────────────────────────────────────────────────
# SANKEY DIAGRAM
# Single full-width Sankey: Revenue sources → CENTER → Cost destinations
#
# Node layout:
#   Left:   Revenue source nodes  (Main product, Byproducts, [Carbon, Financial])
#   Center: Single bridge node    ("Revenue = Cost")
#   Right:  Cost destination nodes (RM, CU, Labor, S&M, AFC, IFC, Taxes, ROI, [Net margin])
#
# All values in USD/unit. Flows must sum to same total on both sides.
# ─────────────────────────────────────────────────────────────────────────────
with _snk_col:
    # Build node list dynamically (skip zero-value nodes)
    _nodes  = []   # {"label": str, "color": str}
    _source = []
    _target = []
    _value  = []
    _link_colors = []

    def _add_node(label, color):
        _nodes.append({"label": label, "color": color})
        return len(_nodes) - 1

    # Center node
    _ctr_lbl = f"Total<br>{_u_total_rev:,.1f} USD/{_prod_unit}"
    _ctr_idx = _add_node(_ctr_lbl, "#58a6ff")

    # ── Revenue sources → CENTER ──────────────────────────────────────────────
    _rev_items = [
        (f"Main product<br>{_u_main:,.1f}", _u_main,   "#3fb950", "rgba(63,185,80,0.4)"),
        (f"Byproducts<br>{_u_byprod:,.1f}", _u_byprod, "#79c0ff", "rgba(121,192,255,0.4)"),
    ]
    if _u_carbon_rev > 0.01:
        _rev_items.append((f"Carbon credits<br>{_u_carbon_rev:,.1f}", _u_carbon_rev,
                           "#a8dadc", "rgba(168,218,220,0.4)"))
    if _fa_leveraged and _u_fin_rev > 0.01:
        _rev_items.append((f"Financial revenue<br>{_u_fin_rev:,.1f}", _u_fin_rev,
                           "#8b949e", "rgba(139,148,158,0.4)"))

    for lbl, val, clr, lclr in _rev_items:
        if val > 0.001:
            idx = _add_node(lbl, clr)
            _source.append(idx); _target.append(_ctr_idx)
            _value.append(val);  _link_colors.append(lclr)

    # ── CENTER → Cost destinations ────────────────────────────────────────────
    _cost_items = [
        (f"Raw materials<br>{_u_rm:,.1f}",          _u_rm,          "#f85149", "rgba(248,81,73,0.35)"),
        (f"Chem. inputs & util.<br>{_u_cu:,.1f}",   _u_cu,          "#ffa657", "rgba(255,166,87,0.35)"),
        (f"Labor<br>{_u_lab:,.1f}",                 _u_lab,         "#e6a817", "rgba(230,168,23,0.35)"),
        (f"Supply & maint.<br>{_u_sm:,.1f}",        _u_sm,          "#d2a8ff", "rgba(210,168,255,0.35)"),
        (f"AFC<br>{_u_afc:,.1f}",                   _u_afc,         "#ff7b72", "rgba(255,123,114,0.35)"),
        (f"Indirect fixed<br>{_u_ifc:,.1f}",        _u_ifc,         "#79c0ff", "rgba(121,192,255,0.35)"),
        (f"Taxes<br>{_u_tax:,.1f}",                 _u_tax,         "#8b949e", "rgba(139,148,158,0.35)"),
        (f"ROI (cost of capital)<br>{_u_roi:,.1f}", _u_roi,         "#3fb950", "rgba(63,185,80,0.35)"),
    ]
    if _u_carbon_cost > 0.001:
        _cost_items.append(
            (f"Carbon costs<br>{_u_carbon_cost:,.1f}", _u_carbon_cost,
             "#58a6ff", "rgba(88,166,255,0.35)"))
    if _u_net_margin > 0.01:
        _cost_items.append(
            (f"Net margin<br>{_u_net_margin:,.1f}", _u_net_margin,
             "#238636", "rgba(35,134,54,0.35)"))

    for lbl, val, clr, lclr in _cost_items:
        if val > 0.001:
            idx = _add_node(lbl, clr)
            _source.append(_ctr_idx); _target.append(idx)
            _value.append(val);       _link_colors.append(lclr)

    # Build Plotly Sankey
    _node_labels = [n["label"] for n in _nodes]
    _node_colors = [n["color"] for n in _nodes]

    _fig_snk = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=24,
            line=dict(color="#21262d", width=0.5),
            label=_node_labels,
            color=_node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=_source,
            target=_target,
            value=_value,
            color=_link_colors,
            hovertemplate=(
                "%{source.label} → %{target.label}<br>"
                f"%{{value:,.2f}} USD/{_prod_unit}"
                "<extra></extra>"
            ),
        ),
    ))

    _fig_snk.update_layout(
        paper_bgcolor="#0d1117",
        font=dict(family="Inter, sans-serif", color="#c9d1d9", size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        height=480,
        title=dict(
            text=(
                f"Cost & Revenue Composition  ·  "
                f"{_eff_price:,.2f} USD/{_prod_unit}  ·  "
                f"{_wif_cap:,.0f} {_prod_unit}/yr capacity"
            ),
            font=dict(size=12, color="#8b949e"),
            x=0.5, xanchor="center",
        ),
    )

    st.plotly_chart(_fig_snk, use_container_width=True)

    # Quick KPI strip below Sankey
    _kpi_c = st.columns(4)
    with _kpi_c[0]:
        kpi_card("Total cost/unit", f"${_u_total_cost:,.2f}", "#f85149",
                 "excl. ROI", f"${_u_total_cost-_u_roi:,.2f}")
    with _kpi_c[1]:
        kpi_card("ROI/unit", f"${_u_roi:,.2f}", "#e6a817",
                 "MARR", f"{_fa_marr*100:.2f}%")
    with _kpi_c[2]:
        kpi_card("Revenue/unit", f"${_u_total_rev:,.2f}", "#3fb950",
                 "Byproduct share", f"{_u_byprod/_u_total_rev*100:.1f}%" if _u_total_rev > 0 else "—")
    with _kpi_c[3]:
        _margin_pct = _u_net_margin / _u_total_rev * 100 if _u_total_rev > 0 else 0
        kpi_card("Net margin/unit", f"${_u_net_margin:,.2f}", "#58a6ff",
                 "of revenue", f"{_margin_pct:.1f}%")

st.space("medium")
