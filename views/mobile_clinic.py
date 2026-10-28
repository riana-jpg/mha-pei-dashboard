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

# ------------------------------------------------------------------ monthly calendar
import calendar as _cal
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SITE_COLORS = {  # tints that echo the colors on the public flyers
    "Point Arena High School": ("#F2C14E", "#3B2F0B"),
    "Twofish Bakery": ("#A9C6EA", "#14304F"),
    "Point Arena Port Rd": ("#9CCB7A", "#1F3A12"),
    "Manchester Elementary": ("#F4E46B", "#3A3409"),
    "MHA Main Office": ("#D9B3A8", "#4A1E12"),
}


@st.cache_data
def _schedule():
    p = DATA / "clinic_schedule.csv"
    if not p.exists():
        return pd.DataFrame(columns=["date", "site", "hours", "note"])
    s = pd.read_csv(p, parse_dates=["date"])
    s["note"] = s["note"].fillna("")
    return s


@st.cache_data
def _visits():
    p = DATA / "clinic_visits.csv"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else pd.DataFrame()


sch = _schedule()
st.subheader("Where the clinic went, day by day")
if sch.empty:
    st.info("No schedule loaded yet.")
else:
    cal_months = sorted(sch["date"].dt.to_period("M").dt.to_timestamp().unique())
    labels = [brand.month_label(x) for x in cal_months]
    pick_ix = cal_months.index(m) if m in cal_months else len(cal_months) - 1
    pick = st.selectbox("Calendar month", labels, index=pick_ix, key="cal_month",
                        help="Follows the reporting month when that month's schedule is on file.")
    cm = cal_months[labels.index(pick)]
    month_rows = sch[sch["date"].dt.to_period("M").dt.to_timestamp() == cm]
    by_day = {r.date.day: r for r in month_rows.itertuples()}

    weeks = _cal.Calendar(firstweekday=6).monthdayscalendar(cm.year, cm.month)  # Sunday first, like the flyers
    head = "".join(f"<th>{d}</th>" for d in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"])
    body = ""
    for wk in weeks:
        body += "<tr>"
        for i, day in enumerate(wk):
            if day == 0:
                body += "<td class='cal-empty'></td>"
                continue
            r = by_day.get(day)
            chip = ""
            if r is not None:
                bg, fg = SITE_COLORS.get(r.site, ("#E3E0D8", brand.INK))
                note = f"<div class='cal-note'>{r.note}</div>" if r.note else ""
                chip = (f"<div class='cal-chip' style='background:{bg};color:{fg}'>{r.site}</div>"
                        f"<div class='cal-hours'>{r.hours}</div>{note}")
            weekend = " cal-weekend" if i in (0, 6) else ""
            body += f"<td class='cal-day{weekend}'><div class='cal-num'>{day}</div>{chip}</td>"
        body += "</tr>"
    st.markdown(
        f"""
        <style>
        .cal {{ width:100%; border-collapse:collapse; table-layout:fixed; font-family:{brand.FONT}; }}
        .cal th {{ background:{brand.NAVY}; color:white; font-weight:600; font-size:.85rem; padding:6px; }}
        .cal td {{ border:1px solid {brand.GRID}; vertical-align:top; height:84px; padding:4px 6px; }}
        .cal-weekend {{ background:#FAF8F3; }}
        .cal-num {{ font-size:.8rem; color:{brand.MUTED}; text-align:right; }}
        .cal-chip {{ border-radius:6px; padding:3px 6px; font-size:.78rem; font-weight:600; line-height:1.2; }}
        .cal-hours {{ font-size:.75rem; color:{brand.INK}; margin-top:3px; }}
        .cal-note {{ font-size:.72rem; color:{brand.ALERT}; font-weight:600; }}
        </style>
        <table class='cal'><tr>{head}</tr>{body}</table>
        """,
        unsafe_allow_html=True,
    )
    days_by_site = month_rows.groupby("site").size().sort_values(ascending=False)
    st.caption("Clinic days this month: " + " · ".join(f"{s} {n}" for s, n in days_by_site.items()))
    brand.note("Source: the monthly schedule flyers posted on the MHA website's Mobile Health Clinic page. "
               "This is the plan as published; a day can still be cancelled after posting. "
               "Usual pattern: Mon and Tue Point Arena High School, Wed Twofish Bakery, Thu alternating "
               "Point Arena Port Rd and Manchester Elementary.")

# ------------------------------------------------------------- services and patients by site
st.subheader("Services at each site")
v = _visits()
if v.empty:
    brand.note("<b>Coming once the eCW visit data is loaded.</b> This section will show the types of visits at "
               "each site (office visit, MAT, urgent care, telehealth, women's health, physicals) and the average "
               "number of patients seen per clinic day at each site. It reads <code>data/clinic_visits.csv</code>: "
               "totals by date, site and visit type from eCW report 4.02, with no patient identifiers.")
else:
    v["month"] = v["date"].dt.to_period("M").dt.to_timestamp()
    vm = v[v["month"] == m]
    if vm.empty:
        vm_month = v["month"].max()
        brand.note(f"Visit detail runs through <b>{brand.month_label(vm_month)}</b>. Showing that month.")
        vm = v[v["month"] == vm_month]
    sites = list(vm.groupby("site")["encounters"].sum().sort_values(ascending=False).index)
    site_pick = st.radio("Site", ["All sites"] + sites, horizontal=True, key="svc_site")
    sel = vm if site_pick == "All sites" else vm[vm["site"] == site_pick]
    types = sel.groupby("visit_type")["encounters"].sum().sort_values()
    fig3 = go.Figure(go.Bar(x=types.values, y=types.index, orientation="h", marker_color=brand.NAVY,
                            text=types.values, texttemplate="%{text:,.0f}", textposition="outside",
                            hovertemplate="%{y}: %{x:,.0f} visits<extra></extra>"))
    fig3.update_layout(title=f"Visit types, {site_pick.lower() if site_pick == 'All sites' else site_pick}",
                       height=max(280, 34 * len(types) + 90), xaxis_title="Visits")
    st.plotly_chart(fig3, width="stretch")

    mix = vm.groupby(["site", "visit_type"])["encounters"].sum().reset_index()
    fig4 = px.bar(mix, x="site", y="encounters", color="visit_type", barmode="stack",
                  labels={"encounters": "Visits", "site": "", "visit_type": "Visit type"},
                  color_discrete_sequence=brand.PALETTE)
    fig4.update_layout(title="Visit mix by site", height=360)
    st.plotly_chart(fig4, width="stretch")

    st.subheader("Average patients per clinic day, by site")
    daily = vm.groupby(["site", "date"])["patients"].sum().reset_index()
    avg = daily.groupby("site").agg(days=("date", "nunique"), patients=("patients", "sum")).reset_index()
    avg["per_day"] = avg["patients"] / avg["days"]
    avg = avg.sort_values("per_day")
    fig5 = go.Figure(go.Bar(x=avg["per_day"], y=avg["site"], orientation="h", marker_color=brand.GOLD,
                            text=[f"{p:.1f}" for p in avg["per_day"]], textposition="outside",
                            customdata=avg[["patients", "days"]],
                            hovertemplate="%{y}: %{x:.1f} patients a day<br>%{customdata[0]} patient-visits "
                                          "over %{customdata[1]} days<extra></extra>"))
    fig5.update_layout(height=max(260, 46 * len(avg) + 90), xaxis_title="Patients per clinic day")
    st.plotly_chart(fig5, width="stretch")
    brand.note("Patients per day counts each person once per day at that site, divided by the days the clinic "
               "saw at least one patient there. Telehealth visits count under the site scheduled that day.")

st.subheader("Coming next")
st.markdown(
    "Still to come from eCW:\n"
    "- Cancellations and no-shows, with reasons and how many were rescheduled\n"
    "- New vs. returning patients, and total enrolled\n"
    "- Insurance (payer) mix\n"
    "- Age group, gender, language, ethnicity and ZIP code of patients\n"
    "- Patients with high blood pressure, diabetes or obesity, by age group and gender"
)
