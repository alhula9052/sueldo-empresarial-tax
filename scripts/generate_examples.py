"""Generate private example files from the latest saved demo evaluations."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()
from core.models import Evaluation, Work  # noqa: E402
from core.exports import pdf_report, excel_report  # noqa: E402

out = ROOT / "artifacts"
out.mkdir(exist_ok=True)
evaluations = []
for work in Work.objects.filter(client__name="Consultora Demo · Datos ficticios"):
    ev = Evaluation.objects.filter(work=work).order_by("-created_at").first()
    if ev:
        evaluations.append(ev)
if not evaluations:
    raise SystemExit("Ejecute primero seed_demo y guarde una evaluación.")
for name, content in [
    ("ejemplo-completo.pdf", pdf_report(evaluations, True)),
    ("ejemplo-ejecutivo.pdf", pdf_report(evaluations[:1], False)),
    ("ejemplo-consolidado.xlsx", excel_report(evaluations)),
]:
    (out / name).write_bytes(content.getvalue())
print(
    "Ejemplos ficticios generados en artifacts/: PDF completo, ejecutivo y expediente XLSX."
)
