# MHA PEI Committee Dashboard (Streamlit)

A plain-language dashboard for the PEI committee, built from the PEI Monthly Summaries workbook.
Totals only. No patient names, birth dates or IDs.

## Run it

```
pip install -r requirements.txt
streamlit run app.py
```

It opens at http://localhost:8501. To share with the committee, deploy the folder to the
approved Streamlit host (same setup as the mobile clinic financial dashboard).

## Pages

One page per type of workbook tab, with a single month picker in the sidebar instead of a tab per month.

| Page | Built from |
|---|---|
| Monthly Snapshot | Monthly Program Summary + CalAIM Clients (headline numbers, 13-month trends, same month last year) |
| Services & Activities | Monthly tabs, Activities Performed block; services-by-program trend |
| Clients & CalAIM | Monthly Program Summary (clients in program); CalAIM Clients (RTF counts) |
| Health Screenings | Monthly tabs, Screening block; people screened in/out of range |
| Resources & Narcan | Monthly tabs, Resource Distribution block |
| Referrals | Monthly Program Summary, Outreach Referrals + MHA CalAIM Self-Referral |
| Mobile Clinic | Monthly Clinical Summary; weekly site schedule; planned clinic metrics |
| About the Data | Sources, glossary, caveats, how to update |

## Update each month

Quick (no code): in the dashboard sidebar open **Update the data** and upload the newest workbook.
It wins for every month it contains, for that session only.

Permanent: rebuild the bundled totals and push them:
```
python build_extract.py PEI_2026-07-31.xlsx PEI_2026-08-31.xlsx PEI_new.xlsx   # oldest first
```
This rewrites `data/extract/` (CSV totals only). The raw workbooks are never stored in the app,
because they include CHW names and billing figures.

## Files

- `app.py` - navigation and sidebar
- `pei_data.py` - reads workbooks into tidy tables (finds blocks by label, so small layout changes are fine), merges them, and saves/loads the bundled totals
- `build_extract.py` - rebuilds `data/extract/` from one or more workbooks
- `data/extract/` - the totals-only CSVs the app shows
- `brand.py` - MHA colors, fonts, chart template and card styles. Put exact brand-kit hex codes here.
- `state.py` - shared data access and month selection
- `views/` - one file per page
- `.streamlit/config.toml` - theme

## Known limits

- Month-by-month detail starts April 2025 (eCW era). Pre-eCW monthly tabs use a different layout and are
  only shown through the long-run trends.
- Bundled data: workbooks through 02/28/26, 07/31/26 and 08/31/26 (newest wins per month). Data runs April 2025 to August 2026.
- June 2026 and July 2026 CalAIM counts are not in the August workbook; July (81) comes from the July workbook. June is blank.
- Narcan units were mixed between boxes and doses in some months.
