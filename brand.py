"""MHA brand settings and shared UI helpers.

Swap the hex values below for the exact codes in the MHA brand kit.
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

NAVY = "#1F3A5F"        # Coastal Navy (primary)
GOLD = "#C9A227"        # Heritage Gold (secondary)
SAND = "#F4F1EA"
INK = "#1C2430"
MUTED = "#6B7480"
GRID = "#E3E0D8"
GOOD = "#2E7D6B"        # in range
ALERT = "#B5523B"       # out of range

# Ordered palette for multi-series charts: navy, gold, then quieter coastal tones.
PALETTE = [NAVY, GOLD, "#5B8DB8", "#8C6D1F", "#7FA7A0", "#A9B4C2", "#D9C27A", "#3E5C7E"]

FONT = "Avenir Next, Avenir, Arial, sans-serif"

pio.templates["mha"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family=FONT, color=INK, size=14),
        colorway=PALETTE,
        paper_bgcolor="white",
        plot_bgcolor="white",
        title=dict(font=dict(size=16, color=NAVY)),
        xaxis=dict(showgrid=False, linecolor=GRID, ticks="outside", tickcolor=GRID),
        yaxis=dict(gridcolor=GRID, zeroline=False),
        legend=dict(orientation="h", y=-0.2, x=0),
        margin=dict(l=10, r=10, t=40, b=10),
        hoverlabel=dict(font=dict(family=FONT)),
    )
)
pio.templates.default = "mha"


def inject_css():
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{ font-family: {FONT}; }}
        h1, h2, h3 {{ color: {NAVY}; font-family: {FONT}; }}
        .mha-band {{ background:{NAVY}; color:white; padding:18px 22px; border-radius:10px;
                    border-bottom:4px solid {GOLD}; margin-bottom:18px; }}
        .mha-band h1 {{ color:white; margin:0; font-size:1.7rem; }}
        .mha-band p {{ color:#E8EDF3; margin:4px 0 0 0; font-size:0.98rem; }}
        .kpi {{ background:white; border:1px solid {GRID}; border-top:4px solid {NAVY};
               border-radius:10px; padding:14px 16px; height:100%; }}
        .kpi .label {{ color:{MUTED}; font-size:0.85rem; text-transform:uppercase; letter-spacing:.04em; }}
        .kpi .value {{ color:{NAVY}; font-size:2rem; font-weight:700; line-height:1.2; }}
        .kpi .delta {{ font-size:0.85rem; color:{MUTED}; }}
        .kpi .delta.up {{ color:{GOOD}; }} .kpi .delta.down {{ color:{ALERT}; }}
        .kpi.gold {{ border-top-color:{GOLD}; }}
        .note {{ background:{SAND}; border-left:4px solid {GOLD}; padding:10px 14px; border-radius:6px;
                font-size:0.93rem; margin:8px 0 14px 0; }}
        section[data-testid="stSidebar"] {{ background:{SAND}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = ""):
    st.markdown(f'<div class="mha-band"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def fmt_num(v, pct=False):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if pct:
        return f"{v:.0%}"
    return f"{v:,.0f}"


def kpi(label, value, prior=None, prior_label="vs last month", pct=False, gold=False, help_text=None):
    delta_html = ""
    if prior is not None and value is not None and not pd.isna(prior) and not pd.isna(value):
        diff = value - prior
        if pct:
            txt = f"{diff*100:+.0f} pts {prior_label}"
        else:
            txt = f"{diff:+,.0f} {prior_label}"
        cls = "up" if diff > 0 else "down" if diff < 0 else ""
        delta_html = f'<div class="delta {cls}">{txt}</div>'
    title = f' title="{help_text}"' if help_text else ""
    st.markdown(
        f'<div class="kpi{" gold" if gold else ""}"{title}><div class="label">{label}</div>'
        f'<div class="value">{fmt_num(value, pct)}</div>{delta_html}</div>',
        unsafe_allow_html=True,
    )


def note(text: str):
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def month_label(m) -> str:
    return pd.Timestamp(m).strftime("%B %Y")
