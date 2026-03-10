import streamlit as st
import pandas as pd

st.set_page_config(page_title="Input Configuration", layout="wide")

st.title("Scenario Configuration & Inputs")
st.markdown("Define the parameters for your scenario. Type an existing Scenario Name to load it, or type a new name for a blank slate.")

# --- INITIALIZE SESSION STATE ---
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}

if "sn_input" not in st.session_state:
    st.session_state.sn_input = ""
if "mp_input" not in st.session_state:
    st.session_state.mp_input = ""
if "pu_input" not in st.session_state:
    st.session_state.pu_input = "kg"
if "pc_input" not in st.session_state:
    st.session_state.pc_input = None
if "table_key" not in st.session_state:
    st.session_state.table_key = 0

# --- THE FIX: Clear fields at the TOP of the script before widgets are drawn ---
if st.session_state.get("clear_on_next_run", False):
    st.session_state.sn_input = ""
    st.session_state.mp_input = ""
    st.session_state.pc_input = None
    st.session_state.pu_input = "kg"
    st.session_state.table_key += 1
    st.session_state.clear_on_next_run = False # Reset the flag

# Handle success messages across reruns
if "success_msg" in st.session_state and st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = "" # Clear it so it only shows once


# --- CALLBACK FUNCTION ---
def load_scenario_data():
    """Triggered instantly when the Scenario Name text box changes."""
    sn = st.session_state.sn_input
    if sn in st.session_state.scenarios:
        data = st.session_state.scenarios[sn]
        st.session_state.mp_input = data["Product Name"]
        st.session_state.pu_input = data["Unit"]
        st.session_state.pc_input = data["Capacity"]
    else:
        st.session_state.mp_input = ""
        st.session_state.pu_input = "kg"
        st.session_state.pc_input = None
    st.session_state.table_key += 1


# --- 1. SCENARIO SELECTION ---
st.header("1. Scenario Name")
scenario_name = st.text_input(
    "Scenario Name (Type a new name to create, or an existing name to edit)", 
    key="sn_input",
    on_change=load_scenario_data,
    help="Press Enter after typing to load existing data or clear the board for a new scenario."
)

st.divider()

# --- 2. BASIC INFORMATION ---
st.header("2. Basic Information")

col1, col2 = st.columns(2)
with col1:
    main_product = st.text_input("Main Product Name", key="mp_input")

with col2:
    allowed_units = ["g", "kg", "t", "mL", "L", "m³", "kWh", "MWh", "GWh", "MMBtu"]
    product_unit = st.selectbox("Main product unit", allowed_units, key="pu_input")
    
    capacity_label = f"Main product capacity ({st.session_state.pu_input}/year)"
    product_capacity = st.number_input(capacity_label, min_value=0.0, step=1.0, key="pc_input")

st.divider()

# --- 3. PROCESS VARIABLES ---
st.header("3. Process Variables")
st.markdown("Add your process variables below. Click the **+** at the bottom of the table to add more rows.")

if scenario_name in st.session_state.scenarios:
    df_vars = pd.DataFrame(st.session_state.scenarios[scenario_name]["Process Variables"])
else:
    df_vars = pd.DataFrame(columns=["Variable Name", "Unit", "Value"])

edited_process_vars = st.data_editor(
    df_vars,
    key=f"editor_{st.session_state.table_key}",
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
    if not st.session_state.sn_input:
        st.error("Please provide a Scenario Name before saving.")
    elif st.session_state.pc_input is None:
        st.error("Please provide a Main Product Capacity before saving.")
    else:
        valid_vars = edited_process_vars.dropna(how="all")
        
        # Save the data
        st.session_state.scenarios[st.session_state.sn_input] = {
            "Product Name": st.session_state.mp_input,
            "Unit": st.session_state.pu_input,
            "Capacity": st.session_state.pc_input,
            "Capacity Label": f"{st.session_state.pc_input} {st.session_state.pu_input}/year",
            "Process Variables": valid_vars.to_dict(orient="records")
        }
        
        st.session_state.success_msg = f"Scenario '{st.session_state.sn_input}' successfully saved!"
        
        # Activate the clear flag and restart
        st.session_state.clear_on_next_run = True
        st.rerun()

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
