"""
ISI-Tool — Finance Engine (pure computation, no Streamlit dependency).

Provides deterministic cash-flow construction, NPV/IRR solvers,
and all financial KPI calculations.  Every function is stateless:
pass in a params dict, get back numbers.

Used by:
  - cash_flow.py  (main analysis page)
  - risk_sensitivity.py  (tornado, surface, Monte Carlo)
  - multi_criteria.py  (MCA / TOPSIS scoring)
"""
import math
import numpy as np

try:
    import numpy_financial as npf
    _HAS_NPF = True
except ImportError:
    _HAS_NPF = False

try:
    from scipy.optimize import brentq
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

from utils.constants import CAPEX_DISTRIBUTION

# ─────────────────────────────────────────────────────────────────────────────
# UNIT CONVERSION (mirrors cash_flow.py / input_data.py)
# ─────────────────────────────────────────────────────────────────────────────
_QTY_TO_BASE = {
    "g": 1e-3, "kg": 1.0, "t": 1e3, "lb": 0.453592, "oz": 0.0283495,
    "mL": 1e-6, "L": 1e-3, "m3": 1.0, "gal": 0.00378541,
    "J": 1/3_600_000, "kJ": 1/3_600, "MJ": 1/3.6,
    "kWh": 1.0, "MWh": 1_000.0, "BTU": 1/3412.14,
    "mol": 1.0, "kmol": 1_000.0,
    "W": 1e-3, "kW": 1.0, "MW": 1_000.0,
}
_TIME_TO_PER_HOUR = {"s": 3600.0, "min": 60.0, "h": 1.0, "day": 1/24}
_PRICE_UNIT_TO_QTY = {
    "$/g": "g", "$/kg": "kg", "$/t": "t", "$/lb": "lb", "$/oz": "oz",
    "$/mL": "mL", "$/L": "L", "$/m3": "m3", "$/gal": "gal",
    "$/J": "J", "$/kJ": "kJ", "$/MJ": "MJ", "$/kWh": "kWh",
    "$/MWh": "MWh", "$/BTU": "BTU",
    "$/mol": "mol", "$/kmol": "kmol",
}


def annual_qty(rate: float, rate_unit: str, working_hours: float) -> float:
    """Convert rate + unit to annual quantity in base unit (kg/m³/kWh/mol)."""
    if not rate_unit:
        return rate * working_hours
    if rate_unit in ("W", "kW", "MW"):
        return rate * _QTY_TO_BASE[rate_unit] * working_hours
    if "/" not in rate_unit:
        return rate * working_hours
    qty, time = rate_unit.split("/", 1)
    qty_f = _QTY_TO_BASE.get(qty, 1.0)
    if time == "year":
        return rate * qty_f
    time_f = _TIME_TO_PER_HOUR.get(time, 1.0)
    return rate * qty_f * time_f * working_hours


def price_per_base(price: float, price_unit: str) -> float:
    """Convert user price to price per base unit (e.g. $/lb → $/kg)."""
    qty_label = _PRICE_UNIT_TO_QTY.get(price_unit)
    if qty_label is None:
        return price
    factor = _QTY_TO_BASE.get(qty_label, 1.0)
    return price / factor if factor else price


def line_cost(rate: float, rate_unit: str, price: float,
              price_unit: str, working_hours: float) -> float:
    """Annual line cost USD/year using full dimensional conversion."""
    return annual_qty(rate, rate_unit, working_hours) * price_per_base(price, price_unit)


# ─────────────────────────────────────────────────────────────────────────────
# MACRS TABLES
# ─────────────────────────────────────────────────────────────────────────────
MACRS = {
    3:  [0.3333, 0.4445, 0.1481, 0.0741],
    5:  [0.2000, 0.3200, 0.1920, 0.1152, 0.1152, 0.0576],
    7:  [0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446],
    10: [0.1000, 0.1800, 0.1440, 0.1152, 0.0922, 0.0737, 0.0655, 0.0655,
         0.0656, 0.0655, 0.0328],
    15: [0.0500, 0.0950, 0.0855, 0.0770, 0.0693, 0.0623, 0.0590, 0.0590,
         0.0591, 0.0590, 0.0591, 0.0590, 0.0591, 0.0590, 0.0591, 0.0295],
    20: [0.0375, 0.0722, 0.0668, 0.0618, 0.0571, 0.0528, 0.0489, 0.0452,
         0.0446, 0.0446, 0.0446, 0.0446, 0.0446, 0.0446, 0.0446, 0.0446,
         0.0446, 0.0446, 0.0446, 0.0446, 0.0223],
}


# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────
def _sv(d: dict, k: str, default=0.0):
    """Safe numeric value from dict."""
    v = d.get(k, default)
    return v if isinstance(v, (int, float)) else default


def extract_params(scenario: dict, wif: dict | None = None,
                   fin: dict | None = None) -> dict:
    """
    Build a flat parameter dict from a saved scenario, optional what-if
    overrides, and optional financial assumption overrides.

    This is the single entry point for all computation — every downstream
    function takes this dict.
    """
    d = scenario
    w = wif or {}
    f = fin or {}

    def _w(key, default=0.0):
        if key in w:
            return w[key]
        v = d.get(key, default)
        return v if isinstance(v, (int, float)) else default

    def _f(key, default=0.0):
        if key in f:
            return f[key]
        v = d.get(key, default)
        return v if isinstance(v, (int, float)) else default

    # ── Core dimensions ──────────────────────────────────────────────────
    capacity = _w("Capacity", _sv(d, "Capacity"))
    working_hours = _w("Working Hours per Year", _sv(d, "Working Hours per Year", 8000.0))
    capex = _w("Project CAPEX", _sv(d, "Project CAPEX"))
    wc = _w("Working Capital", _sv(d, "Working Capital"))
    startup = _w("Startup Costs", _sv(d, "Startup Costs"))
    isbl_osbl = _sv(d, "Project Costs ISBL+OSBL")

    # ── Variable costs (from working prices if present) ──────────────────
    base_cap = _sv(d, "Capacity", 1.0) or 1.0
    cap_ratio = capacity / base_cap if base_cap > 0 else 1.0

    rm_base = _sv(d, "Total Raw Material Cost") * cap_ratio
    cu_base = _sv(d, "Total Chemical Inputs Utilities") * cap_ratio

    # Byproduct revenue from line items (with unit conversion)
    bp_base = 0.0
    for r in (d.get("Credits and Byproducts", []) or []):
        if not r.get("Name"):
            continue
        bp_base += line_cost(
            float(r.get("Rate", 0.0)), r.get("Rate Unit", ""),
            float(r.get("Price", 0.0)), r.get("Price Unit", ""),
            working_hours,
        )

    # ── Fixed costs ──────────────────────────────────────────────────────
    # Labor
    n_ops = _w("Num Operators", d.get("Num Operators", 2))
    op_sal = _w("Operator Salary", d.get("Operator Salary", 1247.75))
    n_sups = _w("Num Supervisors", d.get("Num Supervisors", 1))
    sup_sal = _w("Supervisor Salary", d.get("Supervisor Salary", 1660.155))
    sal_charges = _w("Salary Charges", d.get("Salary Charges", 2.2))
    op_team = d.get("Operating Team Factor", 5)
    olc = (n_ops * op_sal + n_sups * sup_sal) * sal_charges * op_team * 12.0

    lab_pct = _w("Lab Charges Pct", _sv(d, "Lab Charges Pct"))
    off_pct = _w("Office Labor Pct", _sv(d, "Office Labor Pct"))
    labor = olc * (1.0 + lab_pct + off_pct)

    # Supply & maintenance
    maint_pct = _w("Maint Pct", _sv(d, "Maint Pct"))
    op_sup_pct = _w("Op Sup Pct", _sv(d, "Op Sup Pct"))

    # AFC percentages
    admin_ov = _w("Admin Ov Pct", _sv(d, "Admin Ov Pct"))
    mfg_ov = _w("Mfg Ov Pct", _sv(d, "Mfg Ov Pct"))
    taxes_ins = _w("Taxes Ins Pct", _sv(d, "Taxes Ins Pct"))
    patents = _w("Patents Pct", _sv(d, "Patents Pct"))

    # Indirect percentages
    admin_costs = _w("Admin Costs Pct", _sv(d, "Admin Costs Pct"))
    mfg_costs = _w("Mfg Costs Pct", _sv(d, "Mfg Costs Pct"))
    dist_sell = _w("Dist Sell Pct", _sv(d, "Dist Sell Pct"))
    r_d = _w("R D Pct", _sv(d, "R D Pct"))

    # Determine whether to re-derive or use stored values.
    # When what-if overrides change CAPEX-dependent quantities, we must
    # re-derive from percentages × new CAPEX. Otherwise, use the stored
    # values from the input pipeline (which may have used a different base).
    _has_wif = bool(w)
    if _has_wif:
        supply_maint = (maint_pct + op_sup_pct) * capex
        # OPEX analytical solve
        tvc_for_opex = rm_base + cu_base
        olc_coeff = admin_ov + admin_costs
        capex_coeff = mfg_ov + taxes_ins + mfg_costs
        num = tvc_for_opex + labor + supply_maint + olc_coeff * olc + capex_coeff * capex
        den = 1.0 - patents - dist_sell - r_d
        opex = num / den if den > 0 else 0.0
        afc = admin_ov * olc + (mfg_ov + taxes_ins) * capex + patents * opex
        indirect = admin_costs * olc + mfg_costs * capex + (dist_sell + r_d) * opex
    else:
        # Use stored values from input pipeline
        supply_maint = _sv(d, "Supply Maint Costs")
        afc = _sv(d, "AFC Pre Patents")
        indirect = _sv(d, "Indirect Fixed Costs")
        opex = _sv(d, "Total OPEX")

    # ── Financial assumptions ────────────────────────────────────────────
    land_opt = f.get("Land Option", d.get("Land Option", "Buy"))

    if land_opt == "Rent":
        land_rent_pct = _f("Land Rent Pct", _sv(d, "Land Rent Pct", 0.2))
        if land_rent_pct > 1.0:
            land_rent_pct /= 100.0
        land_rent_yr = isbl_osbl * land_rent_pct
        land_buy = 0.0
    else:
        land_buy_pct = _f("Land Buy Pct", _sv(d, "Land Buy Pct", 2.0))
        if land_buy_pct > 1.0:
            land_buy_pct /= 100.0
        land_buy = isbl_osbl * land_buy_pct
        land_rent_yr = 0.0

    dep_method = f.get("Depreciation Method", d.get("Depreciation Method", "Straight Line"))
    dep_yrs = int(_f("Depreciation Years", _sv(d, "Depreciation Years", 10)))
    resid_pct = _f("Residual Value Pct", _sv(d, "Residual Value Pct", 20.0))
    if resid_pct > 1.0:
        resid_pct /= 100.0

    tax_rate = _f("Tax Rate", _sv(d, "Tax Rate", 0.34))
    if tax_rate > 1.0:
        tax_rate /= 100.0

    fin_type = f.get("Financing Type", d.get("Financing Type", "None"))
    leveraged = fin_type == "Straight Line"

    debt_ratio_raw = _f("Debt Ratio Pct", _sv(d, "Debt Ratio Pct", 50.0))
    debt_ratio = (debt_ratio_raw / 100.0) if leveraged else 0.0
    if debt_ratio > 1.0:
        debt_ratio = debt_ratio_raw  # already fractional

    amort_yrs = int(_f("Amortization Years", _sv(d, "Amortization Years", 13)))
    grace_yrs = int(_f("Grace Period Years", _sv(d, "Grace Period Years", 5)))

    cod = _sv(d, "COD", 0.0)
    if cod > 1.0:
        cod /= 100.0

    # MARR — use override or scenario value
    marr_raw = f.get("_marr_final", _sv(d, "MARR", 0.1))
    marr = marr_raw / 100.0 if marr_raw > 1.0 else marr_raw

    epc_yrs = int(_f("EPC Years", _sv(d, "EPC Years", 3)))
    op_yrs = int(_f("Project Lifetime", _sv(d, "Project Lifetime", 20)))
    total = 1 + epc_yrs + op_yrs

    # Capacity / fixed cost annual distribution
    cap_first = _f("Capacity First Year", _sv(d, "Capacity First Year", 100.0))
    if cap_first > 1.0:
        cap_first /= 100.0
    cap_inter = _f("Capacity Intermediate", _sv(d, "Capacity Intermediate", 100.0))
    if cap_inter > 1.0:
        cap_inter /= 100.0
    cap_last = _f("Capacity Last Year", _sv(d, "Capacity Last Year", 100.0))
    if cap_last > 1.0:
        cap_last /= 100.0
    fc_first = _f("Fixed Costs First Year", _sv(d, "Fixed Costs First Year", 100.0))
    if fc_first > 1.0:
        fc_first /= 100.0
    fc_inter = _f("Fixed Costs Intermediate", _sv(d, "Fixed Costs Intermediate", 100.0))
    if fc_inter > 1.0:
        fc_inter /= 100.0
    fc_last = _f("Fixed Costs Last Year", _sv(d, "Fixed Costs Last Year", 100.0))
    if fc_last > 1.0:
        fc_last /= 100.0

    # Growth rates
    g_main = _f("Growth Main Price", _sv(d, "Growth Main Price", 0.0))
    if abs(g_main) > 1.0:
        g_main /= 100.0
    g_bp = _f("Growth Byproduct Price", _sv(d, "Growth Byproduct Price", 0.0))
    if abs(g_bp) > 1.0:
        g_bp /= 100.0
    g_rm = _f("Growth Raw Materials", _sv(d, "Growth Raw Materials", 0.0))
    if abs(g_rm) > 1.0:
        g_rm /= 100.0
    g_cu = _f("Growth Chem Utilities", _sv(d, "Growth Chem Utilities", 0.0))
    if abs(g_cu) > 1.0:
        g_cu /= 100.0
    g_fc = _f("Growth Fixed Costs", _sv(d, "Growth Fixed Costs", 0.0))
    if abs(g_fc) > 1.0:
        g_fc /= 100.0

    # CAPEX distribution fractions
    epc_col = str(epc_yrs)
    if epc_col in CAPEX_DISTRIBUTION.columns:
        ref_fracs = list(CAPEX_DISTRIBUTION[epc_col].values)[:epc_yrs]
    else:
        ref_fracs = [1.0 / epc_yrs] * epc_yrs

    # Check for user-edited fractions in fin overrides
    capex_fracs = []
    has_custom = any(f"capex_frac_{i}" in f for i in range(epc_yrs))
    if has_custom:
        for i in range(epc_yrs - 1):
            capex_fracs.append(f.get(f"capex_frac_{i}", ref_fracs[i] if i < len(ref_fracs) else 0.0))
        capex_fracs.append(max(0.0, 1.0 - sum(capex_fracs)))
    else:
        capex_fracs = ref_fracs[:epc_yrs]
        if len(capex_fracs) < epc_yrs:
            capex_fracs += [0.0] * (epc_yrs - len(capex_fracs))

    return {
        # Dimensions
        "capacity": capacity,
        "working_hours": working_hours,
        "capex": capex,
        "wc": wc,
        "startup": startup,
        "isbl_osbl": isbl_osbl,
        # Variable cost bases (annual USD)
        "rm_base": rm_base,
        "cu_base": cu_base,
        "bp_base": bp_base,
        # Fixed cost bases (annual USD)
        "labor": labor,
        "supply_maint": supply_maint,
        "afc": afc,
        "indirect": indirect,
        "opex": opex,
        "olc": olc,
        # Financial assumptions
        "land_opt": land_opt,
        "land_buy": land_buy,
        "land_rent_yr": land_rent_yr,
        "dep_method": dep_method,
        "dep_yrs": dep_yrs,
        "resid_pct": resid_pct,
        "tax_rate": tax_rate,
        "fin_type": fin_type,
        "leveraged": leveraged,
        "debt_ratio": debt_ratio,
        "amort_yrs": amort_yrs,
        "grace_yrs": grace_yrs,
        "cod": cod,
        "marr": marr,
        "epc_yrs": epc_yrs,
        "op_yrs": op_yrs,
        "total": total,
        "capex_fracs": capex_fracs,
        # Capacity / FC distribution
        "cap_first": cap_first,
        "cap_inter": cap_inter,
        "cap_last": cap_last,
        "fc_first": fc_first,
        "fc_inter": fc_inter,
        "fc_last": fc_last,
        # Growth rates (fractional)
        "g_main": g_main,
        "g_bp": g_bp,
        "g_rm": g_rm,
        "g_cu": g_cu,
        "g_fc": g_fc,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CASH FLOW BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_cf_arrays(p: dict, product_price: float, capex_mult: float = 1.0):
    """
    Build year-by-year cash flow arrays.

    Parameters
    ----------
    p : dict from extract_params()
    product_price : selling price USD per capacity unit
    capex_mult : multiplier on CAPEX (for TIC bound analysis)

    Returns
    -------
    (cfs, pv_list, accum_list) — each a list[float] of length p["total"]
    """
    _c = p["capex"] * capex_mult
    _wc = p["wc"] * capex_mult
    _su = p["startup"] * capex_mult
    _dep_sl = -(_c - _c * p["resid_pct"]) / p["dep_yrs"] if p["dep_yrs"] > 0 else 0.0
    _fracs = p["capex_fracs"]
    _epc = p["epc_yrs"]
    _op = p["op_yrs"]
    _total = p["total"]
    _marr = p["marr"]

    _mk = min(MACRS.keys(), key=lambda k: abs(k - p["dep_yrs"]))
    _mrat = MACRS[_mk]

    cfs = []
    accum_pv = 0.0
    pv_list = []
    accum_list = []

    for i in range(_total):
        epc = 1 <= i <= _epc
        pre = i == 0
        oi = i - (_epc + 1)

        # ── Investment ───────────────────────────────────────────────
        inv = 0.0
        if pre:
            inv = -(p["land_buy"] * capex_mult if p["land_opt"] == "Buy" else 0.0)
        elif epc:
            inv = -_c * _fracs[i - 1]
        elif oi == _op - 1:
            inv += (p["land_buy"] * capex_mult if p["land_opt"] == "Buy" else 0.0)
        if i == _epc:
            inv += -_wc
        if oi == _op - 1:
            inv += +_wc
        if oi == 0:
            inv += -_su

        # ── Financing ────────────────────────────────────────────────
        f_int = f_amort = 0.0
        if p["leveraged"]:
            _tot_d = _c * p["debt_ratio"]
            _accum_d = _tot_d
            f_int = -_accum_d * p["cod"]
            _ann_r = _tot_d / p["amort_yrs"] if p["amort_yrs"] > 0 else 0.0
            if oi >= p["grace_yrs"] and (oi - p["grace_yrs"]) < p["amort_yrs"]:
                f_amort = -_ann_r

        # ── Pre-construction / EPC years ─────────────────────────────
        if pre or epc:
            cf = inv + f_int + f_amort
            pv = cf / (1 + _marr) ** i
            accum_pv += pv
            cfs.append(cf)
            pv_list.append(pv)
            accum_list.append(accum_pv)
            continue

        # ── Operational years ────────────────────────────────────────
        cp = p["cap_first"] if oi == 0 else (p["cap_last"] if oi == _op - 1 else p["cap_inter"])
        fp = p["fc_first"] if oi == 0 else (p["fc_last"] if oi == _op - 1 else p["fc_inter"])

        g_main_f = (1 + p["g_main"]) ** oi
        g_bp_f = (1 + p["g_bp"]) ** oi
        g_rm_f = (1 + p["g_rm"]) ** oi
        g_cu_f = (1 + p["g_cu"]) ** oi
        g_fc_f = (1 + p["g_fc"]) ** oi

        main_rev = product_price * p["capacity"] * cp * g_main_f
        byprod_rev = p["bp_base"] * cp * g_bp_f
        resid_rev = _c * p["resid_pct"] if oi == _op - 1 else 0.0
        rev = main_rev + byprod_rev + resid_rev

        rm = -(p["rm_base"] * cp * g_rm_f)
        cu = -(p["cu_base"] * cp * g_cu_f)
        lab = -(p["labor"] * fp * g_fc_f)
        sm = -(p["supply_maint"] * fp * g_fc_f)
        afc_v = -(p["afc"] * fp * g_fc_f)
        ifc_v = -(p["indirect"] * fp * g_fc_f)
        rent = -(p["land_rent_yr"] * g_fc_f) if p["land_opt"] == "Rent" else 0.0

        dep = (_dep_sl if oi < p["dep_yrs"] else 0.0) if p["dep_method"] == "Straight Line" \
            else (-_c * _mrat[oi] if oi < len(_mrat) else 0.0)

        ebt = rev + rm + cu + lab + sm + afc_v + ifc_v + rent + dep + f_int
        tax = -max(0.0, ebt) * p["tax_rate"]
        np_ = ebt + tax
        cf = np_ + f_amort + inv
        pv = cf / (1 + _marr) ** i
        accum_pv += pv
        cfs.append(cf)
        pv_list.append(pv)
        accum_list.append(accum_pv)

    return cfs, pv_list, accum_list


# ─────────────────────────────────────────────────────────────────────────────
# SOLVERS
# ─────────────────────────────────────────────────────────────────────────────
def npv_at_price(p: dict, price: float, capex_mult: float = 1.0) -> float:
    """Compute NPV for a given product price."""
    _, _, accum = build_cf_arrays(p, price, capex_mult)
    return accum[-1]


def irr_from_cfs(cfs: list) -> float | None:
    """Compute IRR from a cash flow series."""
    if not _HAS_NPF:
        return None
    try:
        v = npf.irr(cfs)
        return None if (v is None or np.isnan(v) or np.isinf(v)) else float(v)
    except Exception:
        return None


def solve_price_for_npv(p: dict, target_npv: float = 0.0,
                        capex_mult: float = 1.0) -> float | None:
    """Find the product price that achieves a target NPV (MSP when target=0)."""
    if not _HAS_SCIPY:
        return None
    try:
        return brentq(
            lambda pr: npv_at_price(p, pr, capex_mult) - target_npv,
            0.001, 1_000_000.0, xtol=0.01, maxiter=200,
        )
    except Exception:
        return None


def solve_price_for_irr(p: dict, target_irr: float,
                        capex_mult: float = 1.0) -> float | None:
    """Find the product price that achieves a target IRR."""
    if not _HAS_SCIPY or not _HAS_NPF:
        return None

    def irr_err(pr):
        cfs, _, _ = build_cf_arrays(p, pr, capex_mult)
        v = irr_from_cfs(cfs)
        return (v - target_irr) if v is not None else -target_irr

    scan = [100, 500, 1000, 2000, 5000, 10000, 50000]
    irrs = [(pr, irr_err(pr)) for pr in scan]
    lo = [pr for pr, e in irrs if e < 0]
    hi = [pr for pr, e in irrs if e > 0]
    if not lo or not hi:
        return None
    try:
        return brentq(irr_err, max(lo), min(hi) * 2, xtol=0.01, maxiter=200)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL INDICATORS (from a computed cash flow)
# ─────────────────────────────────────────────────────────────────────────────
def compute_indicators(p: dict, product_price: float,
                       capex_mult: float = 1.0) -> dict:
    """
    Compute all financial KPIs for a given parameter set and price.

    Returns dict with: NPV, IRR, MSP, Payback, TIC, MARR, margins, etc.
    """
    cfs, _, acpv = build_cf_arrays(p, product_price, capex_mult)
    _c = p["capex"] * capex_mult
    _tic = (_c + p["wc"] * capex_mult + p["startup"] * capex_mult
            + (p["land_buy"] * capex_mult if p["land_opt"] == "Buy" else 0.0))

    npv_ = acpv[-1]
    irr_ = irr_from_cfs(cfs)
    msp_ = solve_price_for_npv(p, 0.0, capex_mult) if _HAS_SCIPY else None

    _epc = p["epc_yrs"]
    _op = p["op_yrs"]

    payback_ = next((i for i, v in enumerate(acpv) if v >= 0), None)
    payback_op = (payback_ - (_epc + 1)) if payback_ is not None else None

    op_cfs = cfs[_epc + 1:]
    avg_np = np.mean(op_cfs) if op_cfs else 0.0

    # Steady-state snapshot (3rd operational year)
    _ss_oi = min(2, _op - 1)
    cp = p["cap_first"] if _ss_oi == 0 else (p["cap_last"] if _ss_oi == _op - 1 else p["cap_inter"])
    fp = p["fc_first"] if _ss_oi == 0 else (p["fc_last"] if _ss_oi == _op - 1 else p["fc_inter"])

    rev_ss = (product_price * p["capacity"] * cp * (1 + p["g_main"]) ** _ss_oi
              + p["bp_base"] * cp * (1 + p["g_bp"]) ** _ss_oi)
    var_ss = (p["rm_base"] * cp * (1 + p["g_rm"]) ** _ss_oi
              + p["cu_base"] * cp * (1 + p["g_cu"]) ** _ss_oi
              + p["labor"] * fp * (1 + p["g_fc"]) ** _ss_oi)
    fix_ss = ((p["supply_maint"] + p["afc"] + p["indirect"])
              * fp * (1 + p["g_fc"]) ** _ss_oi)

    dep_ss = -(_c - _c * p["resid_pct"]) / p["dep_yrs"] if _ss_oi < p["dep_yrs"] and p["dep_yrs"] > 0 else 0.0
    gp_ss = rev_ss - var_ss
    ebitda_ss = gp_ss - fix_ss
    ebit_ss = ebitda_ss + dep_ss
    np_ss = ebit_ss * (1 - p["tax_rate"])

    return {
        "NPV": npv_,
        "IRR": irr_,
        "MSP": msp_,
        "Payback": payback_op,
        "TIC": _tic,
        "MARR": p["marr"],
        "OPEX": p["opex"],
        "Capacity": p["capacity"],
        "CAPEX": p["capex"] * capex_mult,
        "Gross Margin": gp_ss / rev_ss if rev_ss else 0.0,
        "EBITDA Margin": ebitda_ss / rev_ss if rev_ss else 0.0,
        "EBIT Margin": ebit_ss / rev_ss if rev_ss else 0.0,
        "Net Profit Margin": np_ss / rev_ss if rev_ss else 0.0,
        "ROE": np_ss / _tic if _tic else 0.0,
        "ROA": np_ss / _tic if _tic else 0.0,
        "Avg Net Profit": avg_np,
        "cfs": cfs,
        "acpv": acpv,
    }


# ─────────────────────────────────────────────────────────────────────────────
# VECTORIZED MONTE CARLO
# ─────────────────────────────────────────────────────────────────────────────
def monte_carlo_npv_irr(
    p: dict,
    product_price: float,
    distributions: dict,
    n_iterations: int = 10_000,
    capex_mult: float = 1.0,
) -> dict:
    """
    Run vectorized Monte Carlo simulation.

    Parameters
    ----------
    p : base params dict
    product_price : base selling price
    distributions : dict of {param_key: {"type": "triangular"|"normal", ...}}
        For triangular: {"type": "triangular", "low": x, "mode": y, "high": z}
        For normal: {"type": "normal", "mean": x, "std": y}
    n_iterations : number of samples
    capex_mult : base CAPEX multiplier

    Returns
    -------
    dict with "npv", "irr" arrays and summary statistics
    """
    rng = np.random.default_rng(42)

    # Pre-sample all distributions
    samples = {}
    for key, dist in distributions.items():
        if dist["type"] == "triangular":
            lo, mode, hi = dist["low"], dist["mode"], dist["high"]
            if lo >= hi:
                samples[key] = np.full(n_iterations, mode)
            else:
                mode_c = max(lo, min(hi, mode))
                samples[key] = rng.triangular(lo, mode_c, hi, n_iterations)
        elif dist["type"] == "normal":
            samples[key] = rng.normal(dist["mean"], dist["std"], n_iterations)
        else:
            samples[key] = np.full(n_iterations, dist.get("value", 0.0))

    npvs = np.zeros(n_iterations)
    irrs = np.full(n_iterations, np.nan)

    for i in range(n_iterations):
        pi = dict(p)
        for key, vals in samples.items():
            pi[key] = float(vals[i])

        price_i = float(samples.get("product_price", np.full(1, product_price))[0]) \
            if "product_price" in samples else product_price
        cm_i = float(samples.get("capex_mult", np.full(1, capex_mult))[0]) \
            if "capex_mult" in samples else capex_mult

        cfs_i, _, accum_i = build_cf_arrays(pi, price_i, cm_i)
        npvs[i] = accum_i[-1]
        irr_v = irr_from_cfs(cfs_i)
        if irr_v is not None:
            irrs[i] = irr_v

    valid_irrs = irrs[~np.isnan(irrs)]

    return {
        "npv": npvs,
        "irr": valid_irrs,
        "n": n_iterations,
        "npv_mean": float(np.mean(npvs)),
        "npv_std": float(np.std(npvs)),
        "npv_p10": float(np.percentile(npvs, 10)),
        "npv_p50": float(np.percentile(npvs, 50)),
        "npv_p90": float(np.percentile(npvs, 90)),
        "p_npv_positive": float(np.mean(npvs > 0)),
        "irr_mean": float(np.mean(valid_irrs)) if len(valid_irrs) > 0 else None,
        "irr_std": float(np.std(valid_irrs)) if len(valid_irrs) > 0 else None,
        "irr_p10": float(np.percentile(valid_irrs, 10)) if len(valid_irrs) > 0 else None,
        "irr_p50": float(np.percentile(valid_irrs, 50)) if len(valid_irrs) > 0 else None,
        "irr_p90": float(np.percentile(valid_irrs, 90)) if len(valid_irrs) > 0 else None,
        "p_irr_above_marr": float(np.mean(valid_irrs > p["marr"])) if len(valid_irrs) > 0 else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TOPSIS (for Multi-Criteria Analysis)
# ─────────────────────────────────────────────────────────────────────────────
def topsis(decision_matrix: np.ndarray, weights: np.ndarray,
           is_benefit: np.ndarray) -> np.ndarray:
    """
    TOPSIS ranking.

    Parameters
    ----------
    decision_matrix : (n_alternatives, n_criteria)
    weights : (n_criteria,) — must sum to 1
    is_benefit : (n_criteria,) — True if higher is better

    Returns
    -------
    closeness : (n_alternatives,) — higher = better
    """
    # Step 1: Vector normalization
    norms = np.sqrt(np.sum(decision_matrix ** 2, axis=0))
    norms[norms == 0] = 1.0  # avoid division by zero
    norm_matrix = decision_matrix / norms

    # Step 2: Weighted normalized matrix
    weighted = norm_matrix * weights

    # Step 3: Ideal and anti-ideal solutions
    ideal = np.where(is_benefit, weighted.max(axis=0), weighted.min(axis=0))
    anti_ideal = np.where(is_benefit, weighted.min(axis=0), weighted.max(axis=0))

    # Step 4: Euclidean distances
    d_plus = np.sqrt(np.sum((weighted - ideal) ** 2, axis=1))
    d_minus = np.sqrt(np.sum((weighted - anti_ideal) ** 2, axis=1))

    # Step 5: Closeness coefficient
    denom = d_plus + d_minus
    denom[denom == 0] = 1.0
    closeness = d_minus / denom

    return closeness
