import streamlit as st
import pandas as pd

st.set_page_config(page_title="Operating Expenses", layout="wide")
st.title("Operating Expenses (OPEX) — Scenario Comparison")

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
        return f"{v:.4f}%"
    return "—"

# ── Row definitions ────────────────────────────────────────────────────────
ROWS = [
    # ── Variable Costs ────────────────────────────────────────────────────
    (0, "VARIABLE COSTS",                    None,                              None),
    (2, "Raw Materials",                     "Total Raw Material Cost",         fmt),
    (2, "Chemical Inputs & Utilities",       "Total Chemical Inputs Utilities", fmt),
    (2, "Credits & Byproducts (−)",          "Total Revenue",                   fmt),
    (1, "Total Variable Costs",              None,                              None),  # computed below
    # ── Labor Costs ───────────────────────────────────────────────────────
    (0, "FIXED COSTS — LABOR",               None,                              None),
    (2, "Operating Labor Costs (OLC)",       "OLC",                             fmt),
    (2, "Laboratory Charges",                "Lab Charges Pct",                 pct),
    (2, "Office Labor",                      "Office Labor Pct",                pct),
    (1, "Total Labor Costs",                 "Total Labor Costs",               fmt),
    # ── Supply & Maintenance ──────────────────────────────────────────────
    (0, "SUPPLY & MAINTENANCE",              None,                              None),
    (2, "Maintenance & Repairs",             "Maint Pct",                       pct),
    (2, "Operating Supplies",               "Op Sup Pct",                       pct),
    (1, "Supply & Maintenance Costs",        "Supply Maint Costs",              fmt),
    # ── Additional Fixed Costs (AFC) ──────────────────────────────────────
    (0, "ADDITIONAL FIXED COSTS (AFC)",     None,                               None),
    (2, "Administrative Overhead",          "Admin Ov Pct",                     pct),
    (2, "Manufacturing Overhead",           "Mfg Ov Pct",                       pct),
    (2, "Taxes & Insurance",                "Taxes Ins Pct",                    pct),
    (2, "Patents & Royalties",              "Patents Pct",                       pct),
    (1, "Additional Fixed Costs",           "AFC Pre Patents",                   fmt),
    (1, "Direct Fixed Costs",               "Direct Fixed Costs",               fmt),
    # ── Indirect Fixed Costs ─────────────────────────────────────────────
    (0, "INDIRECT FIXED COSTS",             None,                               None),
    (2, "Administrative Costs",             "Admin Costs Pct",                  pct),
    (2, "Manufacturing Costs",              "Mfg Costs Pct",                    pct),
    (2, "Distribution & Selling",           "Dist Sell Pct",                    pct),
    (2, "Research & Development",           "R D Pct",                          pct),
    (1, "Indirect Fixed Costs",             "Indirect Fixed Costs",             fmt),
    # ── Totals ────────────────────────────────────────────────────────────
    (0, "TOTALS",                           None,                               None),
    (1, "Total Fixed Costs",                "Total Fixed Costs",                fmt),
    (1, "Total OPEX",                       "Total OPEX",                       fmt),
]

col_label = "Section / Line Item"
scenario_names = list(scenarios.keys())
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
            # Special computed rows
            if label == "Total Variable Costs":
                tvc = (d.get("Total Raw Material Cost", 0)
                       + d.get("Total Chemical Inputs Utilities", 0)
                       - d.get("Total Revenue", 0))
                row[sn] = fmt(tvc)
            else:
                row[sn] = ""
        else:
            v = d.get(key)
            row[sn] = fmtr(v) if (fmtr and v is not None) else ("—" if v is None else str(v))
    rows_out.append(row)

df = pd.DataFrame(rows_out)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={col_label: st.column_config.TextColumn(col_label, width="large")}
    | {sn: st.column_config.TextColumn(sn, width="medium") for sn in scenario_names},
)
