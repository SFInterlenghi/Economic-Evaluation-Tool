import streamlit as st
import pandas as pd

st.set_page_config(page_title="Input Configuration", layout="wide")

st.title("Scenario Configuration & Inputs")
st.markdown("Define the parameters for your scenario. Type an existing Scenario Name to load and edit its data.")

# Initialize session state for scenarios
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}

# --- 1. SCENARIO SELECTION ---
st.header("1. Scenario Name")
scenario_name = st.text_input(
    "Scenario Name (Type a new name to create, or an existing name to edit)", 
    help="Press Enter after typing to load existing data or clear the board for a new scenario."
)

# Fetch existing data if the scenario already exists, otherwise return an empty dictionary
existing_data = st.session_state.scenarios.get(scenario_name, {})

st.divider()

# --- 2. BASIC INFORMATION ---
st.header("2. Basic Information")

col1, col2 = st.columns(2)
with col1:
    # Uses existing data if found, otherwise defaults to an empty string ""
    main_product = st.text_input("Main Product Name", value=existing_data.get("Product Name", ""))

with col2:
    allowed_units = ["g", "kg", "t", "mL", "L", "m³", "kWh", "MWh", "GWh", "MMBtu"]
    
    saved_unit = existing_data.get("Unit", "kg")
    unit_index = allowed_units.index(saved_unit) if saved_unit in allowed_units else 1
    
    product_unit = st.selectbox("Main product unit", allowed_units, index=unit_index)
    
    capacity_label = f"Main product capacity ({product_unit}/year)"
    # Uses existing data if found, otherwise defaults to None (empty box)
    saved_capacity = existing_data.get("Capacity", None)
    product_capacity = st.number_input(capacity_label, min_value=0.0, value=saved_capacity, step=1.0)

st.divider()

# --- 3. PROCESS VARIABLES ---
st.header("3. Process Variables")
st.markdown("Add your process variables below. Click the **+** at the bottom of the table to add more rows.")

if "Process Variables" in existing_data and existing_data["Process Variables"]:
    df_vars = pd.DataFrame(existing_data["Process Variables"])
else:
    # Defaults to an empty template if it's a new scenario
    df_vars = pd.DataFrame(columns=["Variable Name", "Unit", "Value"])

edited_process_vars = st.data_editor(
    df_vars,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Variable Name": st.column_config.TextColumn("Variable Name", required=True),
        "Unit": st.column_config.TextColumn("Unit", required=True),
        "Value": st.column_config.NumberColumn("Value", required=True),
    }
)

st.divider()

# --- SAVE BUTTON & LOGIC ---
if st.button("Save / Update Scenario", type="primary"):
    if not scenario_name:
        st.error("Please provide a Scenario Name before saving.")
    elif product_capacity is None:
        st.error("Please provide a Main Product Capacity before saving.")
    else:
        valid_vars = edited_process_vars.dropna(how="all")
        
        is_update = scenario_name in st.session_state.scenarios
        
        # Save or overwrite the inputs without the Project Title
        st.session_state.scenarios[scenario_name] = {
            "Product Name": main_product,
            "Unit": product_unit,
            "Capacity": product_capacity,
            "Capacity Label": f"{product_capacity} {product_unit}/year",
            "Process Variables": valid_vars.to_dict(orient="records")
        }
        
        if is_update:
            st.success(f"Scenario '{scenario_name}' successfully updated!")
        else:
            st.success(f"Scenario '{scenario_name}' successfully saved!")

# --- SCENARIO COMPARISON TABLE ---
st.header("Compiled Scenarios")

if st.session_state.scenarios:
    summary_data = []
    for s_name, data in st.session_state.scenarios.items():
        summary_data.append({
            "Scenario Name": s_name,
            "Product": data["Product Name"],
            "Capacity": data["Capacity Label"],
            "Total Process Variables": len(data["Process Variables"])
        })
    
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
    
    if st.button("Clear All Data", type="secondary"):
        st.session_state.scenarios = {}
        st.rerun()
else:
    st.info("No scenarios defined yet.")
