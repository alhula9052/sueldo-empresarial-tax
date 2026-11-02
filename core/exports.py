import io
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape
from django.conf import settings
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table as PDFTable,
    TableStyle,
    PageBreak,
    Image,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .importing import COLUMNS

SCOPE = {"labor": "Laboral", "tax": "Tributario", "pension": "Previsional"}
LABELS = {
    "effective_work": "Trabajo efectivo",
    "instructions": "Instrucciones obligatorias",
    "supervision": "Control y evaluación",
    "discipline": "Poder disciplinario",
    "leave": "Autorización de permisos",
    "availability": "Disponibilidad",
    "autonomy": "Autonomía real",
    "contribution_work": "Trabajo como aporte",
    "direct_majority": "Mayoría directa de capital",
    "general_admin": "Administración general",
    "legal_rep": "Representación legal",
    "joint_admin": "Administración conjunta",
    "contradictions": "Contradicciones declaradas",
    "tax_support": "Respaldo tributario registrado",
    "reasonableness": "Razonabilidad documentada",
}
TRI = {"yes": "Sí", "no": "No", "unknown": "No determinado"}


def text(value):
    if value is None:
        return "Pendiente"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def pdf_report(evaluations, complete=True):
    out = io.BytesIO()
    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    family = "Helvetica"
    if font.exists():
        pdfmetrics.registerFont(TTFont("DejaVu", str(font)))
        pdfmetrics.registerFont(
            TTFont("DejaVu-Bold", str(font.with_name("DejaVuSans-Bold.ttf")))
        )
        family = "DejaVu"
    styles = getSampleStyleSheet()
    for key in ("Normal", "BodyText", "Title", "Heading1", "Heading2", "Heading3"):
        styles[key].fontName = family
        styles[key].textColor = colors.HexColor("#173335")
    styles["Normal"].fontSize = 9
    styles["Normal"].leading = 14
    styles["Title"].fontSize = 27
    styles["Title"].leading = 34
    styles["Heading1"].fontSize = 17
    styles["Heading1"].leading = 23
    styles["Heading1"].spaceBefore = 14
    styles["Heading2"].fontSize = 12
    styles["Heading2"].leading = 18
    styles["Heading2"].spaceBefore = 12
    styles.add(
        ParagraphStyle(
            name="SmallSafe", fontName=family, fontSize=7, leading=10, wordWrap="CJK"
        )
    )
    styles.add(
        ParagraphStyle(
            name="Cell", fontName=family, fontSize=8, leading=12, wordWrap="CJK"
        )
    )
    story = []

    def p(value, style="Normal"):
        return Paragraph(escape(text(value)).replace("\n", "<br/>"), styles[style])

    def add(value, style="Normal"):
        paragraph = p(value, style)
        spacer = Spacer(1, 5)
        if style.startswith("Heading") or style == "Title":
            paragraph.keepWithNext = True
            spacer.keepWithNext = True
        story.extend([paragraph, spacer])

    def table(headers, rows, widths):
        data = [[p(h, "Cell") for h in headers]] + [
            [p(v, "Cell") for v in row] for row in rows
        ]
        tbl = PDFTable(
            data,
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
            splitByRow=1,
            splitInRow=1,
        )
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcece7")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cadbd6")),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 10))

    for index, ev in enumerate(evaluations):
        if index:
            story.append(PageBreak())
        s = ev.snapshot
        b = s["branding"]
        logo = b.get("logo_path")
        if logo:
            target = (settings.MEDIA_ROOT / logo).resolve()
            if target.is_relative_to(settings.MEDIA_ROOT.resolve()) and target.exists():
                image = Image(str(target), width=100, height=45, kind="proportional")
                image.hAlign = "LEFT"
                story.append(image)
        add(b.get("name") or "Nexo · Asesoría empresarial", "Heading2")
        add("Informe de análisis empresarial", "Title")
        add("EJECUTIVO CON ANEXOS" if complete else "INFORME EJECUTIVO", "Heading2")
        table(
            ["Empresa", "Persona / período"],
            [
                [
                    s["company"]["name"] + "\nRUT " + s["company"]["rut"],
                    s["party"]["name"]
                    + "\nRUT "
                    + s["party"]["rut"]
                    + "\n"
                    + s["period"],
                ]
            ],
            [252, 247],
        )
        add(
            "Emitido: "
            + timezone.localtime(ev.created_at).strftime("%d-%m-%Y %H:%M")
            + " · Autor: "
            + (b.get("author") or ev.author.username)
        )
        add(
            "Revisor: " + (b.get("reviewer") or "No asignado") + " · ID " + str(ev.pk),
            "SmallSafe",
        )
        add(
            "Motor "
            + s["engine"]
            + " · Esquema "
            + s["schema"]
            + " · SHA-256 "
            + ev.digest,
            "SmallSafe",
        )
        add("1. Resumen ejecutivo", "Heading1")
        for r in s["results"]:
            add(SCOPE[r["scope"]] + ": " + r["status"], "Heading2")
            for applied in r["matched"]:
                add(applied["rule"] + " · " + applied["explanation"])
            if r["blocked"]:
                add(
                    "Reglas candidatas pendientes de verificación: "
                    + ", ".join(x["rule"] for x in r["blocked"])
                )
        add(
            "Esta evaluación separa calidad laboral, tratamiento tributario y situación previsional. No constituye un dictamen oficial. Una participación o un poder, por sí solos, no determinan las otras dimensiones."
        )
        add("2. Antecedentes societarios y facultades", "Heading1")
        table(
            ["Titular / vía", "Capital / utilidades / votos", "Vigencia"],
            [
                [
                    o["party_name"]
                    + (" vía " + o["via_name"] if o["via_name"] else " (directo)"),
                    f"{o['capital']}% / {o['profits']}% / {o['votes']}%",
                    o["valid_from"] + " — " + (o["valid_to"] or "abierta"),
                ]
                for o in s["ownership"]
            ]
            or [["Sin antecedentes", "Pendiente", "Pendiente"]],
            [190, 180, 129],
        )
        add(
            "La participación económica indirecta no acredita control jurídico ni condición de socio directo."
        )
        for a in s["authorities"]:
            add(
                "Administración: "
                + TRI.get(a["general_admin"], a["general_admin"])
                + " · Representación: "
                + TRI.get(a["legal_rep"], a["legal_rep"])
                + " · Ejercicio: "
                + a["exercise"]
            )
            add(a["powers"] or "Falta documentar poderes específicos.")
        add("3. Trabajo efectivo y hechos relevantes", "Heading1")
        add(s["work"]["functions"])
        add("Reporta a: " + (s["work"]["reports_to"] or "No determinado"))
        table(
            ["Hecho declarado", "Respuesta"],
            [[LABELS[k], TRI.get(v, v)] for k, v in s["facts"].items()],
            [330, 169],
        )
        add("Observaciones y evidencia: " + (s["work"]["evidence"] or "No aportada"))
        for key, value in s["work"].get("response_evidence", {}).items():
            if value:
                add(LABELS.get(key, key) + ": " + value)
        add(
            "Discrepancias: "
            + (
                s["work"]["discrepancies"]
                or "No declaradas; esto no acredita ausencia de contradicciones."
            )
        )
        add("4. Sueldo empresarial y fundamento", "Heading1")
        add(
            "Asignación mensual registrada: $"
            + str(s["work"]["amount"])
            + " CLP. Razonabilidad: "
            + (s["work"]["reasonableness"] or "Pendiente")
        )
        add("Pago/devengo y contabilidad: " + (s["work"]["pay_setting"] or "Pendiente"))
        add(
            "IUSC, LRE, DJ 1887 y F22: "
            + (s["work"]["tax_support"] or "Aplicabilidad y cumplimiento pendientes.")
        )
        add(
            "No se usa el tope previsional como límite tributario automático. La aceptación del gasto tampoco determina si una cotización es voluntaria."
        )
        add("5. Cotizaciones y coberturas", "Heading1")
        # Narrow tables are split by concept, keeping long obligations readable.
        if complete:
            for row in s["contributions"]:
                add(row["concept"] + " · " + row["status"], "Heading2")
                table(
                    ["Concepto", "Detalle"],
                    [
                        ["Obligado / costo", row["payer"] + " / " + row["cost"]],
                        [
                            "Base / tasa / tope",
                            text(row["base"])
                            + " / "
                            + text(row["rate"])
                            + " / "
                            + text(row["cap"]),
                        ],
                        ["Pago / cobertura", row["payment"] + " / " + row["coverage"]],
                        ["Requisitos", row["requirements"]],
                        [
                            "Fuente / vigencia",
                            text(row["source_id"])
                            + " · "
                            + row["valid_from"]
                            + " — "
                            + row["valid_to"],
                        ],
                    ],
                    [130, 369],
                )
        else:
            table(
                ["Concepto", "Estado", "Obligado / cobertura"],
                [
                    [r["concept"], r["status"], r["payer"] + " / " + r["coverage"]]
                    for r in s["contributions"]
                ],
                [175, 95, 229],
            )
        add(
            "Otras actividades y rentas: "
            + (s["work"]["other_income"] or "Falta confirmar.")
        )
        add("6. Simulación de APV régimen B", "Heading1")
        sim = s["simulation"]
        add(sim["status"])
        table(
            ["Resultado", "CLP"],
            [
                [label, sim.get(key)]
                for label, key in [
                    ("Base antes", "base_before"),
                    ("Rebaja admisible", "deduction"),
                    ("Exceso / sin rebaja", "excess"),
                    ("Base después", "base_after"),
                    ("Impuesto antes", "tax_before"),
                    ("Impuesto después", "tax_after"),
                    ("Ahorro estimado", "saving"),
                ]
            ],
            [330, 169],
        )
        for note in sim["notes"]:
            add(note)
        add(
            "Retiros anticipados: "
            + sim.get(
                "withdrawals",
                "Tratamiento pendiente de verificación; no se estima carga de retiro.",
            )
        )
        add("7. Comparación de escenarios", "Heading1")
        for scenario in s["scenarios"]:
            add(
                scenario["name"]
                + ": "
                + scenario["assumptions"]
                + " "
                + scenario["outcome"]
            )
        add("8. Acciones y antecedentes pendientes", "Heading1")
        for item in s["pending"]:
            add("• " + item)
        add("9. Fuentes del análisis", "Heading1")
        if not s["sources"]:
            add(
                "No hay fuentes verificadas aplicables. Las conclusiones jurídicas y cálculos que las requieren están bloqueados."
            )
        for source in s["sources"]:
            add(
                str(source["id"])
                + " · "
                + source["institution"]
                + " · "
                + source["document"]
                + " · "
                + source["status"],
                "Heading2",
            )
            add(source["summary"])
            add(source["url"], "SmallSafe")
            # Official links are validated on entry; escape href independently.
            story.append(
                Paragraph(
                    '<link href="'
                    + escape(source["url"], {'"': "&quot;"})
                    + '" color="#126c63">Abrir fuente oficial</link>',
                    styles["SmallSafe"],
                )
            )
            if complete:
                add("Extracto: " + (source["excerpt"] or "Pendiente"))
                add(
                    "Vigencia: "
                    + source["valid_from"]
                    + " — "
                    + (source["valid_to"] or "abierta")
                    + " · Verificación: "
                    + text(source["verified_on"]),
                    "SmallSafe",
                )
        if complete:
            add("Anexo · Reglas y parámetros conservados", "Heading1")
            for rule in s["rules"]:
                add(
                    rule["code"] + " v" + str(rule["version"]) + " · " + rule["status"],
                    "Heading2",
                )
                add(rule["explanation"])
                add(
                    json.dumps(
                        {
                            "conditions": rule["conditions"],
                            "exceptions": rule["exceptions"],
                        },
                        ensure_ascii=False,
                    ),
                    "SmallSafe",
                )
            add(json.dumps(s["parameters"], ensure_ascii=False, indent=2), "SmallSafe")
            add("Respaldos privados referenciados", "Heading2")
            for d in s["documents"]:
                add(d["title"] + " · página " + d["page"])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#52666b"))
        canvas.setFont(family, 8)
        canvas.drawString(
            48, 27, "CONFIDENCIAL · Análisis profesional sujeto a revisión"
        )
        canvas.drawRightString(A4[0] - 48, 27, f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        rightMargin=48,
        leftMargin=48,
        topMargin=42,
        bottomMargin=48,
        title="Expediente de análisis empresarial",
        author="Nexo",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    out.seek(0)
    return out


SHEETS = [
    "Resumen ejecutivo",
    "Empresas",
    "Socios y accionistas",
    "Administración y poderes",
    "Antecedentes laborales",
    "Evaluación",
    "Sueldo empresarial",
    "Cotizaciones",
    "APV régimen B",
    "Comparación de escenarios",
    "Parámetros",
    "Normativa",
    "Pendientes",
]


def safe_cell(ws, row, col, value):
    cell = ws.cell(row, col)
    if value is None:
        cell.value = "Pendiente"
    elif isinstance(value, (date, datetime)):
        cell.value = value
        cell.number_format = "dd-mm-yyyy"
    elif isinstance(value, Decimal):
        cell.value = value
        cell.number_format = "#,##0.00"
    elif isinstance(value, (int, bool)):
        cell.value = value
    else:
        # Explicit OOXML string cells prevent imported = + - @ payloads from becoming formulas.
        raw = text(value)
        if len(raw) > 32760:
            name = "Textos extensos"
            extra = (
                ws.parent[name]
                if name in ws.parent.sheetnames
                else ws.parent.create_sheet(name)
            )
            if extra.max_row == 1 and extra.cell(1, 1).value is None:
                for c, h in enumerate(
                    ["Origen", "Parte", "Texto íntegro por partes"], 1
                ):
                    extra.cell(1, c, h).data_type = "s"
            ref = f"{ws.title}!{cell.coordinate}"
            for index, start in enumerate(range(0, len(raw), 32000), 1):
                n = extra.max_row + 1
                extra.cell(n, 1, ref).data_type = "s"
                extra.cell(n, 2, index)
                extra.cell(n, 3, raw[start : start + 32000]).data_type = "s"
            raw = (
                raw[:32000] + " [Continúa en hoja Textos extensos; origen " + ref + "]"
            )
        cell.value = raw
        cell.data_type = "s"
    cell.alignment = Alignment(vertical="top", wrap_text=True)
    return cell


def format_book(wb):
    for index, ws in enumerate(wb.worksheets):
        ws.freeze_panes = "A2"
        ws.sheet_view.showGridLines = False
        for cell in ws[1]:
            cell.fill = PatternFill("solid", fgColor="163B3B")
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(wrap_text=True)
        ws.row_dimensions[1].height = 34
        for col in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(col)].width = min(
                55, max(18, len(str(ws.cell(1, col).value)) + 4)
            )
        if ws.max_row > 1:
            tab = Table(
                displayName="Datos" + str(index),
                ref=f"A1:{get_column_letter(ws.max_column)}{ws.max_row}",
            )
            tab.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2", showRowStripes=True
            )
            ws.add_table(tab)
        else:
            ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}1"
        ws.print_options.horizontalCentered = True
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.print_title_rows = "1:1"
        ws.oddFooter.center.text = "Confidencial · Página &P de &N"


def template_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "Composición"
    for j, key in enumerate(COLUMNS, 1):
        safe_cell(ws, 1, j, key)
    rows = [
        [
            "Socia Ejemplo",
            "11111111-1",
            "natural",
            "90",
            "90",
            "90",
            "",
            "Demostración ficticia",
            "2026-01-01",
            "",
            "",
        ],
        [
            "Socio Administrador",
            "22222222-2",
            "natural",
            "10",
            "10",
            "10",
            "",
            "Demostración ficticia",
            "2026-01-01",
            "",
            "",
        ],
    ]
    for i, row in enumerate(rows, 2):
        for j, value in enumerate(row, 1):
            safe_cell(ws, i, j, value)
    format_book(wb)
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out


def excel_report(evaluations):
    wb = Workbook()
    wb.remove(wb.active)
    headers = {
        "Resumen ejecutivo": [
            "Informe ID",
            "Empresa",
            "Persona",
            "Período",
            "Laboral",
            "Tributario",
            "Previsional",
            "Motor",
            "SHA-256",
            "Emitido",
        ],
        "Empresas": [
            "Informe ID",
            "Razón social",
            "RUT",
            "Tipo",
            "Régimen",
            "Determinación renta",
            "Profesionales",
            "Categoría",
        ],
        "Socios y accionistas": [
            "Informe ID",
            "Titular",
            "RUT entidad ID",
            "Vía",
            "Capital %",
            "Utilidades %",
            "Votos %",
            "Clase",
            "Derechos",
            "Desde",
            "Hasta",
        ],
        "Administración y poderes": [
            "Informe ID",
            "Persona ID",
            "Representación",
            "Administración",
            "Ejercicio",
            "Contratar despedir remunerar",
            "Disciplina",
            "Directorio",
            "Designar remover",
            "Dirección efectiva",
            "Poderes",
            "Desde",
            "Hasta",
        ],
        "Antecedentes laborales": ["Informe ID", "Hecho", "Respuesta / antecedente"],
        "Evaluación": [
            "Informe ID",
            "Ámbito",
            "Resultado",
            "Reglas aplicadas",
            "Bloqueadas",
            "Antecedentes faltantes",
            "Fuentes",
        ],
        "Sueldo empresarial": [
            "Informe ID",
            "Asignación CLP (entrada)",
            "Razonabilidad",
            "Pago y devengo",
            "Respaldo tributario",
            "Nota",
        ],
        "Cotizaciones": [
            "Informe ID",
            "Concepto",
            "Estado",
            "Obligado",
            "Costo",
            "Base",
            "Tasa",
            "Tope CLP",
            "Pago",
            "Cobertura",
            "Requisitos",
            "Fuente",
            "Desde",
            "Hasta",
            "Estimación CLP",
        ],
        "APV régimen B": [
            "Informe ID",
            "Estado",
            "Renta (entrada)",
            "Cotizaciones (entrada)",
            "Rebajas externas (entrada)",
            "Rebaja admisible CLP",
            "Exceso CLP",
            "Base antes CLP",
            "Base después CLP",
            "Impuesto antes CLP",
            "Impuesto después CLP",
            "Ahorro CLP",
            "Comprobación ahorro (fórmula)",
            "Supuestos y retiros",
            "Aportes registrados",
        ],
        "Comparación de escenarios": [
            "Informe ID",
            "Escenario",
            "Supuestos",
            "Resultado",
        ],
        "Parámetros": ["Informe ID", "Versión conservada", "Redondeo", "Supuestos"],
        "Normativa": [
            "Informe ID",
            "Fuente ID",
            "Institución",
            "Documento",
            "Fecha",
            "Materias",
            "Resumen",
            "Extracto",
            "URL",
            "Verificado",
            "Desde",
            "Hasta",
            "Estado",
            "Relacionado",
        ],
        "Pendientes": ["Informe ID", "Acción / antecedente"],
    }
    for name in SHEETS:
        ws = wb.create_sheet(name)
        for j, h in enumerate(headers[name], 1):
            safe_cell(ws, 1, j, h)

    def row(sheet, values):
        ws = wb[sheet]
        n = ws.max_row + 1
        for j, v in enumerate(values, 1):
            safe_cell(ws, n, j, v)
        return n

    def number(value):
        return Decimal(value) if value is not None else None

    def day(value):
        return date.fromisoformat(value) if value else None

    for ev in evaluations:
        s = ev.snapshot
        eid = str(ev.pk)
        c = s["company"]
        w = s["work"]
        sim = s["simulation"]
        inp = sim.get("inputs") or {}
        row(
            "Resumen ejecutivo",
            [
                eid,
                c["name"],
                s["party"]["name"],
                day(s["period"]),
                *[r["status"] for r in s["results"]],
                s["engine"],
                ev.digest,
                timezone.localtime(ev.created_at).replace(tzinfo=None),
            ],
        )
        row(
            "Empresas",
            [
                eid,
                c["name"],
                c["rut"],
                c["legal_type"],
                c["tax_regime"],
                c["income_method"],
                TRI[c["professional_company"]],
                c["tax_category"],
            ],
        )
        for o in s["ownership"]:
            row(
                "Socios y accionistas",
                [
                    eid,
                    o["party_name"],
                    o["party"],
                    o["via_name"],
                    Decimal(o["capital"]),
                    Decimal(o["profits"]),
                    Decimal(o["votes"]),
                    o["share_class"],
                    o["special_rights"],
                    day(o["valid_from"]),
                    day(o["valid_to"]),
                ],
            )
        for a in s["authorities"]:
            row(
                "Administración y poderes",
                [
                    eid,
                    a["party"],
                    TRI[a["legal_rep"]],
                    TRI[a["general_admin"]],
                    a["exercise"],
                    TRI[a["hire_fire_pay"]],
                    TRI[a["disciplinary"]],
                    TRI[a["board"]],
                    TRI[a["appoint_remove"]],
                    TRI[a["effective_direction"]],
                    a["powers"],
                    day(a["valid_from"]),
                    day(a["valid_to"]),
                ],
            )
        for f, v in s["facts"].items():
            row("Antecedentes laborales", [eid, LABELS[f], TRI.get(v, v)])
        for f in (
            "functions",
            "reports_to",
            "pay_setting",
            "evidence",
            "response_evidence",
            "discrepancies",
            "other_income",
        ):
            row("Antecedentes laborales", [eid, f, w.get(f, "")])
        for r in s["results"]:
            row(
                "Evaluación",
                [
                    eid,
                    SCOPE[r["scope"]],
                    r["status"],
                    r["matched"],
                    r["blocked"],
                    r["unknown"],
                    [x["sources"] for x in r["matched"]],
                ],
            )
        row(
            "Sueldo empresarial",
            [
                eid,
                Decimal(w["amount"]),
                w["reasonableness"],
                w["pay_setting"],
                w["tax_support"],
                "No aplica un tope previsional como límite tributario automático; conclusión tributaria separada.",
            ],
        )
        for r in s["contributions"]:
            row(
                "Cotizaciones",
                [
                    eid,
                    r["concept"],
                    r["status"],
                    r["payer"],
                    r["cost"],
                    r["base"],
                    number(r["rate"]),
                    number(r["cap"]),
                    r["payment"],
                    r["coverage"],
                    r["requirements"],
                    r["source_id"],
                    day(r["valid_from"]),
                    day(r["valid_to"]),
                    number(r["estimated_amount"]),
                ],
            )
        n = row(
            "APV régimen B",
            [
                eid,
                sim["status"],
                number(inp.get("income")),
                number(inp.get("mandatory")),
                number(inp.get("prior_deductions")),
                *[
                    number(sim.get(key))
                    for key in (
                        "deduction",
                        "excess",
                        "base_before",
                        "base_after",
                        "tax_before",
                        "tax_after",
                        "saving",
                    )
                ],
                None,
                "; ".join(sim["notes"]) + " " + sim.get("withdrawals", "Pendiente"),
                sim["contributions"],
            ],
        )
        if sim["saving"] is not None:
            wb["APV régimen B"].cell(n, 13, f"=J{n}-K{n}").number_format = "#,##0"
        for col in (3, 4, 5):
            wb["APV régimen B"].cell(n, col).fill = PatternFill(
                "solid", fgColor="FFF0CC"
            )
        for col in range(6, 14):
            wb["APV régimen B"].cell(n, col).fill = PatternFill(
                "solid", fgColor="DCEEE8"
            )
        for scenario in s["scenarios"]:
            row(
                "Comparación de escenarios",
                [eid, scenario["name"], scenario["assumptions"], scenario["outcome"]],
            )
        row(
            "Parámetros",
            [
                eid,
                s["parameters"],
                "Decimal; CLP entero ROUND_HALF_UP. Porcentajes como decimales exactos.",
                "Amarillo: entradas. Verde: resultados. Rebajas externas: fuera del registro de aportes, nunca duplicar. No actualizar este expediente con normas posteriores.",
            ],
        )
        for source in s["sources"]:
            n = row(
                "Normativa",
                [
                    eid,
                    source["id"],
                    source["institution"],
                    source["document"],
                    day(source["date"]),
                    source["subjects"],
                    source["summary"],
                    source["excerpt"],
                    source["url"],
                    day(source["verified_on"]),
                    day(source["valid_from"]),
                    day(source["valid_to"]),
                    source["status"],
                    source["related"],
                ],
            )
            wb["Normativa"].cell(n, 9).hyperlink = source["url"]
            wb["Normativa"].cell(n, 9).style = "Hyperlink"
        for pending in s["pending"]:
            row("Pendientes", [eid, pending])
    format_book(wb)
    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out
