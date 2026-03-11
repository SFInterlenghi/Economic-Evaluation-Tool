import streamlit as st
import pandas as pd
import numpy as np

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
if "dm_trl" not in st.session_state: st.session_state.dm_trl = "Industrial (8 or 9)"
if "dm_info_avail" not in st.session_state: st.session_state.dm_info_avail = "High"
if "dm_severity" not in st.session_state: st.session_state.dm_severity = "High"
if "dm_mat_type" not in st.session_state: st.session_state.dm_mat_type = "Solids"
if "dm_plant_size" not in st.session_state: st.session_state.dm_plant_size = "Large"

# Project CAPEX Inputs
if "equip_acq" not in st.session_state: st.session_state.equip_acq = 0.0
if "spare_parts" not in st.session_state: st.session_state.spare_parts = 0.0
if "equip_setting" not in st.session_state: st.session_state.equip_setting = 0.0

# Installation Costs Inputs
if "piping" not in st.session_state: st.session_state.piping = 0.0
if "civil" not in st.session_state: st.session_state.civil = 0.0
if "steel" not in st.session_state: st.session_state.steel = 0.0
if "instrumentals" not in st.session_state: st.session_state.instrumentals = 0.0
if "electrical" not in st.session_state: st.session_state.electrical = 0.0
if "insulation" not in st.session_state: st.session_state.insulation = 0.0
if "paint" not in st.session_state: st.session_state.paint = 0.0


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
    st.session_state.dm_trl = "Industrial (8 or 9)"
    st.session_state.dm_info_avail = "High"
    st.session_state.dm_severity = "High"
    st.session_state.dm_mat_type = "Solids"
    st.session_state.dm_plant_size = "Large"
    
    # Clear CAPEX Equipment Costs
    st.session_state.equip_acq = 0.0
    st.session_state.spare_parts = 0.0
    st.session_state.equip_setting = 0.0

    # Clear CAPEX Installation Costs
    st.session_state.piping = 0.0
    st.session_state.civil = 0.0
    st.session_state.steel = 0.0
    st.session_state.instrumentals = 0.0
    st.session_state.electrical = 0.0
    st.session_state.insulation = 0.0
    st.session_state.paint = 0.0
    
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
        st.session_state.dm_trl = data.get("TRL", "Industrial (8 or 9)")
        st.session_state.dm_info_avail = data.get("Info Availability", "High")
        st.session_state.dm_severity = data.get("Process Severity", "High")
        st.session_state.dm_mat_type = data.get("Material Handled", "Solids")
        st.session_state.dm_plant_size = data.get("Plant Size", "Large")
        
        st.session_state.equip_acq = data.get("Equipment Acquisition", 0.0)
        st.session_state.spare_parts = data.get("Spare Parts", 0.0)
        st.session_state.equip_setting = data.get("Equipment Setting", 0.0)

        st.session_state.piping = data.get("Piping", 0.0)
        st.session_state.civil = data.get("Civil", 0.0)
        st.session_state.steel = data.get("Steel", 0.0)
        st.session_state.instrumentals = data.get("Instrumentals", 0.0)
        st.session_state.electrical = data.get("Electrical", 0.0)
        st.session_state.insulation = data.get("Insulation", 0.0)
        st.session_state.paint = data.get("Paint", 0.0)
    else:
        st.session_state.mp_input = ""
        st.session_state.pu_input = "kg"
        st.session_state.pc_input = None
        st.session_state.eq_cost_src = "Manual Input"
        st.session_state.oth_cost_src = "Manual Input"
        st.session_state.lang_utility = False
        
        st.session_state.dm_prod_type = "Basic Chemical"
        st.session_state.dm_trl = "Industrial (8 or 9)"
        st.session_state.dm_info_avail = "High"
        st.session_state.dm_severity = "High"
        st.session_state.dm_mat_type = "Solids"
        st.session_state.dm_plant_size = "Large"
        
        st.session_state.equip_acq = 0.0
        st.session_state.spare_parts = 0.0
        st.session_state.equip_setting = 0.0

        st.session_state.piping = 0.0
        st.session_state.civil = 0.0
        st.session_state.steel = 0.0
        st.session_state.instrumentals = 0.0
        st.session_state.electrical = 0.0
        st.session_state.insulation = 0.0
        st.session_state.paint = 0.0
        
    st.session_state.table_key += 1

# --- BACKGROUND REFERENCE TABLES (HIDDEN) ---
reference_tables = {
    "1. Unscheduled Equipment": pd.DataFrame({
        "TRL / Info Availability": ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"],
        "High":   [0.05, None, None, None],
        "Medium": [0.10, 0.15, None, None],
        "Low":    [0.15, 0.20, 0.25, 0.30]
    }),
    "2. Project Contingency": pd.DataFrame({
        "TRL / Info Availability": ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"],
        "High":   [0.25, 0.30, 0.35, 0.40],
        "Medium": [0.20, 0.25, 0.30, 0.35],
        "Low":    [0.15, 0.20, 0.25, 0.30]
    }),
    "3. Laboratory Charges": pd.DataFrame({
        "Type of Main Product": ["Basic chemical", "Specialty chemical", "Consumer product", "Pharmaceutical"],
        "Laboratory Charges":   [0.10, 0.15, 0.20, 0.25]
    }),
    "4. Office Labor": pd.DataFrame({
        "Type of Main Product": ["Basic chemical", "Specialty chemical", "Consumer product", "Pharmaceutical"],
        "Office Labor":         [0.10, 0.175, 0.25, 0.175]
    }),
    "5. Maintenance and Repairs": pd.DataFrame({
        "Type of Material Handled": ["Solids", "Fluids and solids", "Fluids"],
        "Basic chemical":     [0.020, 0.015, 0.010],
        "Specialty chemical": [0.030, 0.025, 0.020],
        "Consumer product":   [0.040, 0.035, 0.030],
        "Pharmaceutical":     [0.020, 0.015, 0.010],
    }),
    "6. Operating Supplies": pd.DataFrame({
        "Process Severity": ["High", "Medium", "Low"],
        "Operating Supplies": [0.20, 0.15, 0.10]
    }),
    "7. Administrative Overhead": pd.DataFrame({
        "Type of Product": ["Basic chemical", "Specialty chemical", "Consumer product", "Pharmaceutical"],
        "Administrative Overhead": [0.50, 0.60, 0.70, 0.60]
    }),
    "8. Manufacturing Overhead": pd.DataFrame({
        "Process Severity": ["High", "Medium", "Low"],
        "Manufacturing Overhead": [0.700, 0.600, 0.500]
    }),
    "9. Taxes and Insurance": pd.DataFrame({
        "Process Severity": ["High", "Medium", "Low"],
        "Taxes and Insurance": [0.050, 0.032, 0.014]
    }),
    "10. Patents and Royalties": pd.DataFrame({
        "TRL / Type of Product": ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"],
        "Basic chemical":     [0.01, 0.00, 0.00, 0.00],
        "Specialty chemical": [0.02, 0.01, 0.01, 0.01],
        "Consumer product":   [0.04, 0.02, 0.02, 0.02],
        "Pharmaceutical":     [0.06, 0.03, 0.03, 0.03],
    }),
    "11. Distribution and Selling": pd.DataFrame({
        "Type of Product": ["Basic chemical", "Specialty chemical", "Consumer product", "Pharmaceutical"],
        "Distribution and Selling": [0.08, 0.02, 0.20, 0.14]
    }),
    "12. Research and Development": pd.DataFrame({
        "TRL / Type of Product": ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"],
        "Basic chemical":     [0.02, 0.03, 0.03, 0.03],
        "Specialty chemical": [0.03, 0.05, 0.05, 0.05],
        "Consumer product":   [0.02, 0.025, 0.025, 0.025],
        "Pharmaceutical":     [0.12, 0.17, 0.17, 0.17],
    }),
    "13. TIC Lower Bound": pd.DataFrame({
        "TRL / Info Availability": ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"],
        "High":   [-0.15,  0.00,  0.00,  0.00],
        "Medium": [-0.20, -0.25,  0.00,  0.00],
        "Low":    [-0.25, -0.30, -0.40, -0.50],
    }),
    "14. TIC Upper Bound": pd.DataFrame({
        "TRL / Info Availability": ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"],
        "High":   [0.20, 0.00, 0.00, 0.00],
        "Medium": [0.30, 0.40, 0.00, 0.00],
        "Low":    [0.40, 0.50, 0.70, 1.00],
    }),
    "15. Land Cost Factor": pd.DataFrame({
        "Plant Size": ["Small", "Medium", "Large"],
        "Buy":  [0.02, 0.02, 0.02],
        "Rent": [0.002, 0.002, 0.002],
    }),
    "16. Lang Cost Factors": pd.DataFrame({
        "Contains Utility Systems?": ["Yes", "No"],
        "Spare Parts":               [0.083, 0.051],
        "Equipment Setting":         [0.019, 0.019],
        "Unscheduled Equipment":     [0.110, 0.107],
        "Piping":                    [0.131, 0.368],
        "Civil":                     [0.041, 0.191],
        "Steel":                     [0.017, 0.272],
        "Instrumentals":             [0.033, 0.342],
        "Electrical":                [0.041, 0.335],
        "Insulation":                [0.015, 0.082],
        "Paint":                     [0.002, 0.040],
        "Field Office Staff":        [0.037, 0.172],
        "Construction Indirects":    [0.077, 0.377],
        "Freight":                   [0.052, 0.091],
        "Taxes and Permits":         [0.081, 0.142],
        "Engineering and HO":        [0.065, 0.684],
        "GA Overheads":              [0.049, 0.104],
        "Contract Fee":              [0.044, 0.161],
    }),
}


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
    st.selectbox("TRL", ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"], key="dm_trl")
    st.selectbox("Process severity", ["High", "Medium", "Low"], key="dm_severity")
with col_dm3:
    st.selectbox("Type of material handled", ["Solids", "Fluids and solids", "Fluids"], key="dm_mat_type")
    st.selectbox("Plant size", ["Large", "Medium", "Small"], key="dm_plant_size")
st.divider()

# --- 7. PROJECT CAPEX ---
st.header("7. Project CAPEX")

# --- 7.1 Equipment Costs ---
st.subheader("Equipment Costs")
col_cap1, col_cap2, col_cap3 = st.columns(3)

# 1. Equipment Acquisition (Always manual input in this proof of concept)
with col_cap1:
    equip_acq = st.number_input("Equipment Acquisition ($)", min_value=0.0, step=1000.0, key="equip_acq")

# 2. Spare Parts & Equipment Setting
lang_idx = 0 if st.session_state.lang_utility else 1
lang_table = reference_tables["16. Lang Cost Factors"]
is_lang = (st.session_state.oth_cost_src == "Lang Factors")

with col_cap2:
    if is_lang:
        factor_spare = lang_table["Spare Parts"].iloc[lang_idx]
        spare_parts = equip_acq * factor_spare
        st.number_input("Spare Parts ($) [Lang Factored]", value=float(spare_parts), disabled=True)
    else:
        spare_parts = st.number_input("Spare Parts ($)", min_value=0.0, step=100.0, key="spare_parts")

with col_cap3:
    if is_lang:
        factor_setting = lang_table["Equipment Setting"].iloc[lang_idx]
        equip_setting = equip_acq * factor_setting
        st.number_input("Equipment Setting ($) [Lang Factored]", value=float(equip_setting), disabled=True)
    else:
        equip_setting = st.number_input("Equipment Setting ($)", min_value=0.0, step=100.0, key="equip_setting")

# Base Equipment Costs (Subtotal)
base_equip_costs = equip_acq + spare_parts + equip_setting

# Lookup Unscheduled Equipment % from Table 1
unsched_table = reference_tables["1. Unscheduled Equipment"]
current_trl = st.session_state.dm_trl
current_info = st.session_state.dm_info_avail

row_match = unsched_table[unsched_table["TRL / Info Availability"] == current_trl]
if not row_match.empty:
    unsched_pct = row_match[current_info].values[0]
    if pd.isna(unsched_pct) or unsched_pct is None:
        unsched_pct = 0.0
else:
    unsched_pct = 0.0

unsched_equip_value = base_equip_costs * float(unsched_pct)
total_equip_costs = base_equip_costs + unsched_equip_value

st.markdown("##### Total Equipment Assembly")
col_cap4, col_cap5, col_cap6 = st.columns(3)

with col_cap4:
    st.number_input("Base Equipment Costs ($)", value=float(base_equip_costs), disabled=True, help="Sum of Acquisition, Spare Parts, and Setting")
with col_cap5:
    st.number_input("Unscheduled Equipment (%)", value=float(unsched_pct * 100), disabled=True, help="Pulled from Reference Table 1")
with col_cap6:
    st.number_input("Total Equipment Costs ($)", value=float(total_equip_costs), disabled=True)

st.markdown("---")

# --- 7.2 Installation Costs ---
st.subheader("Installation Costs")
col_inst1, col_inst2, col_inst3 = st.columns(3)

with col_inst1:
    if is_lang:
        factor_piping = lang_table["Piping"].iloc[lang_idx]
        piping = equip_acq * factor_piping
        st.number_input("Piping ($) [Lang Factored]", value=float(piping), disabled=True)
    else:
        piping = st.number_input("Piping ($)", min_value=0.0, step=100.0, key="piping")

with col_inst2:
    if is_lang:
        factor_civil = lang_table["Civil"].iloc[lang_idx]
        civil = equip_acq * factor_civil
        st.number_input("Civil ($) [Lang Factored]", value=float(civil), disabled=True)
    else:
        civil = st.number_input("Civil ($)", min_value=0.0, step=100.0, key="civil")

with col_inst3:
    if is_lang:
        factor_steel = lang_table["Steel"].iloc[lang_idx]
        steel = equip_acq * factor_steel
        st.number_input("Steel ($) [Lang Factored]", value=float(steel), disabled=True)
    else:
        steel = st.number_input("Steel ($)", min_value=0.0, step=100.0, key="steel")

col_inst4, col_inst5, col_inst6 = st.columns(3)

with col_inst4:
    if is_lang:
        factor_instrumentals = lang_table["Instrumentals"].iloc[lang_idx]
        instrumentals = equip_acq * factor_instrumentals
        st.number_input("Instrumentals ($) [Lang Factored]", value=float(instrumentals), disabled=True)
    else:
        instrumentals = st.number_input("Instrumentals ($)", min_value=0.0, step=100.0, key="instrumentals")

with col_inst5:
    if is_lang:
        factor_electrical = lang_table["Electrical"].iloc[lang_idx]
        electrical = equip_acq * factor_electrical
        st.number_input("Electrical ($) [Lang Factored]", value=float(electrical), disabled=True)
    else:
        electrical = st.number_input("Electrical ($)", min_value=0.0, step=100.0, key="electrical")

with col_inst6:
    if is_lang:
        factor_insulation = lang_table["Insulation"].iloc[lang_idx]
        insulation = equip_acq * factor_insulation
        st.number_input("Insulation ($) [Lang Factored]", value=float(insulation), disabled=True)
    else:
        insulation = st.number_input("Insulation ($)", min_value=0.0, step=100.0, key="insulation")

col_inst7, col_inst8, col_inst9 = st.columns(3)

with col_inst7:
    if is_lang:
        factor_paint = lang_table["Paint"].iloc[lang_idx]
        paint = equip_acq * factor_paint
        st.number_input("Paint ($) [Lang Factored]", value=float(paint), disabled=True)
    else:
        paint = st.number_input("Paint ($)", min_value=0.0, step=100.0, key="paint")

total_inst_costs = piping + civil + steel + instrumentals + electrical + insulation + paint

with col_inst8:
    st.metric("Total Installation Costs", f"${total_inst_costs:,.2f}")

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
            "Plant Size": st.session_state.dm_plant_size,
            
            # Project CAPEX Saving
            "Equipment Acquisition": equip_acq,
            "Spare Parts": spare_parts,
            "Equipment Setting": equip_setting,
            "Base Equipment Costs": base_equip_costs,
            "Unscheduled Equip Pct": unsched_pct,
            "Total Equipment Costs": total_equip_costs,
            
            # Installation Costs Saving
            "Piping": piping,
            "Civil": civil,
            "Steel": steel,
            "Instrumentals": instrumentals,
            "Electrical": electrical,
            "Insulation": insulation,
            "Paint": paint,
            "Total Installation Costs": total_inst_costs
        }
        
        st.session_state.success_msg = f"Scenario '{st.session_state.sn_input}' successfully saved!"
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
            "Eq. Cost": data["Equipment Costs Source"],
            "Total Equip. Cost": f"${data['Total Equipment Costs']:,.2f}",
            "Total Inst. Cost": f"${data['Total Installation Costs']:,.2f}",
            "TRL": data["TRL"]
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
    
    if st.button("Clear All Data", type="secondary"):
        st.session_state.scenarios = {}
        st.rerun()
else:
    st.info("No scenarios defined yet.")
