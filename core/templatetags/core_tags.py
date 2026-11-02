from django import template
from core.exports import LABELS, TRI

register = template.Library()


@register.filter
def human(value):
    return TRI.get(str(value), value)


@register.filter
def label(value):
    return LABELS.get(value, value)


@register.filter
def money(value):
    if value is None:
        return "Pendiente"
    try:
        return "$ " + format(int(value), ",").replace(",", ".")
    except (ValueError, TypeError):
        return value


@register.filter
def getitem(obj, key):
    return obj.get(key, "")
