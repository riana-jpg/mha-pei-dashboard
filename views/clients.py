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
pm = state.prior_month(m)
brand.page_header("Clients & CalAIM", f"Who was enrolled in MHA programs in {brand.month_label(m)}.")

progs = ["Care Coordination", "Care Transitions", "Matter of Balance", "Chronic Care Management"]
c = st.columns(5)
with c[0]:
    brand.kpi("All program clients", state.value_for("Total", m, "Total Clients In Program"),
              state.value_for("Total", pm, "Total Clients In Program"))
for i, p in enumerate(progs, start=1):
    with c[i]:
        brand.kpi(p, state.value_for(p, m, "Total Clients In Program"),
                  state.value_for(p, pm, "Total Clients In Program"), gold=(i % 2 == 0))

st.write("")
cl = d.summary[(d.summary["section"] == "Total Clients In Program") & (d.summary["metric"].isin(progs))]
yrs = st.radio("Show", ["Last 13 months", "Last 2 years", "All history"], horizontal=True)
n = {"Last 13 months": 13, "Last 2 years": 25, "All history": 999}[yrs]
cl = state.window(cl, n)
fig = px.area(cl, x="month", y="value", color="metric", labels={"value": "Clients", "month": "", "metric": "Program"},
              color_discrete_sequence=brand.PALETTE)
fig.update_layout(height=340, xaxis_tickformat="%b<br>%Y", title="Clients in programs")
st.plotly_chart(fig, width="stretch")

st.subheader("CalAIM Enhanced Care Management")
cal = d.calaim.set_index("month")
row = cal.loc[m] if m in cal.index else None
prow = cal.loc[pm] if pm in cal.index else None
c2 = st.columns(4)
with c2[0]:
    brand.kpi("ECM members", row["ecm"] if row is not None else None, prow["ecm"] if prow is not None else None)
with c2[1]:
    brand.kpi("Community Supports", row["cs"] if row is not None else None,
              prow["cs"] if prow is not None else None, gold=True)
with c2[2]:
    brand.kpi("Total CalAIM", row["total"] if row is not None else None,
              prow["total"] if prow is not None else None)
with c2[3]:
    brand.kpi("Ending this month", row["ending"] if row is not None else None, gold=True)

ch = state.window(d.calaim, n)
if not ch.empty:
    fig2 = go.Figure()
    fig2.add_bar(x=ch["month"], y=ch["ecm"], name="ECM", marker_color=brand.NAVY)
    fig2.add_bar(x=ch["month"], y=ch["cs"], name="Community Supports", marker_color=brand.GOLD)
    fig2.add_hline(y=84, line_dash="dot", line_color=brand.MUTED,
                   annotation_text="Full caseload at current staffing (~84)", annotation_position="top left")
    fig2.update_layout(barmode="stack", height=340, xaxis_tickformat="%b<br>%Y", yaxis_title="Members")
    st.plotly_chart(fig2, width="stretch")

brand.note("CalAIM counts come from the monthly Return Transmittal File (RTF) sent to Partnership HealthPlan, "
           "which is the official source. A member counts in a month if their authorization was active at any "
           "point that month. The program goal is 15 clients per full-time care coordinator.")
