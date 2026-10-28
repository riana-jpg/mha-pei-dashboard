import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import brand
import state

d = state.data()
m = state.selected_month()
if m is None:
    st.stop()
brand.page_header("Services & Activities",
                  f"What our care coordinators, CHWs and peer coaches did in {brand.month_label(m)}.")

a = d.activities[d.activities["month"] == m]
if a.empty:
    st.info("No activity detail for this month in the workbook.")
    st.stop()

by_prog = a.groupby("program")["count"].sum().sort_values(ascending=False)
cols = st.columns(len(by_prog) + 1)
with cols[0]:
    brand.kpi("All activities", a["count"].sum())
for i, (prog, n) in enumerate(by_prog.items(), start=1):
    with cols[i]:
        brand.kpi(prog, n, gold=(i % 2 == 0))

st.write("")
prog = st.radio("Program", ["All programs"] + list(by_prog.index), horizontal=True)
view = a if prog == "All programs" else a[a["program"] == prog]
top = view.groupby("activity")["count"].sum().sort_values()
fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=brand.NAVY,
                       text=top.values, texttemplate="%{text:,.0f}", textposition="outside",
                       hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
fig.update_layout(title=f"{prog}: activities by type", height=max(320, 26 * len(top) + 80),
                  xaxis_title="Number of activities", yaxis_title=None)
st.plotly_chart(fig, width="stretch")

brand.note("Each bar counts how many times that service was recorded in the month. One client can receive "
           "several services, so these are counts of services, not people.")

st.subheader("Services over time")
svc = d.summary[d.summary["metric"].isin(
    ["Care Coordination Services", "Care Transition Services", "MOB Activities", "Chronic Care Mgmt Activities"])]
svc = state.window(svc, 13)
if not svc.empty:
    svc = svc.assign(metric=svc["metric"].replace({
        "Care Coordination Services": "Care Coordination", "Care Transition Services": "Care Transitions",
        "MOB Activities": "Matter of Balance", "Chronic Care Mgmt Activities": "Chronic Care Management"}))
    fig2 = px.bar(svc, x="month", y="value", color="metric", barmode="stack",
                  labels={"value": "Services", "month": "", "metric": "Program"})
    fig2.update_layout(height=340, xaxis_tickformat="%b<br>%Y")
    st.plotly_chart(fig2, width="stretch")

avg = state.series("Avg Services/Client")
c1, c2 = st.columns(2)
with c1:
    brand.kpi("Average services per client", avg.get(m), avg.get(state.prior_month(m)),
              help_text="Total services divided by clients in programs")

with st.expander("See the full table for this month"):
    st.dataframe(view.sort_values("count", ascending=False)[["program", "activity", "count"]]
                 .rename(columns={"program": "Program", "activity": "Activity", "count": "Count"}),
                 hide_index=True, width="stretch")
