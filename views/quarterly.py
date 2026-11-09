"""Board-level view: fiscal quarters (FY runs July to June)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import brand
import metrics
import state

d = state.data()
m = state.selected_month()
if m is None:
    st.stop()

fy, q = metrics.fiscal_quarter(m)
brand.page_header("Quarterly Summary",
                  f"{metrics.quarter_label(fy, q)} for the board, compared with the quarter before. "
                  "MHA's fiscal year runs July to June.")

# Every quarter with at least one month on file, oldest first.
quarters = sorted({metrics.fiscal_quarter(x) for x in d.months})
labels = [metrics.quarter_label(*x) for x in quarters]
pick = st.selectbox("Quarter", labels, index=labels.index(metrics.quarter_label(fy, q)),
                    help="Opens on the quarter of the reporting month in the sidebar.")
fy, q = quarters[labels.index(pick)]
cur = metrics.quarter_row(d, fy, q)
prev_key = quarters[labels.index(pick) - 1] if labels.index(pick) > 0 else None
prev = metrics.quarter_row(d, *prev_key) if prev_key else {}

if not cur["complete"]:
    got = ", ".join(x.strftime("%B") for x in cur["months"])
    brand.note(f"<b>{cur['label']} is not finished yet.</b> It includes {got} only, so totals will grow "
               "as the remaining months are added. Changes from last quarter appear once the quarter is complete.")

cards = [
    ("Services provided", "services", False, False),
    ("Screenings done", "screenings", True, False),
    ("Share needing follow-up", "followup_share", False, True),
    ("Resources distributed", "resources", True, False),
    ("Mobile clinic visits", "clinic_visits", False, False),
    ("CalAIM members, end of quarter", "calaim_total", True, False),
]
cols = st.columns(3)
for i, (label, key, gold, pct) in enumerate(cards):
    with cols[i % 3]:
        # A quarter still in progress is not compared with a full one.
        brand.kpi(label, cur.get(key), prev.get(key) if cur["complete"] else None,
                  prior_label="vs last quarter", pct=pct, gold=gold)
        st.write("")

brand.note(
    "<b>How quarters are counted.</b> Services, screenings, resources and clinic visits are added up "
    "across the months in the quarter. Clients and CalAIM members are the count in the last month of the "
    "quarter, not a count of different people across the quarter. Share needing follow-up is people with "
    "an out-of-range screening divided by people screened."
)

# ------------------------------------------------------------------ trend by quarter
st.subheader("Quarter by quarter")
rows = [metrics.quarter_row(d, *x) for x in quarters[-6:]]
x = [r["label"] + ("" if r["complete"] else " (to date)") for r in rows]
c1, c2 = st.columns(2)
for i, (title, key) in enumerate([("Services provided", "services"), ("Mobile clinic visits", "clinic_visits"),
                                  ("Screenings done", "screenings"), ("Resources distributed", "resources")]):
    y = [r[key] for r in rows]
    fig = go.Figure(go.Bar(x=x, y=y, marker_color=brand.NAVY if i % 2 == 0 else brand.GOLD,
                           text=[brand.fmt_num(v) for v in y], textposition="outside",
                           hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    fig.update_layout(title=title, height=280, showlegend=False)
    (c1 if i % 2 == 0 else c2).plotly_chart(fig, width="stretch")

with st.expander("See the full table by quarter"):
    tbl = pd.DataFrame([{
        "Quarter": r["label"] + ("" if r["complete"] else " (to date)"),
        "Months on file": len(r["months"]),
        "Clients (end)": r["clients"],
        "Services": r["services"],
        "Screenings": r["screenings"],
        "Needing follow-up": f"{r['followup_share']:.0%}" if r["followup_share"] is not None else "—",
        "Resources": r["resources"],
        "Narcan boxes": r["narcan_boxes"],
        "Clinic visits": r["clinic_visits"],
        "Clinic days": r["clinic_days"],
        "CalAIM ECM (end)": r["calaim_ecm"],
        "CalAIM CS (end)": r["calaim_cs"],
    } for r in rows])
    st.dataframe(tbl, hide_index=True, width="stretch")
    st.caption("Narcan is in boxes (2 doses per box) from August 2026 on; earlier months mixed boxes and doses.")
