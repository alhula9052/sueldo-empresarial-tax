"""Build the user manual PDF from its Markdown source; no case data is included."""

from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
GREEN = colors.HexColor("#17695e")
INK = colors.HexColor("#193c3b")
MUTED = colors.HexColor("#687e75")


def build_manual(source, target):
    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    regular, bold = "Helvetica", "Helvetica-Bold"
    if font.exists():
        regular, bold = "ManualSans", "ManualSans-Bold"
        pdfmetrics.registerFont(TTFont(regular, str(font)))
        pdfmetrics.registerFont(
            TTFont(bold, str(font.with_name("DejaVuSans-Bold.ttf")))
        )
        pdfmetrics.registerFontFamily(regular, normal=regular, bold=bold)
    styles = {
        "body": ParagraphStyle(
            "Body",
            fontName=regular,
            fontSize=9,
            leading=14,
            textColor=INK,
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName=bold,
            fontSize=17,
            leading=23,
            textColor=GREEN,
            spaceBefore=18,
            spaceAfter=12,
            keepWithNext=True,
        ),
        "subsection": ParagraphStyle(
            "Subsection",
            fontName=bold,
            fontSize=11,
            leading=16,
            textColor=INK,
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "cell": ParagraphStyle(
            "Cell",
            fontName=regular,
            fontSize=8,
            leading=12,
            textColor=INK,
            wordWrap="CJK",
        ),
        "list": ParagraphStyle(
            "List",
            fontName=regular,
            fontSize=9,
            leading=14,
            textColor=INK,
            leftIndent=14,
            firstLineIndent=-12,
            spaceAfter=7,
        ),
        "title": ParagraphStyle(
            "ManualTitle",
            fontName=bold,
            fontSize=32,
            leading=40,
            textColor=INK,
            spaceAfter=20,
        ),
        "brand": ParagraphStyle(
            "Brand",
            fontName=bold,
            fontSize=16,
            leading=22,
            textColor=GREEN,
            spaceAfter=18,
        ),
        "small": ParagraphStyle(
            "Small",
            fontName=regular,
            fontSize=8,
            leading=12,
            textColor=MUTED,
            spaceAfter=12,
        ),
    }

    def inline(raw):
        safe = escape(raw)
        safe = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            lambda m: '<link href="'
            + (
                "https://github.com/alhula9052/sueldo-empresarial-tax/blob/main/docs/"
                + m[2]
                if not m[2].startswith("https://")
                else m[2]
            )
            + '" color="#17695e">'
            + m[1]
            + "</link>",
            safe,
        )
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
        return re.sub(r"`([^`]+)`", r"\1", safe)

    def para(raw, kind="body"):
        return Paragraph(inline(raw), styles[kind])

    class ManualDocument(BaseDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph) and flowable.style.name in (
                "Section",
                "Subsection",
            ):
                level = 0 if flowable.style.name == "Section" else 1
                key = "section-" + str(self.seq.nextf("section"))
                text = flowable.getPlainText()
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=True)
                if level == 0:
                    self.notify("TOCEntry", (level, text, self.page, key))

    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(48, A4[1] - 28, "NEXO / MANUAL DE USUARIO")
        canvas.setStrokeColor(colors.HexColor("#dbe5dc"))
        canvas.line(48, 40, A4[0] - 48, 40)
        canvas.drawString(48, 27, "Versión 1.0 · 2 de noviembre de 2026")
        canvas.drawRightString(A4[0] - 48, 27, f"Página {doc.page}")
        canvas.restoreState()

    target.parent.mkdir(parents=True, exist_ok=True)
    doc = ManualDocument(
        str(target),
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=50,
        bottomMargin=55,
        title="Nexo · Manual de usuario",
        author="Nexo",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(
        PageTemplate(id="Manual", frames=[frame], onPage=header_footer)
    )
    story = [
        Spacer(1, 85),
        para("Nexo", "brand"),
        para("Manual de usuario", "title"),
        para(
            "Del antecedente al informe: un flujo auditable para la asesoría laboral, tributaria y previsional en Chile."
        ),
        Spacer(1, 25),
        para("Guía de uso · Versión 1.0 · 2 de noviembre de 2026", "small"),
        para(
            "La instalación nueva no incorpora normativa ni tasas oficiales verificadas. Las conclusiones y cálculos que requieren validación pendiente permanecen bloqueados. La guía describe las funciones implementadas, sin presentar sus resultados como un dictamen oficial."
        ),
        PageBreak(),
        para("Contenido", "title"),
    ]
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOC0", fontName=bold, fontSize=9, leading=15, textColor=INK, spaceBefore=7
        ),
        ParagraphStyle(
            "TOC1",
            fontName=regular,
            fontSize=8,
            leading=12,
            leftIndent=14,
            textColor=MUTED,
        ),
    ]
    story.extend([toc, PageBreak()])
    lines = source.read_text().splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith("# "):
            index += 1
            continue
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                row = [v.strip() for v in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", v) for v in row):
                    rows.append(row)
                index += 1
            widths = (
                [doc.width * 0.28, doc.width * 0.72]
                if len(rows[0]) == 2
                else [doc.width * 0.22, doc.width * 0.43, doc.width * 0.35]
            )
            table = Table(
                [[para(v, "cell") for v in row] for row in rows],
                colWidths=widths,
                repeatRows=1,
                splitByRow=1,
                splitInRow=1,
                hAlign="LEFT",
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0eee5")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        (
                            "LINEBELOW",
                            (0, 0),
                            (-1, -1),
                            0.3,
                            colors.HexColor("#dbe5dc"),
                        ),
                    ]
                )
            )
            story.extend([table, Spacer(1, 10)])
            continue
        if line.startswith("### "):
            story.append(para(line[4:], "subsection"))
        elif line.startswith("## "):
            story.append(para(line[3:], "section"))
        elif re.match(r"^(\d+\.\s|-\s)", line):
            story.append(para(line, "list"))
        else:
            paragraph = [line]
            while (
                index + 1 < len(lines)
                and lines[index + 1].strip()
                and not re.match(r"^(#|\||\d+\.\s|-\s)", lines[index + 1].strip())
            ):
                index += 1
                paragraph.append(lines[index].strip())
            story.append(para(" ".join(paragraph)))
        index += 1
    doc.multiBuild(story)
    return target


if __name__ == "__main__":
    print(
        build_manual(ROOT / "docs/manual-usuario.md", ROOT / "docs/manual-usuario.pdf")
    )
