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

# Project contingency factors keyed by (TRL, process_severity) → fraction
PROJECT_CONTINGENCY: dict[tuple[str, str], float] = {
    ("Industrial (8 or 9)", "Low"):    0.05,
    ("Industrial (8 or 9)", "Medium"): 0.10,
    ("Industrial (8 or 9)", "High"):   0.15,
    ("Pilot (5 to 7)",       "Low"):    0.15,
    ("Pilot (5 to 7)",       "Medium"): 0.20,
    ("Pilot (5 to 7)",       "High"):   0.25,
    ("Bench (3 or 4)",       "Low"):    0.20,
    ("Bench (3 or 4)",       "Medium"): 0.25,
    ("Bench (3 or 4)",       "High"):   0.30,
    ("Theoretical (1 or 2)", "Low"):    0.30,
    ("Theoretical (1 or 2)", "Medium"): 0.35,
    ("Theoretical (1 or 2)", "High"):   0.40,
}

# Plant Cost Index keyed by year (int)
PLANT_COST_INDEX: dict[int, float] = {
    2000: 102.44, 2001: 102.32, 2002: 102.09, 2003: 106.35,
    2004: 119.36, 2005: 128.89, 2006: 135.32, 2007: 140.98,
    2008: 157.68, 2009: 138.86, 2010: 146.42, 2011: 156.66,
    2012: 155.24, 2013: 152.74, 2014: 155.32, 2015: 144.33,
    2016: 139.48, 2017: 145.48, 2018: 155.62, 2019: 156.33,
    2020: 150.65, 2021: 181.39, 2022: 214.60, 2023: 206.48,
    2024: 203.90,
}
PCI_YEARS = sorted(PLANT_COST_INDEX.keys())

# Rates-and-prices unit mapping: rate_unit → price_unit
RATE_TO_PRICE_UNIT: dict[str, str] = {
    "g/h":      "USD/g",
    "kg/h":     "USD/kg",
    "t/h":      "USD/t",
    "mL/h":     "USD/mL",
    "L/h":      "USD/L",
    "m³/h":     "USD/m³",
    "kW":       "USD/kWh",
    "MW":       "USD/MWh",
    "GW":       "USD/GWh",
    "MMBtu/h":  "USD/MMBtu",
    "g/y":      "USD/g",
    "kg/y":     "USD/kg",
    "t/y":      "USD/t",
    "mL/y":     "USD/mL",
    "L/y":      "USD/L",
    "m³/y":     "USD/m³",
    "MMBtu/y":  "USD/MMBtu",
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
    "dm_info_avail":   "Medium",
    "dm_severity":     "Medium",
    "dm_mat_type":     "Fluids",
    "dm_plant_size":   "Medium",
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
    # Lang override support
    "allow_override":       False,   # master switch for manual editing of Lang fields
    "lang_seeded_acq":      None,    # equip_acq value used for last Lang seed
    # CAPEX calculations
    "databank_year":   2022,
    "analysis_year":   PCI_YEARS[-1],
    "proj_location":   "Brazil",
    "location_factor": 0.97,
    # Additional information
    "working_hours":   8000.0,
    "scaling_factor":  0.6,
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fmt_curr(val: float) -> str:
    return f"${val:,.2f}"


def reset_state(keys: dict = DEFAULTS):
    """Write every key in *keys* back to session_state, and wipe Lang field overrides."""
    for k, v in keys.items():
        st.session_state[k] = v
    for k in list(st.session_state.keys()):
        if k.startswith("val_") or k.startswith("w_"):
            del st.session_state[k]
    st.session_state.table_key = st.session_state.get("table_key", 0) + 1


def _reseed_lang_fields(equip_acq: float):
    """Overwrite all lf_ keys with freshly computed Lang values for equip_acq."""
    idx = 0 if st.session_state.lang_utility else 1
    for field, factors in LANG_FACTORS.items():
        key = f"lf_{field.lower().replace(' ', '_')}"
        st.session_state[key] = equip_acq * factors[idx]
    st.session_state.lang_seeded_acq = equip_acq


def lang_val(field: str, equip_acq: float) -> float:
    """Return the Lang-factored value for *field* given Equipment Acquisition cost."""
    idx = 0 if st.session_state.lang_utility else 1
    return equip_acq * LANG_FACTORS[field][idx]


def get_pci(year: int) -> float | None:
    return PLANT_COST_INDEX.get(year)


def pci_escalate(base_cost: float, base_year: int, target_year: int) -> float | None:
    pci_base   = PLANT_COST_INDEX.get(base_year)
    pci_target = PLANT_COST_INDEX.get(target_year)
    if pci_base and pci_target:
        return base_cost * (pci_target / pci_base)
    return None


def price_unit_for(rate_unit: str) -> str:
    return RATE_TO_PRICE_UNIT.get(rate_unit, "")


LANG_FIELDS = list(LANG_FACTORS.keys())  # canonical field names in order

def _seed_override_values():
    """
    Called when the user ticks 'Allow manual override'.
    Reads the current equip_acq and writes a val_ key for every
    Lang field.  These are plain state variables — NOT widget keys —
    so Streamlit never overwrites them on widget init.
    """
    acq = st.session_state.get("equip_acq", 0.0)
    idx = 0 if st.session_state.get("lang_utility", False) else 1
    for field, factors in LANG_FACTORS.items():
        vkey = f"val_{field.lower().replace(' ', '_')}"
        st.session_state[vkey] = acq * factors[idx]


def lang_or_manual(field: str, label: str, equip_acq: float, step: float = 100.0) -> float:
    """
    Lang Factors mode — override OFF:
        Read-only text_input showing the live computed Lang value.

    Lang Factors mode — override ON:
        Editable number_input whose *initial* value was seeded by
        _seed_override_values() via the checkbox callback.
        Stored in val_<field> (plain state, not a widget key), read
        back via a widget key w_<field> so Streamlit never zeros it.
        Label is green (✓ Lang) or amber (⚠ overridden).

    Manual mode:
        Plain number_input bound to session_state via ss_key.
    """
    ss_key  = field.lower().replace(" ", "_")
    val_key = f"val_{ss_key}"   # plain storage key — written by callback
    w_key   = f"w_{ss_key}"     # widget key — only used to read user input

    if st.session_state.oth_cost_src == "Lang Factors":
        lang_computed = lang_val(field, equip_acq)
        allow = st.session_state.get("allow_override", False)

        if not allow:
            st.text_input(f"{label}", value=fmt_curr(lang_computed), disabled=True)
            return lang_computed

        # Override ON — use val_key as the source of truth for the current value.
        # val_key was already populated by _seed_override_values() callback.
        stored = st.session_state.get(val_key, lang_computed)
        is_overridden = abs(stored - lang_computed) > 0.005

        color = "#e67e00" if is_overridden else "#2e7d32"
        hint  = " ⚠ overridden" if is_overridden else " ✓ Lang"
        st.markdown(
            f'<p style="margin-bottom:0px; font-size:0.85rem; color:{color};">'
            f'<b>{label} ($)</b>{hint}</p>',
            unsafe_allow_html=True,
        )

        # Render number_input with value= drawn from val_key.
        # on_change writes the widget's new value back into val_key.
        def _sync(vk=val_key, wk=w_key):
            st.session_state[vk] = st.session_state[wk]

        result = st.number_input(
            label, min_value=0.0, step=step,
            value=stored,
            key=w_key,
            label_visibility="collapsed",
            on_change=_sync,
        )
        return result

    # Plain manual mode
    return st.number_input(f"{label} ($)", min_value=0.0, step=step, key=ss_key)


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
        "dm_info_avail":   ("Info Availability",       "Medium"),
        "dm_severity":     ("Process Severity",        "Medium"),
        "dm_mat_type":     ("Material Handled",        "Fluids"),
        "dm_plant_size":   ("Plant Size",              "Medium"),
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
        "allow_override":  ("Allow Override",          False),
        "databank_year":   ("Databank Year",           2022),
        "analysis_year":   ("Year of Analysis",        PCI_YEARS[-1]),
        "proj_location":   ("Project Location",        "Brazil"),
        "location_factor": ("Location Factor",         0.97),
        "working_hours":   ("Working Hours per Year",  8000.0),
        "scaling_factor":  ("Scaling Factor",          0.6),
    }

    for ss_key, (data_key, default) in mapping.items():
        st.session_state[ss_key] = data.get(data_key, default)

    st.session_state.table_key += 1
    st.session_state.lang_seeded_acq = None  # force re-seed on next render


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

is_lang = st.session_state.oth_cost_src == "Lang Factors"

if is_lang:
    st.checkbox(
        "Allow manual override of Lang factor fields?",
        key="allow_override",
        on_change=_seed_override_values,
        help="When checked, all Lang-computed fields become editable. "
             "Fields that differ from their Lang value are highlighted in amber.",
    )
else:
    st.session_state.allow_override = False

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

# 7.6 CAPEX Calculations
st.subheader("Capex Calculations")
project_costs_isbl_osbl = total_direct_field_costs + total_indirect_field_costs + total_non_field_costs
st.metric("Project Costs for ISBL + OSBL", fmt_curr(project_costs_isbl_osbl))

st.markdown("---")
col_cx1, col_cx2, col_cx3 = st.columns(3)

# --- Project Contingency (auto-looked-up) ---
with col_cx1:
    contingency_pct = PROJECT_CONTINGENCY.get(
        (st.session_state.dm_trl, st.session_state.dm_severity), 0.0
    )
    st.text_input(
        "Project Contingency (auto)",
        value=f"{contingency_pct * 100:.1f}%  "
              f"[TRL: {st.session_state.dm_trl} / Severity: {st.session_state.dm_severity}]",
        disabled=True,
        help="Looked up from the Project Contingency reference table using TRL and Process Severity."
    )

# --- Databank Year ---
with col_cx2:
    databank_year_input = st.number_input(
        "Databank Year", min_value=PCI_YEARS[0], max_value=PCI_YEARS[-1],
        step=1, key="databank_year",
        help="Reference year for the cost data (defaults to 2022)."
    )
    pci_databank = PLANT_COST_INDEX.get(int(databank_year_input))
    st.text_input(
        "PCI (Databank Year)",
        value=f"{pci_databank:.2f}" if pci_databank else "—",
        disabled=True,
    )

# --- Year of Analysis ---
with col_cx3:
    analysis_year_input = st.number_input(
        "Year of Analysis", min_value=1900, max_value=2100,
        step=1, key="analysis_year",
        help=f"Target year for cost update. Latest available index year: {PCI_YEARS[-1]}."
    )
    pci_analysis = PLANT_COST_INDEX.get(int(analysis_year_input))
    if pci_analysis is None:
        # Year not in database — warn and fall back to most recent year
        st.warning(
            "Index not yet available in the database. "
            f"Value will default to most recent year ({PCI_YEARS[-1]})."
        )
        pci_analysis = PLANT_COST_INDEX[PCI_YEARS[-1]]
        effective_analysis_year = PCI_YEARS[-1]
    else:
        effective_analysis_year = int(analysis_year_input)
    st.text_input("PCI (Year of Analysis)", value=f"{pci_analysis:.2f}", disabled=True)

# --- Time Update Factor + Location ---
st.markdown("---")
col_cx4, col_cx5, col_cx6, col_cx7 = st.columns(4)

time_update_factor = pci_analysis / pci_databank if pci_databank else 0.0

with col_cx4:
    st.text_input(
        "Time Update Factor",
        value=f"{time_update_factor:.4f}",
        disabled=True,
        help="PCI(Year of Analysis) ÷ PCI(Databank Year)"
    )

with col_cx5:
    st.text_input("Project Location", key="proj_location",
                  help="Enter the target country for this project.")

with col_cx6:
    location_factor = st.number_input(
        "Location Factor", min_value=0.0, step=0.01,
        key="location_factor",
        help="Multiplier that accounts for regional cost differences (e.g. 0.97 for Brazil)."
    )

with col_cx7:
    project_capex = (
        project_costs_isbl_osbl * (1 + contingency_pct)
        * time_update_factor
        * location_factor
    )
    st.metric("Project CAPEX", fmt_curr(project_capex))

st.divider()

# ─────────────────────────────────────────────
# Additional Information
# ─────────────────────────────────────────────
st.header("Additional Information")
col_ai1, col_ai2 = st.columns(2)
with col_ai1:
    working_hours = st.number_input(
        "Working Hours per Year (h/y)",
        min_value=1.0, max_value=8760.0,
        step=10.0, key="working_hours",
        help="Operating hours per year. Maximum is 8 760 h/y (continuous operation)."
    )
with col_ai2:
    scaling_factor = st.number_input(
        "Scaling Factor",
        min_value=0.001, step=0.01,
        key="scaling_factor",
        help="Six-tenths rule exponent or other capacity scaling factor. Must be > 0."
    )
st.divider()

# ─────────────────────────────────────────────
# Variable Costs
# ─────────────────────────────────────────────
st.header("Variable Costs")

# ── Raw Materials ──────────────────────────────
st.subheader("Raw Materials")

RATE_UNITS = list(RATE_TO_PRICE_UNIT.keys())

# Load existing rows for the current scenario (if any)
existing_rm = (
    st.session_state.scenarios
    .get(st.session_state.sn_input, {})
    .get("Raw Materials", [])
)

# Build starting DataFrame — one blank row so the editor starts ready to fill
_blank_row = {"Name": None, "Unit": RATE_UNITS[0], "Price Unit": "", "Price": 0.0, "Rate": 0.0, "Rate Unit": ""}
if existing_rm:
    rm_df = pd.DataFrame(existing_rm)
    rm_df["Price Unit"] = rm_df["Unit"].map(RATE_TO_PRICE_UNIT).fillna("")
    rm_df["Rate Unit"]  = rm_df["Unit"]
    rm_df = rm_df[["Name", "Unit", "Price Unit", "Price", "Rate", "Rate Unit"]]
else:
    rm_df = pd.DataFrame([_blank_row])

rm_edited = st.data_editor(
    rm_df,
    key=f"rm_editor_{st.session_state.table_key}",
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Name":       st.column_config.TextColumn("Name",      width="large"),
        "Unit":       st.column_config.SelectboxColumn(
                          "Unit", options=RATE_UNITS,          width="small"),
        "Price Unit": st.column_config.TextColumn("Price Unit", width="small",
                          disabled=True),
        "Price":      st.column_config.NumberColumn(
                          "Price", min_value=0.0, step=0.01,
                          format="%.4f",                       width="small"),
        "Rate":       st.column_config.NumberColumn(
                          "Rate",  min_value=0.0, step=0.01,
                          format="%.5f",                       width="small"),
        "Rate Unit":  st.column_config.TextColumn("Rate Unit", width="small",
                          disabled=True),
    },
)

# Recompute the auto columns from the latest Unit selection
rm_edited = rm_edited.copy()
rm_edited["Price Unit"] = rm_edited["Unit"].map(RATE_TO_PRICE_UNIT).fillna("")
rm_edited["Rate Unit"]  = rm_edited["Unit"]

# Active rows = rows where Name is filled
rm_active = rm_edited[rm_edited["Name"].notna() & (rm_edited["Name"].str.strip() != "")].copy()
rm_active["Line Cost"] = rm_active["Price"] * rm_active["Rate"] * working_hours
total_raw_material_cost = rm_active["Line Cost"].sum()

# Total
st.markdown("---")
col_rm1, col_rm2 = st.columns([4, 1])
with col_rm1:
    st.markdown("**Total raw materials cost**")
with col_rm2:
    st.metric(label="", value=fmt_curr(total_raw_material_cost))

st.divider()

# Reference tables (PLANT_COST_INDEX, RATE_TO_PRICE_UNIT) are defined as
# constants above and used programmatically — no UI section needed.

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
            # CAPEX calculations
            "Allow Override":            st.session_state.allow_override,
            "Contingency Pct":           contingency_pct,
            "Databank Year":             int(databank_year_input),
            "Year of Analysis":          effective_analysis_year,
            "PCI Databank":              pci_databank,
            "PCI Analysis":              pci_analysis,
            "Time Update Factor":        time_update_factor,
            "Project Location":          st.session_state.proj_location,
            "Location Factor":           location_factor,
            "Project CAPEX":             project_capex,
            # Additional information
            "Working Hours per Year":    working_hours,
            "Scaling Factor":            scaling_factor,
            # Variable costs
            "Raw Materials":             rm_active.drop(columns=["Line Cost"]).to_dict(orient="records"),
            "Total Raw Material Cost":   total_raw_material_cost,
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
            "Project CAPEX":    fmt_curr(d.get("Project CAPEX", 0.0)),
            "Raw Mat. Cost":    fmt_curr(d.get("Total Raw Material Cost", 0.0)),
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
