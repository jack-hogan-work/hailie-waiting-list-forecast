# Initial Exploratory Data Analysis — National & Regional (Week 1)

**Source:** MHCLG Live Table 600, Regional Data worksheet, 1987–2025 (households on the register at 1 April each year). Retrieved 7 August 2026. See `data/README.md` for extraction and transformation detail.
**Data:** `data/processed/regional_waiting_lists_long.csv`, validated against the raw extract for 1987, 2015, 2020, 2024 and 2025 in `docs/national_validation.md`.
**Script:** `scripts/explore_national.py` (standard-library `csv` for data loading; matplotlib, installed only in the project-local `.venv`, for charts). Every figure quoted below is printed directly by that script from the processed dataset — none is estimated by eye from a chart.
**Charts:** `outputs/figures/england_waiting_list_1987_2025.png`, `england_waiting_list_2010_2025.png`, `regional_waiting_list_trends.png`, `england_annual_percentage_change.png`.

This is a descriptive read of the series only. **No forecasting, trend-fitting, or causal interpretation is performed in this note** — per the Week 1 EDA scope, that is left to later work.

## 1. England total, 1987–2025

- The England total starts at **1,289,492** households (1987) and ends at **1,340,527** (2025) — a rise of **51,035 households (+4.0%)** over the full 39-year span, but that headline comparison masks a large amount of movement in between.
- The series is not monotonic. It reaches a **trough of 1,020,229 in 1998** and a **peak of 1,851,884 in 2012** — the peak is roughly 82% higher than the trough.
- Visually the series traces two broad cycles: a fall from 1987 to the late 1990s, a sustained rise from the late 1990s/early 2000s to a peak around 2011–2012, then a sharp fall through the mid-2010s to a second, shallower trough around 2018, followed by a renewed rise to 2025.
- Over 1988–2025 (38 year-on-year changes), **21 years saw an increase and 17 a decrease**; no year was exactly flat.
- The single largest year-on-year rise was **+16.1% in 2003**; the single largest year-on-year fall was **-18.8% in 2014**. Both sit inside the two cyclical turning periods identified above.
- The most recent period shows renewed growth: the total rose from **1,137,234 in 2020 to 1,340,527 in 2025**, an increase of **203,293 households (+17.9%)** over five years, with 2024 (1,330,602) and 2025 (1,340,527) the two highest values recorded since 2013.

See `outputs/figures/england_waiting_list_1987_2025.png` for the full series and `outputs/figures/england_waiting_list_2010_2025.png` for a zoomed view of the 2010–2025 fall-and-recovery.

## 2. Year-on-year percentage change

`outputs/figures/england_annual_percentage_change.png` shows the year-on-year % change for each year from 1988 to 2025. The two largest single-year swings — the +16.1% jump in 2003 and the -18.8% drop in 2014 — stand out clearly against a background of mostly single-digit annual moves. The chart's caption flags, and `data/README.md` and `docs/initial_feasibility_note.md` document in more detail, that register counts can move for administrative reasons (periodic list "cleanses") as well as changes in underlying demand; this analysis does not attempt to separate the two, so no cause should be inferred for any individual year's swing from this chart alone.

## 3. Regional comparison (nine English regions; England total excluded)

`outputs/figures/regional_waiting_list_trends.png` shows each of the nine English regions as its own panel (small multiples), each with its own y-axis scale — panels are not designed for at-a-glance magnitude comparison; the 2025 snapshot below gives that instead.

**2025 households on the register, largest to smallest:**

| Region | 2025 |
| --- | ---: |
| London | 341,009 |
| North West | 209,887 |
| Yorkshire and The Humber | 172,536 |
| South West | 133,231 |
| West Midlands | 127,179 |
| South East | 117,590 |
| East of England | 91,871 |
| East Midlands | 84,013 |
| North East | 63,211 |

The nine regional 2025 figures sum to **1,340,527**, matching the England total row exactly — consistent with the England row being a straightforward sum of the nine regions in this dataset. This sum was calculated by `scripts/explore_national.py`; `docs/national_validation.md` validates only the five England-total values listed there (1987, 2015, 2020, 2024, 2025) and does not itself check the regional sum.

**Change from 1987 to 2025 by region** (same caution as §1 applies — long-span comparisons mask the intervening cycle):

| Region | 1987 | 2025 | Change |
| --- | ---: | ---: | ---: |
| South West | 87,053 | 133,231 | +53.0% |
| London | 264,343 | 341,009 | +29.0% |
| Yorkshire and The Humber | 160,058 | 172,536 | +7.8% |
| North West | 195,620 | 209,887 | +7.3% |
| West Midlands | 132,023 | 127,179 | -3.7% |
| South East | 127,080 | 117,590 | -7.5% |
| East of England | 115,779 | 91,871 | -20.6% |
| East Midlands | 110,436 | 84,013 | -23.9% |
| North East | 97,100 | 63,211 | -34.9% |

The nine regions do not move uniformly: over the full period the South West and London show the largest proportional increases, while the North East, East Midlands and East of England show the largest proportional falls. All nine regions broadly share the shape described in §1 (a rise to a peak around 2011–2012 and a fall to a trough later in the 2010s, visible in every panel of the small-multiples chart), but they differ in the size of that swing and in where each currently sits relative to its own 1987 starting point.

## 4. Limitations carried into this note

- **Not a causal analysis.** Nothing here identifies drivers of any rise or fall — policy changes, local housing supply, register review cycles, and economic conditions are all plausible contributing factors that this note does not attempt to disentangle.
- **Administrative "cleanse" effect.** As documented in `docs/initial_feasibility_note.md` §5, councils periodically review and remove applicants from their registers; falls in the reported count can reflect this administrative practice rather than a genuine reduction in housing need. This applies to any of the falls described above, most plausibly the sharp 2012–2014 national fall.
- **Not a complete measure of housing need.** Live Table 600 covers local authorities' own housing registers only; it excludes housing-association-run waiting lists in areas where these are separate from the council register, so it understates total social housing demand to a degree that varies by area (`docs/initial_feasibility_note.md` §5).
- **England total validated for five years only.** `docs/national_validation.md` checks 1987, 2015, 2020, 2024 and 2025 against the raw extract; it is not a full independent audit of the underlying MHCLG publication.
- **Regional-panel y-axes are independent.** In `regional_waiting_list_trends.png`, each region's panel is scaled to its own range; comparing the visual "steepness" of two panels without reading the axis ticks will mislead.
