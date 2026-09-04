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
    regional = read_csv(FINAL / "regional_forecast_2026_2028.csv")
    national_chart = FIGURES / "public_national_forecast.png"
    regional_chart = FIGURES / "public_regional_outlook.png"
    if not national_chart.exists() or not regional_chart.exists():
        raise FileNotFoundError("Run scripts/build_public_charts.py before building the briefing")
    latest = 1_340_527
    row_2028 = next(row for row in national if row["forecast_year"] == "2028")
    forecast_2028 = float(row_2028["point_forecast"])
    change = 100 * (forecast_2028 - latest) / latest

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
    story += [stats([(n(latest), "households on registers in 2025"), (n(forecast_2028), "central forecast for 2028"), (p(change), "forecast change, 2025–2028")]), Spacer(1, 8 * mm)]
    story += [P("The central outlook", h1), P("England's published social housing register count reached <b>1.34 million households in 2025</b>. The selected model points to a modest increase to about <b>1.36 million in 2028</b>. This is a broadly stable central path rather than evidence of a decisive rise or fall.", lead), P("The uncertainty range is wide. For 2028, the empirical 80% range is approximately <b>1.17 million to 1.67 million</b>. Planning and public discussion should therefore focus on the range of plausible outcomes as well as the central estimate."), Spacer(1, 4 * mm), P("Source: Ministry of Housing, Communities and Local Government Live Table 600. Counts are households on local-authority housing registers at 1 April each year.", small), PageBreak()]

    story += [P("01  HISTORICAL CONTEXT", kicker), P("Waiting lists have moved in long cycles", h1), P("The national series does not follow a simple straight line. It fell through much of the 1990s, rose strongly during the 2000s, peaked in 2012, then declined before increasing again after 2020.", lead), Image(str(national_chart), width=174 * mm, height=79 * mm), Spacer(1, 5 * mm)]
    story += [stats([("1.02m", "1998 series low"), ("1.85m", "2012 series peak"), ("+17.9%", "increase from 2020 to 2025")]), Spacer(1, 5 * mm), P("Why this matters", h2), P("Models that extend a fixed long-run trend can perform poorly when the underlying series has repeated turning points. The final forecast was therefore chosen through rolling historical tests rather than by selecting the model with the most visually compelling trajectory."), PageBreak()]

    latest_by_region = {row["Region"]: int(row["households_on_register"]) for row in history if row["year"] == "2025" and row["Area code"].startswith("E12")}
    forecast_by_region = {row["region"]: float(row["point_forecast"]) for row in regional if row["forecast_year"] == "2028"}
    regional_rows = [["Region", "2025", "2028 forecast", "Change"]]
    for name in sorted(forecast_by_region, key=forecast_by_region.get, reverse=True):
        old, new = latest_by_region[name], forecast_by_region[name]
        regional_rows.append([name, n(old), n(new), p(100 * (new - old) / old)])
    story += [P("02  REGIONAL OUTLOOK", kicker), P("A varied picture across England", h1), P("London remains the largest regional register count in the central forecast. Most regions are broadly stable over the three-year horizon, while the South West shows the clearest modelled increase.", lead), Image(str(regional_chart), width=174 * mm, height=91 * mm), Spacer(1, 4 * mm), data_table(regional_rows, [64, 35, 43, 32]), PageBreak()]

    uncertainty_rows = [["Year", "Central estimate", "80% range", "95% range"]]
    for row in national:
        uncertainty_rows.append([row["forecast_year"], n(row["point_forecast"]), f"{n(row['lower_80'])}–{n(row['upper_80'])}", f"{n(row['lower_95'])}–{n(row['upper_95'])}"])
    story += [P("03  UNCERTAINTY", kicker), P("A forecast is a range, not a promise", h1), P("The central estimate summarises the model's expected path. The ranges show how far historical forecast errors have extended when the same method was tested on unseen years.", lead), data_table(uncertainty_rows, [28, 42, 52, 52]), Spacer(1, 8 * mm)]
    story += [P("What the ranges show", h2), P("Uncertainty widens with time. The 2026 estimate is relatively concentrated, while the 2028 range is much broader. Outcomes near either side of the range would not automatically mean the model had failed; they reflect the volatility seen in the historical record."), P("What they do not show", h2), P("The ranges are based on historical model error. They cannot capture every possible policy change, administrative change or future shock. They should support scenario planning, not be read as exact probabilities for every future event."), Spacer(1, 5 * mm), P("Communication principle", h2), P("Headlines should pair the central estimate with its uncertainty. Reporting only 1.36 million would give a false impression of precision."), PageBreak()]

    story += [P("04  EVIDENCE AND USE", kicker), P("Built for transparent public use", h1), P("The analysis uses a reproducible pipeline from the published source file to the dashboard, forecast tables and briefing. The final national and regional results can be regenerated from the repository.", lead)]
    evidence = [["Evidence step", "What was done"], ["Source integrity", "The retained Table 600 workbook, extracts and processed series were compared directly."], ["Reconciliation", "The nine regions sum exactly to England in every year from 1987 to 2025."], ["Model testing", "Seven transparent models were evaluated with expanding-window rolling-origin backtesting."], ["Selection", "Mean absolute error was the primary measure because it is interpretable in households."], ["Uncertainty", "80% and 95% empirical ranges were derived from out-of-sample historical errors."]]
    story += [data_table(evidence, [48, 126]), Spacer(1, 7 * mm), P("How the findings can be used", h2), P("The dashboard supports national and regional comparison, planning conversations and accessible communication of uncertainty. The forecast provides an evidence baseline against which new data and policy developments can be assessed."), P("Measure and interpretation", h2), P("Table 600 counts households on local-authority housing registers. These registers are an important administrative measure of social housing waiting-list demand, but they are not a complete measure of housing need. Changes may reflect register management as well as changes in underlying demand."), Spacer(1, 5 * mm), P("Explore the interactive dashboard and full analytical report in the HAILIE waiting-list forecast repository.", body), P("Data source: MHCLG Live Table 600, retrieved 7 August 2026. Analysis covers 1987–2025; forecasts begin in 2026.", small)]

    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=23 * mm, title="HAILIE social housing waiting-list outlook", author="HAILIE", subject="England and regional waiting-list forecasts")
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
