"""ISI-Tool — Database / Reference Tables page."""
import streamlit as st
import pandas as pd
from utils.constants import (
    PRODUCT_TYPES, TRL_OPTIONS, INFO_OPTIONS, SEVERITY_OPTIONS, MAT_OPTIONS,
    UNSCHED_FACTORS, PROJECT_CONTINGENCY,
    LAB_CHARGES, OFFICE_LABOR, MAINTENANCE_REPAIRS, OPERATING_SUPPLIES,
    ADMIN_OVERHEAD, MFG_OVERHEAD, TAXES_INSURANCE,
    PATENTS_ROYALTIES, DIST_SELLING, R_AND_D,
    TIC_LOWER, TIC_UPPER, TAXES_BY_COUNTRY, CAPEX_DISTRIBUTION,
)
from utils.ui import inject_css, page_header

inject_css()

page_header("Database", "Reference tables and default values")
st.caption(
    "All reference tables used by the tool are shown below. "
    "Changes take effect immediately for new inputs — already-saved scenarios are not retroactively changed."
)

# ── Helpers ───────────────────────────────────────────────────────────────
def _get(name, hardcoded):
    return st.session_state.get(f"db_{name}", hardcoded)

def _save(name, value):
    st.session_state[f"db_{name}"] = value

def _reset(name):
    st.session_state.pop(f"db_{name}", None)


def _simple_pct_table(db_name, default_dict, row_label="Key"):
    """Render + edit a simple {key: pct_fraction} table."""
    current = _get(db_name, default_dict)
    is_modified = f"db_{db_name}" in st.session_state
    df = pd.DataFrame([
        {row_label: k, "Value (%)": round(v * 100, 4)} for k, v in current.items()
    ])
    edited = st.data_editor(
        df, key=f"editor_{db_name}", hide_index=True, use_container_width=False,
        column_config={
            row_label: st.column_config.TextColumn(disabled=True, width="medium"),
            "Value (%)": st.column_config.NumberColumn(
                min_value=0.0, max_value=100.0, step=0.01, format="%.4f", width="small"
            ),
        },
    )
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Save changes", key=f"save_{db_name}", type="primary"):
            new = {row[row_label]: row["Value (%)"] / 100.0 for _, row in edited.iterrows()}
            _save(db_name, new)
            st.success("Saved.")
    with c2:
        if is_modified:
            if st.button("Reset to default", key=f"reset_{db_name}"):
                _reset(db_name)
                st.success("Reset to default.")
        else:
            st.caption(":material/check_circle: Using default values")


def _cross_table(db_name, default_dict, row_keys, col_keys,
                 row_label="Row", col_label_text="Column",
                 scale=100.0, allow_none=False):
    """Render + edit a {(row, col): pct_fraction_or_None} table."""
    current = _get(db_name, default_dict)
    is_modified = f"db_{db_name}" in st.session_state
    rows = []
    for rk in row_keys:
        row = {row_label: rk}
        for ck in col_keys:
            v = current.get((rk, ck))
            row[ck] = round(v * scale, 4) if v is not None else None
        rows.append(row)
    df = pd.DataFrame(rows)
    col_config = {row_label: st.column_config.TextColumn(disabled=True, width="medium")}
    for ck in col_keys:
        col_config[ck] = st.column_config.NumberColumn(
            ck, step=0.01, format="%.4f", width="small"
        )
    edited = st.data_editor(
        df, key=f"editor_{db_name}", hide_index=True, use_container_width=False,
        column_config=col_config,
    )
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Save changes", key=f"save_{db_name}", type="primary"):
            new = {}
            for _, row in edited.iterrows():
                rk = row[row_label]
                for ck in col_keys:
                    v = row[ck]
                    if pd.isna(v) or v is None:
                        new[(rk, ck)] = None if allow_none else 0.0
                    else:
                        new[(rk, ck)] = v / scale
            _save(db_name, new)
            st.success("Saved.")
    with c2:
        if is_modified:
            if st.button("Reset to default", key=f"reset_{db_name}"):
                _reset(db_name)
                st.success("Reset to default.")
        else:
            st.caption(":material/check_circle: Using default values")


# ══════════════════════════════════════════════════════════════════════════════
# REFERENCE TABLES
# ══════════════════════════════════════════════════════════════════════════════

# 1. Unscheduled Equipment Factors
with st.expander("Unscheduled Equipment Factors  (fraction, by TRL × info availability)", icon=":material/precision_manufacturing:"):
    _cross_table("UNSCHED_FACTORS", UNSCHED_FACTORS,
                 TRL_OPTIONS, INFO_OPTIONS, row_label="TRL", col_label_text="Info Availability",
                 scale=1.0, allow_none=True)

# 2. Project Contingency
with st.expander("Project Contingency  (fraction, by TRL × process severity)", icon=":material/security:"):
    _cross_table("PROJECT_CONTINGENCY", PROJECT_CONTINGENCY,
                 TRL_OPTIONS, SEVERITY_OPTIONS, row_label="TRL", col_label_text="Process Severity",
                 scale=1.0)

# 3. Laboratory Charges
with st.expander("Laboratory Charges  (% of OLC, by product type)", icon=":material/science:"):
    _simple_pct_table("LAB_CHARGES", LAB_CHARGES, row_label="Product Type")

# 4. Office Labor
with st.expander("Office Labor  (% of OLC, by product type)", icon=":material/work:"):
    _simple_pct_table("OFFICE_LABOR", OFFICE_LABOR, row_label="Product Type")

# 5. Maintenance & Repairs
with st.expander("Maintenance & Repairs  (% of CAPEX, by material type × product type)", icon=":material/build:"):
    _cross_table("MAINTENANCE_REPAIRS", MAINTENANCE_REPAIRS,
                 MAT_OPTIONS, PRODUCT_TYPES, row_label="Material Type", col_label_text="Product Type")

# 6. Operating Supplies
with st.expander("Operating Supplies  (% of Maintenance, by process severity)", icon=":material/inventory:"):
    _simple_pct_table("OPERATING_SUPPLIES", OPERATING_SUPPLIES, row_label="Process Severity")

# 7. Administrative Overhead
with st.expander("Administrative Overhead  (% of OLC, by product type)", icon=":material/admin_panel_settings:"):
    _simple_pct_table("ADMIN_OVERHEAD", ADMIN_OVERHEAD, row_label="Product Type")

# 8. Manufacturing Overhead
with st.expander("Manufacturing Overhead  (% of CAPEX, by process severity)", icon=":material/factory:"):
    _simple_pct_table("MFG_OVERHEAD", MFG_OVERHEAD, row_label="Process Severity")

# 9. Taxes & Insurance
with st.expander("Taxes & Insurance  (% of CAPEX, by process severity)", icon=":material/receipt_long:"):
    _simple_pct_table("TAXES_INSURANCE", TAXES_INSURANCE, row_label="Process Severity")

# 10. Patents & Royalties
with st.expander("Patents & Royalties  (% of OPEX, by TRL × product type — blank = N/A)", icon=":material/gavel:"):
    _cross_table("PATENTS_ROYALTIES", PATENTS_ROYALTIES,
                 TRL_OPTIONS, PRODUCT_TYPES, row_label="TRL", col_label_text="Product Type",
                 allow_none=True)

# 11. Distribution & Selling
with st.expander("Distribution & Selling  (% of OPEX, by product type)", icon=":material/local_shipping:"):
    _simple_pct_table("DIST_SELLING", DIST_SELLING, row_label="Product Type")

# 12. Research & Development
with st.expander("Research & Development  (% of OPEX, by TRL × product type)", icon=":material/biotech:"):
    _cross_table("R_AND_D", R_AND_D,
                 TRL_OPTIONS, PRODUCT_TYPES, row_label="TRL", col_label_text="Product Type")

# 13. TIC Accuracy
with st.expander("TIC Accuracy — Lower Bound  (%, by TRL × info availability — blank = N/A)", icon=":material/trending_down:"):
    _cross_table("TIC_LOWER", TIC_LOWER,
                 TRL_OPTIONS, INFO_OPTIONS, row_label="TRL", col_label_text="Info Availability",
                 scale=1.0, allow_none=True)

with st.expander("TIC Accuracy — Upper Bound  (%, by TRL × info availability — blank = N/A)", icon=":material/trending_up:"):
    _cross_table("TIC_UPPER", TIC_UPPER,
                 TRL_OPTIONS, INFO_OPTIONS, row_label="TRL", col_label_text="Info Availability",
                 scale=1.0, allow_none=True)

# 14. Corporate Tax Rates by Country
with st.expander("Corporate Tax Rates by Country  (%)", icon=":material/public:"):
    current_taxes = _get("TAXES_BY_COUNTRY", TAXES_BY_COUNTRY)
    is_modified = "db_TAXES_BY_COUNTRY" in st.session_state
    df_tax = pd.DataFrame([
        {"Country": k, "Tax Rate (%)": round(v * 100, 4)}
        for k, v in sorted(current_taxes.items())
    ])
    edited_tax = st.data_editor(
        df_tax, key="editor_TAXES_BY_COUNTRY", hide_index=True, use_container_width=False,
        column_config={
            "Country": st.column_config.TextColumn("Country", disabled=True, width="medium"),
            "Tax Rate (%)": st.column_config.NumberColumn(
                "Tax Rate (%)", min_value=0.0, max_value=100.0,
                step=0.01, format="%.4f", width="small"
            ),
        },
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
            st.caption(":material/check_circle: Using default values")

# 15. CAPEX Distribution
with st.expander("CAPEX Distribution by EPC Duration  (fractions per execution year)", icon=":material/calendar_month:"):
    CAPEX_DIST_DEFAULT = CAPEX_DISTRIBUTION
    current_cd = _get("CAPEX_DISTRIBUTION", CAPEX_DIST_DEFAULT)
    is_modified_cd = "db_CAPEX_DISTRIBUTION" in st.session_state

    df_cd = current_cd.reset_index().rename(columns={"index": "Execution Year", "Execution Year": "Execution Year"})
    edited_cd = st.data_editor(
        df_cd, key="editor_CAPEX_DIST", hide_index=True, use_container_width=False,
        column_config={"Execution Year": st.column_config.TextColumn(disabled=True, width="small")}
        | {str(c): st.column_config.NumberColumn(f"EPC {c}yr", step=0.00001, format="%.6f", width="small")
           for c in range(1, 11)},
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
            st.caption(":material/check_circle: Using default values")

st.space("medium")
st.caption("All changes are stored for this session only. When the tool is reloaded, values reset to defaults.")
