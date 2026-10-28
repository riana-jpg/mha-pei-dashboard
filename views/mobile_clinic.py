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
brand.page_header("Mobile Clinic",
                  "Primary care on wheels: where the clinic went, how many visits it had, and who it served.")

k = d.clinic.copy()
OTHER = ("flu", "physical")
k["kind"] = k["site"].str.lower().apply(lambda s: "Special event" if any(o in s for o in OTHER) else "Clinic day")
reg = k[k["kind"] == "Clinic day"]
by_month = reg.groupby("month").agg(encounters=("encounters", "sum"), days=("days", "sum"))
by_month["per_day"] = by_month["encounters"] / by_month["days"].where(by_month["days"] > 0)

latest = by_month.index.max() if not by_month.empty else None
show = m if m in by_month.index else latest
pm = state.prior_month(show) if show is not None else None

if show is None:
    st.info("No mobile clinic data in this workbook yet.")
else:
    if show != m:
        brand.note(f"Mobile clinic detail in this workbook runs through <b>{brand.month_label(latest)}</b>. "
                   f"Showing that month.")
    row = by_month.loc[show]
    prow = by_month.loc[pm] if pm in by_month.index else None
    c = st.columns(4)
    with c[0]:
        brand.kpi("Visits", row["encounters"], prow["encounters"] if prow is not None else None)
    with c[1]:
        brand.kpi("Clinic days", row["days"], prow["days"] if prow is not None else None, gold=True)
    with c[2]:
        brand.kpi("Visits per clinic day", round(row["per_day"], 1) if pd.notna(row["per_day"]) else None)
    with c[3]:
        brand.kpi("Visits since opening", by_month["encounters"].sum(), gold=True,
                  help_text="Regular clinic days only; excludes flu-shot and sports-physical events")

    st.write("")
    left, right = st.columns([3, 2])
    with left:
        fig = px.bar(reg, x="month", y="encounters", color="site", barmode="stack",
                     labels={"encounters": "Visits", "month": "", "site": "Site"},
                     color_discrete_sequence=brand.PALETTE)
        fig.update_layout(title="Visits by site, by month", height=360, xaxis_tickformat="%b<br>%Y")
        st.plotly_chart(fig, width="stretch")
    with right:
        cur = reg[reg["month"] == show]
        if not cur.empty:
            fig2 = px.pie(cur, names="site", values="encounters", hole=0.55,
                          color_discrete_sequence=brand.PALETTE)
            fig2.update_traces(textinfo="label+value")
            fig2.update_layout(title=f"Visits by site, {brand.month_label(show)}", height=360, showlegend=False)
            st.plotly_chart(fig2, width="stretch")

    ev = k[k["kind"] == "Special event"]
    if not ev.empty:
        st.caption("Special events (not counted above): " +
                   "; ".join(f"{r.site} {brand.month_label(r.month)}: {r.encounters:,.0f}" for r in ev.itertuples()))

st.subheader("Where the clinic goes each week")
sched = pd.DataFrame([
    ("Monday", "Point Arena High School", "8 am – 4 pm"),
    ("Tuesday", "Point Arena High School", "8 am – 4 pm"),
    ("Wednesday", "Twofish Bakery (Stewarts Point)", "8 am – 4 pm"),
    ("Thursday", "Alternates: Point Arena Port Rd / Manchester Elementary", "8 am – 4 pm"),
], columns=["Day", "Site", "Usual hours"])
st.dataframe(sched, hide_index=True, width="stretch")
brand.note("Source: monthly schedule flyers on the MHA website (Mobile Health Clinic page). "
           "Holidays and special events change the pattern. In November 2026 there is no clinic Nov 9–12 or on "
           "Thanksgiving, and Thursdays are Port Rd only.")

st.subheader("Coming next")
st.markdown(
    "The committee asked for more detail on the mobile clinic. These views are being built from eCW and will "
    "appear here once the data is pulled:\n"
    "- Appointments per day by location, and days in service\n"
    "- Cancellations and no-shows, with reasons and how many were rescheduled\n"
    "- Patients seen each month, new vs. returning, and total enrolled\n"
    "- Insurance (payer) mix\n"
    "- Age group, gender, language, ethnicity and ZIP code of patients\n"
    "- Visit types (office visit, MAT, urgent care, telehealth, women's health, physicals)\n"
    "- Patients with high blood pressure, diabetes or obesity, by age group and gender"
)
