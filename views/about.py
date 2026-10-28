import streamlit as st

import brand
import state

d = state.data()
brand.page_header("About the Data", "Where each number comes from, what the terms mean, and what to keep in mind.")

st.subheader("Where the numbers come from")
st.markdown("""
| Page | Source system | Report |
|---|---|---|
| Services & Activities | eClinicalWorks (eCW) | Cal AIM Reporting; Action Structured Data (4.28); CCMR 51.03 group classes |
| Health Screenings | eCW and Extended Reach (eR) | Preventive Raw Data (enrolled clients); eR screening results (walk-up community screenings) |
| Resources & Narcan | eR, plus eCW lookups | eR resource/outreach report; eCW for items given to enrolled clients |
| Referrals | eR and CalAIM files | eR outreach referrals; CalAIM self-referrals from the RTF/MIF |
| Clients & CalAIM | eCW and Partnership files | CCMR 2.01 (program enrollment); monthly ECM/CS RTF (official CalAIM count) |
| Mobile Clinic | eCW | 4.02 Encounter Patient Download, MHA Mobile Clinic facility |
""")

st.subheader("Plain-language glossary")
st.markdown("""
- **Care Coordination (CC):** one-on-one help connecting people to health care, benefits, food and housing.
- **Care Transitions (CT):** support for people leaving the hospital so they recover safely at home.
- **Matter of Balance (MOB):** an 8-week fall-prevention class. Clients are counted once, however many classes they attend.
- **CalAIM / ECM:** a Medi-Cal benefit (Enhanced Care Management) that pays MHA to coordinate care for high-need members.
- **Community Supports (CS):** CalAIM services such as housing and meal support.
- **Screening "out of range":** a result outside the healthy range that should be followed up. It is not a diagnosis.
- **Narcan:** a nasal spray that reverses opioid overdoses. One box holds 2 doses.
- **RTF:** the monthly file MHA sends Partnership HealthPlan confirming who is enrolled in CalAIM. It is the official count.
""")

st.subheader("Good to know")
st.markdown("""
- All numbers are **totals only**. No names, birth dates or IDs are stored in this dashboard.
- **Services are not people.** One person can receive many services in a month.
- Detailed month-by-month pages start in **April 2025**, when MHA moved to eCW. Longer trends (clients, services,
  screenings, resources, referrals) go back to **March 2022**.
- **Narcan units:** some months were recorded as boxes and some as doses. Treat month-to-month Narcan changes with care until this is standardized.
- The most recent month may be **partial** if it was pulled before the month ended.
""")

st.subheader("How to update")
st.markdown("""
1. Add the new month's tab to the PEI Monthly Summaries workbook in the usual layout.
2. Open **Update the data** in the left sidebar and upload the workbook. It replaces any month it contains.
3. Pick the new month in **Reporting month**. Every page updates.
4. To make the update permanent for everyone, the data coordinator rebuilds the bundled totals (see README).
""")

if d.warnings:
    for w in d.warnings:
        st.warning(w)
st.caption(f"Currently showing: {d.source_name} · months available: "
           f"{brand.month_label(d.months[0])} to {brand.month_label(d.months[-1])}" if d.months else "")
