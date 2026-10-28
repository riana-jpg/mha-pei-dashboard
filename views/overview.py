import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import brand
import state

d = state.data()
m = state.selected_month()
if m is None:
    st.stop()
pm = state.prior_month(m)
ly = pd.Timestamp(m) - pd.DateOffset(years=1)

brand.page_header("Monthly Snapshot", f"{brand.month_label(m)} at a glance, compared with the month before.")

calaim = d.calaim.set_index("month")
clinic_m = d.clinic.groupby("month")["encounters"].sum()

def cal(month):
    return float(calaim.loc[month, "total"]) if month in calaim.index else None

def enc(month):
    return float(clinic_m.loc[month]) if month in clinic_m.index else None

metrics = [
    ("Clients in programs", lambda x: state.value_for("Total", x, "Total Clients In Program"), False),
    ("Services provided", lambda x: state.value_for("All services", x), False),
    ("People screened", lambda x: state.value_for("Total Screened", x), True),
    ("Resources distributed", lambda x: state.value_for("Resources Distributed", x), True),
    ("Outreach referrals", lambda x: state.value_for("Total", x, "Outreach Referrals"), False),
    ("CalAIM members (ECM + CS)", cal, True),
]

cols = st.columns(3)
for i, (label, fn, gold) in enumerate(metrics):
    with cols[i % 3]:
        brand.kpi(label, fn(m), fn(pm), gold=gold)
        st.write("")

brand.note(
    "<b>How to read this page.</b> Each card shows the number for the selected month. "
    "The small line underneath compares it with the month before. Use the menu on the left "
    "to see the detail behind any number."
)

st.subheader("The last 13 months")
start = pd.Timestamp(m) - pd.DateOffset(months=12)
trend_specs = [
    ("Clients in programs", state.series("Total", "Total Clients In Program")),
    ("Services provided", state.series("All services")),
    ("People screened", state.series("Total Screened")),
    ("Resources distributed", state.series("Resources Distributed")),
]
c1, c2 = st.columns(2)
for i, (title, s) in enumerate(trend_specs):
    s = s[(s.index >= start) & (s.index <= m)]
    fig = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines+markers",
                               line=dict(color=brand.NAVY if i % 2 == 0 else brand.GOLD, width=3),
                               hovertemplate="%{x|%b %Y}: %{y:,.0f}<extra></extra>"))
    if m in s.index:
        fig.add_trace(go.Scatter(x=[m], y=[s.loc[m]], mode="markers",
                                 marker=dict(size=13, color=brand.GOLD, line=dict(color=brand.NAVY, width=2)),
                                 hoverinfo="skip", showlegend=False))
    fig.update_layout(title=title, height=260, showlegend=False, xaxis_tickformat="%b<br>%Y")
    (c1 if i % 2 == 0 else c2).plotly_chart(fig, width="stretch")

st.subheader("Same month last year")
rows = []
for label, fn, _ in metrics:
    cur, prev = fn(m), fn(ly)
    rows.append({"Measure": label, brand.month_label(m): cur, brand.month_label(ly): prev,
                 "Change": (cur - prev) if cur is not None and prev is not None else None})
tbl = pd.DataFrame(rows)
st.dataframe(tbl, hide_index=True, width="stretch",
             column_config={c: st.column_config.NumberColumn(format="%d") for c in tbl.columns if c != "Measure"})
