"""ISI-Tool — Cash Flow & Analysis page."""
import streamlit as st
import pandas as pd
from utils.constants import safe_val, smart_fmt, coeff_unit, is_per_year
from utils.ui import inject_css, page_header, section_header, kpi_card

inject_css()

# ── Guard ─────────────────────────────────────────────────────────────────────
if "scenarios" not in st.session_state or not st.session_state.scenarios:
    page_header("Cash Flow & Analysis")
    st.info("No scenarios saved yet — go to **Input Data** to configure and save a scenario first.",
            icon=":material/info:")
    st.stop()

scenarios = st.session_state.scenarios

# ── Helpers (page-local) ─────────────────────────────────────────────────────
# safe_val, smart_fmt, coeff_unit, is_per_year are imported from utils.constants

# ── Session state init ─────────────────────────────────────────────────────────
# cf_selected: currently chosen scenario name
# cf_session_defaults[scenario][table][item_name] = price  (saved by user)
# cf_working[scenario][table][item_name] = price           (current editing)

if "cf_selected" not in st.session_state:
    st.session_state.cf_selected = list(scenarios.keys())[0]
if "cf_session_defaults" not in st.session_state:
    st.session_state.cf_session_defaults = {}
if "cf_working" not in st.session_state:
    st.session_state.cf_working = {}

def _input_prices(scenario_name, table_key):
    """Return {item_name: price} from the original input data."""
    items = scenarios[scenario_name].get(table_key, []) or []
    return {r["Name"]: float(r.get("Price", 0.0)) for r in items if r.get("Name")}

def _ensure_scenario(scenario_name):
    """Initialise session defaults and working state for a scenario if not present."""
    if scenario_name not in st.session_state.cf_session_defaults:
        st.session_state.cf_session_defaults[scenario_name] = {}
    if scenario_name not in st.session_state.cf_working:
        st.session_state.cf_working[scenario_name] = {}

    for tbl in ["Raw Materials", "Chemical Inputs and Utilities", "Credits and Byproducts"]:
        inp = _input_prices(scenario_name, tbl)
        sd  = st.session_state.cf_session_defaults[scenario_name]
        wk  = st.session_state.cf_working[scenario_name]
        # Session default: use saved value if exists, else input price
        if tbl not in sd:
            sd[tbl] = dict(inp)
        # Working: always start from session default when scenario first loaded
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

# When scenario changes reset working to that scenario's session defaults
if chosen != prev_scenario:
    st.session_state.cf_selected = chosen
    _ensure_scenario(chosen)
    # Reset working prices to this scenario's session defaults
    sd = st.session_state.cf_session_defaults.get(chosen, {})
    st.session_state.cf_working[chosen] = {tbl: dict(prices) for tbl, prices in sd.items()}
    st.rerun()

scenario_name = st.session_state.cf_selected
_ensure_scenario(scenario_name)
d = scenarios[scenario_name]

with col_reset:
    if st.button("↺  Reset all to defaults", type="secondary", use_container_width=True):
        sd = st.session_state.cf_session_defaults.get(scenario_name, {})
        st.session_state.cf_working[scenario_name] = {tbl: dict(p) for tbl, p in sd.items()}
        # Force all price widget keys for this scenario to their default values
        for tbl, prices in sd.items():
            for item_name, price in prices.items():
                wgt_key = f"cf_{scenario_name}_{tbl}_{item_name}"
                st.session_state[wgt_key] = float(price)
        st.rerun()
# ── Scenario summary ──────────────────────────────────────────────────────────
prod_name = d.get("Product Name", "—")
prod_unit = d.get("Unit", "")
capacity  = safe_val(d, "Capacity")
tic       = safe_val(d, "Total Investment")
opex      = safe_val(d, "Total OPEX")

section_header("Scenario summary", "#58a6ff")
c1, c2, c3 = st.columns(3)
with c1:
    kpi_card("Main Product", f"{prod_name}", "#e6a817",
             "Capacity", f"{capacity:,.0f} {prod_unit}/year")
with c2:
    kpi_card("Total Investment Cost (TIC)", smart_fmt(tic), "#58a6ff")
with c3:
    kpi_card("Total Annual OPEX", smart_fmt(opex), "#3fb950")

st.space("medium")

# ── Legend ────────────────────────────────────────────────────────────────────
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.badge("Matches default", icon=":material/check:", color="blue")
    with c2:
        st.badge("Modified from default", icon=":material/edit:", color="orange")
    with c3:
        st.badge("Calculated result", icon=":material/calculate:", color="green")

# ── Save button ───────────────────────────────────────────────────────────────
save_col, _ = st.columns([1, 3])
with save_col:
    if st.button("💾  Save as new defaults for this scenario", type="primary", use_container_width=True):
        wk = st.session_state.cf_working.get(scenario_name, {})
        st.session_state.cf_session_defaults[scenario_name] = {
            tbl: dict(prices) for tbl, prices in wk.items()
        }
        st.success("Saved. These values are now the session defaults for this scenario.")

st.space("medium")

# ── Variable Costs Section ────────────────────────────────────────────────────
section_header("Variable Costs & Credits", "#58a6ff")

working_hours = safe_val(d, "Working Hours per Year", 8000.0)
product_rate  = capacity / working_hours  # product_unit/h  (or per year unit depending)

def _build_vc_table(table_key: str, is_credit: bool = False):
    """
    Build and render a variable cost table with editable prices.
    Returns (rows, total_cost_usd) where rows is a list of computed row dicts.
    """
    items = d.get(table_key, []) or []
    items = [r for r in items if r.get("Name")]
    if not items:
        st.caption("No items defined for this table in the selected scenario.")
        return [], 0.0

    wk   = st.session_state.cf_working[scenario_name]
    inp  = _input_prices(scenario_name, table_key)
    sd   = st.session_state.cf_session_defaults[scenario_name].get(table_key, inp)

    if table_key not in wk:
        wk[table_key] = dict(sd)

    total_cost = 0.0
    rows = []
    for r in items:
        name      = r["Name"]
        rate      = float(r.get("Rate", 0.0))
        rate_unit = r.get("Rate Unit", "")
        p_unit    = r.get("Price Unit", "")

        # Technical coefficient = rate / product_rate
        # For /y units the rate is already annual → divide by annual capacity
        if is_per_year(rate_unit):
            coeff = rate / capacity if capacity else 0.0
        else:
            coeff = rate / product_rate if product_rate else 0.0

        c_unit    = coeff_unit(rate_unit, prod_unit)
        curr_price = wk[table_key].get(name, inp.get(name, 0.0))
        input_def  = inp.get(name, 0.0)
        sess_def   = sd.get(name, input_def)
        modified   = abs(curr_price - input_def) > 1e-9

        spec_cost  = curr_price * coeff          # USD/prod_unit
        line_cost  = curr_price * rate * (1.0 if is_per_year(rate_unit) else working_hours)
        total_cost += line_cost

        rows.append({
            "name": name, "rate": rate, "rate_unit": rate_unit,
            "coeff": coeff, "coeff_unit": c_unit,
            "price": curr_price, "price_unit": p_unit,
            "input_default": input_def, "sess_default": sess_def,
            "modified": modified,
            "spec_cost": spec_cost, "line_cost": line_cost,
        })

    # ── Render table as HTML + price inputs ───────────────────────────────────
    pct_total = total_cost if total_cost > 0 else 1.0

    # Header
    header = """
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-family:'Inter',sans-serif;font-size:.8rem">
    <thead>
      <tr style="border-bottom:2px solid #21262d">
        <th style="padding:.5rem .7rem;text-align:left;color:#8b949e;min-width:160px">Name</th>
        <th style="padding:.5rem .7rem;text-align:center;color:#58a6ff;min-width:130px">Price (editable)</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:90px">Price Unit</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:110px">Tech. Coefficient</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:110px">Coeff. Unit</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:90px">Rate</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#8b949e;min-width:80px">Rate Unit</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#3fb950;min-width:120px">Cost/year</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#3fb950;min-width:120px">Specific cost</th>
        <th style="padding:.5rem .7rem;text-align:right;color:#3fb950;min-width:60px">%</th>
      </tr>
    </thead>
    <tbody>
    """
    body_rows = []
    for row in rows:
        bg   = "#2d2a1a" if row["modified"] else "#1c2d3a"
        bdr  = "#e6a817" if row["modified"] else "#58a6ff"
        fc   = "#e6a817" if row["modified"] else "#58a6ff"
        pct  = row["line_cost"] / pct_total * 100 if not is_credit else 0.0
        body_rows.append(
            f'<tr style="border-bottom:1px solid #21262d22">'
            f'<td style="padding:.4rem .7rem;color:#c9d1d9">{row["name"]}</td>'
            f'<td style="padding:.3rem .7rem;text-align:center;background:{bg};border-left:2px solid {bdr}">'
            f'<span style="font-family:DM Mono,monospace;font-size:.85rem;color:{fc};font-weight:500">'
            f'{row["price"]:.6g}</span></td>'
            f'<td style="padding:.4rem .7rem;text-align:right;color:#8b949e">{row["price_unit"]}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#c9d1d9">'
            f'{row["coeff"]:.4f}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;color:#8b949e">{row["coeff_unit"]}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;color:#c9d1d9">'
            f'{row["rate"]:.4f}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;color:#8b949e">{row["rate_unit"]}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;'
            f'color:#3fb950;background:#161b22">{smart_fmt(row["line_cost"])}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;'
            f'color:#3fb950;background:#161b22">{row["spec_cost"]:.4f} USD/{prod_unit}</td>'
            f'<td style="padding:.4rem .7rem;text-align:right;font-family:DM Mono,monospace;'
            f'color:#3fb950;background:#161b22">{"—" if is_credit else f"{pct:.2f}%"}</td>'
            f'</tr>'
        )

    # Total row
    body_rows.append(
        f'<tr style="border-top:2px solid #21262d;background:#1a2030">'
        f'<td colspan="7" style="padding:.5rem .7rem;color:#e6edf3;font-weight:600;font-family:Syne,sans-serif">'
        f'TOTAL</td>'
        f'<td style="padding:.5rem .7rem;text-align:right;font-family:DM Mono,monospace;'
        f'color:#e6edf3;font-weight:600">{smart_fmt(total_cost)}</td>'
        f'<td style="padding:.5rem .7rem"></td>'
        f'<td style="padding:.5rem .7rem;text-align:right;font-family:DM Mono,monospace;'
        f'color:#e6edf3;font-weight:600">{"—" if is_credit else "100.00%"}</td>'
        f'</tr>'
    )

    html = header + "".join(body_rows) + "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)

    # ── Price editors: one row per item, input + reset button ────────────────
    st.space("small")
    st.markdown(
        '<p style="font-family:Inter,sans-serif;font-size:.75rem;color:#58a6ff;'
        'text-transform:uppercase;letter-spacing:.08em;margin-bottom:.6rem">'
        'Edit prices — press ↩ to restore to session default</p>',
        unsafe_allow_html=True
    )

    changed = False
    for row in rows:
        name      = row["name"]
        modified  = row["modified"]
        inp_def   = row["input_default"]
        wgt_key   = f"cf_{scenario_name}_{table_key}_{name}"
        reset_key = f"rst_{scenario_name}_{table_key}_{name}"

        label_color = "#e6a817" if modified else "#8b949e"

        col_lbl, col_inp, col_btn = st.columns([2, 1, 1])

        with col_lbl:
            hint = f"  ← default: {inp_def:.6g}" if modified else ""
            st.markdown(
                f'<p style="font-family:Inter,sans-serif;font-size:.82rem;'
                f'color:{label_color};margin:0;padding:.45rem 0">'
                f'{name}<span style="font-size:.72rem;color:#8b949e">{hint}</span></p>',
                unsafe_allow_html=True
            )

        with col_inp:
            new_val = st.number_input(
                name,
                value=float(row["price"]),
                min_value=0.0,
                step=0.001,
                format="%.6f",
                key=wgt_key,
                label_visibility="collapsed",
            )
            if abs(new_val - row["price"]) > 1e-12:
                wk[table_key][name] = new_val
                changed = True

with col_btn:
            if st.button(
                f"↩ {inp_def:.6g}",
                key=reset_key,
                help=f"Restore to default: {inp_def:.6g}",
                disabled=not modified,
            ):
                wk[table_key][name] = inp_def
                # Force the widget to show the default value on rerun
                st.session_state[wgt_key] = float(inp_def)
                changed = True
    if changed:
        st.rerun()

    return rows, total_cost


# ── 1. Raw Materials ──────────────────────────────────────────────────────────
st.markdown("#### Raw Materials")
rm_rows, rm_total = _build_vc_table("Raw Materials")

st.space("medium")

# ── 2. Chemical Inputs & Utilities ───────────────────────────────────────────
st.markdown("#### Chemical Inputs & Utilities")
cu_rows, cu_total = _build_vc_table("Chemical Inputs and Utilities")

st.space("medium")

# ── 3. Credits & Byproducts ───────────────────────────────────────────────────
st.markdown("#### Credits & Byproducts")
cb_rows, cb_total = _build_vc_table("Credits and Byproducts", is_credit=True)

st.space("medium")

# ── Variable Costs Summary ────────────────────────────────────────────────────
section_header("Variable Costs Summary", "#58a6ff")

tvc_gross = rm_total + cu_total
tvc_net   = tvc_gross - cb_total

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Raw Materials", smart_fmt(rm_total), "#58a6ff")
with c2: kpi_card("Chemical Inputs & Utilities", smart_fmt(cu_total), "#79c0ff")
with c3: kpi_card("Credits & Byproducts", smart_fmt(cb_total), "#3fb950")
with c4: kpi_card("Net Variable Costs", smart_fmt(tvc_net), "#e6a817")
