"""Monthly PEI report as a PDF, for the committee's shared folder.

Dashboard:  sidebar button "Download this month as a PDF".
Command line:  python report_pdf.py 2026-10 PEI_Report_2026-10.pdf
"""
import io
import sys

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import metrics

NAVY = colors.HexColor("#1F3A5F")
GOLD = colors.HexColor("#C9A227")
GRID = colors.HexColor("#E3E0D8")
SAND = colors.HexColor("#F4F1EA")

_ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_ss["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=NAVY,
                    alignment=TA_LEFT, spaceAfter=2)
SUB = ParagraphStyle("sub", parent=_ss["Normal"], fontSize=10, textColor=colors.HexColor("#6B7480"), spaceAfter=10)
H2 = ParagraphStyle("h2", parent=_ss["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
                    spaceBefore=12, spaceAfter=6)
BODY = ParagraphStyle("body", parent=_ss["Normal"], fontSize=9.5, leading=13)
NOTE = ParagraphStyle("note", parent=BODY, backColor=SAND, borderPadding=6, leftIndent=4, rightIndent=4,
                      spaceBefore=4, spaceAfter=8)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, textColor=colors.HexColor("#6B7480"))


def _n(v, pct=False, dec=0):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if pct:
        return f"{v:.0%}"
    return f"{v:,.{dec}f}"


def _delta(a, b, pct=False):
    if a is None or b is None:
        return ""
    d = a - b
    if pct:
        pts = round(d * 100)
        return f"{pts:+d} pts" if pts else "no change"
    return f"{d:+,.0f}"


def _table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    style = [("FONT", (0, 0), (-1, -1), "Helvetica", 9), ("GRID", (0, 0), (-1, -1), 0.5, GRID),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9), ("LINEBELOW", (0, 0), (-1, 0), 1.5, GOLD)]
    t.setStyle(TableStyle(style))
    return t


def build(d, month) -> bytes:
    m = pd.Timestamp(month)
    pm = m - pd.offsets.MonthBegin(1)
    cur, prv = metrics.month_row(d, m), metrics.month_row(d, pm)
    label, plabel = m.strftime("%B %Y"), pm.strftime("%B %Y")
    story = [Paragraph("Mendonoma Health Alliance", SUB),
             Paragraph(f"PEI Committee Monthly Report: {label}", H1),
             Paragraph(f"Totals only, no client information. Compared with {plabel}. "
                       f"Source: MHA PEI Dashboard (mha-pei-dashboard.streamlit.app).", SUB)]

    for t in metrics.month_notes(m, "all") + metrics.month_notes(m, "snapshot"):
        story.append(Paragraph(f"<b>Note:</b> {t}", NOTE))

    # --- headline
    story.append(Paragraph("At a glance", H2))
    head = [["Measure", label, plabel, "Change"]]
    lines = [("Clients in programs", "clients", False), ("Services provided", "services", False),
             ("People screened", "people_screened", False),
             ("Share needing follow-up", "followup_share", True),
             ("Resources distributed", "resources", False), ("Narcan (boxes, 2 doses each)", "narcan_boxes", False),
             ("CalAIM members (ECM + CS)", "calaim_total", False), ("Mobile clinic visits", "clinic_visits", False)]
    for name, key, pct in lines:
        head.append([name, _n(cur[key], pct), _n(prv[key], pct), _delta(cur[key], prv[key], pct)])
    story.append(_table(head, [2.6 * inch, 1.3 * inch, 1.3 * inch, 1.0 * inch]))

    # --- services
    story.append(Paragraph("Services and activities", H2))
    a = d.activities[d.activities["month"] == m] if not d.activities.empty else pd.DataFrame()
    if a.empty:
        story.append(Paragraph("No activity detail on file for this month.", BODY))
    else:
        allk = a.groupby("activity")["count"].sum().sort_values(ascending=False, kind="stable")
        cutoff = allk.iloc[min(9, len(allk) - 1)]
        top = allk[allk >= cutoff]  # top 10, keeping any ties at the cutoff
        rest = allk[allk < cutoff]
        rows = [["Activity type", "Count"]] + [[k, _n(v)] for k, v in top.items()]
        if not rest.empty:
            rows.append([f"All other activity types ({len(rest)})", _n(rest.sum())])
        rows.append(["Total", _n(allk.sum())])
        story.append(_table(rows, [3.6 * inch, 1.0 * inch]))

    # --- screenings
    story.append(Paragraph("Health screenings", H2))
    s = d.screening[d.screening["month"] == m] if not d.screening.empty else pd.DataFrame()
    if s.empty:
        story.append(Paragraph("No screening detail on file for this month.", BODY))
    else:
        rows = [["Screening", "Done", "In range", "Out of range"]]
        for r in s.sort_values("total", ascending=False).itertuples():
            rows.append([r.screening, _n(r.total), _n(r.in_range), _n(r.out_range)])
        rows.append(["Total", _n(s["total"].sum()), _n(s["in_range"].sum()), _n(s["out_range"].sum())])
        story.append(_table(rows, [2.2 * inch, 0.9 * inch, 0.9 * inch, 1.0 * inch]))
        story.append(Paragraph(
            f"{_n(cur['people_screened'])} people were screened and {_n(cur['people_out'])} had at least one result "
            f"to follow up ({_n(cur['followup_share'], True)}).", BODY))

    # --- resources
    story.append(Paragraph("Resources and Narcan", H2))
    r = d.resources[d.resources["month"] == m] if not d.resources.empty else pd.DataFrame()
    if r.empty:
        story.append(Paragraph("No resource detail on file for this month.", BODY))
    else:
        rows = [["Item", "Count"]] + [[k, _n(v)] for k, v in
                                      r.groupby("resource")["count"].sum().sort_values(ascending=False).items()]
        story.append(_table(rows, [3.0 * inch, 1.0 * inch]))
        story.append(Paragraph("Narcan is reported in boxes, month by month. One box holds 2 doses.", SMALL))

    # --- CalAIM
    story.append(Paragraph("CalAIM members served", H2))
    for t in metrics.month_notes(m, "calaim"):
        story.append(Paragraph(f"<b>Note:</b> {t}", NOTE))
    rows = [["", label, plabel], ["Enhanced Care Management (ECM)", _n(cur["calaim_ecm"]), _n(prv["calaim_ecm"])],
            ["Community Supports (CS)", _n(cur["calaim_cs"]), _n(prv["calaim_cs"])],
            ["Total", _n(cur["calaim_total"]), _n(prv["calaim_total"])]]
    story.append(_table(rows, [2.6 * inch, 1.3 * inch, 1.3 * inch]))
    story.append(Paragraph("From the monthly Return Transmission File (RTF) sent to Partnership HealthPlan. "
                           "The most recent month can be preliminary until the RTF is final.", SMALL))

    # --- mobile clinic
    story.append(Paragraph("Mobile clinic", H2))
    for t in metrics.month_notes(m, "mobile_clinic"):
        story.append(Paragraph(f"<b>Note:</b> {t}", NOTE))
    k = metrics.clinic_by_site(d)
    reg = k[(k["month"] == m) & (k["kind"] == "Clinic day")] if not k.empty else pd.DataFrame()
    if reg.empty:
        story.append(Paragraph("No mobile clinic visits on file for this month.", BODY))
    else:
        story.append(Paragraph(
            f"{_n(cur['clinic_visits'])} visits over {_n(cur['clinic_days'])} clinic days "
            f"({_n(cur['visits_per_day'], dec=1)} per day). {plabel}: {_n(prv['clinic_visits'])} visits over "
            f"{_n(prv['clinic_days'])} days.", BODY))
        rows = [["Site", "Visits", "Clinic days"]] + [
            [x.site, _n(x.encounters), _n(x.days)] for x in reg.sort_values("encounters", ascending=False).itertuples()]
        story.append(_table(rows, [2.6 * inch, 1.0 * inch, 1.0 * inch]))
        story.append(Paragraph("Regular clinic days only. Flu-shot clinics and sports physicals are special events "
                               "and are not counted here.", SMALL))

    story += [Spacer(1, 10), Paragraph(
        "Prepared by Riana Lee, Data Coordinator &amp; Analyst. Sources: eClinicalWorks, Extended Reach and "
        "Partnership HealthPlan CalAIM files. Live dashboard: mha-pei-dashboard.streamlit.app", SMALL)]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title=f"PEI Committee Monthly Report {label}", author="Mendonoma Health Alliance")
    doc.build(story)
    return buf.getvalue()


if __name__ == "__main__":
    from pathlib import Path
    from pei_data import load_extract
    month, out = sys.argv[1], sys.argv[2]
    data = load_extract(Path(__file__).parent / "data" / "extract")
    Path(out).write_bytes(build(data, pd.Timestamp(month + "-01")))
    print("wrote", out)
