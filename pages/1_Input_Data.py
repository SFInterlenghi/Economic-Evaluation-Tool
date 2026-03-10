import streamlit as st
import pandas as pd

st.set_page_config(page_title="Input Configuration", layout="wide")

st.title("Scenario Configuration & Inputs")
st.markdown("Define the parameters for each scenario below.")

# Initialize session state for scenarios
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}

# --- INPUT FORM ---
with st.form("scenario_input_form", clear_on_submit=True):
    
    # 1. Basic Information
    st.subheader("1. Basic Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        scenario_name = st.text_input("Scenario Name/ID", placeholder="e.g., Base Case A")
    with col2:
        project_location = st.text_input("Project Location")
    with col3:
        currency = st.selectbox("Currency", ["USD ($)", "BRL (R$)", "EUR (€)"])

    st.divider()

    # 2. Scenario and Product Information
    st.subheader("2. Scenario and Product Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        plant_life = st.number_input("Plant Lifespan (Years)", min_value=1, value=20)
        construction_time = st.number_input("Construction Time (Years)", min_value=0, value=2)
    with col2:
        main_product = st.text_input("Main Product Name")
        target_production = st.number_input("Target Production (kTA)", min_value=0.0, value=100.0)
    with col3:
        product_price = st.number_input("Product Selling Price (/ton)", min_value=0.0, value=1200.0)
        price_escalation = st.number_input("Annual Price Escalation (%)", value=2.0)

    st.divider()

    # 3. Process Variables
    st.subheader("3. Process Variables")
    col1, col2, col3 = st.columns(3)
    with col1:
        feedstock_name = st.text_input("Primary Feedstock")
        feedstock_consumption = st.number_input("Feedstock Consumption (ton/ton product)", min_value=0.0, value=1.2)
    with col2:
        feedstock_price = st.number_input("Feedstock Price (/ton)", min_value=0.0, value=400.0)
        utility_costs = st.number_input("Total Utility Costs (/ton product)", min_value=0.0, value=50.0)
    with col3:
        operating_hours = st.number_input("Annual Operating Hours", min_value=0, max_value=8760, value=8000)
        process_yield = st.slider("Overall Process Yield (%)", min_value=0.0, max_value=100.0, value=95.0)

    st.divider()

    # 4. Investment Costs Sources (CAPEX/OPEX)
    st.subheader("4. Investment Costs Sources")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**CAPEX Parameters**")
        isbl_cost = st.number_input("ISBL (Inside Battery Limits) Cost (M)", min_value=0.0, value=80.0)
        osbl_factor = st.number_input("OSBL Factor (% of ISBL)", min_value=0.0, value=30.0)
        contingency = st.number_input("Contingency (% of Total CAPEX)", min_value=0.0, value=10.0)
    with col2:
        st.markdown("**OPEX Parameters**")
        fixed_opex = st.number_input("Fixed OPEX (M/Year)", min_value=0.0, value=15.0)
        maintenance_rate = st.number_input("Maintenance Rate (% of CAPEX/yr)", min_value=0.0, value=3.0)
        discount_rate = st.number_input("Discount Rate / WACC (%)", min_value=0.0, value=10.0)

    # Form Submit Button
    submitted = st.form_submit_button("Save Scenario to Table", type="primary")

    if submitted:
        if not scenario_name:
            st.error("Please provide a Scenario Name.")
        elif len(st.session_state.scenarios) >= 40:
            st.error("Maximum limit of 40 scenarios reached.")
        elif scenario_name in st.session_state.scenarios:
            st.error("A scenario with this name already exists.")
        else:
            # Calculate total capex rough estimate for display purposes
            total_capex = isbl_cost * (1 + osbl_factor/100) * (1 + contingency/100)

            st.session_state.scenarios[scenario_name] = {
                "Location": project_location,
                "Plant Life (yr)": plant_life,
                "Prod Target (kTA)": target_production,
                "Product Price": product_price,
                "Feedstock": feedstock_name,
                "Yield (%)": process_yield,
                "ISBL (M)": isbl_cost,
                "Total CAPEX (M)": round(total_capex, 2),
                "Fixed OPEX (M)": fixed_opex,
                "WACC (%)": discount_rate
            }
            st.success(f"Scenario '{scenario_name}' added successfully!")
            st.rerun() # Refresh to update the table below

# --- SCENARIO COMPARISON TABLE ---
st.header("Compiled Scenarios")

if st.session_state.scenarios:
    # Build dataframe and transpose it so scenarios are columns (side-by-side)
    df_scenarios = pd.DataFrame(st.session_state.scenarios)
    
    st.dataframe(
        df_scenarios, 
        use_container_width=True,
        height=350
    )
    
    # Optional: Add a button to clear all scenarios
    if st.button("Clear All Data", type="secondary"):
        st.session_state.scenarios = {}
        st.rerun()
else:
    st.info("No scenarios defined yet. Use the form above to add your first case.")
