"""Month and quarter measures shared by the dashboard pages and the PDF export.

No Streamlit here, so the PDF can be built from the command line too.
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"

# One name per mobile clinic site. eCW has several spellings of the same place; until the
# medical record uses one name per site, the dashboard folds the variants together here.
SITE_ALIASES = {
    "2fish": "Twofish Bakery",
    "two fish": "Twofish Bakery",
    "two fish bakery": "Twofish Bakery",
    "twofish": "Twofish Bakery",
    "twofish bakery": "Twofish Bakery",
    "point arena hs": "Point Arena High School",
    "pt arena hs": "Point Arena High School",
    "point arena high school": "Point Arena High School",
    "manchester": "Manchester Elementary",
    "manchester elementary": "Manchester Elementary",
}
SPECIAL_EVENT_WORDS = ("flu", "physical")


def canonical_site(name) -> str:
    s = str(name).strip()
    return SITE_ALIASES.get(s.lower(), s)


def clinic_by_site(d) -> pd.DataFrame:
    """Mobile clinic visits and days by month and site, with site names folded together.

    Adds kind = "Clinic day" or "Special event" (flu shots, sports physicals).
    """
    k = d.clinic.copy()
    if k.empty:
        return k.assign(kind=pd.Series(dtype=str))
    k = k[k["site"].astype(str).str.strip().str.lower() != "site"]  # stray header rows
    k["site"] = k["site"].map(canonical_site)
    k["kind"] = k["site"].str.lower().apply(
        lambda s: "Special event" if any(w in s for w in SPECIAL_EVENT_WORDS) else "Clinic day")
    return k.groupby(["month", "site", "kind"], as_index=False)[["encounters", "days"]].sum()


def summary_value(d, metric, month, section=None):
    s = d.summary
    if s.empty:
        return None
    q = s[s["metric"].str.strip().str.lower() == metric.lower()]
    if section:
        q = q[q["section"].str.lower() == section.lower()]
    q = q[q["month"] == pd.Timestamp(month)]
    if q.empty and metric.lower() == "all services":
        parts = s[(s["month"] == pd.Timestamp(month)) &
                  s["metric"].isin(["Care Coordination Services", "Care Transition Services",
                                    "MOB Activities", "Chronic Care Mgmt Activities"])]
        return float(parts["value"].sum()) if not parts.empty else None
    return float(q["value"].iloc[0]) if not q.empty else None


def month_row(d, month) -> dict:
    """Headline measures for one month. None where the month has no data."""
    m = pd.Timestamp(month)
    sc = d.screening[d.screening["month"] == m] if not d.screening.empty else pd.DataFrame()
    rs = d.resources[d.resources["month"] == m] if not d.resources.empty else pd.DataFrame()
    ca = d.calaim[d.calaim["month"] == m] if not d.calaim.empty else pd.DataFrame()
    k = clinic_by_site(d)
    reg = k[(k["month"] == m) & (k["kind"] == "Clinic day")] if not k.empty else pd.DataFrame()

    people = summary_value(d, "Total Screened", m)
    people_out = summary_value(d, "People Out of Range", m)
    narcan = rs.loc[rs["resource"].str.lower() == "narcan", "count"] if not rs.empty else pd.Series(dtype=float)
    visits = float(reg["encounters"].sum()) if not reg.empty else None
    days = float(reg["days"].sum()) if not reg.empty else None
    return {
        "month": m,
        "clients": summary_value(d, "Total", m, "Total Clients In Program"),
        "services": summary_value(d, "All services", m),
        "screenings": float(sc["total"].sum()) if not sc.empty else None,
        "screenings_out": float(sc["out_range"].sum()) if not sc.empty else None,
        "people_screened": people,
        "people_out": people_out,
        "followup_share": (people_out / people) if people and people_out is not None else None,
        "resources": summary_value(d, "Resources Distributed", m),
        "narcan_boxes": float(narcan.sum()) if not narcan.empty else None,
        "calaim_ecm": float(ca["ecm"].iloc[0]) if not ca.empty else None,
        "calaim_cs": float(ca["cs"].iloc[0]) if not ca.empty else None,
        "calaim_total": float(ca["total"].iloc[0]) if not ca.empty else None,
        "clinic_visits": visits,
        "clinic_days": days,
        "visits_per_day": (visits / days) if visits and days else None,
    }


# ------------------------------------------------------------------ fiscal quarters (FY starts July 1)
def fiscal_quarter(month) -> tuple[int, int]:
    m = pd.Timestamp(month)
    fy = m.year + 1 if m.month >= 7 else m.year
    return fy, ((m.month - 7) % 12) // 3 + 1


def quarter_label(fy: int, q: int) -> str:
    return f"Q{q} FY{str(fy)[-2:]}"


def quarter_months(fy: int, q: int) -> list[pd.Timestamp]:
    start = pd.Timestamp(year=fy - 1, month=7, day=1) + pd.DateOffset(months=3 * (q - 1))
    return [start + pd.DateOffset(months=i) for i in range(3)]


FLOW = ["services", "screenings", "screenings_out", "people_screened", "people_out", "resources",
        "narcan_boxes", "clinic_visits", "clinic_days"]
POINT_IN_TIME = ["clients", "calaim_ecm", "calaim_cs", "calaim_total"]


def quarter_row(d, fy: int, q: int) -> dict:
    """Quarter totals. Activity counts are added up across the months on file; client and CalAIM
    counts are the last month on file in the quarter (a snapshot, not a count of distinct people)."""
    have = set(pd.Timestamp(x) for x in d.months)
    months = [m for m in quarter_months(fy, q) if m in have]
    rows = [month_row(d, m) for m in months]
    out = {"fy": fy, "q": q, "label": quarter_label(fy, q), "months": months,
           "complete": len(months) == 3}
    for key in FLOW:
        vals = [r[key] for r in rows if r[key] is not None]
        out[key] = float(sum(vals)) if vals else None
    last = rows[-1] if rows else {}
    for key in POINT_IN_TIME:
        out[key] = last.get(key)
    out["followup_share"] = (out["people_out"] / out["people_screened"]
                             if out["people_screened"] and out["people_out"] is not None else None)
    out["visits_per_day"] = (out["clinic_visits"] / out["clinic_days"]
                             if out["clinic_visits"] and out["clinic_days"] else None)
    return out


# ------------------------------------------------------------------ notes shown on a month
def month_notes(month, page: str) -> list[str]:
    """Notes from data/notes.csv for this month and page ("all" shows on every page)."""
    p = DATA / "notes.csv"
    if not p.exists():
        return []
    n = pd.read_csv(p, parse_dates=["month"])
    n["page"] = n["page"].str.strip().str.lower()
    hit = n[(n["month"] == pd.Timestamp(month)) & (n["page"].isin([page.lower(), "all"]))]
    return hit["note"].dropna().tolist()
