import streamlit as st
import pandas as pd

st.set_page_config(page_title="Cash Flow & Analysis", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&family=Inter:wght@300;400;500;600&display=swap');

.hero-title{font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;
    color:#e6edf3;letter-spacing:-.03em;margin-bottom:.1rem;}
.hero-sub{font-family:'Inter',sans-serif;font-size:.85rem;font-weight:300;
    color:#8b949e;letter-spacing:.08em;text-transform:uppercase;}
.section-hdr{font-family:'Syne',sans-serif;font-size:.7rem;font-weight:700;
    color:#58a6ff;text-transform:uppercase;letter-spacing:.15em;
    padding:.5rem 0 .3rem 0;border-bottom:1px solid #21262d;margin-bottom:.6rem;}
.divider{border:none;border-top:1px solid #21262d;margin:1.2rem 0;}
.summary-card{background:#161b22;border:1px solid #21262d;border-radius:8px;
    padding:1rem 1.2rem;border-left:3px solid #58a6ff;}
.sum-label{font-family:'Inter',sans-serif;font-size:.68rem;font-weight:500;
    color:#8b949e;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.3rem;}
.sum-value{font-family:'DM Mono',monospace;font-size:1.3rem;font-weight:500;color:#e6edf3;}
.sum-sub{font-family:'Inter',sans-serif;font-size:.72rem;color:#8b949e;margin-top:.2rem;}
.legend-row{display:flex;gap:1.5rem;align-items:center;margin-bottom:.8rem;flex-wrap:wrap;}
.leg-item{display:flex;align-items:center;gap:.4rem;font-family:'Inter',sans-serif;
    font-size:.78rem;color:#8b949e;}
.leg-swatch{width:12px;height:12px;border-radius:3px;flex-shrink:0;}
</style>
""", unsafe_allow_html=True)

# ── Guard ─────────────────────────────────────────────────────────────────────
if "scenarios" not in st.session_state or not st.session_state.scenarios:
    st.markdown('<div class="hero-title">Cash Flow & Analysis</div>', unsafe_allow_html=True)
    st.info("No scenarios saved yet. Configure and save scenarios on the Input Data page first.")
    st.stop()

scenarios = st.session_state.scenarios

# ── Helpers ───────────────────────────────────────────────────────────────────
def _v(d, k, default=0.0):
    v = d.get(k, default)
    return v if isinstance(v, (int, float)) else default

def smart_fmt(v, unit="USD"):
    """Format as MMUSD if ≥1M, else USD."""
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.3f} MM{unit}"
    return f"${v:,.2f}"

def coeff_unit(rate_unit: str, product_unit: str) -> str:
    """Derive technical coefficient unit from rate_unit / product_unit."""
    _numerator = {
        "g/h": "g", "kg/h": "kg", "t/h": "t",
        "mL/h": "mL", "L/h": "L", "m³/h": "m³",
        "kW": "kWh", "MW": "MWh", "GW": "GWh",
        "MMBtu/h": "MMBtu",
        "g/y": "g", "kg/y": "kg", "t/y": "t",
        "mL/y": "mL", "L/y": "L", "m³/y": "m³", "MMBtu/y": "MMBtu",
    }
    num = _numerator.get(rate_unit, rate_unit.split("/")[0] if "/" in rate_unit else rate_unit)
    return f"{num}/{product_unit}"

def is_per_year(rate_unit: str) -> bool:
    return rate_unit.endswith("/y")

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
st.markdown('<div class="hero-title">Cash Flow & Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Interactive economic analysis — scenario-based</div>',
            unsafe_allow_html=True)
st.markdown('<hr class="divider">', unsafe_allow_html=True)

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
        st.rerun()

# ── Scenario summary ──────────────────────────────────────────────────────────
prod_name = d.get("Product Name", "—")
prod_unit = d.get("Unit", "")
capacity  = _v(d, "Capacity")
tic       = _v(d, "Total Investment")
opex      = _v(d, "Total OPEX")

st.markdown('<div class="section-hdr">Scenario Summary</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div class="summary-card" style="border-left-color:#e6a817">
        <div class="sum-label">Main Product</div>
        <div class="sum-value" style="font-size:1.1rem;color:#e6edf3">{prod_name}</div>
        <div class="sum-sub">{capacity:,.0f} {prod_unit}/year</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="summary-card" style="border-left-color:#58a6ff">
        <div class="sum-label">Total Investment Cost (TIC)</div>
        <div class="sum-value">{smart_fmt(tic)}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="summary-card" style="border-left-color:#3fb950">
        <div class="sum-label">Total Annual OPEX</div>
        <div class="sum-value">{smart_fmt(opex)}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Legend ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="legend-row">
  <div class="leg-item">
    <div class="leg-swatch" style="background:#1c2d3a;border:1px solid #58a6ff66"></div>
    <span>Editable input — value matches scenario default</span>
  </div>
  <div class="leg-item">
    <div class="leg-swatch" style="background:#2d2a1a;border:1px solid #e6a81766"></div>
    <span>Editable input — value differs from default</span>
  </div>
  <div class="leg-item">
    <div class="leg-swatch" style="background:#161b22;border:1px solid #3fb95066"></div>
    <span>Calculated result</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Save button ───────────────────────────────────────────────────────────────
save_col, _ = st.columns([1, 3])
with save_col:
    if st.button("💾  Save as new defaults for this scenario", type="primary", use_container_width=True):
        wk = st.session_state.cf_working.get(scenario_name, {})
        st.session_state.cf_session_defaults[scenario_name] = {
            tbl: dict(prices) for tbl, prices in wk.items()
        }
        st.success("Saved. These values are now the session defaults for this scenario.")

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Variable Costs Section ────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Variable Costs & Credits</div>', unsafe_allow_html=True)

working_hours = _v(d, "Working Hours per Year", 8000.0)
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

    # ── Price editors (below the table) ───────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-family:Inter,sans-serif;font-size:.75rem;color:#58a6ff;'
        'text-transform:uppercase;letter-spacing:.08em;margin-bottom:.4rem">'
        'Edit prices below — delete value and press Enter to restore default</p>',
        unsafe_allow_html=True
    )

    n_cols = min(len(rows), 4)
    cols = st.columns(n_cols)
    changed = False
    for i, row in enumerate(rows):
        name = row["name"]
        modified = row["modified"]
        label_color = "#e6a817" if modified else "#8b949e"
        default_hint = f" (default: {row['input_default']:.6g})" if modified else ""
        with cols[i % n_cols]:
            st.markdown(
                f'<p style="font-family:Inter,sans-serif;font-size:.72rem;'
                f'color:{label_color};margin-bottom:2px">'
                f'{name}{default_hint}</p>',
                unsafe_allow_html=True
            )
            new_val = st.number_input(
                name,
                value=float(row["price"]),
                min_value=0.0,
                step=0.001,
                format="%.6f",
                key=f"cf_{scenario_name}_{table_key}_{name}",
                label_visibility="collapsed",
            )
            # If user clears to 0 and item had a non-zero default, treat as reset
            inp_def = row["input_default"]
            if new_val == 0.0 and inp_def != 0.0:
                new_val = inp_def
            if abs(new_val - row["price"]) > 1e-12:
                wk[table_key][name] = new_val
                changed = True

    if changed:
        st.rerun()

    return rows, total_cost


# ── 1. Raw Materials ──────────────────────────────────────────────────────────
st.markdown("#### Raw Materials")
rm_rows, rm_total = _build_vc_table("Raw Materials")

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── 2. Chemical Inputs & Utilities ───────────────────────────────────────────
st.markdown("#### Chemical Inputs & Utilities")
cu_rows, cu_total = _build_vc_table("Chemical Inputs and Utilities")

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── 3. Credits & Byproducts ───────────────────────────────────────────────────
st.markdown("#### Credits & Byproducts")
cb_rows, cb_total = _build_vc_table("Credits and Byproducts", is_credit=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Variable Costs Summary ────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">Variable Costs Summary</div>', unsafe_allow_html=True)

tvc_gross = rm_total + cu_total
tvc_net   = tvc_gross - cb_total

c1, c2, c3, c4 = st.columns(4)
def _sum_card(col, label, value, color):
    with col:
        st.markdown(f"""<div class="summary-card" style="border-left-color:{color}">
            <div class="sum-label">{label}</div>
            <div class="sum-value" style="font-size:1.05rem">{smart_fmt(value)}</div>
        </div>""", unsafe_allow_html=True)

_sum_card(c1, "Raw Materials",               rm_total, "#58a6ff")
_sum_card(c2, "Chemical Inputs & Utilities", cu_total, "#79c0ff")
_sum_card(c3, "Credits & Byproducts",        cb_total, "#3fb950")
_sum_card(c4, "Net Variable Costs",          tvc_net,  "#e6a817")
