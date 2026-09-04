#!/usr/bin/env python3
"""Create the five-page public HAILIE forecast briefing as a PDF."""

from __future__ import annotations

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "outputs" / "final"
DATA = ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"
FIGURES = ROOT / "outputs" / "figures"
OUTPUT = ROOT / "outputs" / "pdf" / "HAILIE_social_housing_waiting_list_briefing.pdf"
ENGLAND = "E92000001"

NAVY = colors.HexColor("#102F46")
BLUE = colors.HexColor("#176D8D")
TEAL = colors.HexColor("#16877E")
PALE = colors.HexColor("#E7F4F2")
WASH = colors.HexColor("#F2F6F7")
INK = colors.HexColor("#14242F")
MUTED = colors.HexColor("#526675")
LINE = colors.HexColor("#D4DEE3")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def n(value: str | float) -> str:
    return f"{float(value):,.0f}"


def p(value: float) -> str:
    return f"{value:+.1f}%"


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    history = read_csv(DATA)
    national = read_csv(FINAL / "national_forecast_2026_2028.csv")
    sensitivity = read_csv(FINAL / "national_history_sensitivity.csv")
    regional = read_csv(FINAL / "regional_forecast_2026_2028.csv")
    regional_selections = read_csv(FINAL / "regional_model_selection.csv")
    national_chart = FIGURES / "public_national_forecast.png"
    regional_chart = FIGURES / "public_regional_outlook.png"
    if not national_chart.exists() or not regional_chart.exists():
        raise FileNotFoundError("Run scripts/build_public_charts.py before building the briefing")
    latest = int(next(row["households_on_register"] for row in history if row["Area code"] == ENGLAND and row["year"] == "2025"))
    row_2028 = next(row for row in national if row["forecast_year"] == "2028")
    forecast_2028 = float(row_2028["point_forecast"])
    change = 100 * (forecast_2028 - latest) / latest

    model_order = ["naive", "drift", "linear_trend", "ses", "holt", "damped_trend", "arima"]

    def later_window(start_year: str) -> dict[str, object]:
        records = [row for row in sensitivity if row["history_start_year"] == start_year]
        scores = {
            model: sum(
                float(row["mae_households"])
                for row in records
                if row["model"] == model and row["horizon_years"] in {"1", "2", "3"}
            )
            / 3
            for model in model_order
        }
        ranking = sorted(model_order, key=lambda model: (scores[model], model_order.index(model)))
        labels = {row["model"]: row["model_label"] for row in records}
        return {
            "damped_mae": scores["damped_trend"],
            "damped_rank": ranking.index("damped_trend") + 1,
            "naive_mae": scores["naive"],
            "winner": labels[ranking[0]],
        }

    later_windows = {year: later_window(year) for year in ["1998", "2005"]}

    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=30, leading=32, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8)
    kicker = ParagraphStyle("Kicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=TEAL, spaceAfter=6)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=22, leading=25, textColor=NAVY, spaceBefore=3, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=NAVY, spaceBefore=8, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.3, leading=15, textColor=INK, spaceAfter=8)
    lead = ParagraphStyle("Lead", parent=body, fontSize=14, leading=20, textColor=INK, spaceAfter=14)
    small = ParagraphStyle("Small", parent=body, fontSize=8.3, leading=11.5, textColor=MUTED, spaceAfter=5)
    stat = ParagraphStyle("Stat", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=24, leading=26, textColor=NAVY, alignment=TA_CENTER)
    statlabel = ParagraphStyle("StatLabel", parent=small, alignment=TA_CENTER)

    def P(text: str, style=body) -> Paragraph:
        return Paragraph(text, style)

    def stats(items: list[tuple[str, str]]) -> Table:
        cells = [[P(value, stat) for value, _ in items], [P(label, statlabel) for _, label in items]]
        t = Table(cells, colWidths=[(174 * mm) / len(items)] * len(items), rowHeights=[15 * mm, 12 * mm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WASH), ("BOX", (0, 0), (-1, -1), .5, LINE), ("INNERGRID", (0, 0), (-1, -1), .5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
        return t

    def data_table(rows: list[list[str]], widths: list[float]) -> Table:
        prepared = [[P(str(cell), small if r else ParagraphStyle("TH", parent=small, fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_CENTER)) for cell in row] for r, row in enumerate(rows)]
        t = Table(prepared, colWidths=[w * mm for w in widths], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), .45, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, WASH]), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return t

    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE); canvas.line(18 * mm, 17 * mm, 192 * mm, 17 * mm)
        canvas.setFont("Helvetica-Bold", 8); canvas.setFillColor(NAVY); canvas.drawString(18 * mm, 11 * mm, "HAILIE")
        canvas.setFont("Helvetica", 8); canvas.setFillColor(MUTED); canvas.drawRightString(192 * mm, 11 * mm, f"Social housing waiting-list outlook  |  {doc.page}")
        canvas.restoreState()

    story = []
    story += [P("HAILIE PUBLIC BRIEFING", kicker), P("England's social housing<br/>waiting-list outlook", title), P("What published register data suggests for 2026–2028, with a cautious planning view to 2030.", lead), Spacer(1, 5 * mm)]
    story += [stats([(n(latest), "households on registers in 2025"), (n(forecast_2028), "full-history estimate for 2028"), (p(change), "full-history change, 2025–2028")]), Spacer(1, 8 * mm)]
    story += [P("The central outlook", h1), P("<b>The evidence does not identify a robust national increase or decrease over the next three years.</b> The damped-Holt model selected on the full 1987–2025 history gives a central estimate of <b>1,359,901 households in 2028 (+1.4%)</b>. However, naive performs better in both later-history sensitivity windows, especially 2005–2025.", lead), P("The uncertainty range is wide. For 2028, the empirical 80% range is approximately <b>1.17 million to 1.67 million</b>. Planning and public discussion should therefore focus on the range of plausible outcomes as well as the full-history central estimate."), Spacer(1, 4 * mm), P("Source: Ministry of Housing, Communities and Local Government Live Table 600. Counts are households on local-authority housing registers. The reference date is 1 April up to 2018 and 31 March from 2019 onward. Data retrieved 7 August 2026. Accessible HTML alternative: the repository's analytical report.", small), PageBreak()]

    story += [P("01  HISTORICAL CONTEXT", kicker), P("Waiting lists have moved in long cycles", h1), P("The national series does not follow a simple straight line. It fell through much of the 1990s, rose strongly during the 2000s, peaked in 2012, then declined before increasing again after 2020.", lead), Image(str(national_chart), width=174 * mm, height=79 * mm), Spacer(1, 5 * mm)]
    story += [stats([("1.02m", "1998 series low"), ("1.85m", "2012 series peak"), ("+17.9%", "increase from 2020 to 2025")]), Spacer(1, 5 * mm), P("Why this matters", h2), P("Models that extend a fixed long-run trend can perform poorly when the underlying series has repeated turning points. The final forecast was therefore chosen through rolling historical tests rather than by selecting the model with the most visually compelling trajectory."), PageBreak()]

    latest_by_region = {row["Region"]: int(row["households_on_register"]) for row in history if row["year"] == "2025" and row["Area code"].startswith("E12")}
    forecast_by_region = {row["region"]: row for row in regional if row["forecast_year"] == "2028"}
    model_by_region = {row["region"]: row["primary_model_label"] for row in regional_selections}
    regional_rows = [["Region", "Selected model", "2025", "2028 central", "2028 80% range"]]
    for name in sorted(forecast_by_region, key=lambda region: float(forecast_by_region[region]["point_forecast"]), reverse=True):
        row = forecast_by_region[name]
        regional_rows.append([
            name,
            model_by_region[name],
            n(latest_by_region[name]),
            n(row["point_forecast"]),
            f"{n(row['lower_80'])}–{n(row['upper_80'])}",
        ])
    story += [P("02  REGIONAL OUTLOOK", kicker), P("Regional backtests do not support a strong directional call", h1), P("For six of nine regions, backtesting selected a naive model that carries the 2025 observation forward. The repeated 2028 central estimates are therefore properties of the selected models, not evidence that regional waiting lists will remain unchanged. The chart and table pair each central estimate with its 80% range.", lead), Image(str(regional_chart), width=174 * mm, height=91 * mm), Spacer(1, 4 * mm), data_table(regional_rows, [43, 32, 25, 29, 45]), PageBreak()]

    uncertainty_rows = [["Year", "Central estimate", "80% range"]]
    for row in national:
        uncertainty_rows.append([row["forecast_year"], n(row["point_forecast"]), f"{n(row['lower_80'])}–{n(row['upper_80'])}"])
    story += [P("03  UNCERTAINTY", kicker), P("A forecast is a range, not a promise", h1), P("The central estimate summarises the model's expected path. The public 80% range shows how far historical forecast errors have extended when the same method was tested on unseen years.", lead), data_table(uncertainty_rows, [34, 55, 85]), Spacer(1, 7 * mm)]
    story += [P("What the 80% range shows", h2), P("Uncertainty widens with time. The 2026 estimate is relatively concentrated, while the 2028 range is much broader. Outcomes near either side of the range would not automatically mean the model had failed; they reflect the volatility seen in the historical record."), P("Why a 95% range is not shown", h2), P("Only 27 three-year backtest errors are available. Each 95% tail would therefore depend on roughly one extreme observation, including periods affected by identifiable changes in housing-register policy. Wider 95% figures remain in the technical report as diagnostic historical ranges, not stable probability limits."), P("What the range does not show", h2), P("The range is based on historical model error. It cannot capture every possible policy change, administrative change or future shock. It should support scenario planning, not be read as an exact probability for every future event."), Spacer(1, 4 * mm), P("Communication principle", h2), P("Headlines should pair the central estimate with its uncertainty. Reporting only 1.36 million would give a false impression of precision."), PageBreak()]

    story += [P("04  EVIDENCE AND USE", kicker), P("Built for transparent public use", h1), P("The analysis uses a reproducible pipeline from the published source file to the dashboard, forecast tables and briefing. The final national and regional results can be regenerated from the repository.", lead)]
    evidence = [["Evidence step", "What was done"], ["Source integrity", "The retained Table 600 workbook, extracts and processed series were compared directly."], ["Reconciliation", "The nine regions sum exactly to England in every year from 1987 to 2025."], ["Model testing", "Seven transparent models were evaluated with expanding-window rolling-origin backtesting. The ARIMA search collapses to the naive random walk and SES converges to an alpha of about 1 on this series, so those rows are effectively equivalent baselines."], ["Selection", "Mean absolute error was the primary measure because it is interpretable in households. Differences are descriptive; overlapping origins do not support formal claims of significance."], ["Uncertainty", "Public 80% ranges were derived from out-of-sample historical errors; wider 95% diagnostics remain in the technical report."]]
    sensitivity_rows = [["History window", "Damped-Holt mean MAE", "Rank", "Naive mean MAE", "Winner"]]
    for start_year in ["1998", "2005"]:
        result = later_windows[start_year]
        sensitivity_rows.append([
            f"{start_year}–2025",
            n(result["damped_mae"]),
            f'{result["damped_rank"]} of {len(model_order)}',
            n(result["naive_mae"]),
            str(result["winner"]),
        ])
    story += [data_table(evidence, [48, 126]), Spacer(1, 5 * mm), P("Later-history sensitivity", h2), P("Naive has lower mean Y1–Y3 MAE than the selected damped-Holt model in both later windows. This weakens the directional conclusion without changing the preserved full-history estimate.", small), data_table(sensitivity_rows, [34, 44, 24, 42, 30]), Spacer(1, 5 * mm), P("How the findings can be used", h2), P("The dashboard supports national and regional comparison, planning conversations and accessible communication of uncertainty. The forecast provides an evidence baseline against which new data and policy developments can be assessed."), P("Measure and interpretation", h2), P("Table 600 counts households on local-authority housing registers. Separate housing-association lists are not included; applicants can appear on more than one authority register, and the publisher says periodic reviews and duplicate listings mean the total is likely to overstate households still requiring social housing at any one time. These registers are therefore not a complete measure of housing need. Source-noted breaks include Telford & Wrekin leaving the register series from 31 March 2021 and Epping Forest changing transfer-applicant treatment from 2022–23; no re-modelling has been applied."), P("Accessible alternative: the repository's HTML analytical report provides the structured, screen-reader-friendly version of this briefing.", small)]

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=23 * mm, title="HAILIE social housing waiting-list outlook", author="HAILIE", subject="England and regional waiting-list forecasts", lang="en-GB", displayDocTitle=True)
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
