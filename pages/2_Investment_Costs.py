import streamlit as st
import pandas as pd

st.set_page_config(page_title="Investment Costs", layout="wide")
st.title("Investment Costs — Scenario Comparison")

if "scenarios" not in st.session_state or not st.session_state.scenarios:
    st.info("No scenarios saved yet. Configure and save scenarios on the Input Data page first.")
    st.stop()

scenarios = st.session_state.scenarios

def fmt(v):
    if isinstance(v, (int, float)):
        return f"${v:,.2f}"
    return str(v) if v is not None else "—"

def pct(v):
    if isinstance(v, (int, float)):
        return f"{v:.2f}%"
    return "—"

# ── Row definitions ────────────────────────────────────────────────────────
# Each entry: (indent_level, label, data_key, formatter)
# indent_level: 0 = section header, 1 = subsection, 2 = line item
ROWS = [
    # ── Equipment Costs ───────────────────────────────────────────────────
    (0, "EQUIPMENT COSTS",                   None,                       None),
    (2, "Equipment Acquisition",             "Equipment Acquisition",    fmt),
    (2, "Spare Parts",                       "Spare Parts",              fmt),
    (2, "Equipment Setting",                 "Equipment Setting",        fmt),
    (1, "Base Equipment Costs",              "Base Equipment Costs",     fmt),
    (2, "Unscheduled Equipment",             "Unscheduled Equip Pct",    pct),
    (1, "Total Equipment Costs",             "Total Equipment Costs",    fmt),
    # ── Installation Costs ────────────────────────────────────────────────
    (0, "INSTALLATION COSTS",                None,                       None),
    (2, "Piping",                            "Piping",                   fmt),
    (2, "Civil",                             "Civil",                    fmt),
    (2, "Steel",                             "Steel",                    fmt),
    (2, "Instrumentals",                     "Instrumentals",            fmt),
    (2, "Electrical",                        "Electrical",               fmt),
    (2, "Insulation",                        "Insulation",               fmt),
    (2, "Paint",                             "Paint",                    fmt),
    (1, "Total Installation Costs",          "Total Installation Costs", fmt),
    # ── Direct Field Costs ────────────────────────────────────────────────
    (0, "DIRECT FIELD COSTS",               None,                        None),
    (1, "Total Direct Field Costs",          "Total Direct Field Costs", fmt),
    (2, "ISBL Contribution",                 "ISBL Contribution (%)",    pct),
    (2, "OSBL Contribution",                 "OSBL Contribution (%)",    pct),
    # ── Indirect Field Costs ─────────────────────────────────────────────
    (0, "INDIRECT FIELD COSTS",              None,                       None),
    (2, "Field Office Staff",                "Field Office Staff",       fmt),
    (2, "Construction Indirects",            "Construction Indirects",   fmt),
    (1, "Total Indirect Field Costs",        "Total Indirect Field Costs", fmt),
    # ── Non-Field Costs ───────────────────────────────────────────────────
    (0, "NON-FIELD COSTS",                   None,                       None),
    (2, "Freight",                           "Freight",                  fmt),
    (2, "Taxes and Permits",                 "Taxes and Permits",        fmt),
    (2, "Engineering and HO",               "Engineering and HO",        fmt),
    (2, "GA Overheads",                      "GA Overheads",             fmt),
    (2, "Contract Fee",                      "Contract Fee",             fmt),
    (1, "Total Non-Field Costs",             "Total Non-Field Costs",    fmt),
    # ── CAPEX Calculations ────────────────────────────────────────────────
    (0, "CAPEX CALCULATIONS",                None,                       None),
    (1, "Project Costs (ISBL + OSBL)",       "Project Costs ISBL+OSBL",  fmt),
    (2, "Project Contingency",               "Contingency Pct",          pct),
    (2, "Time Update Factor",                "Time Update Factor",       lambda v: f"{v:.4f}" if isinstance(v, float) else "—"),
    (2, "Location Factor",                   "Location Factor",          lambda v: f"{v:.4f}" if isinstance(v, float) else "—"),
    (1, "Project CAPEX",                     "Project CAPEX",            fmt),
    # ── Working Capital ───────────────────────────────────────────────────
    (0, "WORKING CAPITAL",                   None,                       None),
    (2, "Method",                            "WC Method",                lambda v: str(v)),
    (1, "Working Capital",                   "Working Capital",          fmt),
    # ── Startup Costs ─────────────────────────────────────────────────────
    (0, "STARTUP COSTS",                     None,                       None),
    (2, "Method",                            "Startup Method",           lambda v: str(v)),
    (1, "Startup Costs",                     "Startup Costs",            fmt),
    # ── Total Investment ──────────────────────────────────────────────────
    (0, "TOTAL INVESTMENT",                  None,                       None),
    (2, "Additional Costs",                  "Additional Costs",         fmt),
    (1, "Total Investment Costs (TIC)",      "Total Investment",         fmt),
    (2, "TIC Lower Bound",                   "TIC Lower Pct",            pct),
    (2, "TIC Upper Bound",                   "TIC Upper Pct",            pct),
]

# ── Build DataFrame ────────────────────────────────────────────────────────
scenario_names = list(scenarios.keys())
col_label = "Section / Line Item"
rows_out = []

for indent, label, key, fmtr in ROWS:
    if indent == 0:
        display = f"**{label}**"
    elif indent == 1:
        display = f"  ▸ {label}"
    else:
        display = f"    {label}"

    row = {col_label: display}
    for sn in scenario_names:
        d = scenarios[sn]
        if key is None:
            row[sn] = ""
        else:
            v = d.get(key)
            row[sn] = fmtr(v) if (fmtr and v is not None) else ("—" if v is None else str(v))
    rows_out.append(row)

df = pd.DataFrame(rows_out)

# Style section headers bold via column config
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={col_label: st.column_config.TextColumn(col_label, width="large")}
    | {sn: st.column_config.TextColumn(sn, width="medium") for sn in scenario_names},
)
