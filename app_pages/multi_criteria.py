"""ISI-Tool — Multi-Criteria Analysis (MCA) page.

Ranks heterogeneous scenarios using TOPSIS for strategic decision support.
Uses what-if overrides, financial assumptions, and user-configurable
product prices for evaluation.
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
from utils.constants import safe_val, fmt_compact, PLOTLY_LAYOUT, PALETTE, TRL_OPTIONS
from utils.ui import inject_css, page_header, section_header, kpi_card, require_scenarios
from utils.finance import (
    extract_params, compute_indicators, solve_price_for_npv, topsis,
)

inject_css()

# ── Data guard ────────────────────────────────────────────────────────────────
scenarios, names, cmap = require_scenarios("Multi-Criteria Analysis")

if len(names) < 2:
    page_header("Multi-Criteria Analysis")
    st.info(
        "At least **2 scenarios** are needed for comparative ranking. "
        "Go to **Input Data** to create more scenarios.",
        icon=":material/info:",
    )
    st.stop()

page_header("Multi-Criteria Analysis",
            "TOPSIS-based scenario ranking for strategic decision support")

st.caption(
    "TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution) "
    "ranks scenarios by measuring their distance to the best and worst possible "
    "outcomes across multiple weighted criteria."
)

st.space("medium")

# ── TRL ordinal mapping ──────────────────────────────────────────────────────
TRL_ORDINAL = {
    "Theoretical (1 or 2)": 1.5,
    "Bench (3 or 4)": 3.5,
    "Pilot (5 to 7)": 6.0,
    "Industrial (8 or 9)": 8.5,
}


# ── Scenario selection ───────────────────────────────────────────────────────
section_header("Scenario selection", "#e6a817")
selected = st.multiselect(
    "Select scenarios to rank",
    names, default=names,
    key="mca_scenarios",
)
if len(selected) < 2:
    st.info("Select at least 2 scenarios to proceed.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATION PARAMETERS — price & what-if source
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Evaluation parameters", "#58a6ff")

st.caption(
    "The MCA uses what-if overrides and financial assumptions from the Cash Flow page. "
    "You can also override the product price here to evaluate all scenarios at a common "
    "price point, or set individual prices per scenario."
)

# ── Price mode ───────────────────────────────────────────────────────────────
price_mode = st.radio(
    "Product price source",
    [
        "Use Cash Flow prices (what-if / MSP fallback)",
        "Set a common price for all scenarios",
        "Set individual prices per scenario",
    ],
    index=0,
    key="mca_price_mode",
    horizontal=True,
)


def _resolve_cf_price(scenario_name: str, scenario_data: dict) -> float:
    """Get the effective price from the Cash Flow page state."""
    _pm = st.session_state.get("cf_price_mode", {}).get(scenario_name, {})
    _pm_mode = _pm.get("mode", "MANUAL")
    _input_price = safe_val(scenario_data, "Main Product Price", 0.0)
    if _pm_mode != "MANUAL" and _pm.get("solved_price"):
        return float(_pm["solved_price"])
    elif _pm.get("manual_price") is not None:
        return float(_pm["manual_price"])
    return _input_price


# Resolve prices based on mode
mca_prices = {}

if price_mode == "Set a common price for all scenarios":
    # Get a default — use average of existing prices or a reasonable default
    existing_prices = []
    for name in selected:
        p = _resolve_cf_price(name, scenarios[name])
        if p > 0:
            existing_prices.append(p)
    default_common = sum(existing_prices) / len(existing_prices) if existing_prices else 5000.0

    unit_labels = list({scenarios[n].get("Unit", "unit") for n in selected})
    unit_str = unit_labels[0] if len(unit_labels) == 1 else "/".join(unit_labels)

    common_price = st.number_input(
        f"Common product price (USD / {unit_str})",
        value=default_common,
        min_value=0.01,
        step=100.0,
        format="%.2f",
        key="mca_common_price",
    )
    for name in selected:
        mca_prices[name] = common_price

elif price_mode == "Set individual prices per scenario":
    price_cols = st.columns(min(len(selected), 4))
    for i, name in enumerate(selected):
        d = scenarios[name]
        cf_price = _resolve_cf_price(name, d)
        unit = d.get("Unit", "unit")
        with price_cols[i % len(price_cols)]:
            mca_prices[name] = st.number_input(
                f"{name} (USD/{unit})",
                value=cf_price if cf_price > 0 else 5000.0,
                min_value=0.01,
                step=100.0,
                format="%.2f",
                key=f"mca_price_{name}",
            )
else:
    # Use Cash Flow prices
    for name in selected:
        mca_prices[name] = _resolve_cf_price(name, scenarios[name])

st.space("small")

# Show what-if status per scenario
wif_status = []
for name in selected:
    wif = st.session_state.get("cf_wif", {}).get(name, {})
    fin = st.session_state.get("cf_fin", {}).get(name, {})
    n_wif = len(wif)
    n_fin = sum(1 for k in fin if not k.startswith("_"))
    price = mca_prices[name]
    wif_status.append({
        "Scenario": name,
        "Price (USD/unit)": f"${price:,.2f}" if price > 0 else "MSP (auto)",
        "What-if overrides": f"{n_wif}" if n_wif else "—",
        "Financial overrides": f"{n_fin}" if n_fin else "—",
    })

st.markdown(
    '<p style="font-size:.72rem;color:#6e7681;font-weight:600;text-transform:uppercase;'
    'letter-spacing:.08em;margin:.3rem 0 .2rem 0">Data sources per scenario</p>',
    unsafe_allow_html=True,
)

# Build concise HTML status table
status_hdr = "".join(
    f'<th style="padding:.3rem .6rem;text-align:left;font-size:.72rem;'
    f'color:#8b949e;border-bottom:1px solid #21262d">{col}</th>'
    for col in ["Scenario", "Price", "What-if", "Fin. assumptions"]
)
status_rows = ""
for row in wif_status:
    color = cmap.get(row["Scenario"], "#8b949e")
    status_rows += (
        f'<tr style="border-bottom:1px solid #21262d22">'
        f'<td style="padding:.3rem .6rem;font-size:.8rem;color:{color};font-weight:600">{row["Scenario"]}</td>'
        f'<td style="padding:.3rem .6rem;font-size:.8rem;font-family:DM Mono,monospace;color:#c9d1d9">{row["Price (USD/unit)"]}</td>'
        f'<td style="padding:.3rem .6rem;font-size:.8rem;color:#8b949e">{row["What-if overrides"]}</td>'
        f'<td style="padding:.3rem .6rem;font-size:.8rem;color:#8b949e">{row["Financial overrides"]}</td>'
        f'</tr>'
    )
st.markdown(
    f'<div style="border:1px solid #21262d;border-radius:6px;background:#161b22;overflow-x:auto">'
    f'<table style="width:100%;border-collapse:collapse"><thead><tr>{status_hdr}</tr></thead>'
    f'<tbody>{status_rows}</tbody></table></div>',
    unsafe_allow_html=True,
)

st.space("medium")

# ═══════════════════════════════════════════════════════════════════════════════
# COMPUTE KPIs
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Financial KPI computation", "#3fb950")

scenario_kpis = {}
for name in selected:
    d = scenarios[name]
    wif = st.session_state.get("cf_wif", {}).get(name, {})
    fin = st.session_state.get("cf_fin", {}).get(name, {})
    p = extract_params(d, wif, fin)

    price = mca_prices[name]

    # If still no price, compute MSP as fallback
    if price <= 0:
        msp = solve_price_for_npv(p, 0.0)
        price = msp if (msp is not None and msp > 0) else 0.0
        mca_prices[name] = price

    if price > 0:
        ind = compute_indicators(p, price)
    else:
        ind = {
            "NPV": 0.0, "IRR": None, "MSP": None, "Payback": None,
            "TIC": p["capex"] + p["wc"] + p["startup"],
            "MARR": p["marr"], "OPEX": p["opex"],
            "Capacity": p["capacity"], "CAPEX": p["capex"],
            "Gross Margin": 0.0, "EBITDA Margin": 0.0,
            "Net Profit Margin": 0.0,
        }

    ind["price"] = price
    ind["TRL_ordinal"] = TRL_ORDINAL.get(d.get("TRL", ""), 5.0)
    ind["TRL_label"] = d.get("TRL", "—")

    lo_pct = safe_val(d, "TIC Lower Pct", 0.0)
    hi_pct = safe_val(d, "TIC Upper Pct", 0.0)
    ind["TIC_accuracy_width"] = abs(hi_pct - lo_pct) if (lo_pct != 0 or hi_pct != 0) else 60.0

    tic = ind.get("TIC", 1.0) or 1.0
    ind["Capital_Efficiency"] = ind["NPV"] / tic if tic > 0 else 0.0

    cap = ind.get("Capacity", 1.0) or 1.0
    ind["OPEX_per_unit"] = ind["OPEX"] / cap if cap > 0 else 0.0

    scenario_kpis[name] = ind

# Show computed KPIs
kpi_cols = st.columns(min(len(selected), 4))
for i, name in enumerate(selected):
    with kpi_cols[i % len(kpi_cols)]:
        ind = scenario_kpis[name]
        npv_str = f"${ind['NPV']/1e6:.1f}M" if ind["NPV"] else "—"
        irr_str = f"{ind['IRR']*100:.1f}%" if ind["IRR"] else "—"
        price_str = f"${ind['price']:,.0f}" if ind["price"] else "—"
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(
                f"Price: {price_str}  ·  NPV: {npv_str}  ·  "
                f"IRR: {irr_str}  ·  TRL: {ind['TRL_label']}"
            )

st.space("medium")

# ═══════════════════════════════════════════════════════════════════════════════
# CRITERIA WEIGHTS
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Criteria & weights", "#e6a817")

st.caption(
    "Assign relative importance to each criterion. Weights are automatically "
    "normalized to sum to 100%. Drag sliders to reflect your strategic priorities."
)

CRITERIA = [
    {
        "name": "Financial Return",
        "key": "NPV",
        "description": "Net Present Value — absolute financial viability",
        "is_benefit": True,
        "icon": ":material/trending_up:",
        "default_weight": 25,
    },
    {
        "name": "Capital Efficiency",
        "key": "Capital_Efficiency",
        "description": "NPV / TIC — return per dollar invested",
        "is_benefit": True,
        "icon": ":material/account_balance:",
        "default_weight": 20,
    },
    {
        "name": "Technology Maturity",
        "key": "TRL_ordinal",
        "description": "TRL level — higher = lower technology risk",
        "is_benefit": True,
        "icon": ":material/science:",
        "default_weight": 15,
    },
    {
        "name": "Operational Cost",
        "key": "OPEX_per_unit",
        "description": "OPEX per unit product — lower = more competitive",
        "is_benefit": False,
        "icon": ":material/payments:",
        "default_weight": 15,
    },
    {
        "name": "Investment Risk",
        "key": "TIC_accuracy_width",
        "description": "TIC accuracy range — narrower = less estimation risk",
        "is_benefit": False,
        "icon": ":material/warning:",
        "default_weight": 15,
    },
    {
        "name": "Scale",
        "key": "Capacity",
        "description": "Annual production capacity — larger = more market impact",
        "is_benefit": True,
        "icon": ":material/factory:",
        "default_weight": 10,
    },
]

w_cols = st.columns(len(CRITERIA))
raw_weights = []
for col, crit in zip(w_cols, CRITERIA):
    with col:
        st.markdown(f'{crit["icon"]} **{crit["name"]}**')
        st.caption(crit["description"])
        w = st.slider(
            crit["name"],
            min_value=0, max_value=100,
            value=crit["default_weight"],
            key=f"mca_w_{crit['key']}",
            label_visibility="collapsed",
        )
        raw_weights.append(w)

total_w = sum(raw_weights)
if total_w == 0:
    st.warning("All weights are zero — set at least one weight above 0.")
    st.stop()

norm_weights = [w / total_w for w in raw_weights]

w_display = "  ·  ".join(
    f"**{c['name']}**: {nw*100:.0f}%"
    for c, nw in zip(CRITERIA, norm_weights)
)
st.caption(f"Normalized weights: {w_display}")

st.space("medium")

# ═══════════════════════════════════════════════════════════════════════════════
# TOPSIS COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════
section_header("TOPSIS ranking", "#3fb950")

n_alt = len(selected)
n_crit = len(CRITERIA)

decision_matrix = np.zeros((n_alt, n_crit))
for i, name in enumerate(selected):
    ind = scenario_kpis[name]
    for j, crit in enumerate(CRITERIA):
        val = ind.get(crit["key"], 0.0)
        if val is None:
            val = 0.0
        decision_matrix[i, j] = val

weights_arr = np.array(norm_weights)
is_benefit_arr = np.array([c["is_benefit"] for c in CRITERIA])

closeness = topsis(decision_matrix, weights_arr, is_benefit_arr)

rank_order = np.argsort(-closeness)
ranks = np.empty_like(rank_order)
ranks[rank_order] = np.arange(1, n_alt + 1)

# ── Results Table ────────────────────────────────────────────────────────────
crit_headers = "".join(
    f'<th style="padding:.4rem .6rem;text-align:right;font-size:.72rem;'
    f'color:#8b949e;white-space:nowrap">{c["name"]}<br>'
    f'<span style="font-size:.6rem;color:#484f58">'
    f'{"↑ higher=better" if c["is_benefit"] else "↓ lower=better"}</span></th>'
    for c in CRITERIA
)

rows_html = ""
for idx in rank_order:
    name = selected[idx]
    rank = int(ranks[idx])
    score = closeness[idx]
    color = cmap.get(name, PALETTE[idx % len(PALETTE)])

    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")

    cells = ""
    for j, crit in enumerate(CRITERIA):
        val = decision_matrix[idx, j]
        if crit["key"] == "NPV":
            cell = f"${val/1e6:.1f}M"
        elif crit["key"] == "Capital_Efficiency":
            cell = f"{val:.3f}"
        elif crit["key"] == "OPEX_per_unit":
            cell = f"${val:,.0f}"
        elif crit["key"] in ("TRL_ordinal",):
            cell = f"{val:.1f}"
        elif crit["key"] == "TIC_accuracy_width":
            cell = f"±{val:.0f}%"
        elif crit["key"] == "Capacity":
            cell = f"{val:,.0f}"
        else:
            cell = f"{val:.2f}"
        cells += (
            f'<td style="padding:.4rem .6rem;text-align:right;'
            f'font-family:DM Mono,monospace;font-size:.8rem;color:#c9d1d9">{cell}</td>'
        )

    rows_html += (
        f'<tr style="border-bottom:1px solid #21262d;'
        f'{"background:#1a2030" if rank <= 3 else ""}">'
        f'<td style="padding:.4rem .6rem;font-size:1rem;text-align:center">{medal}</td>'
        f'<td style="padding:.4rem .6rem;font-weight:600;color:{color}">{name}</td>'
        f'<td style="padding:.4rem .6rem;text-align:right;font-family:DM Mono,monospace;'
        f'font-size:.85rem;color:#e6a817;font-weight:600">{score:.4f}</td>'
        f'{cells}'
        f'</tr>'
    )

st.markdown(f"""
<div style="overflow-x:auto;border:1px solid #21262d;border-radius:6px;background:#161b22">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="border-bottom:2px solid #21262d">
  <th style="padding:.5rem .6rem;text-align:center;font-size:.75rem;color:#8b949e;width:40px">Rank</th>
  <th style="padding:.5rem .6rem;text-align:left;font-size:.75rem;color:#8b949e;min-width:120px">Scenario</th>
  <th style="padding:.5rem .6rem;text-align:right;font-size:.75rem;color:#e6a817">TOPSIS Score</th>
  {crit_headers}
</tr></thead>
<tbody>{rows_html}</tbody>
</table></div>
""", unsafe_allow_html=True)

st.space("medium")

# ── Radar Chart ──────────────────────────────────────────────────────────────
section_header("Radar chart — trade-off visualization", "#58a6ff")

st.caption("Normalized scores (0–1) across all criteria. Larger area = better overall performance.")

radar_matrix = np.zeros_like(decision_matrix)
for j in range(n_crit):
    col = decision_matrix[:, j]
    cmin, cmax = col.min(), col.max()
    if cmax - cmin > 1e-12:
        normalized = (col - cmin) / (cmax - cmin)
    else:
        normalized = np.full_like(col, 0.5)
    if not CRITERIA[j]["is_benefit"]:
        normalized = 1.0 - normalized
    radar_matrix[:, j] = normalized

categories = [c["name"] for c in CRITERIA]

max_radar = min(5, n_alt)
top_indices = rank_order[:max_radar]

fig_radar = go.Figure()
for idx in top_indices:
    name = selected[idx]
    vals = list(radar_matrix[idx])
    vals.append(vals[0])
    cats = categories + [categories[0]]
    color = cmap.get(name, PALETTE[idx % len(PALETTE)])

    fig_radar.add_trace(go.Scatterpolar(
        r=vals, theta=cats,
        fill="toself",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
        line=dict(color=color, width=2),
        name=f"#{int(ranks[idx])} {name}",
    ))

fig_radar.update_layout(
    polar=dict(
        bgcolor="rgba(0,0,0,0)",
        angularaxis=dict(
            tickfont=dict(size=11, color="#c9d1d9", family="DM Sans"),
            gridcolor="#21262d",
            linecolor="#21262d",
        ),
        radialaxis=dict(
            range=[0, 1],
            tickfont=dict(size=9, color="#6e7681"),
            gridcolor="#21262d",
            linecolor="#21262d",
        ),
    ),
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#8b949e", size=12),
    legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)",
                font=dict(size=11)),
    margin=dict(l=60, r=60, t=30, b=60),
    height=450,
)
st.plotly_chart(fig_radar, use_container_width=True)

st.space("medium")

# ── TOPSIS Step-by-Step (expandable) ─────────────────────────────────────────
with st.expander("TOPSIS methodology — step-by-step detail",
                  icon=":material/info:"):
    st.markdown("**Step 1: Decision Matrix**")
    st.caption("Raw values for each scenario × criterion.")
    dm_df = pd.DataFrame(
        decision_matrix,
        index=selected,
        columns=[c["name"] for c in CRITERIA],
    )
    st.dataframe(dm_df.style.format("{:.4f}"), use_container_width=True)

    st.markdown("**Step 2: Vector Normalization**")
    st.caption("Each value divided by the column's Euclidean norm.")
    norms = np.sqrt(np.sum(decision_matrix ** 2, axis=0))
    norms[norms == 0] = 1.0
    norm_dm = decision_matrix / norms
    norm_df = pd.DataFrame(norm_dm, index=selected,
                           columns=[c["name"] for c in CRITERIA])
    st.dataframe(norm_df.style.format("{:.4f}"), use_container_width=True)

    st.markdown("**Step 3: Weighted Matrix**")
    weighted_dm = norm_dm * weights_arr
    w_df = pd.DataFrame(weighted_dm, index=selected,
                        columns=[c["name"] for c in CRITERIA])
    st.dataframe(w_df.style.format("{:.4f}"), use_container_width=True)

    st.markdown("**Step 4: Ideal & Anti-Ideal Solutions**")
    ideal = np.where(is_benefit_arr, weighted_dm.max(axis=0), weighted_dm.min(axis=0))
    anti = np.where(is_benefit_arr, weighted_dm.min(axis=0), weighted_dm.max(axis=0))
    ia_df = pd.DataFrame(
        [ideal, anti], index=["Ideal (A⁺)", "Anti-ideal (A⁻)"],
        columns=[c["name"] for c in CRITERIA],
    )
    st.dataframe(ia_df.style.format("{:.4f}"), use_container_width=True)

    st.markdown("**Step 5: Distances & Closeness**")
    d_plus = np.sqrt(np.sum((weighted_dm - ideal) ** 2, axis=1))
    d_minus = np.sqrt(np.sum((weighted_dm - anti) ** 2, axis=1))
    result_df = pd.DataFrame({
        "D⁺ (to ideal)": d_plus,
        "D⁻ (to anti-ideal)": d_minus,
        "Closeness Cᵢ": closeness,
        "Rank": ranks,
    }, index=selected)
    st.dataframe(
        result_df.sort_values("Rank").style.format({
            "D⁺ (to ideal)": "{:.4f}",
            "D⁻ (to anti-ideal)": "{:.4f}",
            "Closeness Cᵢ": "{:.4f}",
            "Rank": "{:.0f}",
        }),
        use_container_width=True,
    )

    st.markdown(
        r"$$C_i = \frac{D_i^-}{D_i^+ + D_i^-}$$"
    )
    st.caption(
        "Higher Cᵢ = closer to ideal solution. "
        "A score of 1.0 means the scenario is the ideal on all criteria; "
        "0.0 means it matches the anti-ideal on all criteria."
    )
