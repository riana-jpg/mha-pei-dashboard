"""Read the PEI Monthly Summaries workbook into tidy tables.

The workbook is totals-only (no patient data). Layouts have drifted over the
years, so every parser looks for labels rather than fixed cell addresses.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

import openpyxl
import pandas as pd

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

# Program group headings that appear inside the "Activities Performed" block.
PROGRAM_HEADS = {
    "care coordination": "Care Coordination",
    "care transitions": "Care Transitions",
    "matter of balance": "Matter of Balance",
    "chronic care management": "Chronic Care Management",
    "healthy living": "Healthy Living",
    "healthy living class": "Healthy Living",
}

BLOCKS = {
    "activities performed": "activities",
    "screening": "screening",
    "resource distribution": "resources",
    "referrals": "referrals",
}


def _txt(v) -> str:
    return str(v).strip() if v is not None else ""


def _num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def parse_month_label(label: str, default_year: int | None = None) -> pd.Timestamp | None:
    """'February 2026', 'Feb 2026', "Feb '26", "Sept '24", 'July 2026 (New)' -> first of month."""
    s = _txt(label).lower().replace("(new)", "").replace("'", " '").strip()
    m = re.match(r"([a-z]+)\.?\s*'?\s*(\d{2,4})?", s)
    if not m:
        return None
    mon = MONTHS.get(m.group(1)[:3])
    if not mon:
        return None
    yr = m.group(2)
    if yr:
        yr = int(yr)
        if yr < 100:
            yr += 2000
    else:
        yr = default_year
    if not yr:
        return None
    return pd.Timestamp(year=yr, month=mon, day=1)


@dataclass
class PEIData:
    activities: pd.DataFrame = field(default_factory=pd.DataFrame)   # month, program, activity, count
    screening: pd.DataFrame = field(default_factory=pd.DataFrame)    # month, screening, total, in_range, out_range
    resources: pd.DataFrame = field(default_factory=pd.DataFrame)    # month, resource, count
    referrals: pd.DataFrame = field(default_factory=pd.DataFrame)    # month, destination, count
    summary: pd.DataFrame = field(default_factory=pd.DataFrame)      # month, section, metric, value
    calaim: pd.DataFrame = field(default_factory=pd.DataFrame)       # month, ecm, cs, total, ending
    clinic: pd.DataFrame = field(default_factory=pd.DataFrame)       # month, site, encounters, days
    clinic_notes: list = field(default_factory=list)
    source_name: str = ""
    warnings: list = field(default_factory=list)

    @property
    def months(self) -> list[pd.Timestamp]:
        ms = set()
        for df in (self.activities, self.screening, self.resources, self.referrals):
            if not df.empty:
                ms.update(df["month"].unique())
        return sorted(pd.Timestamp(m) for m in ms)


# ---------------------------------------------------------------- monthly tabs
def _find_blocks(ws):
    """Return {block: (row, label_col)} for each block header on a monthly tab."""
    found = {}
    for row in ws.iter_rows():
        for c in row:
            key = _txt(c.value).lower()
            if key in BLOCKS and BLOCKS[key] not in found:
                # Header must have 'Count' in the next column to count as a block.
                nxt = _txt(ws.cell(c.row, c.column + 1).value).lower()
                if nxt == "count":
                    found[BLOCKS[key]] = (c.row, c.column)
    return found


def _block_rows(ws, start_row, col, max_blank=2):
    """Yield (label, value) under a block header until Grand Total or a blank run."""
    blanks = 0
    r = start_row + 1
    while r <= ws.max_row:
        label = _txt(ws.cell(r, col).value)
        val = ws.cell(r, col + 1).value
        if not label:
            blanks += 1
            if blanks > max_blank:
                break
            r += 1
            continue
        blanks = 0
        if label.lower().startswith("grand total"):
            break
        # Stop if we run into the next block header.
        if label.lower() in BLOCKS and _txt(ws.cell(r, col + 1).value).lower() == "count":
            break
        yield r, label, val
        r += 1


def _parse_month_tab(ws, month, out):
    blocks = _find_blocks(ws)

    if "activities" in blocks:
        r0, col = blocks["activities"]
        program = "Care Coordination"
        for _, label, val in _block_rows(ws, r0, col):
            low = label.lower().strip()
            if low in PROGRAM_HEADS:
                program = PROGRAM_HEADS[low]
                continue
            n = _num(val)
            if n is None:
                continue
            if program == "Matter of Balance" and low.startswith("mob class"):
                out["activities"].append((month, program, label, n))
            else:
                out["activities"].append((month, program, label, n))

    if "screening" in blocks:
        r0, col = blocks["screening"]
        cur = None
        for _, label, val in _block_rows(ws, r0, col):
            low = label.lower()
            if low.startswith("%"):
                continue
            if low == "in range" and cur:
                cur["in_range"] = _num(val)
            elif low == "out of range" and cur:
                cur["out_range"] = _num(val)
            else:
                if cur:
                    out["screening"].append(cur)
                cur = {"month": month, "screening": label, "total": _num(val),
                       "in_range": None, "out_range": None}
        if cur:
            out["screening"].append(cur)

    if "resources" in blocks:
        r0, col = blocks["resources"]
        for _, label, val in _block_rows(ws, r0, col):
            n = _num(val)
            if n is None:
                continue
            out["resources"].append((month, label, n))

    if "referrals" in blocks:
        r0, col = blocks["referrals"]
        for _, label, val in _block_rows(ws, r0, col):
            n = _num(val)
            if n is None:
                continue
            out["referrals"].append((month, label, n))


# ------------------------------------------------------- Monthly Program Summary
def _parse_program_summary(ws, out):
    """Wide time-series sections: a label in column A with month dates across."""
    rows = list(ws.iter_rows(values_only=True))
    section, date_cols, blank_run = None, {}, 0
    all_dates = {}
    for row in rows:
        if row and _txt(row[0]) and not isinstance(row[0], datetime):
            ds = {j: v for j, v in enumerate(row) if j > 0 and isinstance(v, datetime)}
            if len(ds) >= 3:
                all_dates.update(ds)
    for i, row in enumerate(rows):
        if not row:
            continue
        if isinstance(row[0], datetime):
            # A month in column A starts the old billing table, which is not a time series row.
            date_cols = {}
            continue
        first = _txt(row[0])
        dates = {j: v for j, v in enumerate(row) if j > 0 and isinstance(v, datetime)}
        if len(dates) >= 3 and first:
            section = first.strip()
            # Some section headers stop a column short of the newest month, so merge in
            # every month column seen in any header on this tab.
            all_dates.update(dates)
            date_cols = dict(all_dates)
            blank_run = 0
            continue
        if not date_cols:
            continue
        has_vals = any(_num(row[j]) is not None for j in date_cols if j < len(row))
        if not has_vals:
            blank_run += 1
            if blank_run > 4:
                date_cols = {}
            continue
        blank_run = 0
        # Unlabelled row under the services block is the all-services total.
        label = first or "All services"
        for j, d in date_cols.items():
            if j < len(row):
                n = _num(row[j])
                if n is not None:
                    out["summary"].append((pd.Timestamp(d).to_period("M").to_timestamp(), section, label.strip(), n))


# ---------------------------------------------------------------- CalAIM Clients
def _parse_calaim(ws, out, default_year=None):
    """Monthly RTF counts. Handles the long month list and the single-month block
    ('August' over a header row and a 'Count' row). Quarterly tables are skipped."""
    for row in ws.iter_rows():
        for c in row:
            if _txt(c.value).lower() != "ecm total":
                continue
            hr, hc = c.row, c.column
            if _txt(ws.cell(hr, hc - 1).value).lower().startswith("quarter"):
                continue
            heads = {}
            for cc in range(hc, hc + 8):
                h = _txt(ws.cell(hr, cc).value).lower()
                if h:
                    heads[h] = cc

            def g(r, k):
                col = next((v for h, v in heads.items() if h.startswith(k)), None)
                return _num(ws.cell(r, col).value) if col else None

            r = hr + 1
            while r <= ws.max_row:
                lab = _txt(ws.cell(r, hc - 1).value)
                if lab.lower().startswith("count"):
                    m = parse_month_label(_txt(ws.cell(hr - 1, hc - 1).value), default_year)
                    if m is not None:
                        out["calaim"].append({"month": m, "ecm": g(r, "ecm"), "cs": g(r, "cs"),
                                              "total": g(r, "grand"), "ending": g(r, "ending")})
                    break
                m = parse_month_label(lab) if lab else None
                if m is None:
                    break
                out["calaim"].append({"month": m, "ecm": g(r, "ecm"), "cs": g(r, "cs"),
                                      "total": g(r, "grand"), "ending": g(r, "ending")})
                r += 1


# --------------------------------------------------------- Monthly Clinical Summary
def _parse_clinic(ws, out):
    start_year = None
    for row in ws.iter_rows(values_only=True):
        for v in row:
            m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})\s*-", _txt(v))
            if m:
                y = int(m.group(3))
                start_year = y + 2000 if y < 100 else y
                break
        if start_year:
            break
    header_row = None
    for row in ws.iter_rows():
        for c in row:
            if _txt(c.value).lower() == "location" and _txt(ws.cell(c.row, c.column + 1).value).lower() == "encounters":
                header_row, col = c.row, c.column
                break
        if header_row:
            break
    for row in ws.iter_rows(max_row=8, values_only=True):
        for v in row:
            t = _txt(v)
            if t and re.search(r"(encounters|physicals|flu)", t, re.I):
                out["clinic_notes"].append(t)
    if not header_row or not start_year:
        return
    year, last_mon, cur_month = start_year, None, None
    r = header_row + 1
    while r <= ws.max_row:
        label = _txt(ws.cell(r, col).value)
        enc = _num(ws.cell(r, col + 1).value)
        days = _num(ws.cell(r, col + 2).value)
        if not label:
            r += 1
            if r > header_row + 80:
                break
            continue
        low = label.lower()
        if low.startswith("total"):
            break
        mon = MONTHS.get(low[:3]) if len(low) <= 9 and low[:3] in MONTHS and not low.startswith("man") else None
        if mon:
            if last_mon and mon < last_mon:
                year += 1
            last_mon = mon
            cur_month = pd.Timestamp(year=year, month=mon, day=1)
        elif cur_month is not None and enc is not None:
            out["clinic"].append({"month": cur_month, "site": label, "encounters": enc, "days": days})
        r += 1


# --------------------------------------------------------------------- loader
def load_workbook(path_or_buffer, source_name: str = "") -> PEIData:
    wb = openpyxl.load_workbook(path_or_buffer, data_only=True, read_only=False)
    out = {k: [] for k in ("activities", "screening", "resources", "referrals", "summary",
                           "calaim", "clinic", "clinic_notes")}
    seen_months = {}
    calaim_sheets = []
    for name in wb.sheetnames:
        ws = wb[name]
        low = name.lower().strip()
        if low.startswith("monthly program summary"):
            _parse_program_summary(ws, out)
            continue
        if low.startswith("calaim clients"):
            calaim_sheets.append(ws)
            continue
        if low.startswith("monthly clinical summary"):
            _parse_clinic(ws, out)
            continue
        m = parse_month_label(name)
        if m is None or not re.search(r"\d{4}", name):
            continue
        # If a month appears twice ("July 2026" and "July 2026 (New)"), keep the (New) one.
        is_new = "(new)" in low
        if m in seen_months and not is_new:
            continue
        if m in seen_months and is_new:
            for k in ("activities", "resources", "referrals"):
                out[k] = [t for t in out[k] if t[0] != m]
            out["screening"] = [d for d in out["screening"] if d["month"] != m]
        seen_months[m] = name
        _parse_month_tab(ws, m, out)

    # A single-month CalAIM block names only the month, so give it the year of the newest month tab.
    latest_year = max(seen_months).year if seen_months else None
    for ws in calaim_sheets:
        _parse_calaim(ws, out, latest_year)

    d = PEIData(source_name=source_name)
    d.activities = pd.DataFrame(out["activities"], columns=["month", "program", "activity", "count"])
    d.screening = pd.DataFrame(out["screening"], columns=["month", "screening", "total", "in_range", "out_range"])
    # Some months leave the type row blank and only fill In/Out of Range.
    d.screening["total"] = d.screening["total"].fillna(
        d.screening["in_range"].fillna(0) + d.screening["out_range"].fillna(0))
    d.screening["in_range"] = d.screening["in_range"].fillna(0)
    d.screening["out_range"] = d.screening["out_range"].fillna(0)
    d.resources = pd.DataFrame(out["resources"], columns=["month", "resource", "count"])
    d.referrals = pd.DataFrame(out["referrals"], columns=["month", "destination", "count"])
    s = pd.DataFrame(out["summary"], columns=["month", "section", "metric", "value"])
    # Later tabs ("(New)") come first in the workbook, so keep the first value seen.
    d.summary = s.drop_duplicates(["month", "section", "metric"], keep="first")
    c = pd.DataFrame(out["calaim"], columns=["month", "ecm", "cs", "total", "ending"])
    d.calaim = c.drop_duplicates("month", keep="first").sort_values("month")
    k = pd.DataFrame(out["clinic"], columns=["month", "site", "encounters", "days"])
    d.clinic = k.drop_duplicates(["month", "site"], keep="first")
    d.clinic_notes = list(dict.fromkeys(out["clinic_notes"]))

    # Clean labels so the same thing has one name across months.
    d.resources["resource"] = d.resources["resource"].str.replace(r"\s+Distribution$", "", regex=True).str.strip()
    d.screening["screening"] = d.screening["screening"].str.replace(r"\s+Screening$", "", regex=True).str.strip()
    d.referrals["destination"] = d.referrals["destination"].str.strip()
    if d.activities.empty:
        d.warnings.append("No monthly activity tabs were found in this workbook.")
    return d


def merge(datasets: list[PEIData]) -> PEIData:
    """Combine workbooks ordered oldest to newest. For each month, the newest workbook
    that has that month wins, so later corrections replace earlier numbers."""
    if not datasets:
        return PEIData()
    out = PEIData(source_name=", ".join(d.source_name for d in datasets))
    keys = {"activities": None, "screening": None, "resources": None, "referrals": None,
            "summary": ["month", "section", "metric"], "calaim": ["month"], "clinic": None}
    for name, key in keys.items():
        frames = []
        for rank, d in enumerate(datasets):
            df = getattr(d, name)
            if not df.empty:
                frames.append(df.assign(_rank=rank))
        if not frames:
            setattr(out, name, getattr(datasets[-1], name))
            continue
        allf = pd.concat(frames, ignore_index=True)
        if key:
            allf = allf.sort_values("_rank").drop_duplicates(key, keep="last")
        else:
            # Whole-month replacement: keep each month only from the newest workbook that has it.
            newest = allf.groupby("month")["_rank"].transform("max")
            allf = allf[allf["_rank"] == newest]
        setattr(out, name, allf.drop(columns="_rank").sort_values("month").reset_index(drop=True))
    out.clinic_notes = datasets[-1].clinic_notes
    out.warnings = [w for d in datasets for w in d.warnings]
    return out


TABLES = ["activities", "screening", "resources", "referrals", "summary", "calaim", "clinic"]


def save_extract(d: PEIData, folder) -> None:
    """Write the totals-only tables the dashboard needs. No raw workbook is copied."""
    import json
    from pathlib import Path
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for t in TABLES:
        getattr(d, t).to_csv(folder / f"{t}.csv", index=False)
    (folder / "meta.json").write_text(json.dumps({
        "source": d.source_name, "clinic_notes": d.clinic_notes,
        "built": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}, indent=2))


def load_extract(folder) -> PEIData:
    import json
    from pathlib import Path
    folder = Path(folder)
    d = PEIData()
    for t in TABLES:
        p = folder / f"{t}.csv"
        if p.exists():
            df = pd.read_csv(p, parse_dates=["month"])
            setattr(d, t, df)
    meta = json.loads((folder / "meta.json").read_text()) if (folder / "meta.json").exists() else {}
    d.source_name = meta.get("source", "bundled extract")
    d.clinic_notes = meta.get("clinic_notes", [])
    return d


if __name__ == "__main__":
    import sys
    data = load_workbook(sys.argv[1])
    print("months:", [m.strftime("%b %Y") for m in data.months])
    for name in ("activities", "screening", "resources", "referrals", "summary", "calaim", "clinic"):
        df = getattr(data, name)
        print(f"\n== {name}: {len(df)} rows")
        print(df.tail(6).to_string())
    print(data.clinic_notes)
