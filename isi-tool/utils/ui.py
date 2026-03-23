"""
ISI-Tool — Shared UI components and styling helpers.

Provides consistent visual elements across all pages without
injecting per-page CSS blocks. The config.toml theme handles
all base styling; this module adds only structural HTML for
KPI cards and breakdown tables.
"""
import streamlit as st
from utils.constants import smart_fmt, fmt_compact, scenario_colors, safe_val, PALETTE


# ─────────────────────────────────────────────
# MINIMAL TARGETED CSS
# Only for elements that config.toml cannot style
# ─────────────────────────────────────────────
_TARGETED_CSS = """
<style>
/* KPI card component */
.kpi-card {
    background: var(--secondary-background-color, #161b22);
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    border-left: 3px solid var(--accent, #e6a817);
}
.kpi-label {
    font-size: .72rem;
    font-weight: 500;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: .1em;
    margin-bottom: .35rem;
}
.kpi-value {
    font-family: 'DM Mono', monospace;
    font-size: 1.45rem;
    font-weight: 500;
    line-height: 1.15;
}
.kpi-sub {
    font-size: .72rem;
    color: #8b949e;
    margin-top: .25rem;
}

/* Scenario badge */
.scen-badge {
    background: var(--secondary-background-color, #161b22);
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    height: 100%;
}
.scen-tag {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: .68rem;
    padding: .12rem .45rem;
    border-radius: 4px;
    margin: .12rem .08rem 0 0;
}

/* Section header accent bar */
.section-hdr {
    font-size: .7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .15em;
    padding: .5rem 0 .3rem 0;
    border-bottom: 1px solid #21262d;
    margin-bottom: .5rem;
}
</style>
"""

_css_injected = False

def inject_css():
    """Inject minimal targeted CSS once per page render."""
    global _css_injected
    if not _css_injected:
        st.html(_TARGETED_CSS)
        _css_injected = True


# ─────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────
def page_header(title: str, subtitle: str = "", accent: str = "#e6a817"):
    """Render a consistent page header with optional subtitle."""
    inject_css()
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle.upper())


# ─────────────────────────────────────────────
# SECTION DIVIDER
# ─────────────────────────────────────────────
def section_header(text: str, color: str = "#e6a817"):
    """Render a small uppercase section label."""
    st.markdown(
        f'<div class="section-hdr" style="color:{color}">{text}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# KPI CARD
# ─────────────────────────────────────────────
def kpi_card(label: str, value: str, accent: str = "#e6a817",
             sub_label: str = "", sub_value: str = ""):
    """Render a styled KPI card."""
    inject_css()
    sub_html = ""
    if sub_label:
        sub_html = f'<div class="kpi-sub">{sub_label}: {sub_value}</div>'
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color:{accent}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{accent}">{value}</div>
        {sub_html}
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SCENARIO BANNER
# ─────────────────────────────────────────────
def scenario_banner(name: str, d: dict, color: str):
    """Render a scenario summary badge."""
    inject_css()
    prod = d.get("Product Name", "—")
    unit = d.get("Unit", "")
    cap = d.get("Capacity", "—")
    trl = d.get("TRL", "—")
    sev = d.get("Process Severity", "—")
    mat = d.get("Material Handled", "—")

    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    st.markdown(f"""
    <div class="scen-badge" style="border-left:4px solid {color}">
      <div style="font-weight:700;color:{color};margin-bottom:.4rem">{name}</div>
      <div style="font-size:.85rem;margin-bottom:.2rem">{prod}</div>
      <div style="font-family:'DM Mono',monospace;font-size:.8rem;color:#8b949e;margin-bottom:.5rem">
        {cap} {unit}/yr
      </div>
      <div>
        <span class="scen-tag" style="background:rgba({r},{g},{b},0.15);color:{color};border:1px solid {color}33">{trl}</span>
        <span class="scen-tag" style="background:#21262d;color:#8b949e">{sev}</span>
        <span class="scen-tag" style="background:#21262d;color:#8b949e">{mat}</span>
      </div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BREAKDOWN TABLE (HTML)
# ─────────────────────────────────────────────
def breakdown_table(rows_spec: list, selected: list, scenarios: dict,
                    cmap: dict, cell_fn, accent: str = "#e6a817"):
    """
    Render a detailed HTML breakdown table.

    rows_spec: list of (row_type, label, key) tuples
        row_type: "H" = header, "I" = item, "S" = subtotal, "T" = total
    cell_fn: callable(row_type, key, scenario_dict) -> str
    """
    inject_css()

    scen_headers = "".join(
        f'<th style="padding:.5rem .8rem;text-align:right;font-size:.75rem;'
        f'color:{cmap[n]};border-bottom:2px solid {cmap[n]}44;white-space:nowrap">{n}</th>'
        for n in selected
    )

    html_rows = []
    for rtype, label, key in rows_spec:
        if rtype == "H":
            html_rows.append(
                f'<tr><td colspan="{len(selected) + 1}" style="padding:.55rem .8rem .2rem;'
                f'font-size:.65rem;font-weight:700;color:{accent};text-transform:uppercase;'
                f'letter-spacing:.12em;background:#0d1117;border-top:1px solid #21262d">{label}</td></tr>'
            )
        else:
            is_total = rtype == "T"
            is_sub = rtype == "S"
            indent = "0" if is_total else ("1rem" if is_sub else "2rem")
            bg = "#1a2030" if is_total else ("#161b22" if is_sub else "transparent")
            fw = "600" if (is_total or is_sub) else "400"
            fc = "#e6edf3" if is_total else ("#c9d1d9" if is_sub else "#8b949e")

            cells = "".join(
                f'<td style="padding:.4rem .8rem;text-align:right;font-family:DM Mono,monospace;'
                f'font-size:.8rem;color:{fc};white-space:nowrap">{cell_fn(rtype, key, scenarios[n])}</td>'
                for n in selected
            )
            html_rows.append(
                f'<tr style="background:{bg};border-bottom:1px solid #21262d22">'
                f'<td style="padding:.4rem .8rem .4rem {indent};'
                f'font-size:.82rem;font-weight:{fw};color:{fc}">{label}</td>'
                f'{cells}</tr>'
            )

    st.markdown(f"""
    <div style="overflow-x:auto;border:1px solid #21262d;border-radius:6px;background:#161b22">
    <table style="width:100%;border-collapse:collapse">
    <thead><tr>
      <th style="padding:.5rem .8rem;text-align:left;font-size:.75rem;color:#8b949e;
          border-bottom:2px solid #21262d;min-width:220px">Line Item</th>
      {scen_headers}
    </tr></thead>
    <tbody>{"".join(html_rows)}</tbody>
    </table>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# GUARD — no scenarios yet
# ─────────────────────────────────────────────
def require_scenarios(title: str = ""):
    """
    Check that scenarios exist. If not, show a message and stop.
    Returns (scenarios, names, cmap) if OK.
    """
    inject_css()
    if "scenarios" not in st.session_state or not st.session_state.scenarios:
        if title:
            st.markdown(f"### {title}")
        st.info("No scenarios saved yet — go to **Input Data** to configure and save a scenario first.",
                icon=":material/info:")
        st.stop()
    scenarios = st.session_state.scenarios
    names = list(scenarios.keys())
    cmap = scenario_colors(names)
    return scenarios, names, cmap


def scenario_filter(names: list[str]) -> list[str]:
    """Show a multiselect filter if >1 scenario exists. Returns selected names."""
    if len(names) > 1:
        selected = st.multiselect("Filter scenarios", names, default=names,
                                  label_visibility="collapsed")
        return selected if selected else names
    return names
