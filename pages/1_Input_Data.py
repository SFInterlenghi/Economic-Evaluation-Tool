import streamlit as st
import pandas as pd

st.set_page_config(page_title="Input Configuration", layout="wide")

st.title("Scenario Configuration & Inputs")
st.markdown("Define the parameters for your scenario. Click **Save Scenario** at the bottom to lock it in.")

# Initialize session state for scenarios
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}

# --- 1. BASIC INFORMATION ---
st.header("1. Basic Information")

col1, col2 = st.columns(2)
with col1:
    project_title = st.text_input("Project Title")
    scenario_name = st.text_input("Scenario Name")
    main_product = st.text_input("Main Product Name")

with col2:
    # Predefined units
    allowed_units = ["g", "kg", "t", "mL", "L", "m^3", "kWh", "MWh", "GWh", "MMBtu"]
    product_unit = st.selectbox("Main product unit", allowed_units)
    
    # Dynamic label based on the unit chosen above
    capacity_label = f"Main product capacity ({product_unit}/year)"
    product_capacity = st.number_input(capacity_label, min_value=0.0, step=1.0)

st.divider()

# --- 2. PROCESS VARIABLES ---
st.header("2. Process Variables")
st.markdown("Add your process variables below. Click the **+** at the bottom of the table to add more rows.")

# Initialize an empty dataframe to act as the template for our interactive table
if "process_vars_template" not in st.session_state:
    st.session_state.process_vars_template = pd.DataFrame(
        columns=["Variable Name", "Unit", "Value"]
    )

# st.data_editor creates the interactive Excel-like table
edited_process_vars = st.data_editor(
    st.session_state.process_vars_template,
    num_rows="dynamic", # Allows the user to add/delete rows
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
if st.button("Save Scenario", type="primary"):
    if not scenario_name:
        st.error("Please provide a Scenario Name before saving.")
    elif scenario_name in st.session_state.scenarios:
        st.error(f"A scenario named '{scenario_name}' already exists.")
    else:
        # Clean up the table to remove any completely empty rows the user might have left
        valid_vars = edited_process_vars.dropna(how="all")
        
        # Save all inputs into the session state dictionary
        st.session_state.scenarios[scenario_name] = {
            "Project Title": project_title,
            "Product Name": main_product,
            "Unit": product_unit,
            "Capacity": product_capacity,
            "Capacity Label": f"{product_capacity} {product_unit}/year", # Storing the formatted string for easy display
            "Process Variables": valid_vars.to_dict(orient="records") # Saves the table as a neat list of dictionaries
        }
        st.success(f"Scenario '{scenario_name}' saved successfully!")

# --- SCENARIO COMPARISON TABLE ---
st.header("Compiled Scenarios")

if st.session_state.scenarios:
    # Build a quick summary table to show the saved scenarios
    summary_data = []
    for s_name, data in st.session_state.scenarios.items():
        summary_data.append({
            "Scenario Name": s_name,
            "Project Title": data["Project Title"],
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
