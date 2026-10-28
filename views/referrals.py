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
brand.page_header("Referrals", f"Where we connected community members for more help in {brand.month_label(m)}.")

pm = state.prior_month(m)
c = st.columns(3)
with c[0]:
    brand.kpi("Outreach referrals", state.value_for("Total", m, "Outreach Referrals"),
              state.value_for("Total", pm, "Outreach Referrals"))
with c[1]:
    brand.kpi("CalAIM self-referrals by MHA", state.value_for("MHA CalAIM Self-Referral", m),
              state.value_for("MHA CalAIM Self-Referral", pm), gold=True,
              help_text="Members MHA referred into CalAIM ECM (tracked since June 2025)")

ref = d.summary[(d.summary["section"] == "Outreach Referrals") &
                (~d.summary["metric"].isin(["Total", "MHA CalAIM Self-Referral"]))]
cur = ref[ref["month"] == m]
if cur.empty:
    cur = d.referrals[d.referrals["month"] == m].rename(columns={"destination": "metric", "count": "value"})
cur = cur[cur["value"] > 0]

st.write("")
if cur.empty:
    st.info("No outreach referrals recorded for this month.")
else:
    fig = px.pie(cur, names="metric", values="value", hole=0.55,
                 color_discrete_sequence=brand.PALETTE)
    fig.update_traces(textinfo="label+value", hovertemplate="%{label}: %{value}<extra></extra>")
    fig.update_layout(title="Referred to", height=360, showlegend=False)
    st.plotly_chart(fig, width="stretch")

brand.note("MHA means the person was referred into an MHA program. RCMS is Redwood Coast Medical Services. "
           "Other covers partners that are only used occasionally.")

st.subheader("Referrals over time")
hist = state.window(ref, 13)
if not hist.empty:
    fig2 = px.bar(hist, x="month", y="value", color="metric", barmode="stack",
                  labels={"value": "Referrals", "month": "", "metric": "Referred to"},
                  color_discrete_sequence=brand.PALETTE)
    fig2.update_layout(height=320, xaxis_tickformat="%b<br>%Y")
    st.plotly_chart(fig2, width="stretch")
