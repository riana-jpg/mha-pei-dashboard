"""MHA PEI Committee Dashboard.

Run:  streamlit run app.py
"""
import streamlit as st

import brand
import state

st.set_page_config(page_title="MHA PEI Dashboard", page_icon="🌊", layout="wide")
brand.inject_css()

pages = {
    "Start here": [
        st.Page("views/overview.py", title="Monthly Snapshot", icon=":material/dashboard:", default=True),
        st.Page("views/quarterly.py", title="Quarterly Summary", icon=":material/calendar_view_month:"),
    ],
    "Program activity": [
        st.Page("views/activities.py", title="Services & Activities", icon=":material/volunteer_activism:"),
        st.Page("views/clients.py", title="Clients & CalAIM", icon=":material/groups:"),
    ],
    "Community health": [
        st.Page("views/screenings.py", title="Health Screenings", icon=":material/monitor_heart:"),
        st.Page("views/resources.py", title="Resources & Narcan", icon=":material/inventory_2:"),
    ],
    "Clinical": [
        st.Page("views/mobile_clinic.py", title="Mobile Clinic", icon=":material/local_shipping:"),
    ],
    "Reference": [
        st.Page("views/about.py", title="About the Data", icon=":material/info:"),
    ],
}
nav = st.navigation(pages)

with st.sidebar:
    st.markdown(f"<h3 style='color:{brand.NAVY};margin-bottom:0'>Mendonoma Health Alliance</h3>"
                f"<div style='color:{brand.MUTED};margin-bottom:12px'>PEI Committee Dashboard</div>",
                unsafe_allow_html=True)
    d = state.data()
    months = d.months
    if months:
        labels = [brand.month_label(m) for m in months]
        if st.session_state.get("month_pick") not in labels:
            st.session_state["month_pick"] = labels[-1]
        pick = st.selectbox("Reporting month", labels, key="month_pick",
                            help="Every page updates to show this month.")
        st.session_state["month"] = months[labels.index(pick)]
        try:
            import report_pdf
            st.download_button(
                "Download this month as a PDF",
                data=report_pdf.build(d, st.session_state["month"]),
                file_name=f"PEI_Report_{st.session_state['month']:%Y-%m}.pdf",
                mime="application/pdf", width="stretch",
                help="A one-file summary of the selected month for the committee's shared folder.")
        except Exception as e:  # never let the export break the dashboard
            st.caption(f"PDF export unavailable: {e}")
    else:
        st.warning("No monthly tabs found in the workbook.")
    st.divider()
    with st.expander("Update the data"):
        st.file_uploader("Upload the latest PEI Monthly Summaries workbook (.xlsx)",
                         type=["xlsx"], key="upload",
                         help="Totals-only workbook. No patient names or IDs.")
        st.caption(f"Showing: {d.source_name}")

nav.run()
