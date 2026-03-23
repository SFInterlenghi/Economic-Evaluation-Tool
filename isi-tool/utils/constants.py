"""
ISI-Tool — Shared constants, reference tables, and helper functions.

Single source of truth for all economic evaluation parameters.
Imported by all pages and utils modules.
"""
import pandas as pd
import math

# ─────────────────────────────────────────────
# UNIT SYSTEM
# ─────────────────────────────────────────────
ALLOWED_UNITS = ["g", "kg", "t", "mL", "L", "m³", "kWh", "MWh", "GWh", "MMBtu"]

RATE_TO_PRICE_UNIT: dict[str, str] = {
    "g/h": "USD/g", "kg/h": "USD/kg", "t/h": "USD/t",
    "mL/h": "USD/mL", "L/h": "USD/L", "m³/h": "USD/m³",
    "kW": "USD/kWh", "MW": "USD/MWh", "GW": "USD/GWh",
    "MMBtu/h": "USD/MMBtu",
    "g/y": "USD/g", "kg/y": "USD/kg", "t/y": "USD/t",
    "mL/y": "USD/mL", "L/y": "USD/L", "m³/y": "USD/m³",
    "MMBtu/y": "USD/MMBtu",
}

RATE_UNITS  = list(RATE_TO_PRICE_UNIT.keys())
PRICE_UNITS = list(dict.fromkeys(RATE_TO_PRICE_UNIT.values()))

# ─────────────────────────────────────────────
# DECISION MAKING ASSISTANT — OPTION SETS
# ─────────────────────────────────────────────
PRODUCT_TYPES    = ["Basic Chemical", "Specialty chemical", "Consumer product", "Pharmaceutical"]
TRL_OPTIONS      = ["Industrial (8 or 9)", "Pilot (5 to 7)", "Bench (3 or 4)", "Theoretical (1 or 2)"]
INFO_OPTIONS     = ["High", "Medium", "Low"]
SEVERITY_OPTIONS = ["High", "Medium", "Low"]
MAT_OPTIONS      = ["Solids", "Fluids and solids", "Fluids"]
SIZE_OPTIONS     = ["Large", "Medium", "Small"]

# ─────────────────────────────────────────────
# INVESTMENT COST FACTORS
# ─────────────────────────────────────────────
UNSCHED_FACTORS = {
    ("Industrial (8 or 9)", "High"):   0.05,
    ("Industrial (8 or 9)", "Medium"): 0.10,
    ("Industrial (8 or 9)", "Low"):    0.15,
    ("Pilot (5 to 7)",       "Medium"): 0.15,
    ("Pilot (5 to 7)",       "Low"):    0.20,
    ("Bench (3 or 4)",       "Low"):    0.25,
    ("Theoretical (1 or 2)", "Low"):    0.30,
}

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
LANG_FIELDS = list(LANG_FACTORS.keys())

PROJECT_CONTINGENCY: dict[tuple[str, str], float] = {
    ("Industrial (8 or 9)", "Low"):    0.15, ("Industrial (8 or 9)", "Medium"): 0.20, ("Industrial (8 or 9)", "High"):   0.25,
    ("Pilot (5 to 7)",       "Low"):    0.20, ("Pilot (5 to 7)",       "Medium"): 0.25, ("Pilot (5 to 7)",       "High"):   0.30,
    ("Bench (3 or 4)",       "Low"):    0.25, ("Bench (3 or 4)",       "Medium"): 0.30, ("Bench (3 or 4)",       "High"):   0.35,
    ("Theoretical (1 or 2)", "Low"):    0.30, ("Theoretical (1 or 2)", "Medium"): 0.35, ("Theoretical (1 or 2)", "High"):   0.40,
}

# ─────────────────────────────────────────────
# OPERATING COST FACTORS
# ─────────────────────────────────────────────
LAB_CHARGES: dict[str, float] = {
    "Basic Chemical": 0.10, "Specialty chemical": 0.15,
    "Consumer product": 0.20, "Pharmaceutical": 0.25,
}
OFFICE_LABOR: dict[str, float] = {
    "Basic Chemical": 0.10, "Specialty chemical": 0.175,
    "Consumer product": 0.25, "Pharmaceutical": 0.175,
}
MIN_SALARY = 273.0

MAINTENANCE_REPAIRS: dict[tuple[str, str], float] = {
    ("Solids", "Basic Chemical"): 0.02, ("Solids", "Specialty chemical"): 0.03,
    ("Solids", "Consumer product"): 0.04, ("Solids", "Pharmaceutical"): 0.02,
    ("Fluids and solids", "Basic Chemical"): 0.015, ("Fluids and solids", "Specialty chemical"): 0.025,
    ("Fluids and solids", "Consumer product"): 0.035, ("Fluids and solids", "Pharmaceutical"): 0.015,
    ("Fluids", "Basic Chemical"): 0.01, ("Fluids", "Specialty chemical"): 0.02,
    ("Fluids", "Consumer product"): 0.03, ("Fluids", "Pharmaceutical"): 0.01,
}
OPERATING_SUPPLIES: dict[str, float] = {"High": 0.0020, "Medium": 0.0015, "Low": 0.0010}
ADMIN_OVERHEAD: dict[str, float] = {
    "Basic Chemical": 0.50, "Specialty chemical": 0.60,
    "Consumer product": 0.70, "Pharmaceutical": 0.60,
}
MFG_OVERHEAD: dict[str, float] = {"High": 0.0070, "Medium": 0.0060, "Low": 0.0050}
TAXES_INSURANCE: dict[str, float] = {"High": 0.050, "Medium": 0.032, "Low": 0.014}

PATENTS_ROYALTIES: dict[tuple[str, str], float | None] = {
    ("Industrial (8 or 9)", "Basic Chemical"): 0.010, ("Industrial (8 or 9)", "Specialty chemical"): 0.020,
    ("Industrial (8 or 9)", "Consumer product"): 0.040, ("Industrial (8 or 9)", "Pharmaceutical"): 0.060,
    ("Pilot (5 to 7)", "Basic Chemical"): None, ("Pilot (5 to 7)", "Specialty chemical"): 0.010,
    ("Pilot (5 to 7)", "Consumer product"): 0.020, ("Pilot (5 to 7)", "Pharmaceutical"): 0.030,
    ("Bench (3 or 4)", "Basic Chemical"): None, ("Bench (3 or 4)", "Specialty chemical"): 0.010,
    ("Bench (3 or 4)", "Consumer product"): 0.020, ("Bench (3 or 4)", "Pharmaceutical"): 0.030,
    ("Theoretical (1 or 2)", "Basic Chemical"): None, ("Theoretical (1 or 2)", "Specialty chemical"): 0.010,
    ("Theoretical (1 or 2)", "Consumer product"): 0.020, ("Theoretical (1 or 2)", "Pharmaceutical"): 0.030,
}
DIST_SELLING: dict[str, float] = {
    "Basic Chemical": 0.08, "Specialty chemical": 0.02,
    "Consumer product": 0.20, "Pharmaceutical": 0.14,
}
R_AND_D: dict[tuple[str, str], float] = {
    ("Industrial (8 or 9)", "Basic Chemical"): 0.020, ("Industrial (8 or 9)", "Specialty chemical"): 0.030,
    ("Industrial (8 or 9)", "Consumer product"): 0.020, ("Industrial (8 or 9)", "Pharmaceutical"): 0.120,
    ("Pilot (5 to 7)", "Basic Chemical"): 0.030, ("Pilot (5 to 7)", "Specialty chemical"): 0.050,
    ("Pilot (5 to 7)", "Consumer product"): 0.025, ("Pilot (5 to 7)", "Pharmaceutical"): 0.170,
    ("Bench (3 or 4)", "Basic Chemical"): 0.030, ("Bench (3 or 4)", "Specialty chemical"): 0.050,
    ("Bench (3 or 4)", "Consumer product"): 0.025, ("Bench (3 or 4)", "Pharmaceutical"): 0.170,
    ("Theoretical (1 or 2)", "Basic Chemical"): 0.030, ("Theoretical (1 or 2)", "Specialty chemical"): 0.050,
    ("Theoretical (1 or 2)", "Consumer product"): 0.025, ("Theoretical (1 or 2)", "Pharmaceutical"): 0.170,
}

# ─────────────────────────────────────────────
# TIC ACCURACY
# ─────────────────────────────────────────────
TIC_LOWER: dict[tuple[str, str], float | None] = {
    ("Industrial (8 or 9)", "High"): -15.0, ("Industrial (8 or 9)", "Medium"): -20.0, ("Industrial (8 or 9)", "Low"): -25.0,
    ("Pilot (5 to 7)", "High"): None, ("Pilot (5 to 7)", "Medium"): -25.0, ("Pilot (5 to 7)", "Low"): -30.0,
    ("Bench (3 or 4)", "High"): None, ("Bench (3 or 4)", "Medium"): None, ("Bench (3 or 4)", "Low"): -40.0,
    ("Theoretical (1 or 2)", "High"): None, ("Theoretical (1 or 2)", "Medium"): None, ("Theoretical (1 or 2)", "Low"): -50.0,
}
TIC_UPPER: dict[tuple[str, str], float | None] = {
    ("Industrial (8 or 9)", "High"): 20.0, ("Industrial (8 or 9)", "Medium"): 30.0, ("Industrial (8 or 9)", "Low"): 40.0,
    ("Pilot (5 to 7)", "High"): None, ("Pilot (5 to 7)", "Medium"): 40.0, ("Pilot (5 to 7)", "Low"): 50.0,
    ("Bench (3 or 4)", "High"): None, ("Bench (3 or 4)", "Medium"): None, ("Bench (3 or 4)", "Low"): 70.0,
    ("Theoretical (1 or 2)", "High"): None, ("Theoretical (1 or 2)", "Medium"): None, ("Theoretical (1 or 2)", "Low"): 100.0,
}

# ─────────────────────────────────────────────
# TAX RATES & PCI
# ─────────────────────────────────────────────
TAXES_BY_COUNTRY: dict[str, float] = {
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
COUNTRY_LIST = sorted(TAXES_BY_COUNTRY.keys())

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

CAPEX_DISTRIBUTION = pd.DataFrame({
    "1":  [1.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.000000],
    "2":  [0.60000, 0.40000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.000000],
    "3":  [0.30000, 0.50000, 0.20000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.000000],
    "4":  [0.40000, 0.30000, 0.20000, 0.10000, 0.00000, 0.00000, 0.00000, 0.00000, 0.00000, 0.000000],
    "5":  [0.30000, 0.20000, 0.20000, 0.20000, 0.10000, 0.00000, 0.00000, 0.00000, 0.00000, 0.000000],
    "6":  [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.05000, 0.00000, 0.00000, 0.00000, 0.000000],
    "7":  [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.02500, 0.02500, 0.00000, 0.00000, 0.000000],
    "8":  [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.02500, 0.01250, 0.01250, 0.00000, 0.000000],
    "9":  [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.02500, 0.01250, 0.00625, 0.00625, 0.000000],
    "10": [0.30000, 0.20000, 0.20000, 0.20000, 0.05000, 0.02500, 0.01250, 0.00625, 0.003125, 0.003125],
}, index=["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th"])
CAPEX_DISTRIBUTION.index.name = "Execution Year"

# ─────────────────────────────────────────────
# DEFAULT SESSION STATE VALUES
# ─────────────────────────────────────────────
DEFAULTS = {
    "sn_input": "", "mp_input": "", "pu_input": "kg", "pc_input": None,
    "eq_cost_src": "Manual Input", "oth_cost_src": "Manual Input",
    "lang_utility": False,
    "dm_prod_type": "Basic Chemical", "dm_trl": "Industrial (8 or 9)",
    "dm_info_avail": "Medium", "dm_severity": "Medium",
    "dm_mat_type": "Fluids", "dm_plant_size": "Medium",
    "equip_acq": 0.0, "spare_parts": 0.0, "equipment_setting": 0.0,
    "piping": 0.0, "civil": 0.0, "steel": 0.0, "instrumentals": 0.0,
    "electrical": 0.0, "insulation": 0.0, "paint": 0.0, "isbl_contrib": 100.0,
    "field_office_staff": 0.0, "construction_indirects": 0.0,
    "freight": 0.0, "taxes_and_permits": 0.0, "engineering_and_ho": 0.0,
    "ga_overheads": 0.0, "contract_fee": 0.0,
    "allow_override": False, "lang_seeded_acq": None,
    "pea_last_fingerprint": "", "pea_last_parsed": None, "pea_fmt": "",
    "databank_year": 2022, "analysis_year": PCI_YEARS[-1],
    "proj_location": "Brazil", "location_factor": 0.97,
    "working_hours": 8000.0, "scaling_factor": 0.6,
    "n_operators": 2, "operator_salary": 1247.75,
    "n_supervisors": 1, "supervisor_salary": 1660.155,
    "salary_charges": 2.2, "plant_daily_hours": 24.0, "weekly_op_days": 7.0,
    "worker_hours_shift": 8.0, "worker_shifts_week": 5.0, "worker_vacation_weeks": 4.0,
    "lab_charges_override": None, "office_labor_override": None,
    "labor_working_hrs_override": None,
    "maint_repair_override": None, "op_supplies_override": None,
    "admin_overhead_override": None, "mfg_overhead_override": None,
    "taxes_ins_override": None, "patents_roy_override": None,
    "admin_costs_override": None, "mfg_costs_override": None,
    "dist_selling_override": None, "r_and_d_override": None,
    "wc_method": "Percentage", "wc_pct": 5.0,
    "wc_equiv_cash_days": 30.0, "wc_raw_mat_days": 15.0,
    "wc_accounts_rec_days": 30.0, "wc_accrued_payroll_days": 30.0, "wc_accounts_pay_days": 30.0,
    "startup_method": "Multiple Factors", "startup_single_pct": 8.0,
    "startup_op_training_days": 150.0, "startup_commerc_pct": 5.0, "startup_inefficiency_pct": 4.0,
    "additional_costs": 0.0,
    "tic_lower_override": None, "tic_upper_override": None,
    "land_option": "Buy", "land_buy_pct_override": None, "land_rent_pct_override": None,
    "depreciation_method": "Straight Line", "depreciation_years": 10, "residual_value_pct": 20.0,
    "tax_country": "Brazil", "tax_rate_override": None,
    "financing_type": "None", "debt_ratio_pct": 50.0,
    "amortization_years": 13, "grace_period_years": 5,
    "central_bank_rate": 5.45, "credit_spread": 2.94,
    "unlevered_beta": 1.0, "market_return": 8.63, "risk_free_rate": 1.94,
    "country_risk_premium": 3.63, "us_cpi": 2.46, "country_cpi": 4.65,
    "marr_override": None,
    "epc_years": 3, "project_lifetime": 20,
    "capacity_first_year": 100.0, "capacity_intermediate": 100.0, "capacity_last_year": 100.0,
    "fixed_costs_first_year": 100.0, "fixed_costs_intermediate": 100.0, "fixed_costs_last_year": 100.0,
    "growth_main_price": 0.0, "growth_byproduct_price": 0.0,
    "growth_raw_materials": 0.0, "growth_chem_utilities": 0.0, "growth_fixed_costs": 0.0,
    "main_product_price": None,
}


# ─────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────
def fmt_curr(val: float) -> str:
    """Format value as USD currency string."""
    return f"${val:,.2f}"


def smart_fmt(v: float, unit: str = "USD") -> str:
    """Format as MMUSD if ≥1M, else standard USD."""
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.3f} MM{unit}"
    return f"${v:,.2f}"


def fmt_compact(v: float) -> str:
    """Compact format: $1.2M or $450K or $1,234."""
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


def get_pci(year: int) -> float | None:
    return PLANT_COST_INDEX.get(year)


def pci_escalate(base_cost: float, base_year: int, target_year: int) -> float | None:
    pci_base = PLANT_COST_INDEX.get(base_year)
    pci_target = PLANT_COST_INDEX.get(target_year)
    if pci_base and pci_target:
        return base_cost * (pci_target / pci_base)
    return None


def price_unit_for(rate_unit: str) -> str:
    return RATE_TO_PRICE_UNIT.get(rate_unit, "")


def coeff_unit(rate_unit: str, product_unit: str) -> str:
    _numerator = {
        "g/h": "g", "kg/h": "kg", "t/h": "t",
        "mL/h": "mL", "L/h": "L", "m³/h": "m³",
        "kW": "kWh", "MW": "MWh", "GW": "GWh", "MMBtu/h": "MMBtu",
        "g/y": "g", "kg/y": "kg", "t/y": "t",
        "mL/y": "mL", "L/y": "L", "m³/y": "m³", "MMBtu/y": "MMBtu",
    }
    num = _numerator.get(rate_unit, rate_unit.split("/")[0] if "/" in rate_unit else rate_unit)
    return f"{num}/{product_unit}"


def is_per_year(rate_unit: str) -> bool:
    return rate_unit.endswith("/y")


# ─────────────────────────────────────────────
# PLOTLY THEME (consistent across all dashboard pages)
# ─────────────────────────────────────────────
PALETTE = ["#e6a817", "#3fb950", "#58a6ff", "#f78166", "#bc8cff", "#79c0ff", "#ffa657", "#ff7b72"]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#8b949e", size=13),
    legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
    margin=dict(l=0, r=0, t=40, b=0),
    yaxis=dict(gridcolor="#21262d", tickformat="$,.0f", tickfont=dict(family="DM Mono, monospace", size=11)),
    xaxis=dict(tickfont=dict(family="DM Sans, sans-serif", size=12, color="#c9d1d9")),
)


def scenario_colors(names: list[str]) -> dict[str, str]:
    """Assign consistent palette colors to scenario names."""
    return {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(names)}


def safe_val(d: dict, k: str, default: float = 0.0) -> float:
    """Safely extract a numeric value from a scenario dict."""
    v = d.get(k, default)
    return v if isinstance(v, (int, float)) else default
