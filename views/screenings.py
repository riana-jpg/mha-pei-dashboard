import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import brand
import state

d = state.data()
m = state.selected_month()
if m is None:
    st.stop()
brand.page_header("Health Screenings",
                  f"Blood pressure, A1C, depression and substance-use screenings in {brand.month_label(m)}.")

s = d.screening[d.screening["month"] == m].copy()
people = state.value_for("Total Screened", m)
people_out = state.value_for("People Out of Range", m)
pm = state.prior_month(m)

c = st.columns(4)
with c[0]:
    brand.kpi("Screenings done", s["total"].sum() if not s.empty else None,
              d.screening[d.screening["month"] == pm]["total"].sum() or None)
with c[1]:
    brand.kpi("People screened", people, state.value_for("Total Screened", pm), gold=True)
with c[2]:
    brand.kpi("People with a result to follow up", people_out, state.value_for("People Out of Range", pm))
with c[3]:
    share = (people_out / people) if people and people_out is not None else None
    brand.kpi("Share needing follow-up", share, pct=True, gold=True)

st.write("")
if s.empty:
    st.info("No screening detail for this month in the workbook.")
else:
    s = s.sort_values("total")
    fig = go.Figure()
    fig.add_bar(y=s["screening"], x=s["in_range"], name="In healthy range", orientation="h",
                marker_color=brand.GOOD, hovertemplate="%{y}: %{x} in range<extra></extra>")
    fig.add_bar(y=s["screening"], x=s["out_range"], name="Outside healthy range", orientation="h",
                marker_color=brand.ALERT, hovertemplate="%{y}: %{x} out of range<extra></extra>")
    fig.update_layout(barmode="stack", title="Results by screening type",
                      height=max(300, 50 * len(s) + 100), xaxis_title="Screenings")
    st.plotly_chart(fig, width="stretch")

brand.note(
    "<b>What 'outside healthy range' means.</b> Blood pressure 130/80 or higher. A1C above 5.7. "
    "Cholesterol 200 or higher. PHQ (depression) above 9. AUDIT-C 8 or higher. DAST-10 3 or higher. "
    "ACE 3 or higher. A result outside the range is a prompt for follow-up, not a diagnosis."
)

st.subheader("People screened over time")
ppl = pd.DataFrame({"In range": state.series("People In Range"),
                    "Out of range": state.series("People Out of Range")})
ppl = state.window(ppl, 13)
if not ppl.empty:
    fig2 = go.Figure()
    fig2.add_bar(x=ppl.index, y=ppl["In range"], name="In healthy range", marker_color=brand.GOOD)
    fig2.add_bar(x=ppl.index, y=ppl["Out of range"], name="Outside healthy range", marker_color=brand.ALERT)
    fig2.update_layout(barmode="stack", height=320, xaxis_tickformat="%b<br>%Y", yaxis_title="People")
    st.plotly_chart(fig2, width="stretch")

with st.expander("See the full table for this month"):
    if not s.empty:
        t = s.assign(pct=lambda x: x["out_range"] / x["total"])[["screening", "total", "in_range", "out_range", "pct"]]
        st.dataframe(t.sort_values("total", ascending=False).rename(columns={
            "screening": "Screening", "total": "Total", "in_range": "In range", "out_range": "Out of range",
            "pct": "% out of range"}), hide_index=True, width="stretch",
            column_config={"% out of range": st.column_config.NumberColumn(format="percent")})
