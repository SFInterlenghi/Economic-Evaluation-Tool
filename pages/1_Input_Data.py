import streamlit as st
import pandas as pd

st.set_page_config(page_title="Input Configuration", layout="wide")

st.title("Scenario Configuration & Inputs")
st.markdown("Define the parameters for your scenario. Type an existing Scenario Name to load it, or type a new name for a blank slate.")

# --- INITIALIZE SESSION STATE ---
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}

if "sn_input" not in st.session_state: st.session_state.sn_input = ""
if "mp_input" not in st.session_state: st.session_state.mp_input = ""
if "pu_input" not in st.session_state: st.session_state.pu_input = "kg"
if "pc_input" not in st.session_state: st.session_state.pc_input = None
if "table_key" not in st.session_state: st.session_state.table_key = 0

# Investment Costs Sources
if "eq_cost_src" not in st.session_state: st.session_state.eq_cost_src = "Manual Input"
if "oth_cost_src" not in st.session_state: st.session_state.oth_cost_src = "Manual Input"
if "lang_utility" not in st.session_state: st.session_state.lang_utility = False

# Decision Making Assistant
if "dm_prod_type" not in st.session_state: st.session_state.dm_prod_type = "Basic Chemical"
if "dm_trl" not in st.session_state: st.session_state.dm_trl = "Industrial (8 to 9)"
if "dm_info_avail" not in st.session_state: st.session_state.dm_info_avail = "High"
if "dm_severity" not in st.session_state: st.session_state.dm_severity = "High"
if "dm_mat_type" not in st.session_state: st.session_state.dm_mat_type = "Solids"
if "dm_plant_size" not in st.session_state: st.session_state.dm_plant_size = "Large"

# --- THE FIX: Clear fields at the TOP of the script before widgets are drawn ---
if st.session_state.get("clear_on_next_run", False):
    st.session_state.sn_input = ""
    st.session_state.mp_input = ""
    st.session_state.pc_input = None
    st.session_state.pu_input = "kg"
    st.session_state.eq_cost_src = "Manual Input"
    st.session_state.oth_cost_src = "Manual Input"
    st.session_state.lang_utility = False
    
    # Clear Decision Making states back to defaults
    st.session_state.dm_prod_type = "Basic Chemical"
    st.session_state.dm_trl = "Industrial (8 to 9)"
    st.session_state.dm_info_avail = "High"
    st.session_state.dm_severity = "High"
    st.session_state.dm_mat_type = "Solids"
    st.session_state.dm_plant_size = "Large"
    
    st.session_state.table_key += 1
    st.session_state.clear_on_next_run = False

# Handle success messages across reruns
if "success_msg" in st.session_state and st.session_state.success_msg:
    st.success(st.session_state.success_msg)
    st.session_state.success_msg = ""


# --- CALLBACK FUNCTION ---
def load_scenario_data():
    """Triggered instantly when the Scenario Name text box changes."""
    sn = st.session_state.sn_input
    if sn in st.session_state.scenarios:
        data = st.session_state.scenarios[sn]
        st.session_state.mp_input = data.get("Product Name", "")
        st.session_state.pu_input = data.get("Unit", "kg")
        st.session_state.pc_input = data.get("Capacity", None)
        st.session_state.eq_cost_src = data.get("Equipment Costs Source", "Manual Input")
        st.session_state.oth_cost_src = data.get("Other Costs Source", "Manual Input")
        st.session_state.lang_utility = data.get("Contains Utility Systems", False)
        
        st.session_state.dm_prod_type = data.get("Product Type", "Basic Chemical")
        st.session_state.dm_trl = data.get("TRL", "Industrial (8 to 9)")
        st.session_state.dm_info_avail = data.get("Info Availability", "High")
        st.session_state.dm_severity = data.get("Process Severity", "High")
        st.session_state.dm_mat_type = data.get("Material Handled", "Solids")
        st.session_state.dm_plant_size = data.get("Plant Size", "Large")
    else:
        st.session_state.mp_input = ""
        st.session_state.pu_input = "kg"
        st.session_state.pc_input = None
        st.session_state.eq_cost_src = "Manual Input"
        st.session_state.oth_cost_src = "Manual Input"
        st.session_state.lang_utility = False
        
        st.session_state.dm_prod_type = "Basic Chemical"
        st.session_state.dm_trl = "Industrial (8 to 9)"
        st.session_state.dm_info_avail = "High"
        st.session_state.dm_severity = "High"
        st.session_state.dm_mat_type = "Solids"
        st.session_state.dm_plant_size = "Large"
        
    st.session_state.table_key += 1


# --- 1. SCENARIO SELECTION ---
st.header("1. Scenario Name")
scenario_name = st.text_input(
    "Scenario Name", key="sn_input", on_change=load_scenario_data,
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
if scenario_name in st.session_state.scenarios:
    df_vars = pd.DataFrame(st.session_state.scenarios[scenario_name].get("Process Variables", []))
else:
    df_vars = pd.DataFrame(columns=["Variable Name", "Unit", "Value"])

edited_process_vars = st.data_editor(
    df_vars, key=f"editor_{st.session_state.table_key}", num_rows="dynamic",
    use_container_width=True, hide_index=True,
    column_config={
        "Variable Name": st.column_config.TextColumn("Variable Name", required=True),
        "Unit": st.column_config.TextColumn("Unit", required=True),
        "Value": st.column_config.NumberColumn("Value", required=True),
    }
)
st.divider()

# --- 4. INVESTMENT COSTS SOURCES ---
st.header("4. Investment Costs Sources")
col_eq, col_oth = st.columns(2)
with col_eq:
    eq_source = st.selectbox("Equipment costs source", ["Manual Input", "Aspen PEA"], key="eq_cost_src")
with col_oth:
    oth_source = st.selectbox("Other Costs source", ["Manual Input", "Aspen PEA", "Lang Factors"], key="oth_cost_src")
    if st.session_state.oth_cost_src == "Lang Factors":
        st.checkbox("Contains utility systems?", key="lang_utility")

if st.session_state.eq_cost_src == "Aspen PEA" or st.session_state.oth_cost_src == "Aspen PEA":
    st.markdown("#### Upload Aspen PEA Files")
    col_file1, col_file2 = st.columns(2)
    with col_file1:
        st.file_uploader("IPEWB File", type=["xls", "xlsx", "xlsm"], key=f"ipewb_{st.session_state.table_key}")
    with col_file2:
        st.file_uploader("Reports file", type=["xls", "xlsx", "xlsm"], key=f"reports_{st.session_state.table_key}")
st.divider()

# --- 5. DECISION MAKING ASSISTANT ---
st.header("5. Decision Making Assistant")
col_dm1, col_dm2, col_dm3 = st.columns(3)
with col_dm1:
    st.selectbox("Type of main product", ["Basic Chemical", "Specialty chemical", "Consumer product", "Pharmaceutical"], key="dm_prod_type")
    st.selectbox("Availability of information", ["High", "Medium", "Low"], key="dm_info_avail")
with col_dm2:
    st.selectbox("TRL", ["Industrial (8 to 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"], key="dm_trl")
    st.selectbox("Process severity", ["High", "Medium", "Low"], key="dm_severity")
with col_dm3:
    st.selectbox("Type of material handled", ["Solids", "Fluids and solids", "Fluids"], key="dm_mat_type")
    st.selectbox("Plant size", ["Large", "Medium", "Small"], key="dm_plant_size")
st.divider()

# --- SAVE BUTTON & LOGIC ---
if st.button("Save / Update Scenario", type="primary"):
    if not st.session_state.sn_input:
        st.error("Please provide a Scenario Name before saving.")
    elif st.session_state.pc_input is None:
        st.error("Please provide a Main Product Capacity before saving.")
    else:
        valid_vars = edited_process_vars.dropna(how="all")
        util_bool = st.session_state.lang_utility if st.session_state.oth_cost_src == "Lang Factors" else False

        st.session_state.scenarios[st.session_state.sn_input] = {
            "Product Name": st.session_state.mp_input,
            "Unit": st.session_state.pu_input,
            "Capacity": st.session_state.pc_input,
            "Capacity Label": f"{st.session_state.pc_input} {st.session_state.pu_input}/year",
            "Process Variables": valid_vars.to_dict(orient="records"),
            "Equipment Costs Source": st.session_state.eq_cost_src,
            "Other Costs Source": st.session_state.oth_cost_src,
            "Contains Utility Systems": util_bool,
            "Product Type": st.session_state.dm_prod_type,
            "TRL": st.session_state.dm_trl,
            "Info Availability": st.session_state.dm_info_avail,
            "Process Severity": st.session_state.dm_severity,
            "Material Handled": st.session_state.dm_mat_type,
            "Plant Size": st.session_state.dm_plant_size
        }
        
        st.session_state.success_msg = f"Scenario '{st.session_state.sn_input}' successfully saved!"
        st.session_state.clear_on_next_run = True
        st.rerun()

# --- TEMPORARY: REFERENCE TABLES ---
st.header("6. Reference Tables View (To Be Hidden)")
st.markdown("Verify these factors based on your image. They will be pushed to the backend `Calculations.py` page later.")

reference_tables = {
"1. Unscheduled Equipment": pd.DataFrame({
        "TRL / Info Availability": ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"],
        "High": [0.05, None, None, None],
        "Medium": [0.10, 0.15, None, None],
        "Low": [0.15, 0.20, 0.25, 0.30]
    }),
 "2. Project contingency": pd.DataFrame({
        "TRL / Info Availability": ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"],
        "High": [0.25,0.3,0.35,0.4],
        "Medium": [0.2,0.25,0.3,0.35],
        "Low": [0.15, 0.20, 0.25, 0.30]
    }),       

}

with st.expander("Show/Hide 15 Reference Tables"):
    # Dynamically generate 3 columns to display the 15 tables efficiently
    cols = st.columns(3)
    for i, (table_name, df) in enumerate(reference_tables.items()):
        col = cols[i % 3]
        col.markdown(f"**{table_name}**")
        col.dataframe(df, hide_index=True, use_container_width=True)

st.divider()

# --- SCENARIO COMPARISON TABLE ---
st.header("Compiled Scenarios")
if st.session_state.scenarios:
    summary_data = []
    for s_name, data in st.session_state.scenarios.items():
        summary_data.append({
            "Scenario Name": s_name,
            "Product": data["Product Name"],
            "Eq. Cost": data["Equipment Costs Source"],
            "Product Type": data["Product Type"],
            "TRL": data["TRL"],
            "Info Avail.": data["Info Availability"],
            "Severity": data["Process Severity"]
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
    
    if st.button("Clear All Data", type="secondary"):
        st.session_state.scenarios = {}
        st.rerun()
else:
    st.info("No scenarios defined yet.")
