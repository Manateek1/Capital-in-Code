"""Build the public CIC-001 results PDF from the verified research report."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "site" / "public" / "reports" / "cic-001-the-overnight-effect.pdf"
IMAGE_DIR = REPO_ROOT / "site" / "public" / "images" / "cic-001"

INK = colors.HexColor("#101114")
NAVY = colors.HexColor("#123675")
MUTED = colors.HexColor("#595D64")
RULE = colors.HexColor("#A8ABB1")
PALE_NAVY = colors.HexColor("#EAF0F8")
PALE_GRAY = colors.HexColor("#F3F4F5")


def p(text: str, style: ParagraphStyle) -> Paragraph:
    """Make a ReportLab paragraph with the project's publication typography."""
    return Paragraph(text, style)


def on_page(canvas, document) -> None:
    """Draw consistent report furniture without distracting from the findings."""
    canvas.saveState()
    width, height = letter
    if document.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.45)
        canvas.line(document.leftMargin, height - 0.45 * inch, width - document.rightMargin, height - 0.45 * inch)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(document.leftMargin, height - 0.32 * inch, "CAPITAL IN CODE  /  CIC-001")
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        label = f"DILLON NAGAR  /  {document.page}"
        canvas.drawRightString(width - document.rightMargin, height - 0.32 * inch, label)
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.45)
    canvas.line(document.leftMargin, 0.48 * inch, width - document.rightMargin, 0.48 * inch)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    footer = "Educational research only. Not investment, tax, or legal advice."
    canvas.drawString(document.leftMargin, 0.32 * inch, footer)
    canvas.drawRightString(width - document.rightMargin, 0.32 * inch, "capitalincode.vercel.app")
    canvas.restoreState()


def styled_table(rows, widths, header=True, font_size=8.4) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 3),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ]
        )
    table.setStyle(TableStyle(commands))
    return table


def report() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Times-Bold", fontSize=33,
        leading=35, textColor=INK, alignment=TA_LEFT, spaceAfter=16,
    )
    subtitle = ParagraphStyle(
        "Subtitle", parent=styles["BodyText"], fontName="Helvetica", fontSize=12,
        leading=18, textColor=MUTED, spaceAfter=18,
    )
    kicker = ParagraphStyle(
        "Kicker", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.5,
        leading=11, textColor=NAVY, spaceAfter=12, tracking=1.1,
    )
    heading = ParagraphStyle(
        "Heading", parent=styles["Heading2"], fontName="Times-Bold", fontSize=19,
        leading=22, textColor=INK, spaceBefore=6, spaceAfter=10,
    )
    subheading = ParagraphStyle(
        "Subheading", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10,
        leading=13, textColor=NAVY, spaceBefore=6, spaceAfter=5,
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5,
        leading=14.3, textColor=INK, spaceAfter=8,
    )
    small = ParagraphStyle(
        "Small", parent=body, fontSize=8.2, leading=11.6, textColor=MUTED, spaceAfter=5,
    )
    callout = ParagraphStyle(
        "Callout", parent=body, fontName="Helvetica-Bold", fontSize=11.5,
        leading=16, textColor=INK, alignment=TA_CENTER, spaceAfter=0,
    )

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH), pagesize=letter, leftMargin=0.72 * inch, rightMargin=0.72 * inch,
        topMargin=0.74 * inch, bottomMargin=0.72 * inch,
        title="CIC-001 - The Overnight Effect in SPY",
        author="Dillon Nagar",
        subject="Capital in Code research report",
    )
    story = []

    # Cover
    story.extend([
        Spacer(1, 0.62 * inch),
        p("CAPITAL IN CODE  /  CIC-001", kicker),
        p("The Overnight<br/>Effect in SPY", title),
        p("A reproducible historical return decomposition of the close-to-next-open and open-to-close intervals.", subtitle),
        HRFlowable(width="100%", thickness=1.2, color=NAVY, spaceBefore=4, spaceAfter=22),
        p("RESEARCH QUESTION", kicker),
        p("From January 1994 through December 2025, did SPY historically earn more of its adjusted close-to-close return overnight than during regular market hours?", ParagraphStyle("Question", parent=body, fontName="Times-Italic", fontSize=15, leading=21, textColor=INK, spaceAfter=22)),
        p("ABSTRACT", kicker),
        p("Using adjusted daily OHLC data for SPY, this study separates the previous trading close-to-next-open return from the open-to-close return. Across 8,053 aligned observations, the overnight component annualized at 9.86% and regular-hours component annualized at 0.79%. The average paired difference was 3.18 basis points per trading day. Paired tests and a bootstrap provided historical evidence of a positive difference under the study assumptions.", body),
        p("The pattern is not a trading recommendation. It varied across time, was sharply negative during the defined COVID shock window, and was substantially weakened by a simplified daily transaction-cost model. The results describe historical association in one adjusted-price sample - not causality, prediction, or executable profit.", body),
        Spacer(1, 0.12 * inch),
        Table([[p("<b>8,053</b><br/><font size=8>aligned return observations</font>", callout), p("<b>1994-01-04</b><br/><font size=8>through 2025-12-31</font>", callout), p("<b>SPY</b><br/><font size=8>adjusted daily OHLC</font>", callout)]], colWidths=[2.02 * inch] * 3, style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PALE_NAVY), ("BOX", (0, 0), (-1, -1), 0.55, NAVY),
            ("INNERGRID", (0, 0), (-1, -1), 0.55, NAVY), ("TOPPADDING", (0, 0), (-1, -1), 13),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
        ])),
        Spacer(1, 0.32 * inch),
        p("Prepared by Dillon Nagar  |  Verified fixed-sample results", small),
        PageBreak(),
    ])

    # Design and primary evidence
    story.extend([
        p("01  /  DESIGN AND FINDINGS", kicker),
        p("A focused question, paired evidence, and explicit limits.", heading),
        p("The study uses Yahoo Finance daily SPY Open and Close data through yfinance with <i>auto_adjust=True</i>. The data convention applies a consistent split- and dividend-adjustment factor to both fields; raw and adjusted values are never mixed. The verified run contained 8,054 clean price rows and 8,053 aligned return rows, with no invalid prices, duplicate dates, or removals beyond the first unaligned observation.", body),
        p("For each observed trading day t, overnight return equals current Open divided by the previous observed Close minus 1. Regular-hours return equals current Close divided by current Open minus 1. The pipeline verifies that the components reconstruct the adjusted close-to-close return on every row.", body),
        Spacer(1, 3),
        p("FULL-SAMPLE RETURN DECOMPOSITION", subheading),
        styled_table([
            ["Metric", "Overnight", "Regular hours", "Buy and hold"],
            ["Arithmetic mean per day", "0.03962%", "0.00785%", "0.04748%"],
            ["Cumulative return", "1,917.13%", "28.63%", "2,494.64%"],
            ["Annualized return", "9.86%", "0.79%", "10.73%"],
            ["Annualized volatility", "10.75%", "15.43%", "18.84%"],
            ["Sharpe ratio", "0.929", "0.128", "0.635"],
            ["Maximum drawdown", "-32.79%", "-68.49%", "-55.19%"],
        ], [2.22 * inch, 1.28 * inch, 1.43 * inch, 1.35 * inch]),
        Spacer(1, 0.18 * inch),
        p("The full-sample decomposition favors the overnight component on compounded and annualized return, volatility, Sharpe ratio, and maximum drawdown. Those descriptive comparisons do not on their own show a causal mechanism or a realistically tradable strategy.", small),
        Spacer(1, 0.12 * inch),
        Image(str(IMAGE_DIR / "growth-of-one-dollar.png"), width=6.0 * inch, height=3.58 * inch, hAlign="CENTER"),
        p("Figure 1. Compounded adjusted growth of $1 by component. The logarithmic axis preserves proportional changes.", small),
        PageBreak(),
    ])

    # Statistics and robustness
    story.extend([
        p("02  /  INFERENCE AND ROBUSTNESS", kicker),
        p("Statistical evidence is not the same as economic feasibility.", heading),
        p("The primary comparison uses matched overnight and regular-hours returns from the same trading dates. A paired design reflects that the two components are parts of the same day. The paired t-test evaluates the mean difference; the Wilcoxon signed-rank test is a nonparametric paired check; and a paired bootstrap resamples same-date pairs 10,000 times with a fixed seed.", body),
        styled_table([
            ["Measure", "Verified result", "Interpretation"],
            ["Mean paired difference", "3.18 bps/day", "Overnight minus regular hours"],
            ["Paired t-test", "p = 0.0160", "Evidence under its null model"],
            ["Wilcoxon signed-rank", "p = 0.000163", "Nonparametric paired check"],
            ["Paired bootstrap", "0.55 to 5.74 bps/day", "95% interval for mean difference"],
        ], [1.75 * inch, 1.55 * inch, 2.98 * inch], font_size=8.1),
        Spacer(1, 0.16 * inch),
        Table([[p("Statistical significance concerns compatibility with a test's null model. Economic significance additionally requires attention to magnitude, risk, costs, capacity, and investability.", callout)]], colWidths=[6.28 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PALE_GRAY), ("BOX", (0, 0), (-1, -1), 0.5, RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 14), ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING", (0, 0), (-1, -1), 18), ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ])),
        Spacer(1, 0.2 * inch),
        p("ROBUSTNESS SNAPSHOT", subheading),
        styled_table([
            ["Sensitivity check", "Overnight", "Regular hours", "What it shows"],
            ["Later start: 2000", "6.96%", "1.01%", "Ordering remains, gap is smaller"],
            ["Later start: 2010", "8.62%", "4.89%", "Period dependence is material"],
            ["Later start: 2020", "8.71%", "5.66%", "Recent gap remains narrower"],
            ["COVID shock", "-28.12%", "-7.34%", "Overnight exposure was especially damaging"],
        ], [1.7 * inch, 1.1 * inch, 1.25 * inch, 2.23 * inch], font_size=7.85),
        Spacer(1, 0.13 * inch),
        p("A paired tail trim retained 7,769 dates after removing 284 dates outside the components' respective 1st and 99th percentiles. The retained sample still favored overnight (3,746.17% compounded versus 11.76%), but this is a sensitivity check - not a claim that an investor could avoid adverse tails.", body),
        Image(str(IMAGE_DIR / "drawdown-comparison.png"), width=6.0 * inch, height=3.58 * inch, hAlign="CENTER"),
        p("Figure 2. Drawdown from each component's prior peak. Component wealth paths are not simulated executable strategies.", small),
        PageBreak(),
    ])

    # Costs, limitations and methods
    limitation_label = ParagraphStyle("LimitationLabel", parent=small, fontName="Helvetica-Bold", textColor=INK, spaceAfter=0)
    limitation_text = ParagraphStyle("LimitationText", parent=small, textColor=INK, spaceAfter=0)
    limitation_rows = [
        [p("Data", limitation_label), p("Yahoo Finance may revise adjusted history; yfinance is an unofficial interface to that provider.", limitation_text)],
        [p("Pricing", limitation_label), p("Adjusted daily Open and Close are historical accounting inputs, not evidence of executable prices at a chosen size or time.", limitation_text)],
        [p("Statistics", limitation_label), p("Daily differences can have serial dependence, fat tails, and changing volatility not fully modeled by these procedures.", limitation_text)],
        [p("Scope", limitation_label), p("One U.S. ETF and one fixed sample do not establish cross-asset stability, causality, or future performance.", limitation_text)],
    ]
    limitations = Table(limitation_rows, colWidths=[1.02 * inch, 5.26 * inch], hAlign="LEFT")
    limitations.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (0, -1), PALE_NAVY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.4), ("LEADING", (0, 0), (-1, -1), 11.8),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE), ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([
        p("03  /  PRACTICAL INTERPRETATION", kicker),
        p("The evidence describes a pattern. It does not prove a strategy.", heading),
        p("The transaction-cost exercise applies a deliberately simple 1-basis-point cost on entry and 1 basis point on exit for every observed trading day. It assumes fills at price multiplied by (1 + cost) on entry and price multiplied by (1 - cost) on exit. This mechanical sensitivity is useful for scale, but it is not an execution simulation.", body),
        styled_table([
            ["Component", "Gross annualized", "Net annualized", "Net cumulative"],
            ["Overnight", "9.86%", "4.46%", "302.96%"],
            ["Regular hours", "0.79%", "-4.16%", "-74.30%"],
        ], [1.7 * inch, 1.55 * inch, 1.55 * inch, 1.48 * inch]),
        Spacer(1, 0.16 * inch),
        p("Even under this simplified model, the overnight series remains positive, but it underperformed the 10.73% annualized historical close-to-close buy-and-hold result. The model omits changing spreads, slippage, market impact, partial or failed executions, financing, account constraints, capacity, and taxes.", body),
        p("LIMITATIONS", subheading),
        limitations,
        Spacer(1, 0.2 * inch),
        p("REPRODUCIBILITY", subheading),
        p("The full source code, methods, tests, and generated result artifacts are available in the public Capital in Code repository. The documented configuration can be reproduced from the CIC-001 project directory with <font name='Courier'>python -m src.main --ticker SPY --start-date 1994-01-01 --end-date 2025-12-31</font>. The fixed bootstrap seed is 42 with 10,000 resamples. A future refresh may differ if Yahoo Finance revises historical data or adjustment logic.", body),
        p("Conclusion: within this adjusted SPY sample, more historical close-to-close growth was associated with the close-to-next-open interval than with regular trading hours. That finding is historical evidence about a return decomposition, not a causal explanation, forecast, or investment recommendation.", ParagraphStyle("Conclusion", parent=body, fontName="Times-Bold", fontSize=12.2, leading=17, textColor=INK, spaceBefore=3, spaceAfter=12)),
        HRFlowable(width="100%", thickness=0.7, color=RULE, spaceBefore=3, spaceAfter=10),
        p("Sources: Yahoo Finance daily SPY OHLC data retrieved via yfinance; CIC-001 generated result artifacts; CIC-001 research pipeline. Full formal report and source materials: github.com/Manateek1/Capital-in-Code", small),
    ])

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    report()
