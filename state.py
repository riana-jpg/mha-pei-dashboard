"""Shared data access for every page."""
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from pei_data import PEIData, load_extract, load_workbook, merge

EXTRACT_DIR = Path(__file__).parent / "data" / "extract"


def _sig():
    return tuple((p.name, p.stat().st_mtime) for p in sorted(EXTRACT_DIR.glob("*")))


@st.cache_data(show_spinner="Loading PEI data...")
def _load_bundled(signature: tuple) -> PEIData:
    return load_extract(EXTRACT_DIR)


@st.cache_data(show_spinner="Reading the uploaded workbook...")
def _load_upload(file_bytes: bytes, name: str, signature: tuple) -> PEIData:
    # The uploaded workbook wins for every month it contains.
    return merge([load_extract(EXTRACT_DIR), load_workbook(io.BytesIO(file_bytes), source_name=name)])


def data() -> PEIData:
    up = st.session_state.get("upload")
    if up is not None:
        return _load_upload(up.getvalue(), up.name, _sig())
    return _load_bundled(_sig())


def selected_month() -> pd.Timestamp:
    return st.session_state.get("month")


def prior_month(m):
    return pd.Timestamp(m) - pd.offsets.MonthBegin(1)


def series(metric: str, section: str | None = None) -> pd.Series:
    """Monthly time series from the Monthly Program Summary tab, indexed by month."""
    s = data().summary
    q = s[s["metric"].str.strip().str.lower() == metric.lower()]
    if section:
        q = q[q["section"].str.lower() == section.lower()]
    out = q.groupby("month")["value"].first().sort_index()
    if metric.lower() == "all services":
        # Some months leave the all-services total blank; fill from the program lines.
        parts = s[s["metric"].isin(["Care Coordination Services", "Care Transition Services",
                                    "MOB Activities", "Chronic Care Mgmt Activities"])]
        summed = parts.groupby("month")["value"].sum()
        out = out.combine_first(summed).sort_index()
    return out


def value_for(metric, month, section=None):
    s = series(metric, section)
    m = pd.Timestamp(month)
    return float(s.loc[m]) if m in s.index else None


def window(df: pd.DataFrame, months: int = 13) -> pd.DataFrame:
    """Rows within the trailing window ending at the selected month."""
    m = selected_month()
    if df.empty or m is None:
        return df
    start = pd.Timestamp(m) - pd.DateOffset(months=months - 1)
    if "month" in df.columns:
        return df[(df["month"] >= start) & (df["month"] <= m)]
    return df[(df.index >= start) & (df.index <= m)]
