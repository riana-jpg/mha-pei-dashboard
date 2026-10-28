"""Rebuild data/extract from one or more PEI Monthly Summaries workbooks.

Usage (oldest workbook first; later files win for any month they share):
    python build_extract.py PEI_2026-02-28.xlsx PEI_2026-07-31.xlsx PEI_2026-08-31.xlsx
"""
import sys
from pathlib import Path

from pei_data import load_workbook, merge, save_extract

paths = [Path(p) for p in sys.argv[1:]]
if not paths:
    sys.exit(__doc__)
data = merge([load_workbook(p, source_name=p.name) for p in paths])
save_extract(data, Path(__file__).parent / "data" / "extract")
print("months:", data.months[0].strftime("%b %Y"), "to", data.months[-1].strftime("%b %Y"))
