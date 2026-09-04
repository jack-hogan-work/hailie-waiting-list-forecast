# Final report design and review record

## Purpose

The final report answers one primary question:

> What is the likely direction of social housing waiting lists in England and its
> regions over the next three to five years, and how uncertain is that outlook?

The report is designed for three related scenarios:

1. A HAILIE decision-maker needs the national direction and areas of possible regional pressure.
2. A regional stakeholder needs the forecast and uncertainty for one region.
3. A supervisor or technical reviewer needs to trace every conclusion to its data, model-selection evidence and limitations.

## Design decisions

- The executive answer, forecast and uncertainty appear first.
- Regional comparison and an accessible region selector follow the national result.
- Dense backtest evidence, decision records and reproducibility instructions remain in the same report but below the main answer.
- Archived exploratory results are not presented as final evidence.
- Tables include captions and labelled headers; meaning is not communicated by colour alone.
- The layout supports keyboard use, visible focus, narrow screens, 200% zoom and printing.

## Advice incorporated

Tom Stephenson advised beginning with one real user need, keeping the first
version focused, using concrete user scenarios, checking accessibility,
recording decisions and testing an early complete version. Those principles
shaped the report structure above.

External testing by Tom or Myles is not represented as completed. Any feedback
received after sharing the finished report should be added below with the date,
finding, decision and resulting change.

## Review log

| Date | Reviewer | Finding | Decision/change |
|---|---|---|---|
| 4 September 2026 | Internal final QA | Stale report consumed archived MAPE-selected forecasts | Replaced it with a report generated only from final MAE-selected outputs |
| 4 September 2026 | Internal final QA | Region-level forecast details were difficult to inspect | Added a labelled keyboard-operable region selector and full interval tables |
| 4 September 2026 | Internal final QA | Supervisor concerns were dispersed across notes | Added one concern-to-evidence closure matrix to the final report |
| 4 September 2026 | Internal final QA | Sensitivity to historical coverage had been planned but not tested | Added 1998- and 2005-start rolling-origin comparisons and reported the changing near-term winner |
| 4 September 2026 | Scope check against the original brief and weekly update | A graphic and report headings said "housing" without the intended "social housing" scope | Corrected visible titles and retained the precise caveat that Table 600 measures local-authority registers rather than every social housing waiting list |
