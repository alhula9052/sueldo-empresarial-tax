import csv
import io
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from openpyxl import load_workbook
from django.core.exceptions import ValidationError
from .models import Party, Ownership
from .validators import normalize_rut, validate_rut

COLUMNS = [
    "nombre",
    "rut",
    "tipo",
    "capital",
    "utilidades",
    "votos",
    "clase",
    "derechos",
    "desde",
    "hasta",
    "via_rut",
]


def read_upload(file):
    if file.name.lower().endswith(".csv"):
        text = file.read().decode("utf-8-sig")
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(io.StringIO(text), dialect))
    else:
        # Bound decompressed XML size before parsing a user-provided ZIP container.
        with zipfile.ZipFile(file) as z:
            if sum(i.file_size for i in z.infolist()) > 20 * 1024 * 1024:
                raise ValidationError("Excel descomprimido demasiado grande.")
        file.seek(0)
        wb = load_workbook(file, read_only=True, data_only=False)
        rows = []
        for row in wb.active.iter_rows():
            if len(rows) > 1001:
                raise ValidationError("Máximo 1.000 filas.")
            vals = []
            for c in row:
                if c.data_type == "f":
                    raise ValidationError(
                        "La importación no admite fórmulas. Pegue valores."
                    )
                vals.append(
                    c.value.isoformat()[:10]
                    if isinstance(c.value, (date, datetime))
                    else str(c.value)
                    if c.value is not None
                    else ""
                )
            if any(vals):
                rows.append(vals)
        wb.close()
    if len(rows) < 2 or len(rows) > 1001 or len(rows[0]) > 40:
        raise ValidationError(
            "Se requieren encabezados y entre 1 y 1.000 filas; máximo 40 columnas."
        )
    return rows[0], rows[1:]


def mapped_rows(headers, rows, mapping):
    required = ["nombre", "rut", "tipo", "capital", "utilidades", "votos", "desde"]
    if any(mapping.get(key, "") == "" for key in required):
        raise ValidationError(
            "Mapee todas las columnas obligatorias: " + ", ".join(required)
        )
    indices = [int(i) for i in mapping.values() if i != ""]
    if len(indices) != len(set(indices)) or any(
        i < 0 or i >= len(headers) for i in indices
    ):
        raise ValidationError("Mapeo duplicado o inválido.")
    return [
        {
            key: str(row[int(mapping[key])]).strip()
            if mapping.get(key, "") != "" and int(mapping[key]) < len(row)
            else ""
            for key in COLUMNS
        }
        for row in rows
    ]


def validate_rows(client, company, rows):
    errors = []
    seen = set()
    prepared = []
    for number, row in enumerate(rows, 2):
        try:
            validate_rut(row["rut"])
            rut = normalize_rut(row["rut"])
            if not row["nombre"]:
                raise ValidationError("Nombre obligatorio.")
            if row["tipo"] not in ("natural", "legal"):
                raise ValidationError("Tipo: natural o legal.")
            start = date.fromisoformat(row["desde"])
            end = date.fromisoformat(row["hasta"]) if row["hasta"] else None
            if end and end < start:
                raise ValidationError("Fechas invertidas.")
            numbers = {
                key: Decimal(row[key]) for key in ("capital", "utilidades", "votos")
            }
            for n in numbers.values():
                if not n.is_finite() or n < 0 or n > 100 or n.as_tuple().exponent < -4:
                    raise ValidationError(
                        "Porcentaje inválido (0–100, hasta 4 decimales)."
                    )
            via = (
                Party.objects.filter(
                    client=client, rut=normalize_rut(row["via_rut"])
                ).first()
                if row["via_rut"]
                else None
            )
            if row["via_rut"] and not via:
                raise ValidationError("Intermediario no registrado; créelo primero.")
            if via and via.rut == rut:
                raise ValidationError("El intermediario no puede ser el titular.")
            party = Party.objects.filter(client=client, rut=rut).first()
            if party and (party.name != row["nombre"] or party.kind != row["tipo"]):
                raise ValidationError(
                    "El titular existente tiene otro nombre o tipo; revise el registro."
                )
            signature = (rut, row["clase"], via.pk if via else None, start, end)
            if signature in seen:
                raise ValidationError("Fila duplicada.")
            seen.add(signature)
            # Full cross-row and existing composition validation also executes transactionally at confirmation.
            prepared.append(
                dict(
                    row=row,
                    rut=rut,
                    start=start,
                    end=end,
                    via=via,
                    numbers=numbers,
                    party=party,
                )
            )
        except (ValidationError, ValueError, InvalidOperation) as e:
            errors.append(
                f"Fila {number}: "
                + (
                    "; ".join(e.messages)
                    if isinstance(e, ValidationError)
                    else "Fecha o número inválido."
                )
            )
    return prepared, errors


def save_rows(client, company, rows):
    prepared, errors = validate_rows(client, company, rows)
    if errors:
        raise ValidationError(errors)
    from django.db import transaction

    with transaction.atomic():
        for row in prepared:
            party = row["party"]
            if not party:
                party = Party(
                    client=client,
                    name=row["row"]["nombre"],
                    rut=row["rut"],
                    kind=row["row"]["tipo"],
                )
                party.full_clean()
                party.save()
            ownership = Ownership(
                client=client,
                company=company,
                party=party,
                via=row["via"],
                valid_from=row["start"],
                valid_to=row["end"],
                share_class=row["row"]["clase"],
                special_rights=row["row"]["derechos"],
                **{
                    "capital": row["numbers"]["capital"],
                    "profits": row["numbers"]["utilidades"],
                    "votes": row["numbers"]["votos"],
                },
            )
            ownership.full_clean()
            ownership.save()
    return len(prepared)


def preview_rows(client, company, rows):
    # Run exactly the confirmation validations, but roll back every change.
    from django.db import transaction

    try:
        with transaction.atomic():
            count = save_rows(client, company, rows)
            transaction.set_rollback(True)
            return count, []
    except ValidationError as e:
        return 0, e.messages
