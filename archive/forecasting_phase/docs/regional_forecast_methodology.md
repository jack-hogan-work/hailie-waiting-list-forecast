# Regional Forecasting & Backtesting — Methodology and Results (Week 2 extension)

**Scope note:** the original session goal was national-only forecasting (`docs/national_forecast_methodology.md`). This work extends that to the nine English regions individually, as a deliberate, user-approved follow-on rather than an unprompted scope change — the user was asked directly whether to extend to regional forecasting, install a new package for ARIMA/Holt-Winters, or stop, and chose the regional extension.

**Source:** MHCLG Live Table 600, Regional Data worksheet, the nine English regions (`Area code` E12000001-E12000009), 1987-2025, 39 annual observations each, 0 missing (same validated file as the national work; the England total row `E92000001` is excluded here since it is already covered by `scripts/forecast_national.py`).
**Script:** `scripts/forecast_regional.py`. This does **not** reimplement any model or backtest logic — it imports `MODELS`, `run_backtest()`, `summarize()`, `write_csv()`, and the chart styling helpers directly from `scripts/forecast_national.py` and calls them once per region. The five benchmark models (`naive`, `drift`, `linear_trend`, `ses`, `holt`) and the no-leakage, expanding-window, `MIN_TRAIN_YEARS=10`, `HORIZONS=[1,2,3,5]` backtest design are therefore identical to the national work — see `docs/national_forecast_methodology.md` §1 for the full rationale, which is not repeated here. Run with:

```
.venv/bin/python3 scripts/forecast_regional.py
```

**Outputs:**
- `outputs/regional_model_results.csv` — MAE / RMSE / MAPE / mean-error bias per region x model x horizon (180 rows: 9 regions x 5 models x 4 horizons).
- `outputs/regional_backtest_predictions.csv` — every individual backtest forecast (4,905 rows: 9 regions x 109 origin/horizon combinations x 5 models).
- `outputs/figures/regional_backtest_mape_heatmap.png` — MAPE by region x model, at the 1-year and 5-year horizons side by side.
- `outputs/figures/regional_model_win_counts.png` — how many of the 9 regions each model has the lowest MAPE in, by horizon.

## 1. QA

`run_qa()` in the script checks: exactly 9 regions loaded, each with a complete 1987-2025 (39-year) series; the backtest produces exactly 4,905 detail rows and 180 summary rows (both computed independently from the origin/horizon grid, matching the assertion style in `forecast_national.py`); and zero leakage violations (`target_year <= origin_year`) across all 4,905 rows. All checks passed. Because `run_backtest()` itself is unmodified and imported from the already-independently-verified national script, the region-level results carry the same no-leakage guarantee without needing to be re-derived.

## 2. Results

### 2.1 Regional series are harder to forecast than the national total

Every region's 1-year naive MAPE (6.2-10.7%) is higher than the national total's (4.71%), and the same holds at every horizon. This is the expected statistical effect of aggregation: summing across regions cancels out some of each region's idiosyncratic year-to-year movement, so the national total is smoother (and more predictable by these benchmarks) than any individual region. East Midlands is the easiest region to forecast at every horizon (naive MAPE 6.39% / 9.66% / 13.54% / 21.70% at 1/2/3/5 years); the North East is hardest at short horizons (10.72% / 15.53% / 18.78% at 1/2/3 years) but the South East overtakes it as hardest by 5 years (29.53% vs. North East's 26.33%).

### 2.2 No single model dominates, and the pattern varies by region — not just by horizon

At the 1-year horizon, naive wins outright in 5 of 9 regions, drift in 2 (North East, South West), and Holt in 2 (North West, South East). This is a more varied picture than the national series, where naive/SES tied for best at every horizon except 1-year (won by Holt). By 5 years, naive wins in all 9 regions — but see §2.4 below before reading that as a strong result.

### 2.3 Holt repeats its national pattern — strong short-horizon, weak long-horizon — more starkly

Holt has the lowest 1-year MAPE in North West (6.71%) and South East (5.80%), consistent with its national 1-year win. But at 5 years, Holt is the *worst* model (of the five) in 7 of the 9 regions, including two of the highest MAPEs recorded anywhere in this work: 47.46% in Yorkshire and The Humber and 45.28% in the North East (only linear-trend's South East 5-year MAPE of 54.03% — the single worst value across the whole regional and national analysis — is higher). This confirms the national Finding 1/6 (`docs/national_forecast_methodology.md`) even more strongly at regional level: Holt's fitted trend, extrapolated over 9 regions individually, overshoots badly whenever a region's own cycle turns.

### 2.4 Caution: most naive-vs-SES "wins" are ties, not real differences

The win-count chart (`outputs/figures/regional_model_win_counts.png`) credits naive with winning in 5, 6, 8 and 9 of the 9 regions at the four horizons respectively — but checking the actual margins: in 27 of the 36 region x horizon combinations, naive's MAPE beats SES's by less than 0.1 percentage points (one combination is a tie to two decimal places, and most of the rest differ by 0.01-0.05 points). This mirrors the national finding (§2, Finding 3 of the national note) that SES's grid-searched alpha sits at the boundary of the search range and behaves almost identically to naive on this kind of series. The chart itself carries this caution as an on-figure footnote. In contrast, drift's and Holt's occasional wins carry real margins (0.08-1.0 percentage points), so those should be read as genuine, not artefacts of the tie-breaking rule (Python's `min()` favours whichever model is listed first among equal values, which happens to be `naive`).

### 2.5 Linear trend remains the weakest model everywhere

Consistent with the national result, `linear_trend` has the highest or near-highest MAPE in every region at every horizon (range: 15.6% in East Midlands at 1-year to 54.0% in the South East at 5-year), for the same reason given in the national note — a straight line cannot track a series with cyclical turning points, and the effect is, if anything, more pronounced in some individual regions than in the smoother national aggregate.

See `outputs/figures/regional_backtest_mape_heatmap.png` for the full region x model MAPE grid at 1- and 5-year horizons, and `outputs/figures/regional_model_win_counts.png` for the win-count summary (with its caution note).

## 3. Limitations

- **All limitations from the national note apply per-region.** Expanding window, `MIN_TRAIN_YEARS=10`, no exogenous drivers, unvalidated extrapolation beyond the backtest, and the small/overlapping-origin caveat for 5-year horizons (`docs/national_forecast_methodology.md` §4) all carry over unchanged, now multiplied across 9 regions.
- **Multiple comparisons.** This analysis runs 9 regions x 4 horizons = 36 "horse races" between 5 models. With that many comparisons, some models will look better than others by chance even with no real underlying difference — this is exactly what §2.4 found for naive vs. SES, and the same caution should be applied lightly to any single region/horizon result that isn't corroborated by a similar pattern in neighbouring horizons or regions.
- **No forward (2026-2030) regional forecast produced in this 5-model pass.** This extension stops at backtesting; a regional forward forecast was added later, alongside the 7-model statistical extension — see `docs/statistical_models_methodology.md` §5, `outputs/regional_forecast_2026_2030_extended.csv`, and `outputs/regional_forecast_selected_2026_2030.csv`.
- **Regions are not independent of the national total.** The nine regions sum to the England total (`docs/initial_eda_findings.md` §3), so regional and national results in this and the companion national note are not independent evidence — they are different views of the same underlying data at different levels of aggregation.
- **No boundary-change complications (unlike local authorities).** The regional file has 0 missing values and stable region definitions across 1987-2025 (confirmed in `docs/initial_feasibility_note.md`), so none of the local-authority reorganisation caveats apply here. Local-authority-level forecasting, if pursued later, would need to address that reconciliation first (documented in `docs/initial_feasibility_note.md` §2) — it was not attempted in this session.
