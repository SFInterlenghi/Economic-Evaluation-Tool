"""ISI-Tool — Risk & Sensitivity Analysis page.

Section A: Tornado chart (1D perturbation)
Section B: Viability surface (2D parameter sweep)
Section C: Monte Carlo simulation
"""
import streamlit as st
import numpy as np
import plotly.graph_objects as go
from utils.constants import safe_val, fmt_compact, PLOTLY_LAYOUT, PALETTE
from utils.ui import inject_css, page_header, section_header, kpi_card, require_scenarios, scenario_filter
from utils.finance import (
    extract_params, build_cf_arrays, npv_at_price, irr_from_cfs,
    solve_price_for_npv, compute_indicators, monte_carlo_npv_irr,
)

inject_css()

# ── Data guard ────────────────────────────────────────────────────────────────
scenarios, names, cmap = require_scenarios("Risk & Sensitivity")

page_header("Risk & Sensitivity", "Tornado · Viability Surface · Monte Carlo")

# ── Scenario selector ────────────────────────────────────────────────────────
sel_col, _ = st.columns([3, 1])
with sel_col:
    scenario_name = st.selectbox("Baseline scenario", names, key="risk_scen_sel")
d = scenarios[scenario_name]

# Get what-if and financial overrides from session state (if any)
wif = st.session_state.get("cf_wif", {}).get(scenario_name, {})
fin = st.session_state.get("cf_fin", {}).get(scenario_name, {})

# Extract base params
base_params = extract_params(d, wif, fin)

# Determine effective price (same logic as cash_flow.py)
_pm_state = st.session_state.get("cf_price_mode", {}).get(scenario_name, {})
_pm_mode = _pm_state.get("mode", "MANUAL")
_input_price = safe_val(d, "Main Product Price", 0.0)
if _pm_mode != "MANUAL" and _pm_state.get("solved_price"):
    base_price = float(_pm_state["solved_price"])
elif _pm_state.get("manual_price") is not None:
    base_price = float(_pm_state["manual_price"])
else:
    base_price = _input_price

# TIC accuracy bounds
_tic_lo_pct = safe_val(d, "TIC Lower Pct", 0.0)
_tic_hi_pct = safe_val(d, "TIC Upper Pct", 0.0)
_has_bounds = (_tic_lo_pct != 0 and _tic_hi_pct != 0)
_cm_lo = 1.0 + (_tic_lo_pct / 100.0) if _has_bounds else 0.75
_cm_hi = 1.0 + (_tic_hi_pct / 100.0) if _has_bounds else 1.40

if base_price <= 0:
    st.warning(
        "No selling price set for this scenario. Go to **Cash Flow & Analysis** "
        "to set a price or calculate MSP first.",
        icon=":material/warning:",
    )
    st.stop()

st.caption(
    f"**{scenario_name}** — Price: ${base_price:,.2f} / {d.get('Unit', 'unit')}  ·  "
    f"CAPEX: {fmt_compact(base_params['capex'])}  ·  "
    f"MARR: {base_params['marr']*100:.2f}%"
)

st.space("medium")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION A: TORNADO CHART (1D Sensitivity)
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Tornado chart — 1D perturbation", "#e6a817")

# Perturbable variables — mapping display name → params dict key
TORNADO_VARS = {
    "CAPEX":                ("capex",        "investment"),
    "Working Capital":      ("wc",           "investment"),
    "Startup Costs":        ("startup",      "investment"),
    "Product Price":        ("_price",       "revenue"),
    "Raw Material Cost":    ("rm_base",      "variable"),
    "Chem. & Utilities":    ("cu_base",      "variable"),
    "Labor":                ("labor",        "fixed"),
    "Supply & Maintenance": ("supply_maint", "fixed"),
    "MARR":                 ("marr",         "financial"),
    "Tax Rate":             ("tax_rate",     "financial"),
    "Working Hours":        ("working_hours","operational"),
    "Capacity":             ("capacity",     "operational"),
}

t_col1, t_col2, t_col3 = st.columns([2, 1, 1])
with t_col1:
    tornado_vars_sel = st.multiselect(
        "Variables to perturb",
        list(TORNADO_VARS.keys()),
        default=["CAPEX", "Product Price", "Raw Material Cost",
                 "Chem. & Utilities", "Labor", "MARR"],
        key="tornado_vars",
    )
with t_col2:
    tornado_pct = st.number_input(
        "Perturbation ±%", value=20.0, min_value=1.0, max_value=80.0,
        step=5.0, key="tornado_pct",
    )
with t_col3:
    tornado_kpi = st.selectbox(
        "Target KPI", ["NPV", "IRR"], key="tornado_kpi",
    )

if tornado_vars_sel and st.button("Run tornado analysis", key="btn_tornado",
                                   type="primary"):
    delta = tornado_pct / 100.0
    results = []

    for var_name in tornado_vars_sel:
        param_key, _ = TORNADO_VARS[var_name]

        if param_key == "_price":
            # Perturb price directly
            price_lo = base_price * (1 - delta)
            price_hi = base_price * (1 + delta)
            if tornado_kpi == "NPV":
                val_lo = npv_at_price(base_params, price_lo)
                val_hi = npv_at_price(base_params, price_hi)
            else:
                cfs_lo, _, _ = build_cf_arrays(base_params, price_lo)
                cfs_hi, _, _ = build_cf_arrays(base_params, price_hi)
                val_lo = irr_from_cfs(cfs_lo)
                val_hi = irr_from_cfs(cfs_hi)
        else:
            base_val = base_params[param_key]
            for mult, label in [(1 - delta, "lo"), (1 + delta, "hi")]:
                p_mod = dict(base_params)
                p_mod[param_key] = base_val * mult
                if tornado_kpi == "NPV":
                    v = npv_at_price(p_mod, base_price)
                else:
                    cfs_v, _, _ = build_cf_arrays(p_mod, base_price)
                    v = irr_from_cfs(cfs_v)
                if label == "lo":
                    val_lo = v
                else:
                    val_hi = v

        results.append((var_name, val_lo, val_hi))

    # Compute base KPI
    if tornado_kpi == "NPV":
        base_kpi = npv_at_price(base_params, base_price)
    else:
        cfs_b, _, _ = build_cf_arrays(base_params, base_price)
        base_kpi = irr_from_cfs(cfs_b)

    if base_kpi is None:
        st.error("Could not compute base IRR.")
    else:
        # Sort by impact (absolute spread)
        valid = [(n, lo, hi) for n, lo, hi in results if lo is not None and hi is not None]
        valid.sort(key=lambda x: abs((x[2] or 0) - (x[1] or 0)))

        var_names = [v[0] for v in valid]
        lo_vals = [v[1] for v in valid]
        hi_vals = [v[2] for v in valid]

        if tornado_kpi == "NPV":
            lo_deltas = [(v - base_kpi) / 1e6 for v in lo_vals]
            hi_deltas = [(v - base_kpi) / 1e6 for v in hi_vals]
            unit = "MMUSD"
            base_disp = f"{base_kpi/1e6:.2f}"
        else:
            lo_deltas = [(v - base_kpi) * 100 for v in lo_vals]
            hi_deltas = [(v - base_kpi) * 100 for v in hi_vals]
            unit = "pp"
            base_disp = f"{base_kpi*100:.2f}%"

        fig_tornado = go.Figure()
        fig_tornado.add_trace(go.Bar(
            y=var_names,
            x=lo_deltas,
            orientation="h",
            name=f"−{tornado_pct:.0f}%",
            marker=dict(color="#f85149", line_width=0),
            text=[f"{v:+.2f}" for v in lo_deltas],
            textposition="auto",
            textfont=dict(family="DM Mono", size=10),
        ))
        fig_tornado.add_trace(go.Bar(
            y=var_names,
            x=hi_deltas,
            orientation="h",
            name=f"+{tornado_pct:.0f}%",
            marker=dict(color="#3fb950", line_width=0),
            text=[f"{v:+.2f}" for v in hi_deltas],
            textposition="auto",
            textfont=dict(family="DM Mono", size=10),
        ))
        fig_tornado.add_vline(x=0, line_color="#484f58", line_width=1)
        fig_tornado.update_layout(
            **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("yaxis",)},
            barmode="overlay",
            height=max(280, len(valid) * 45),
            yaxis=dict(
                tickfont=dict(family="DM Sans", size=11, color="#c9d1d9"),
                autorange="reversed" if tornado_kpi == "NPV" else True,
            ),
            xaxis_title=f"Δ {tornado_kpi} ({unit})",
            title=dict(
                text=f"Tornado — {tornado_kpi} sensitivity (base = {base_disp})",
                font=dict(size=13, color="#c9d1d9"),
            ),
        )
        st.plotly_chart(fig_tornado, use_container_width=True)

st.space("large")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION B: VIABILITY SURFACE (2D Sweep)
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Viability surface — 2D parameter sweep", "#58a6ff")

SURFACE_VARS = {
    "Product Price (USD/unit)":   "_price",
    "CAPEX Multiplier":           "_capex_mult",
    "CAPEX (USD)":                "capex",
    "OPEX — Raw Materials":       "rm_base",
    "OPEX — Chem. & Utilities":   "cu_base",
    "MARR":                       "marr",
    "Working Hours":              "working_hours",
    "Tax Rate":                   "tax_rate",
    "Capacity":                   "capacity",
}

sc1, sc2, sc3 = st.columns(3)
with sc1:
    x_var_label = st.selectbox("X-axis variable", list(SURFACE_VARS.keys()),
                               index=0, key="surf_x")
    x_key = SURFACE_VARS[x_var_label]

    if x_key == "_price":
        x_base = base_price
    elif x_key == "_capex_mult":
        x_base = 1.0
    else:
        x_base = base_params[x_key]
    x_lo = st.number_input("X min", value=x_base * 0.5, key="surf_x_lo")
    x_hi = st.number_input("X max", value=x_base * 1.5, key="surf_x_hi")

with sc2:
    y_var_label = st.selectbox("Y-axis variable", list(SURFACE_VARS.keys()),
                               index=2, key="surf_y")
    y_key = SURFACE_VARS[y_var_label]

    if y_key == "_price":
        y_base = base_price
    elif y_key == "_capex_mult":
        y_base = 1.0
    else:
        y_base = base_params[y_key]
    y_lo = st.number_input("Y min", value=y_base * 0.5, key="surf_y_lo")
    y_hi = st.number_input("Y max", value=y_base * 1.5, key="surf_y_hi")

with sc3:
    surf_kpi = st.selectbox("Target KPI", ["NPV", "IRR"], key="surf_kpi")
    surf_criterion = st.selectbox("Viability criterion", [
        "NPV > 0", "IRR > MARR", "Custom threshold",
    ], key="surf_crit")
    if surf_criterion == "Custom threshold":
        surf_threshold = st.number_input("Threshold value", value=0.0, key="surf_thresh")
    else:
        surf_threshold = 0.0 if "NPV" in surf_criterion else base_params["marr"]
    surf_resolution = st.slider("Grid resolution", 20, 80, 40, step=10, key="surf_res")
    surf_3d = st.toggle("3D surface view", value=False, key="surf_3d")

if st.button("Generate viability surface", key="btn_surface", type="primary"):
    x_vals = np.linspace(x_lo, x_hi, surf_resolution)
    y_vals = np.linspace(y_lo, y_hi, surf_resolution)
    Z = np.zeros((surf_resolution, surf_resolution))

    progress = st.progress(0, text="Computing surface…")
    total_cells = surf_resolution * surf_resolution

    for i, yv in enumerate(y_vals):
        for j, xv in enumerate(x_vals):
            p_mod = dict(base_params)
            price_v = base_price
            cm_v = 1.0

            # Apply X
            if x_key == "_price":
                price_v = xv
            elif x_key == "_capex_mult":
                cm_v = xv
            else:
                p_mod[x_key] = xv

            # Apply Y
            if y_key == "_price":
                price_v = yv
            elif y_key == "_capex_mult":
                cm_v = yv
            else:
                p_mod[y_key] = yv

            if surf_kpi == "NPV":
                Z[i, j] = npv_at_price(p_mod, price_v, cm_v) / 1e6
            else:
                cfs_v, _, _ = build_cf_arrays(p_mod, price_v, cm_v)
                irr_v = irr_from_cfs(cfs_v)
                Z[i, j] = irr_v * 100 if irr_v is not None else -100.0

        progress.progress((i + 1) / surf_resolution, text=f"Row {i+1}/{surf_resolution}")
    progress.empty()

    # Threshold for contour
    if surf_criterion == "NPV > 0":
        thresh_z = 0.0
    elif surf_criterion == "IRR > MARR":
        thresh_z = base_params["marr"] * 100
    else:
        thresh_z = surf_threshold

    if surf_3d:
        fig_surf = go.Figure(go.Surface(
            x=x_vals, y=y_vals, z=Z,
            colorscale=[[0, "#f85149"], [0.5, "#21262d"], [1, "#3fb950"]],
            cmid=thresh_z,
            contours_z=dict(
                show=True, usecolormap=True,
                highlightcolor="#e6a817", project_z=True,
            ),
            hovertemplate=(
                f"{x_var_label}: %{{x:.2f}}<br>"
                f"{y_var_label}: %{{y:.2f}}<br>"
                f"{surf_kpi}: %{{z:.2f}}<extra></extra>"
            ),
        ))
        fig_surf.update_layout(
            scene=dict(
                xaxis_title=x_var_label,
                yaxis_title=y_var_label,
                zaxis_title=f"{surf_kpi} ({'MMUSD' if surf_kpi == 'NPV' else '%'})",
                bgcolor="#0d1117",
                xaxis=dict(gridcolor="#21262d", color="#8b949e"),
                yaxis=dict(gridcolor="#21262d", color="#8b949e"),
                zaxis=dict(gridcolor="#21262d", color="#8b949e"),
            ),
            paper_bgcolor="#0d1117",
            font=dict(color="#c9d1d9", family="DM Sans"),
            margin=dict(l=0, r=0, t=30, b=0),
            height=500,
        )
    else:
        fig_surf = go.Figure(go.Contour(
            x=x_vals, y=y_vals, z=Z,
            colorscale=[[0, "#f85149"], [0.5, "#21262d"], [1, "#3fb950"]],
            cmid=thresh_z,
            contours=dict(
                showlabels=True,
                labelfont=dict(size=10, color="#c9d1d9"),
            ),
            line=dict(width=1),
            hovertemplate=(
                f"{x_var_label}: %{{x:.2f}}<br>"
                f"{y_var_label}: %{{y:.2f}}<br>"
                f"{surf_kpi}: %{{z:.2f}}<extra></extra>"
            ),
            colorbar=dict(
                title=f"{surf_kpi} ({'MMUSD' if surf_kpi == 'NPV' else '%'})",
                tickfont=dict(color="#8b949e", size=10),
                titlefont=dict(color="#8b949e", size=11),
            ),
        ))
        # Add viability boundary
        fig_surf.add_contour(
            x=x_vals, y=y_vals, z=Z,
            contours=dict(
                type="constraint", operation=">=", value=thresh_z,
                showlabels=False,
            ),
            line=dict(color="#e6a817", width=2, dash="dash"),
            fillcolor="rgba(230,168,23,0.08)",
            showscale=False,
            hoverinfo="skip",
            name="Viable zone",
        )
        # Mark base case point
        if x_key == "_price":
            x_base_pt = base_price
        elif x_key == "_capex_mult":
            x_base_pt = 1.0
        else:
            x_base_pt = base_params[x_key]
        if y_key == "_price":
            y_base_pt = base_price
        elif y_key == "_capex_mult":
            y_base_pt = 1.0
        else:
            y_base_pt = base_params[y_key]

        fig_surf.add_trace(go.Scatter(
            x=[x_base_pt], y=[y_base_pt],
            mode="markers+text",
            marker=dict(size=10, color="#e6a817", symbol="diamond"),
            text=["Base"],
            textposition="top center",
            textfont=dict(size=10, color="#e6a817"),
            showlegend=False,
        ))
        fig_surf.update_layout(
            **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("yaxis", "xaxis")},
            xaxis=dict(title=x_var_label, gridcolor="#21262d",
                       tickfont=dict(family="DM Mono", size=10, color="#c9d1d9")),
            yaxis=dict(title=y_var_label, gridcolor="#21262d",
                       tickfont=dict(family="DM Mono", size=10, color="#c9d1d9")),
            height=480,
        )

    st.plotly_chart(fig_surf, use_container_width=True)

    # Viability percentage
    viable_pct = np.mean(Z >= thresh_z) * 100
    vc1, vc2, vc3 = st.columns(3)
    with vc1:
        kpi_card("Viable parameter space", f"{viable_pct:.1f}%",
                 "#3fb950" if viable_pct > 50 else "#f85149")
    with vc2:
        kpi_card(f"{surf_kpi} range",
                 f"{np.min(Z):.1f} to {np.max(Z):.1f}",
                 "#58a6ff")
    with vc3:
        kpi_card("Grid cells computed", f"{total_cells:,}", "#8b949e")

st.space("large")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION C: MONTE CARLO SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════
section_header("Monte Carlo simulation", "#bc8cff")

st.caption(
    "Assign probability distributions to key drivers. The simulation runs for "
    "all three TIC scenarios: lower bound, base case, and upper bound."
)

# Distribution configuration
MC_VARS = {
    "CAPEX":              ("capex",        base_params["capex"]),
    "Product Price":      ("product_price", base_price),
    "Raw Material Cost":  ("rm_base",       base_params["rm_base"]),
    "Chem. & Utilities":  ("cu_base",       base_params["cu_base"]),
    "Working Hours":      ("working_hours", base_params["working_hours"]),
    "MARR":               ("marr",          base_params["marr"]),
}

# Initialize MC state
if "mc_dists" not in st.session_state:
    st.session_state.mc_dists = {}

mc_enabled = {}
mc_dists = {}

st.markdown("**Configure distributions**")

mc_cols = st.columns(3)
for idx, (var_label, (param_key, base_val)) in enumerate(MC_VARS.items()):
    with mc_cols[idx % 3]:
        enabled = st.checkbox(f"Vary: {var_label}", value=(var_label in ["CAPEX", "Product Price"]),
                              key=f"mc_en_{var_label}")
        if enabled:
            dist_type = st.selectbox(
                f"Distribution", ["Triangular", "Normal"],
                key=f"mc_dist_{var_label}",
                label_visibility="collapsed",
            )
            if dist_type == "Triangular":
                default_spread = 0.2
                lo = st.number_input(f"Low", value=base_val * (1 - default_spread),
                                     key=f"mc_lo_{var_label}")
                hi = st.number_input(f"High", value=base_val * (1 + default_spread),
                                     key=f"mc_hi_{var_label}")
                mc_dists[param_key] = {"type": "triangular", "low": lo, "mode": base_val, "high": hi}
            else:
                mean = st.number_input(f"Mean", value=base_val, key=f"mc_mean_{var_label}")
                std = st.number_input(f"Std dev", value=base_val * 0.1,
                                      key=f"mc_std_{var_label}")
                mc_dists[param_key] = {"type": "normal", "mean": mean, "std": std}
            mc_enabled[var_label] = True

mc_n_col, mc_btn_col = st.columns([1, 2])
with mc_n_col:
    mc_iterations = st.select_slider(
        "Iterations",
        options=[1000, 5000, 10000, 25000, 50000],
        value=10000,
        key="mc_n_iter",
    )

with mc_btn_col:
    st.space("small")
    run_mc = st.button(
        f"Run Monte Carlo ({mc_iterations:,} iterations × 3 TIC scenarios)",
        key="btn_mc", type="primary",
        disabled=(len(mc_dists) == 0),
    )

if run_mc and mc_dists:
    tic_scenarios = [
        ("Lower TIC", _cm_lo),
        ("Base case", 1.0),
        ("Upper TIC", _cm_hi),
    ]
    tic_colors = ["#3fb950", "#58a6ff", "#f85149"]

    all_results = {}
    with st.spinner(f"Running {mc_iterations:,} iterations × {len(tic_scenarios)} TIC scenarios…"):
        for label, cm in tic_scenarios:
            all_results[label] = monte_carlo_npv_irr(
                base_params, base_price, mc_dists,
                n_iterations=mc_iterations, capex_mult=cm,
            )

    # ── KPI Summary ──────────────────────────────────────────────────────
    section_header("Simulation results", "#bc8cff")

    kpi_cols = st.columns(len(tic_scenarios))
    for col, (label, cm), color in zip(kpi_cols, tic_scenarios, tic_colors):
        res = all_results[label]
        with col:
            kpi_card(
                f"P(NPV > 0) — {label}",
                f"{res['p_npv_positive']*100:.1f}%",
                color,
            )
            if res["p_irr_above_marr"] is not None:
                kpi_card(
                    f"P(IRR > MARR) — {label}",
                    f"{res['p_irr_above_marr']*100:.1f}%",
                    color,
                )

    st.space("small")

    # ── NPV Histogram ────────────────────────────────────────────────────
    section_header("NPV distribution", "#58a6ff")
    fig_npv_hist = go.Figure()
    for (label, _), color in zip(tic_scenarios, tic_colors):
        res = all_results[label]
        npv_mm = res["npv"] / 1e6
        fig_npv_hist.add_trace(go.Histogram(
            x=npv_mm, name=label,
            marker=dict(color=color, line=dict(width=0)),
            opacity=0.55,
            nbinsx=60,
        ))
    fig_npv_hist.add_vline(x=0, line_color="#e6a817", line_width=2, line_dash="dash")
    fig_npv_hist.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("yaxis",)},
        barmode="overlay",
        xaxis_title="NPV (MMUSD)",
        yaxis=dict(title="Frequency", gridcolor="#21262d",
                   tickfont=dict(family="DM Mono", size=10)),
        height=350,
    )
    st.plotly_chart(fig_npv_hist, use_container_width=True)

    # ── NPV CDF ──────────────────────────────────────────────────────────
    fig_cdf = go.Figure()
    for (label, _), color in zip(tic_scenarios, tic_colors):
        res = all_results[label]
        npv_sorted = np.sort(res["npv"]) / 1e6
        cdf = np.arange(1, len(npv_sorted) + 1) / len(npv_sorted)
        fig_cdf.add_trace(go.Scatter(
            x=npv_sorted, y=cdf, mode="lines", name=label,
            line=dict(color=color, width=2),
        ))
    fig_cdf.add_vline(x=0, line_color="#e6a817", line_width=1, line_dash="dash")
    fig_cdf.add_hline(y=0.5, line_color="#484f58", line_width=1, line_dash="dot")
    fig_cdf.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("yaxis",)},
        xaxis_title="NPV (MMUSD)",
        yaxis=dict(title="Cumulative probability", gridcolor="#21262d",
                   tickformat=".0%", tickfont=dict(family="DM Mono", size=10)),
        height=320,
    )
    st.plotly_chart(fig_cdf, use_container_width=True)

    # ── IRR Distribution ─────────────────────────────────────────────────
    section_header("IRR distribution", "#e6a817")
    fig_irr = go.Figure()
    for (label, _), color in zip(tic_scenarios, tic_colors):
        res = all_results[label]
        if len(res["irr"]) > 0:
            fig_irr.add_trace(go.Histogram(
                x=res["irr"] * 100, name=label,
                marker=dict(color=color, line=dict(width=0)),
                opacity=0.55,
                nbinsx=60,
            ))
    fig_irr.add_vline(
        x=base_params["marr"] * 100,
        line_color="#e6a817", line_width=2, line_dash="dash",
        annotation_text="MARR",
        annotation_font=dict(size=10, color="#e6a817"),
    )
    fig_irr.update_layout(
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("yaxis",)},
        barmode="overlay",
        xaxis_title="IRR (%)",
        yaxis=dict(title="Frequency", gridcolor="#21262d",
                   tickfont=dict(family="DM Mono", size=10)),
        height=320,
    )
    st.plotly_chart(fig_irr, use_container_width=True)

    # ── Percentile Table ─────────────────────────────────────────────────
    section_header("Percentile summary", "#8b949e")

    def _f_mm(v):
        return f"${v/1e6:,.2f}M" if v is not None else "—"

    def _f_pct(v):
        return f"{v*100:.2f}%" if v is not None else "—"

    rows_html = ""
    for (label, _), color in zip(tic_scenarios, tic_colors):
        res = all_results[label]
        rows_html += (
            f'<tr style="border-bottom:1px solid #21262d">'
            f'<td style="padding:.4rem .6rem;font-weight:600;color:{color}">{label}</td>'
            f'<td style="padding:.4rem .6rem;text-align:right;font-family:DM Mono,monospace">'
            f'{_f_mm(res["npv_p10"])}</td>'
            f'<td style="padding:.4rem .6rem;text-align:right;font-family:DM Mono,monospace">'
            f'{_f_mm(res["npv_p50"])}</td>'
            f'<td style="padding:.4rem .6rem;text-align:right;font-family:DM Mono,monospace">'
            f'{_f_mm(res["npv_p90"])}</td>'
            f'<td style="padding:.4rem .6rem;text-align:right;font-family:DM Mono,monospace">'
            f'{_f_pct(res["irr_p10"])}</td>'
            f'<td style="padding:.4rem .6rem;text-align:right;font-family:DM Mono,monospace">'
            f'{_f_pct(res["irr_p50"])}</td>'
            f'<td style="padding:.4rem .6rem;text-align:right;font-family:DM Mono,monospace">'
            f'{_f_pct(res["irr_p90"])}</td>'
            f'<td style="padding:.4rem .6rem;text-align:right;font-family:DM Mono,monospace">'
            f'{res["p_npv_positive"]*100:.1f}%</td>'
            f'</tr>'
        )

    st.markdown(f"""
    <div style="overflow-x:auto;border:1px solid #21262d;border-radius:6px;background:#161b22">
    <table style="width:100%;border-collapse:collapse;font-size:.82rem">
    <thead><tr style="border-bottom:2px solid #21262d">
      <th style="padding:.5rem .6rem;text-align:left;color:#8b949e">Scenario</th>
      <th style="padding:.5rem .6rem;text-align:right;color:#8b949e">NPV P10</th>
      <th style="padding:.5rem .6rem;text-align:right;color:#8b949e">NPV P50</th>
      <th style="padding:.5rem .6rem;text-align:right;color:#8b949e">NPV P90</th>
      <th style="padding:.5rem .6rem;text-align:right;color:#8b949e">IRR P10</th>
      <th style="padding:.5rem .6rem;text-align:right;color:#8b949e">IRR P50</th>
      <th style="padding:.5rem .6rem;text-align:right;color:#8b949e">IRR P90</th>
      <th style="padding:.5rem .6rem;text-align:right;color:#8b949e">P(NPV&gt;0)</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)
