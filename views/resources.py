import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import brand
import state

d = state.data()
m = state.selected_month()
if m is None:
    st.stop()
brand.page_header("Resources & Narcan",
                  f"Health supplies and harm-reduction items handed out in {brand.month_label(m)}.")

r = d.resources[d.resources["month"] == m]
is_dose_row = r["resource"].str.contains("Doses", case=False)
items = r[~is_dose_row & ~r["resource"].str.contains("Takeback|lbs", case=False)]
pm = state.prior_month(m)
rp = d.resources[d.resources["month"] == pm]

narcan = items[items["resource"].str.fullmatch("Narcan", case=False)]["count"].sum()
narcan_p = rp[rp["resource"].str.fullmatch("Narcan", case=False)]["count"].sum()
fts = items[items["resource"].str.contains("Fentanyl", case=False)]["count"].sum()
takeback = r[r["resource"].str.contains("Takeback", case=False)]["count"].sum()

c = st.columns(4)
with c[0]:
    brand.kpi("Items distributed", items["count"].sum() if not items.empty else None,
              state.value_for("Resources Distributed", pm))
with c[1]:
    brand.kpi("Narcan", narcan if narcan else None, narcan_p if narcan_p else None, gold=True)
with c[2]:
    brand.kpi("Fentanyl test strips", fts if fts else None)
with c[3]:
    brand.kpi("Medication take-back (lbs)", takeback if takeback else None, gold=True)

st.write("")
if items.empty:
    st.info("No resource detail for this month in the workbook.")
else:
    top = items.groupby("resource")["count"].sum().sort_values()
    colors = [brand.GOLD if ("narcan" in k.lower() or "fentanyl" in k.lower() or "harm" in k.lower())
              else brand.NAVY for k in top.index]
    fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=colors,
                           text=top.values, texttemplate="%{text:,.0f}", textposition="outside",
                           hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
    fig.update_layout(title="Items by type (gold = harm reduction)",
                      height=max(300, 30 * len(top) + 90), xaxis_title="Number distributed")
    st.plotly_chart(fig, width="stretch")

brand.note(
    "<b>About Narcan counts.</b> Narcan has been recorded in eR both as boxes and as doses "
    "(one box holds 2 doses; each harm-reduction bag holds 2 doses). Month-to-month Narcan "
    "numbers may not be directly comparable until a single unit is confirmed."
)

st.subheader("Resources over time")
s = state.window(state.series("Resources Distributed").to_frame("value"), 13)
nar = d.resources[d.resources["resource"].str.fullmatch("Narcan", case=False)].groupby("month")["count"].sum()
nar = state.window(nar.to_frame("value"), 13)
fig2 = go.Figure()
fig2.add_bar(x=s.index, y=s["value"], name="All resources", marker_color=brand.NAVY)
fig2.add_scatter(x=nar.index, y=nar["value"], name="Narcan", mode="lines+markers",
                 line=dict(color=brand.GOLD, width=3))
fig2.update_layout(height=320, xaxis_tickformat="%b<br>%Y", yaxis_title="Items")
st.plotly_chart(fig2, width="stretch")

with st.expander("See the full table for this month"):
    st.dataframe(r.sort_values("count", ascending=False)[["resource", "count"]]
                 .rename(columns={"resource": "Resource", "count": "Count"}),
                 hide_index=True, width="stretch")
