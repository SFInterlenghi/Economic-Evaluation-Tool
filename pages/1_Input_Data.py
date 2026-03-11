import streamlit as st
import pandas as pd

st.set_page_config(page_title="Input Configuration", layout="wide")

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
ALLOWED_UNITS = ["g", "kg", "t", "mL", "L", "m³", "kWh", "MWh", "GWh", "MMBtu"]

PRODUCT_TYPES    = ["Basic Chemical", "Specialty chemical", "Consumer product", "Pharmaceutical"]
TRL_OPTIONS      = ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"]
INFO_OPTIONS     = ["High", "Medium", "Low"]
SEVERITY_OPTIONS = ["High", "Medium", "Low"]
MAT_OPTIONS      = ["Solids", "Fluids and solids", "Fluids"]
SIZE_OPTIONS     = ["Large", "Medium", "Small"]

# Unscheduled equipment factors keyed by (TRL, info_availability)
UNSCHED_FACTORS = {
    ("Industrial (8 or 9)", "High"):   0.05,
    ("Industrial (8 or 9)", "Medium"): 0.10,
    ("Industrial (8 or 9)", "Low"):    0.15,
    ("Pilot (5 to 7)",       "Medium"): 0.15,
    ("Pilot (5 to 7)",       "Low"):    0.20,
    ("Bench (3 or 4)",       "Low"):    0.25,
    ("Theoretical (1 or 2)", "Low"):    0.30,
}

# Lang cost factors keyed by field name; tuple = (with_utility, without_utility)
LANG_FACTORS = {
    "Spare Parts":            (0.083, 0.051),
    "Equipment Setting":      (0.019, 0.019),
    "Unscheduled Equipment":  (0.110, 0.107),
    "Piping":                 (0.131, 0.368),
    "Civil":                  (0.041, 0.191),
    "Steel":                  (0.017, 0.272),
    "Instrumentals":          (0.033, 0.342),
    "Electrical":             (0.041, 0.335),
    "Insulation":             (0.015, 0.082),
    "Paint":                  (0.002, 0.040),
    "Field Office Staff":     (0.037, 0.172),
    "Construction Indirects": (0.077, 0.377),
    "Freight":                (0.052, 0.091),
    "Taxes and Permits":      (0.081, 0.142),
    "Engineering and HO":     (0.065, 0.684),
    "GA Overheads":           (0.049, 0.104),
    "Contract Fee":           (0.044, 0.161),
}

# Default session-state values — single source of truth
DEFAULTS = {
    "sn_input":        "",
    "mp_input":        "",
    "pu_input":        "kg",
    "pc_input":        None,
    "eq_cost_src":     "Manual Input",
    "oth_cost_src":    "Manual Input",
    "lang_utility":    False,
    "dm_prod_type":    "Basic Chemical",
    "dm_trl":          "Industrial (8 or 9)",
    "dm_info_avail":   "High",
    "dm_severity":     "High",
    "dm_mat_type":     "Solids",
    "dm_plant_size":   "Large",
    # CAPEX
    "equip_acq":       0.0,
    "spare_parts":     0.0,
    "equip_setting":   0.0,
    "piping":          0.0,
    "civil":           0.0,
    "steel":           0.0,
    "instrumentals":   0.0,
    "electrical":      0.0,
    "insulation":      0.0,
    "paint":           0.0,
    "isbl_contrib":    100.0,
    "field_office":    0.0,
    "const_indirects": 0.0,
    "freight":         0.0,
    "taxes_permits":   0.0,
    "eng_ho":          0.0,
    "ga_overheads":    0.0,
    "contract_fee":    0.0,
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fmt_curr(val: float) -> str:
    return f"${val:,.2f}"


def reset_state(keys: dict = DEFAULTS):
    """Write every key in *keys* back to session_state."""
    for k, v in keys.items():
        st.session_state[k] = v
    st.session_state.table_key = st.session_state.get("table_key", 0) + 1


def lang_val(field: str, equip_acq: float) -> float:
    """Return the Lang-factored value for *field* given Equipment Acquisition cost."""
    idx = 0 if st.session_state.lang_utility else 1
    return equip_acq * LANG_FACTORS[field][idx]


def lang_or_manual(field: str, label: str, equip_acq: float, step: float = 100.0):
    """Render either a disabled Lang-factored text input or a number_input widget."""
    if st.session_state.oth_cost_src == "Lang Factors":
        value = lang_val(field, equip_acq)
        st.text_input(f"{label} [Lang Factored]", value=fmt_curr(value), disabled=True)
        return value
    return st.number_input(f"{label} ($)", min_value=0.0, step=step,
                           key=field.lower().replace(" ", "_"))


# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}
if "table_key" not in st.session_state:
    st.session_state.table_key = 0

for key, default in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Deferred clear (must run before widgets are drawn)
if st.session_state.pop("clear_on_next_run", False):
    reset_state()

if st.session_state.get("success_msg"):
    st.success(st.session_state.pop("success_msg"))


# ─────────────────────────────────────────────
# CALLBACK
# ─────────────────────────────────────────────
def load_scenario_data():
    sn = st.session_state.sn_input
    data = st.session_state.scenarios.get(sn, {})

    mapping = {
        "mp_input":        ("Product Name",            ""),
        "pu_input":        ("Unit",                    "kg"),
        "pc_input":        ("Capacity",                None),
        "eq_cost_src":     ("Equipment Costs Source",  "Manual Input"),
        "oth_cost_src":    ("Other Costs Source",      "Manual Input"),
        "lang_utility":    ("Contains Utility Systems",False),
        "dm_prod_type":    ("Product Type",            "Basic Chemical"),
        "dm_trl":          ("TRL",                     "Industrial (8 or 9)"),
        "dm_info_avail":   ("Info Availability",       "High"),
        "dm_severity":     ("Process Severity",        "High"),
        "dm_mat_type":     ("Material Handled",        "Solids"),
        "dm_plant_size":   ("Plant Size",              "Large"),
        "equip_acq":       ("Equipment Acquisition",   0.0),
        "spare_parts":     ("Spare Parts",             0.0),
        "equip_setting":   ("Equipment Setting",       0.0),
        "piping":          ("Piping",                  0.0),
        "civil":           ("Civil",                   0.0),
        "steel":           ("Steel",                   0.0),
        "instrumentals":   ("Instrumentals",           0.0),
        "electrical":      ("Electrical",              0.0),
        "insulation":      ("Insulation",              0.0),
        "paint":           ("Paint",                   0.0),
        "isbl_contrib":    ("ISBL Contribution (%)",   100.0),
        "field_office":    ("Field Office Staff",      0.0),
        "const_indirects": ("Construction Indirects",  0.0),
        "freight":         ("Freight",                 0.0),
        "taxes_permits":   ("Taxes and Permits",       0.0),
        "eng_ho":          ("Engineering and HO",      0.0),
        "ga_overheads":    ("GA Overheads",            0.0),
        "contract_fee":    ("Contract Fee",            0.0),
    }

    for ss_key, (data_key, default) in mapping.items():
        st.session_state[ss_key] = data.get(data_key, default)

    st.session_state.table_key += 1


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
st.title("Scenario Configuration & Inputs")
st.markdown("Define the parameters for your scenario. "
            "Type an existing Scenario Name to load it, or type a new name for a blank slate.")

# 1. Scenario Name
st.header("1. Scenario Name")
scenario_name = st.text_input("Scenario Name", key="sn_input", on_change=load_scenario_data)
st.divider()

# 2. Basic Information
st.header("2. Basic Information")
col1, col2 = st.columns(2)
with col1:
    st.text_input("Main Product Name", key="mp_input")
with col2:
    st.selectbox("Main product unit", ALLOWED_UNITS, key="pu_input")
    st.number_input(f"Main product capacity ({st.session_state.pu_input}/year)",
                    min_value=0.0, step=1.0, key="pc_input")
st.divider()

# 3. Process Variables
st.header("3. Process Variables")
saved_vars = st.session_state.scenarios.get(scenario_name, {}).get("Process Variables", [])
df_vars = pd.DataFrame(saved_vars) if saved_vars else pd.DataFrame(columns=["Variable Name", "Unit", "Value"])

edited_process_vars = st.data_editor(
    df_vars, key=f"editor_{st.session_state.table_key}", num_rows="dynamic",
    use_container_width=True, hide_index=True,
    column_config={
        "Variable Name": st.column_config.TextColumn(required=True),
        "Unit":          st.column_config.TextColumn(required=True),
        "Value":         st.column_config.NumberColumn(required=True),
    },
)
st.divider()

# 4. Investment Costs Sources
st.header("4. Investment Costs Sources")
col_eq, col_oth = st.columns(2)
with col_eq:
    st.selectbox("Equipment costs source", ["Manual Input", "Aspen PEA"], key="eq_cost_src")
with col_oth:
    st.selectbox("Other Costs source", ["Manual Input", "Aspen PEA", "Lang Factors"], key="oth_cost_src")
    if st.session_state.oth_cost_src == "Lang Factors":
        st.checkbox("Contains utility systems?", key="lang_utility")
st.divider()

# 5. Decision Making Assistant
st.header("5. Decision Making Assistant")
col_dm1, col_dm2, col_dm3 = st.columns(3)
with col_dm1:
    st.selectbox("Type of main product",      PRODUCT_TYPES,    key="dm_prod_type")
    st.selectbox("Availability of information", INFO_OPTIONS,    key="dm_info_avail")
with col_dm2:
    st.selectbox("TRL",                       TRL_OPTIONS,      key="dm_trl")
    st.selectbox("Process severity",          SEVERITY_OPTIONS, key="dm_severity")
with col_dm3:
    st.selectbox("Type of material handled",  MAT_OPTIONS,      key="dm_mat_type")
    st.selectbox("Plant size",                SIZE_OPTIONS,     key="dm_plant_size")
st.divider()

# 7. Project CAPEX
st.header("7. Project CAPEX")
equip_acq = st.session_state.equip_acq   # convenience alias

# 7.1 Equipment Costs
st.subheader("Equipment Costs")
col1, col2, col3 = st.columns(3)
with col1:
    equip_acq = st.number_input("Equipment Acquisition ($)", min_value=0.0, step=1000.0, key="equip_acq")
with col2:
    spare_parts = lang_or_manual("Spare Parts", "Spare Parts", equip_acq)
with col3:
    equip_setting = lang_or_manual("Equipment Setting", "Equipment Setting", equip_acq)

base_equip_costs  = equip_acq + spare_parts + equip_setting
unsched_pct       = UNSCHED_FACTORS.get((st.session_state.dm_trl, st.session_state.dm_info_avail), 0.0)
total_equip_costs = base_equip_costs * (1 + unsched_pct)

st.markdown("##### Total Equipment Assembly")
col4, col5, col6 = st.columns(3)
with col4:
    st.text_input("Base Equipment Costs",      value=fmt_curr(base_equip_costs),      disabled=True)
with col5:
    st.text_input("Unscheduled Equipment (%)", value=f"{unsched_pct * 100:.2f}%",     disabled=True)
with col6:
    st.text_input("Total Equipment Costs",     value=fmt_curr(total_equip_costs),     disabled=True)
st.markdown("---")

# 7.2 Installation Costs
st.subheader("Installation Costs")
inst_fields = ["Piping", "Civil", "Steel", "Instrumentals", "Electrical", "Insulation"]
inst_cols   = st.columns(3)
inst_values = []
for i, field in enumerate(inst_fields):
    with inst_cols[i % 3]:
        inst_values.append(lang_or_manual(field, field, equip_acq))

col_p, col_t = st.columns(2)
with col_p:
    paint = lang_or_manual("Paint", "Paint", equip_acq)
total_inst_costs = sum(inst_values) + paint
with col_t:
    st.text_input("Total Installation Costs", value=fmt_curr(total_inst_costs), disabled=True)
st.markdown("---")

# 7.3 Direct Field Costs
st.subheader("Direct Field Costs")
total_direct_field_costs = total_equip_costs + total_inst_costs
col1, col2, col3 = st.columns(3)
with col1:
    st.text_input("Total Direct Field Costs", value=fmt_curr(total_direct_field_costs), disabled=True)
with col2:
    isbl_contrib = st.number_input("ISBL Contribution (%)", min_value=0.0, max_value=100.0,
                                   step=1.0, key="isbl_contrib")
with col3:
    st.text_input("OSBL Contribution (%)", value=f"{100.0 - isbl_contrib:.2f}%", disabled=True)
st.markdown("---")

# 7.4 Indirect Field Costs
st.subheader("Indirect Field Costs")
col1, col2, col3 = st.columns(3)
with col1:
    field_office = lang_or_manual("Field Office Staff", "Field Office Staff", equip_acq)
with col2:
    const_indirects = lang_or_manual("Construction Indirects", "Construction Indirects", equip_acq)
total_indirect_field_costs = field_office + const_indirects
with col3:
    st.text_input("Total Indirect Field Costs", value=fmt_curr(total_indirect_field_costs), disabled=True)
st.markdown("---")

# 7.5 Non-Field Costs
st.subheader("Non-Field Costs")
nf_fields = ["Freight", "Taxes and Permits", "Engineering and HO", "GA Overheads", "Contract Fee"]
nf_cols   = st.columns(3)
nf_values = []
for i, field in enumerate(nf_fields):
    with nf_cols[i % 3]:
        nf_values.append(lang_or_manual(field, field, equip_acq))

total_non_field_costs = sum(nf_values)
# Fill remaining cell in last row with the total
with nf_cols[(len(nf_fields)) % 3]:
    st.text_input("Total Non-Field Costs", value=fmt_curr(total_non_field_costs), disabled=True)
st.markdown("---")

# 7.6 CAPEX Summary
st.subheader("Capex Calculations")
project_costs_isbl_osbl = total_direct_field_costs + total_indirect_field_costs + total_non_field_costs
st.metric("Project Costs for ISBL + OSBL", fmt_curr(project_costs_isbl_osbl))
st.divider()

# ─────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────
if st.button("Save / Update Scenario", type="primary"):
    if not st.session_state.sn_input:
        st.error("Please provide a Scenario Name before saving.")
    elif st.session_state.pc_input is None:
        st.error("Please provide a Main Product Capacity before saving.")
    else:
        util_bool = st.session_state.lang_utility if st.session_state.oth_cost_src == "Lang Factors" else False

        # Unpack nf_values list to named keys
        freight, taxes_permits, eng_ho, ga_overheads, contract_fee = nf_values
        piping, civil, steel, instrumentals, electrical, insulation = inst_values

        st.session_state.scenarios[st.session_state.sn_input] = {
            "Product Name":              st.session_state.mp_input,
            "Unit":                      st.session_state.pu_input,
            "Capacity":                  st.session_state.pc_input,
            "Capacity Label":            f"{st.session_state.pc_input} {st.session_state.pu_input}/year",
            "Process Variables":         edited_process_vars.dropna(how="all").to_dict(orient="records"),
            "Equipment Costs Source":    st.session_state.eq_cost_src,
            "Other Costs Source":        st.session_state.oth_cost_src,
            "Contains Utility Systems":  util_bool,
            "Product Type":              st.session_state.dm_prod_type,
            "TRL":                       st.session_state.dm_trl,
            "Info Availability":         st.session_state.dm_info_avail,
            "Process Severity":          st.session_state.dm_severity,
            "Material Handled":          st.session_state.dm_mat_type,
            "Plant Size":                st.session_state.dm_plant_size,
            # CAPEX
            "Equipment Acquisition":     equip_acq,
            "Spare Parts":               spare_parts,
            "Equipment Setting":         equip_setting,
            "Base Equipment Costs":      base_equip_costs,
            "Unscheduled Equip Pct":     unsched_pct,
            "Total Equipment Costs":     total_equip_costs,
            "Piping":                    piping,
            "Civil":                     civil,
            "Steel":                     steel,
            "Instrumentals":             instrumentals,
            "Electrical":                electrical,
            "Insulation":                insulation,
            "Paint":                     paint,
            "Total Installation Costs":  total_inst_costs,
            "Total Direct Field Costs":  total_direct_field_costs,
            "ISBL Contribution (%)":     isbl_contrib,
            "OSBL Contribution (%)":     100.0 - isbl_contrib,
            "Field Office Staff":        field_office,
            "Construction Indirects":    const_indirects,
            "Total Indirect Field Costs":total_indirect_field_costs,
            "Freight":                   freight,
            "Taxes and Permits":         taxes_permits,
            "Engineering and HO":        eng_ho,
            "GA Overheads":              ga_overheads,
            "Contract Fee":              contract_fee,
            "Total Non-Field Costs":     total_non_field_costs,
            "Project Costs ISBL+OSBL":   project_costs_isbl_osbl,
        }

        st.session_state.success_msg      = f"Scenario '{st.session_state.sn_input}' successfully saved!"
        st.session_state.clear_on_next_run = True
        st.rerun()

# ─────────────────────────────────────────────
# SCENARIO COMPARISON TABLE
# ─────────────────────────────────────────────
st.header("Compiled Scenarios")
if st.session_state.scenarios:
    summary_rows = [
        {
            "Scenario Name":    name,
            "Product":          d["Product Name"],
            "Eq. Cost":         d["Equipment Costs Source"],
            "Total Equip. Cost":fmt_curr(d["Total Equipment Costs"]),
            "ISBL+OSBL Cost":   fmt_curr(d["Project Costs ISBL+OSBL"]),
            "TRL":              d["TRL"],
        }
        for name, d in st.session_state.scenarios.items()
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

    if st.button("Clear All Data", type="secondary"):
        st.session_state.scenarios = {}
        st.rerun()
else:
    st.info("No scenarios defined yet.")
