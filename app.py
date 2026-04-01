"""
SENAI - TOOL  Strategic Economic Navigator for Advanced Investment
Main entry point with navigation.
"""
import streamlit as st
import json
import os

# --- INITIALIZE HARDCODED VALIDATION CASES ---
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}

# List of your validation files
validation_files = ["ATJ_hardcoded.json", "CADO_hardcoded.json"]

for file_name in validation_files:
    if os.path.exists(file_name):
        try:
            with open(file_name, "r") as f:
                data = json.load(f)
                # These files contain a dictionary like {"ATJ": {...}}
                # We merge them into our main scenarios dictionary
                st.session_state.scenarios.update(data)
        except Exception as e:
            st.error(f"Error loading {file_name}: {e}")

st.set_page_config(
    page_title="ISI-Tool",
    page_icon=":material/precision_manufacturing:",
    layout="wide",
)

# ── Global session state init ─────────────────────────────────────────────────
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}
if "table_key" not in st.session_state:
    st.session_state.table_key = 0

# ── Navigation ────────────────────────────────────────────────────────────────
page = st.navigation(
    {
        "": [
            st.Page("app_pages/home.py", title="Home", icon=":material/home:"),
        ],
        "Configuration": [
            st.Page("app_pages/input_data.py", title="Input Data", icon=":material/tune:"),
            st.Page("app_pages/database.py", title="Database", icon=":material/database:"),
        ],
        "Analysis": [
            st.Page("app_pages/investment_costs.py", title="Investment Costs", icon=":material/account_balance:"),
            st.Page("app_pages/operating_expenses.py", title="Operating Expenses", icon=":material/payments:"),
            st.Page("app_pages/cash_flow.py", title="Cash Flow & Analysis", icon=":material/trending_up:"),
        ],
        "Decision Support": [
            st.Page("app_pages/scenario_comparison.py", title="Scenario Comparison", icon=":material/compare_arrows:"),
            st.Page("app_pages/risk_sensitivity.py", title="Risk & Sensitivity", icon=":material/ssid_chart:"),
            st.Page("app_pages/multi_criteria.py", title="Multi-Criteria Analysis", icon=":material/balance:"),
        ],
    },
    position="sidebar",
)

# ── Sidebar footer ───────────────────────────────────────────────────────────
with st.sidebar:
    st.caption("SENAI-Tool v0.1")
    n = len(st.session_state.scenarios)
    if n:
        st.badge(f"{n} scenario{'s' if n != 1 else ''} saved", icon=":material/check_circle:", color="green")

page.run()
