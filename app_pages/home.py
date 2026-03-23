"""ISI-Tool — Home page."""
import streamlit as st
from utils.ui import inject_css

inject_css()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("### ISI-Tool")
st.caption("CHEMICAL PLANT ECONOMIC EVALUATION")

st.space("medium")

col1, col2 = st.columns([3, 2], vertical_alignment="center")

with col1:
    st.markdown(
        "A techno-economic analysis platform for early-stage chemical process "
        "evaluation. Configure scenarios, compute CAPEX/OPEX breakdowns, and "
        "run cash flow analyses — all driven by industry-standard cost estimation "
        "methodologies."
    )
    st.space("small")
    st.markdown(
        "**Start** by navigating to **Input Data** in the sidebar to define your "
        "first scenario, or explore the **Database** to review reference tables."
    )

with col2:
    n = len(st.session_state.get("scenarios", {}))
    with st.container(border=True):
        st.metric("Scenarios saved", n, border=True)

st.space("large")

# ── Workflow overview ─────────────────────────────────────────────────────────
st.markdown("#### Workflow")

c1, c2, c3, c4 = st.columns(4)
steps = [
    (c1, ":material/tune:", "1. Configure", "Define product, capacity, equipment costs, and process parameters."),
    (c2, ":material/account_balance:", "2. Investment", "Review CAPEX build-up, waterfall charts, and scenario comparisons."),
    (c3, ":material/payments:", "3. OPEX", "Analyze variable and fixed cost structures with Sankey diagrams."),
    (c4, ":material/trending_up:", "4. Cash Flow", "Adjust prices, compute NPV, IRR, and sensitivity analysis."),
]
for col, icon, title, desc in steps:
    with col:
        with st.container(border=True):
            st.markdown(f"{icon} **{title}**")
            st.caption(desc)

st.space("large")

# ── Quick stats if scenarios exist ────────────────────────────────────────────
scenarios = st.session_state.get("scenarios", {})
if scenarios:
    st.markdown("#### Saved scenarios")
    cols = st.columns(min(len(scenarios), 4))
    for i, (name, d) in enumerate(scenarios.items()):
        with cols[i % len(cols)]:
            tic = d.get("Total Investment", 0)
            opex = d.get("Total OPEX", 0)
            prod = d.get("Product Name", "—")
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(prod)
                st.metric("TIC", f"${tic:,.0f}" if tic else "—", border=True)
