import streamlit as st
import pandas as pd

st.set_page_config(page_title="Database", layout="wide")
st.title("Database — Reference Tables & Default Values")
st.caption(
    "This page shows all reference tables and default values used by the tool. "
    "Changes made here take effect immediately on the Input Data page for all new inputs. "
    "Already-saved scenarios are not retroactively changed."
)

# ── Helpers ───────────────────────────────────────────────────────────────
def _get(name, hardcoded):
    """Return the session-state version if the user has edited it, else the hardcoded value."""
    return st.session_state.get(f"db_{name}", hardcoded)

def _save(name, value):
    st.session_state[f"db_{name}"] = value

def _reset(name):
    st.session_state.pop(f"db_{name}", None)

# ── Import hardcoded constants from app module ─────────────────────────────
# We re-define them here so the DB page is self-contained.
# These are the canonical defaults — user edits are stored in session state.

UNSCHED_FACTORS_DEFAULT = {
    ("Industrial (8 or 9)", "High"):   0.05,
    ("Industrial (8 or 9)", "Medium"): 0.10,
    ("Industrial (8 or 9)", "Low"):    0.15,
    ("Pilot (5 to 7)",       "Medium"): 0.15,
    ("Pilot (5 to 7)",       "Low"):    0.20,
    ("Bench (3 or 4)",       "Low"):    0.25,
    ("Theoretical (1 or 2)", "Low"):    0.30,
}

PROJECT_CONTINGENCY_DEFAULT = {
    ("Industrial (8 or 9)", "Low"): 0.15, ("Industrial (8 or 9)", "Medium"): 0.20, ("Industrial (8 or 9)", "High"): 0.25,
    ("Pilot (5 to 7)",       "Low"): 0.20, ("Pilot (5 to 7)",       "Medium"): 0.25, ("Pilot (5 to 7)",       "High"): 0.30,
    ("Bench (3 or 4)",       "Low"): 0.25, ("Bench (3 or 4)",       "Medium"): 0.30, ("Bench (3 or 4)",       "High"): 0.35,
    ("Theoretical (1 or 2)", "Low"): 0.30, ("Theoretical (1 or 2)", "Medium"): 0.35, ("Theoretical (1 or 2)", "High"): 0.40,
}

LAB_CHARGES_DEFAULT         = {"Basic Chemical": 0.10, "Specialty chemical": 0.15, "Consumer product": 0.20, "Pharmaceutical": 0.25}
OFFICE_LABOR_DEFAULT        = {"Basic Chemical": 0.10, "Specialty chemical": 0.175, "Consumer product": 0.25, "Pharmaceutical": 0.175}
ADMIN_OVERHEAD_DEFAULT      = {"Basic Chemical": 0.50, "Specialty chemical": 0.60, "Consumer product": 0.70, "Pharmaceutical": 0.60}
DIST_SELLING_DEFAULT        = {"Basic Chemical": 0.08, "Specialty chemical": 0.02, "Consumer product": 0.20, "Pharmaceutical": 0.14}
OPERATING_SUPPLIES_DEFAULT  = {"High": 0.0020, "Medium": 0.0015, "Low": 0.0010}
MFG_OVERHEAD_DEFAULT        = {"High": 0.0070, "Medium": 0.0060, "Low": 0.0050}
TAXES_INSURANCE_DEFAULT     = {"High": 0.050,  "Medium": 0.032,  "Low": 0.014}

MAINTENANCE_REPAIRS_DEFAULT = {
    ("Solids",           "Basic Chemical"): 0.020, ("Solids",           "Specialty chemical"): 0.030,
    ("Solids",           "Consumer product"): 0.040, ("Solids",           "Pharmaceutical"): 0.020,
    ("Fluids and solids","Basic Chemical"): 0.015, ("Fluids and solids","Specialty chemical"): 0.025,
    ("Fluids and solids","Consumer product"): 0.035, ("Fluids and solids","Pharmaceutical"): 0.015,
    ("Fluids",           "Basic Chemical"): 0.010, ("Fluids",           "Specialty chemical"): 0.020,
    ("Fluids",           "Consumer product"): 0.030, ("Fluids",           "Pharmaceutical"): 0.010,
}

PATENTS_ROYALTIES_DEFAULT = {
    ("Industrial (8 or 9)", "Basic Chemical"): 0.010, ("Industrial (8 or 9)", "Specialty chemical"): 0.020,
    ("Industrial (8 or 9)", "Consumer product"): 0.040, ("Industrial (8 or 9)", "Pharmaceutical"): 0.060,
    ("Pilot (5 to 7)",       "Basic Chemical"): None,   ("Pilot (5 to 7)",       "Specialty chemical"): 0.010,
    ("Pilot (5 to 7)",       "Consumer product"): 0.020, ("Pilot (5 to 7)",       "Pharmaceutical"): 0.030,
    ("Bench (3 or 4)",       "Basic Chemical"): None,   ("Bench (3 or 4)",       "Specialty chemical"): 0.010,
    ("Bench (3 or 4)",       "Consumer product"): 0.020, ("Bench (3 or 4)",       "Pharmaceutical"): 0.030,
    ("Theoretical (1 or 2)", "Basic Chemical"): None,   ("Theoretical (1 or 2)", "Specialty chemical"): 0.010,
    ("Theoretical (1 or 2)", "Consumer product"): 0.020, ("Theoretical (1 or 2)", "Pharmaceutical"): 0.030,
}

R_AND_D_DEFAULT = {
    ("Industrial (8 or 9)", "Basic Chemical"): 0.020, ("Industrial (8 or 9)", "Specialty chemical"): 0.030,
    ("Industrial (8 or 9)", "Consumer product"): 0.020, ("Industrial (8 or 9)", "Pharmaceutical"): 0.120,
    ("Pilot (5 to 7)",       "Basic Chemical"): 0.030, ("Pilot (5 to 7)",       "Specialty chemical"): 0.050,
    ("Pilot (5 to 7)",       "Consumer product"): 0.025, ("Pilot (5 to 7)",       "Pharmaceutical"): 0.170,
    ("Bench (3 or 4)",       "Basic Chemical"): 0.030, ("Bench (3 or 4)",       "Specialty chemical"): 0.050,
    ("Bench (3 or 4)",       "Consumer product"): 0.025, ("Bench (3 or 4)",       "Pharmaceutical"): 0.170,
    ("Theoretical (1 or 2)", "Basic Chemical"): 0.030, ("Theoretical (1 or 2)", "Specialty chemical"): 0.050,
    ("Theoretical (1 or 2)", "Consumer product"): 0.025, ("Theoretical (1 or 2)", "Pharmaceutical"): 0.170,
}

TIC_LOWER_DEFAULT = {
    ("Industrial (8 or 9)", "High"): -15.0, ("Industrial (8 or 9)", "Medium"): -20.0, ("Industrial (8 or 9)", "Low"): -25.0,
    ("Pilot (5 to 7)",       "High"): None,  ("Pilot (5 to 7)",       "Medium"): -25.0, ("Pilot (5 to 7)",       "Low"): -30.0,
    ("Bench (3 or 4)",       "High"): None,  ("Bench (3 or 4)",       "Medium"): None,  ("Bench (3 or 4)",       "Low"): -40.0,
    ("Theoretical (1 or 2)", "High"): None,  ("Theoretical (1 or 2)", "Medium"): None,  ("Theoretical (1 or 2)", "Low"): -50.0,
}

TIC_UPPER_DEFAULT = {
    ("Industrial (8 or 9)", "High"): 20.0, ("Industrial (8 or 9)", "Medium"): 30.0, ("Industrial (8 or 9)", "Low"): 40.0,
    ("Pilot (5 to 7)",       "High"): None, ("Pilot (5 to 7)",       "Medium"): 40.0, ("Pilot (5 to 7)",       "Low"): 50.0,
    ("Bench (3 or 4)",       "High"): None, ("Bench (3 or 4)",       "Medium"): None, ("Bench (3 or 4)",       "Low"): 70.0,
    ("Theoretical (1 or 2)", "High"): None, ("Theoretical (1 or 2)", "Medium"): None, ("Theoretical (1 or 2)", "Low"): 100.0,
}

TAXES_BY_COUNTRY_DEFAULT = {
    "Brazil": 0.340, "United States": 0.258, "Albania": 0.150, "Andorra": 0.100,
    "Angola": 0.250, "Anguilla": 0.000, "Argentina": 0.300, "Armenia": 0.180,
    "Aruba": 0.250, "Australia": 0.300, "Austria": 0.250, "Bahamas": 0.000,
    "Bahrain": 0.000, "Barbados": 0.055, "Belgium": 0.250, "Belize": 0.000,
    "Bermuda": 0.000, "Bosnia and Herzegovina": 0.100, "Botswana": 0.220,
    "British Virgin Islands": 0.000, "Brunei Darussalam": 0.185, "Bulgaria": 0.100,
    "Burkina Faso": 0.275, "Canada": 0.262, "Cayman Islands": 0.000, "Chile": 0.100,
    "China (People's Republic of)": 0.250, "Colombia": 0.310, "Costa Rica": 0.300,
    "Côte d'Ivoire": 0.250, "Croatia": 0.180, "Curacao": 0.220, "Czech Republic": 0.190,
    "Democratic Republic of the Congo": 0.300, "Denmark": 0.220, "Dominica": 0.250,
    "Egypt": 0.225, "Estonia": 0.200, "Eswatini": 0.275, "Faeroe Islands": 0.180,
    "Finland": 0.200, "France": 0.284, "Gabon": 0.300, "Georgia": 0.150,
    "Germany": 0.299, "Greece": 0.240, "Greenland": 0.265, "Grenada": 0.280,
    "Guernsey": 0.000, "Hong Kong, China": 0.165, "Hungary": 0.090, "Iceland": 0.200,
    "India": 0.252, "Indonesia": 0.220, "Ireland": 0.125, "Isle of Man": 0.000,
    "Israel": 0.230, "Italy": 0.278, "Jamaica": 0.250, "Japan": 0.297,
    "Jersey": 0.000, "Kenya": 0.300, "Korea": 0.275, "Latvia": 0.200,
    "Liberia": 0.250, "Liechtenstein": 0.125, "Lithuania": 0.150, "Luxembourg": 0.249,
    "Macau, China": 0.120, "Malaysia": 0.240, "Maldives": 0.150, "Malta": 0.350,
    "Mauritius": 0.150, "Mexico": 0.300, "Monaco": 0.265, "Montserrat": 0.300,
    "Namibia": 0.320, "Netherlands": 0.250, "New Zealand": 0.280, "Nigeria": 0.300,
    "North Macedonia": 0.100, "Norway": 0.220, "Oman": 0.150, "Panama": 0.250,
    "Paraguay": 0.100, "Peru": 0.295, "Poland": 0.190, "Portugal": 0.315,
    "Romania": 0.160, "Russia": 0.200, "Saint Lucia": 0.300,
    "Saint Vincent and the Grenadines": 0.300, "San Marino": 0.170,
    "Saudi Arabia": 0.200, "Senegal": 0.300, "Serbia": 0.150, "Seychelles": 0.300,
    "Singapore": 0.170, "Slovak Republic": 0.210, "Slovenia": 0.190,
    "South Africa": 0.280, "Spain": 0.250, "Sweden": 0.206, "Switzerland": 0.197,
    "Thailand": 0.200, "Türkiye": 0.250, "Turks and Caicos Islands": 0.000,
    "United Arab Emirates": 0.000, "United Kingdom": 0.190, "Uruguay": 0.250,
    "Vietnam": 0.200,
}

# ── Helper: render a simple key→pct table as editable ─────────────────────
def _simple_pct_table(db_key, default, row_label="Category", scale=100.0):
    """Render a dict[str, float] as an editable dataframe. Returns the edited dict."""
    current = _get(db_key, default)
    is_modified = f"db_{db_key}" in st.session_state

    df = pd.DataFrame([
        {row_label: k, "Value (%)": round((v or 0.0) * scale, 6)}
        for k, v in current.items()
    ])
    edited = st.data_editor(
        df, key=f"editor_{db_key}", hide_index=True, use_container_width=False,
        column_config={
            row_label: st.column_config.TextColumn(row_label, disabled=True, width="medium"),
            "Value (%)": st.column_config.NumberColumn("Value (%)", min_value=None, step=0.001, format="%.4f", width="small"),
        }
    )
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Save changes", key=f"save_{db_key}", type="primary"):
            new_dict = {row[row_label]: row["Value (%)"] / scale for _, row in edited.iterrows()}
            _save(db_key, new_dict)
            st.success("Saved.")
    with col2:
        if is_modified:
            if st.button("Reset to default", key=f"reset_{db_key}"):
                _reset(db_key)
                st.success("Reset to default.")
        else:
            st.caption("✓ Using default values")

# ── Helper: render a (trl, category) cross-table ───────────────────────────
TRL_OPTIONS = ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"]
PRODUCT_TYPES = ["Basic Chemical", "Specialty chemical", "Consumer product", "Pharmaceutical"]
INFO_OPTIONS = ["High", "Medium", "Low"]

def _cross_table(db_key, default, row_keys, col_keys, row_label="TRL", col_label_text="Type", scale=100.0, allow_none=False):
    """Render a dict[(row,col), float|None] as a cross-table editor."""
    current = _get(db_key, default)
    is_modified = f"db_{db_key}" in st.session_state

    rows = []
    for r in row_keys:
        row = {row_label: r}
        for c in col_keys:
            v = current.get((r, c))
            row[c] = None if v is None else round(v * scale, 6)
        rows.append(row)

    df = pd.DataFrame(rows)
    col_cfg = {row_label: st.column_config.TextColumn(row_label, disabled=True, width="medium")}
    for c in col_keys:
        col_cfg[c] = st.column_config.NumberColumn(c, min_value=None, step=0.001, format="%.4f", width="small")

    edited = st.data_editor(df, key=f"editor_{db_key}", hide_index=True, use_container_width=False, column_config=col_cfg)

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Save changes", key=f"save_{db_key}", type="primary"):
            new_dict = {}
            for _, row in edited.iterrows():
                r = row[row_label]
                for c in col_keys:
                    v = row[c]
                    new_dict[(r, c)] = None if (allow_none and (v is None or pd.isna(v))) else (float(v) / scale if v is not None and not pd.isna(v) else None)
            _save(db_key, new_dict)
            st.success("Saved.")
    with c2:
        if is_modified:
            if st.button("Reset to default", key=f"reset_{db_key}"):
                _reset(db_key)
                st.success("Reset to default.")
        else:
            st.caption("✓ Using default values")

# ══════════════════════════════════════════════════════════════════════════════
# SECTIONS
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. Unscheduled Equipment Factors ─────────────────────────────────────────
with st.expander("Unscheduled Equipment Factors  (TRL × Information Availability → % of base equip costs)"):
    _cross_table("UNSCHED_FACTORS", UNSCHED_FACTORS_DEFAULT,
                 TRL_OPTIONS, INFO_OPTIONS, row_label="TRL", col_label_text="Info Availability")

# ── 2. Project Contingency ────────────────────────────────────────────────────
with st.expander("Project Contingency  (TRL × Process Severity → %)"):
    _cross_table("PROJECT_CONTINGENCY", PROJECT_CONTINGENCY_DEFAULT,
                 TRL_OPTIONS, ["Low", "Medium", "High"], row_label="TRL", col_label_text="Severity")

# ── 3. Laboratory Charges ─────────────────────────────────────────────────────
with st.expander("Laboratory Charges  (% of OLC, by product type)"):
    _simple_pct_table("LAB_CHARGES", LAB_CHARGES_DEFAULT, row_label="Product Type")

# ── 4. Office Labor ───────────────────────────────────────────────────────────
with st.expander("Office Labor  (% of OLC, by product type)"):
    _simple_pct_table("OFFICE_LABOR", OFFICE_LABOR_DEFAULT, row_label="Product Type")

# ── 5. Maintenance & Repairs ──────────────────────────────────────────────────
with st.expander("Maintenance & Repairs  (% of CAPEX, by material type × product type)"):
    MAT_OPTIONS = ["Solids", "Fluids and solids", "Fluids"]
    _cross_table("MAINTENANCE_REPAIRS", MAINTENANCE_REPAIRS_DEFAULT,
                 MAT_OPTIONS, PRODUCT_TYPES, row_label="Material Type", col_label_text="Product Type")

# ── 6. Operating Supplies ─────────────────────────────────────────────────────
with st.expander("Operating Supplies  (% of Maintenance, by process severity)"):
    _simple_pct_table("OPERATING_SUPPLIES", OPERATING_SUPPLIES_DEFAULT, row_label="Process Severity")

# ── 7. Administrative Overhead ────────────────────────────────────────────────
with st.expander("Administrative Overhead  (% of OLC, by product type)"):
    _simple_pct_table("ADMIN_OVERHEAD", ADMIN_OVERHEAD_DEFAULT, row_label="Product Type")

# ── 8. Manufacturing Overhead ─────────────────────────────────────────────────
with st.expander("Manufacturing Overhead  (% of CAPEX, by process severity)"):
    _simple_pct_table("MFG_OVERHEAD", MFG_OVERHEAD_DEFAULT, row_label="Process Severity")

# ── 9. Taxes & Insurance ──────────────────────────────────────────────────────
with st.expander("Taxes & Insurance  (% of CAPEX, by process severity)"):
    _simple_pct_table("TAXES_INSURANCE", TAXES_INSURANCE_DEFAULT, row_label="Process Severity")

# ── 10. Patents & Royalties ───────────────────────────────────────────────────
with st.expander("Patents & Royalties  (% of OPEX, by TRL × product type — blank = N/A)"):
    _cross_table("PATENTS_ROYALTIES", PATENTS_ROYALTIES_DEFAULT,
                 TRL_OPTIONS, PRODUCT_TYPES, row_label="TRL", col_label_text="Product Type",
                 allow_none=True)

# ── 11. Distribution & Selling ────────────────────────────────────────────────
with st.expander("Distribution & Selling  (% of OPEX, by product type)"):
    _simple_pct_table("DIST_SELLING", DIST_SELLING_DEFAULT, row_label="Product Type")

# ── 12. Research & Development ────────────────────────────────────────────────
with st.expander("Research & Development  (% of OPEX, by TRL × product type)"):
    _cross_table("R_AND_D", R_AND_D_DEFAULT,
                 TRL_OPTIONS, PRODUCT_TYPES, row_label="TRL", col_label_text="Product Type")

# ── 13. TIC Accuracy ──────────────────────────────────────────────────────────
with st.expander("TIC Accuracy — Lower Bound  (%, by TRL × information availability — blank = N/A)"):
    _cross_table("TIC_LOWER", TIC_LOWER_DEFAULT,
                 TRL_OPTIONS, INFO_OPTIONS, row_label="TRL", col_label_text="Info Availability",
                 scale=1.0, allow_none=True)

with st.expander("TIC Accuracy — Upper Bound  (%, by TRL × information availability — blank = N/A)"):
    _cross_table("TIC_UPPER", TIC_UPPER_DEFAULT,
                 TRL_OPTIONS, INFO_OPTIONS, row_label="TRL", col_label_text="Info Availability",
                 scale=1.0, allow_none=True)

# ── 14. Corporate Tax Rates by Country ───────────────────────────────────────
with st.expander("Corporate Tax Rates by Country  (%)"):
    current_taxes = _get("TAXES_BY_COUNTRY", TAXES_BY_COUNTRY_DEFAULT)
    is_modified = "db_TAXES_BY_COUNTRY" in st.session_state
    df_tax = pd.DataFrame([
        {"Country": k, "Tax Rate (%)": round(v * 100, 4)}
        for k, v in sorted(current_taxes.items())
    ])
    edited_tax = st.data_editor(
        df_tax, key="editor_TAXES_BY_COUNTRY", hide_index=True, use_container_width=False,
        column_config={
            "Country":      st.column_config.TextColumn("Country", disabled=True, width="medium"),
            "Tax Rate (%)": st.column_config.NumberColumn("Tax Rate (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.4f", width="small"),
        }
    )
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Save changes", key="save_TAXES_BY_COUNTRY", type="primary"):
            new_taxes = {row["Country"]: row["Tax Rate (%)"] / 100.0 for _, row in edited_tax.iterrows()}
            _save("TAXES_BY_COUNTRY", new_taxes)
            st.success("Saved.")
    with c2:
        if is_modified:
            if st.button("Reset to default", key="reset_TAXES_BY_COUNTRY"):
                _reset("TAXES_BY_COUNTRY")
                st.success("Reset to default.")
        else:
            st.caption("✓ Using default values")

# ── 15. CAPEX Distribution ────────────────────────────────────────────────────
with st.expander("CAPEX Distribution by EPC Duration (fractions per execution year)"):
    CAPEX_DIST_DEFAULT = pd.DataFrame({
        "1":  [1.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000,  0.000000],
        "2":  [0.60000, 0.40000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000,  0.000000],
        "3":  [0.30000, 0.50000, 0.20000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000,  0.000000],
        "4":  [0.40000, 0.30000, 0.20000, 0.10000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000,  0.000000],
        "5":  [0.30000, 0.20000, 0.20000, 0.20000, 0.10000, 0.00000, 0.00000, 0.00000, 0.00000,  0.000000],
        "6":  [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.05000, 0.00000, 0.00000, 0.00000,  0.000000],
        "7":  [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.02500, 0.02500, 0.00000, 0.00000,  0.000000],
        "8":  [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.02500, 0.01250, 0.01250, 0.00000,  0.000000],
        "9":  [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.02500, 0.01250, 0.00625, 0.00625,  0.000000],
        "10": [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.02500, 0.01250, 0.00625, 0.003125, 0.003125],
    }, index=["1st","2nd","3rd","4th","5th","6th","7th","8th","9th","10th"])

    current_cd = _get("CAPEX_DISTRIBUTION", CAPEX_DIST_DEFAULT)
    is_modified_cd = "db_CAPEX_DISTRIBUTION" in st.session_state

    df_cd = current_cd.reset_index().rename(columns={"index": "Execution Year", "Execution Year": "Execution Year"})
    edited_cd = st.data_editor(
        df_cd, key="editor_CAPEX_DIST", hide_index=True, use_container_width=False,
        column_config={"Execution Year": st.column_config.TextColumn(disabled=True, width="small")}
        | {str(c): st.column_config.NumberColumn(f"EPC {c}yr", step=0.00001, format="%.6f", width="small") for c in range(1, 11)}
    )
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Save changes", key="save_CAPEX_DIST", type="primary"):
            new_cd = edited_cd.set_index("Execution Year")
            _save("CAPEX_DISTRIBUTION", new_cd)
            st.success("Saved.")
    with c2:
        if is_modified_cd:
            if st.button("Reset to default", key="reset_CAPEX_DIST"):
                _reset("CAPEX_DISTRIBUTION")
                st.success("Reset to default.")
        else:
            st.caption("✓ Using default values")

st.divider()
st.caption("All changes are stored for this session only. When the tool is reloaded, values reset to defaults.")
