# HAILIE Project Plan — Plain English

> **Historical planning record.** This document records the route agreed before
> the final rebuild. The national and regional modelling, final outputs and
> report are now complete. Current status and reproduction instructions are in
> the root `README.md`; final decisions are in
> `docs/final_forecast_methodology.md`.

## Where the project is now

We already have working code, cleaned files, charts and exploratory forecasts. We are not throwing that work away. We are pausing the forecast claims while we prove that the source data, definitions and geography are suitable for the supervisor's question.

The first audit now shows that the repository copies Table 600 correctly. It also found an important qualification: MHCLG has already made 45 documented replacements inside the published workbook. The next job is therefore about meaning and comparability, not just whether the code runs.

## The full route

### 1. Prove the source chain

Keep the original government workbook unchanged. Check that the exported sheets match it, and that every processed value can be traced back to a source cell. This first pass is complete and reproducible.

### 2. Decide what each awkward value means

Write down the rules for `[x]`, `[z]`, reported zeroes and the publisher's own imputations. Review special notes such as Telford and Wrekin and Epping Forest. Do not silently fill gaps.

### 3. Make geography honest

The file contains historic councils as well as current ones. If the project needs council-level comparisons, build and test a clear method for combining predecessor districts and successor unitaries. If the project only needs national or regional results, avoid creating an unnecessary local-authority series.

### 4. Check against an independent presentation

Compare selected Table 600 results with LG Inform. London now matches for all six periods shown there. If local-authority analysis continues, sample several councils, including reorganised and special-case areas.

### 5. Decide whether extra datasets help

Table 602 describes the flow of council-owned homes let, not the number of households on registers. It may help explain pressure or turnover at England level, but it is not a replacement for Table 600. The Indices of Deprivation 2025 may help describe why places differ once current geography is stable. Neither should be added merely because it is available.

### 6. Agree the actual question and output

Confirm whether the supervisor needs a national outlook, regional planning ranges, council segmentation, or an explanation of historic change. Choose one primary outcome and audience. Freeze a documented analysis dataset for that purpose.

### 7. Re-test whether forecasting is defensible

Start with simple baselines and rolling backtests. Test whether results survive reasonable choices about history length, policy breaks, source imputations and geography. Report ranges and failure modes, not a single confident number. If the data cannot support a useful forecast, say so and provide descriptive/scenario analysis instead.

### 8. Package the result

Produce a short methods note, a data-quality record, the final charts/tables and a clear summary of what the result can and cannot be used for. Keep the code and source files reproducible.

## Best use of today's 2–3 hours

1. **Completed:** reproduce and document the Table 600 source audit.
2. **Completed:** scope Table 602, pass the London LG Inform check, and decide how to treat IoD 2025.
3. **Completed locally:** reset the README and methods documentation so forecasts are explicitly exploratory.
4. **Next:** confirm the exact output the supervisor wants and start the current-geography decision log.
5. **Then:** update the shared status document and send the evidence-based progress note.
