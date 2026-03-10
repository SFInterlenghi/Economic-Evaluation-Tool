import streamlit as st
import pandas as pd

# Configure the page layout
st.set_page_config(page_title="ISI-Tool PoC", layout="wide")

st.title("ISI-Tool: Economic Evaluation Dashboard")
st.markdown("Enter your parameters in the sidebar to build and compare scenarios.")

# Initialize a dictionary in session state to hold our scenarios
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}

# --- INPUT FORM (SIDEBAR) ---
with st.sidebar:
    st.header("Scenario Inputs")
    
    # Dynamic default name based on current scenario count
    default_name = f"Scenario {len(st.session_state.scenarios) + 1}"
    scenario_name = st.text_input("Scenario Name", value=default_name)
    
    st.subheader("Capital & Operating Costs")
    capex = st.number_input("CAPEX ($M)", min_value=0.0, value=150.0, step=5.0)
    opex = st.number_input("OPEX Fixed ($M/yr)", min_value=0.0, value=15.0, step=1.0)
    
    st.subheader("Process Parameters")
    prod_volume = st.number_input("Production Volume (kTA)", min_value=0.0, value=100.0, step=10.0)
    feedstock_cost = st.number_input("Feedstock Cost ($/ton)", min_value=0.0, value=300.0, step=10.0)
    product_price = st.number_input("Product Selling Price ($/ton)", min_value=0.0, value=800.0, step=10.0)
    
    st.subheader("Financials")
    discount_rate = st.slider("Discount Rate (%)", min_value=0.0, max_value=25.0, value=10.0, step=0.5)
    
    # Add Scenario Button
    if st.button("Add Scenario", type="primary"):
        if len(st.session_state.scenarios) >= 40:
            st.error("Maximum limit of 40 scenarios reached.")
        elif scenario_name in st.session_state.scenarios:
            st.error("A scenario with this name already exists. Please choose a different name.")
        else:
            # Save the inputs to the session state dictionary
            st.session_state.scenarios[scenario_name] = {
                "CAPEX ($M)": capex,
                "OPEX Fixed ($M/yr)": opex,
                "Production Volume (kTA)": prod_volume,
                "Feedstock Cost ($/ton)": feedstock_cost,
                "Product Price ($/ton)": product_price,
                "Discount Rate (%)": discount_rate
            }
            st.success(f"Added '{scenario_name}' successfully!")
            st.rerun()

    # Clear Button
    if st.button("Clear All Scenarios"):
        st.session_state.scenarios = {}
        st.rerun()

# --- MAIN DISPLAY AREA ---
st.header("Scenario Comparison")

if st.session_state.scenarios:
    # Convert the dictionary of scenarios into a Pandas DataFrame
    # Pandas automatically aligns dictionary keys as column headers when structured this way, 
    # giving us the side-by-side view you requested.
    df_scenarios = pd.DataFrame(st.session_state.scenarios)
    
    # Display as an interactive table
    st.dataframe(
        df_scenarios.style.format("{:.2f}"), 
        use_container_width=True,
        height=400
    )
else:
    st.info("No scenarios defined yet. Please add at least one scenario using the sidebar.")
