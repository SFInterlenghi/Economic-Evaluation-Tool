"""ISI-Tool — Multi-Criteria Analysis (MCA) page.

Ranks heterogeneous scenarios using TOPSIS for strategic decision support.
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
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

# ── Compute KPIs for all selected scenarios ──────────────────────────────────
section_header("Financial KPI computation", "#58a6ff")

@st.cache_data(show_spinner=False)
def _compute_scenario_kpis(scenario_name: str, scenario_data: dict) -> dict:
    """Compute financial indicators for a single scenario."""
    wif = st.session_state.get("cf_wif", {}).get(scenario_name, {})
    fin = st.session_state.get("cf_fin", {}).get(scenario_name, {})
    p = extract_params(scenario_data, wif, fin)

    # Determine selling price
    _pm = st.session_state.get("cf_price_mode", {}).get(scenario_name, {})
    _pm_mode = _pm.get("mode", "MANUAL")
    _input_price = safe_val(scenario_data, "Main Product Price", 0.0)

    if _pm_mode != "MANUAL" and _pm.get("solved_price"):
        price = float(_pm["solved_price"])
    elif _pm.get("manual_price") is not None:
        price = float(_pm["manual_price"])
    else:
        price = _input_price

    # If no price set, try to compute MSP
    if price <= 0:
        msp = solve_price_for_npv(p, 0.0)
        price = msp if (msp is not None and msp > 0) else 0.0

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

    # Augment with scenario-specific data
    ind["price"] = price
    ind["TRL_ordinal"] = TRL_ORDINAL.get(scenario_data.get("TRL", ""), 5.0)
    ind["TRL_label"] = scenario_data.get("TRL", "—")

    # TIC accuracy range width
    lo_pct = safe_val(scenario_data, "TIC Lower Pct", 0.0)
    hi_pct = safe_val(scenario_data, "TIC Upper Pct", 0.0)
    ind["TIC_accuracy_width"] = abs(hi_pct - lo_pct) if (lo_pct != 0 or hi_pct != 0) else 60.0

    # Capital efficiency: NPV / TIC
    tic = ind.get("TIC", 1.0) or 1.0
    ind["Capital_Efficiency"] = ind["NPV"] / tic if tic > 0 else 0.0

    # OPEX per unit
    cap = ind.get("Capacity", 1.0) or 1.0
    ind["OPEX_per_unit"] = ind["OPEX"] / cap if cap > 0 else 0.0

    return ind


with st.spinner("Computing financial KPIs for selected scenarios…"):
    scenario_kpis = {}
    for name in selected:
        scenario_kpis[name] = _compute_scenario_kpis(name, scenarios[name])

# Show computed KPIs
kpi_cols = st.columns(min(len(selected), 4))
for i, name in enumerate(selected):
    with kpi_cols[i % len(kpi_cols)]:
        ind = scenario_kpis[name]
        npv_str = f"${ind['NPV']/1e6:.1f}M" if ind["NPV"] else "—"
        irr_str = f"{ind['IRR']*100:.1f}%" if ind["IRR"] else "—"
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(f"NPV: {npv_str}  ·  IRR: {irr_str}  ·  TRL: {ind['TRL_label']}")

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

# Weight sliders
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

# Normalize weights
total_w = sum(raw_weights)
if total_w == 0:
    st.warning("All weights are zero — set at least one weight above 0.")
    st.stop()

norm_weights = [w / total_w for w in raw_weights]

# Display normalized weights
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

# Build decision matrix
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

# Run TOPSIS
closeness = topsis(decision_matrix, weights_arr, is_benefit_arr)

# Rank
rank_order = np.argsort(-closeness)  # descending
ranks = np.empty_like(rank_order)
ranks[rank_order] = np.arange(1, n_alt + 1)

# ── Results Table ────────────────────────────────────────────────────────────
# Build header
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

    # Medal for top 3
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

# Normalize each criterion to [0, 1] for radar display
radar_matrix = np.zeros_like(decision_matrix)
for j in range(n_crit):
    col = decision_matrix[:, j]
    cmin, cmax = col.min(), col.max()
    if cmax - cmin > 1e-12:
        normalized = (col - cmin) / (cmax - cmin)
    else:
        normalized = np.full_like(col, 0.5)
    # Flip for cost criteria
    if not CRITERIA[j]["is_benefit"]:
        normalized = 1.0 - normalized
    radar_matrix[:, j] = normalized

categories = [c["name"] for c in CRITERIA]

# Show top N scenarios on radar
max_radar = min(5, n_alt)
top_indices = rank_order[:max_radar]

fig_radar = go.Figure()
for idx in top_indices:
    name = selected[idx]
    vals = list(radar_matrix[idx])
    vals.append(vals[0])  # close the polygon
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
    import pandas as pd
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
