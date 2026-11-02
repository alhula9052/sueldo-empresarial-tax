import re
from django.core.exceptions import ValidationError


def normalize_rut(value):
    return re.sub(r"[.\s-]", "", value).upper()


def validate_rut(value):
    value = normalize_rut(value)
    if not re.fullmatch(r"[1-9][0-9]{5,7}[0-9K]", value):
        raise ValidationError("RUT inválido. Use cuerpo y dígito verificador.")
    body, dv = value[:-1], value[-1]
    total = sum(int(n) * (2 + i % 6) for i, n in enumerate(reversed(body)))
    check = 11 - total % 11
    if dv != ("0" if check == 11 else "K" if check == 10 else str(check)):
        raise ValidationError("Dígito verificador de RUT incorrecto.")


def percent(value):
    if value < 0 or value > 100:
        raise ValidationError("El porcentaje debe estar entre 0 y 100.")


def nonnegative(value):
    if value < 0:
        raise ValidationError("El importe no puede ser negativo.")
