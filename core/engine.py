"""Deterministic three-valued rules. Money uses Decimal / ROUND_HALF_UP (CLP)."""

import calendar
import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms.models import model_to_dict
from .models import (
    Ownership,
    Authority,
    Rule,
    Parameters,
    Simulation,
    Contribution,
    Branding,
    Document,
)

FIELDS = {
    "effective_work",
    "instructions",
    "supervision",
    "discipline",
    "leave",
    "availability",
    "autonomy",
    "contribution_work",
    "direct_majority",
    "general_admin",
    "legal_rep",
    "joint_admin",
    "contradictions",
    "tax_support",
    "reasonableness",
}


def validate_condition(node, depth=0):
    if depth > 8 or not isinstance(node, dict) or not node:
        raise ValidationError("Condición vacía o demasiado profunda.")
    if set(node) in ({"all"}, {"any"}):
        children = next(iter(node.values()))
        if not isinstance(children, list) or not 1 <= len(children) <= 30:
            raise ValidationError("all/any requiere entre 1 y 30 condiciones.")
        for child in children:
            validate_condition(child, depth + 1)
    elif set(node) == {"field", "eq"}:
        if node["field"] not in FIELDS or node["eq"] not in ("yes", "no"):
            raise ValidationError(
                "Campo o valor no admitido. Use yes/no; unknown no equivale a no."
            )
    else:
        raise ValidationError(
            'Use {"all":[...]} / {"any":[...]} o {"field":"instructions","eq":"yes"}.'
        )


def match(node, facts):
    if "field" in node:
        val = facts.get(node["field"], "unknown")
        return None if val == "unknown" else val == node["eq"]
    values = [match(n, facts) for n in node.get("all", node.get("any", []))]
    if "all" in node:
        return False if False in values else None if None in values else True
    return True if True in values else None if None in values else False


def dec(value):
    if isinstance(value, (float, bool)):
        raise ValidationError("Use decimales como texto, nunca float o booleano.")
    try:
        d = Decimal(str(value))
        if (
            not d.is_finite()
            or d < 0
            or d.adjusted() > 24
            or d.as_tuple().exponent < -12
        ):
            raise InvalidOperation
        return d
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Parámetro decimal inválido o negativo.")


def clp(value):
    return dec(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _validate_parameters(data):
    if not isinstance(data, dict):
        raise ValidationError("Los parámetros deben ser un objeto JSON.")
    for key in ("uf", "utm"):
        if key in data:
            dec(data[key])
    for category, cfg in data.get("apv", {}).items():
        if category not in ("dependent", "independent", "business"):
            raise ValidationError("Calidad APV inválida.")
        for key in ("annual_cap_clp", "monthly_payroll_cap_clp"):
            if key in cfg:
                dec(cfg[key])
        for horizon, brackets in cfg.get("brackets", {}).items():
            if (
                horizon not in ("annual", "monthly")
                or not isinstance(brackets, list)
                or not brackets
            ):
                raise ValidationError("Tramos anuales o mensuales requeridos.")
            previous = Decimal("-1")
            for index, b in enumerate(brackets):
                if set(b) != {"up_to", "rate", "deduction"}:
                    raise ValidationError(
                        "Cada tramo requiere up_to, rate y deduction."
                    )
                rate = dec(b["rate"])
                dec(b["deduction"])
                if rate > 1:
                    raise ValidationError("Tasa fuera de 0 a 1.")
                if b["up_to"] is None:
                    if index != len(brackets) - 1:
                        raise ValidationError("El tramo sin límite debe ser el último.")
                else:
                    limit = dec(b["up_to"])
                    if limit <= previous:
                        raise ValidationError("Tramos no crecientes.")
                    previous = limit
            if brackets[-1]["up_to"] is not None:
                raise ValidationError("El último tramo debe tener up_to null.")
    for row in data.get("contributions", []):
        required = {
            "concept",
            "category",
            "status",
            "payer",
            "cost",
            "base",
            "rate",
            "cap",
            "payment",
            "coverage",
            "requirements",
            "source_id",
        }
        if not required.issubset(row):
            raise ValidationError(
                "Fila previsional incompleta; consulte el esquema documentado."
            )
        if row["category"] not in ("dependent", "independent", "business"):
            raise ValidationError("Calidad previsional inválida.")
        if row["status"] not in (
            "Obligatorio",
            "Voluntario",
            "No corresponde",
            "Pendiente",
        ):
            raise ValidationError("Estado previsional inválido.")
        if row["rate"] is not None and dec(row["rate"]) > 1:
            raise ValidationError("Tasa previsional fuera de 0 a 1.")
        if row["cap"] is not None:
            dec(row["cap"])


def validate_parameters(data):
    try:
        _validate_parameters(data)
        if not isinstance(data.get("apv", {}), dict) or not isinstance(
            data.get("contributions", []), list
        ):
            raise ValidationError("apv debe ser objeto y contributions una lista.")
        for cfg in data.get("apv", {}).values():
            if not isinstance(cfg.get("eligibility_verified", False), bool):
                raise ValidationError("eligibility_verified debe ser booleano.")
            coordination = cfg.get("coordination", {})
            if not isinstance(coordination, dict) or any(
                k not in ("APVC", "DC")
                or v not in ("consume_cap_only", "excluded_verified")
                for k, v in coordination.items()
            ):
                raise ValidationError("Coordinación APVC/DC inválida.")
            if cfg.get("monthly_cap_mode") not in (None, "fixed_verified"):
                raise ValidationError("Modo de tope mensual inválido.")
            for month, value in cfg.get("monthly_payroll_caps_clp", {}).items():
                if str(month) not in {str(i) for i in range(1, 13)}:
                    raise ValidationError("Mes inválido en topes.")
                dec(value)
    except (AttributeError, TypeError, KeyError) as exc:
        raise ValidationError(
            "Estructura de parámetros inválida; consulte el esquema documentado."
        ) from exc


def active(qs, day):
    return qs.filter(valid_from__lte=day).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=day)
    )


def serialized(obj):
    data = model_to_dict(obj, exclude=["client", "sources", "logo"])
    return json.loads(json.dumps(data, default=str))


def sources_ready(obj, day):
    sources = list(obj.sources.all())
    return (
        obj.status == "verified"
        and bool(sources)
        and all(
            s.official
            and s.status == "verified"
            and s.verified_on
            and s.valid_from <= day
            and (not s.valid_to or s.valid_to >= day)
            for s in sources
        )
    )


def applicable_parameters(work):
    rows = list(active(Parameters.objects.filter(client=work.client), work.period))
    # Multiple overlapping versions are ambiguous: never choose silently.
    if len(rows) != 1:
        return None, "Falta un conjunto único de parámetros vigente para el período."
    p = rows[0]
    if not sources_ready(p, work.period):
        return None, "Parámetros o sus fuentes pendientes de verificación."
    return p, ""


def tax(base, brackets):
    for b in brackets:
        if b["up_to"] is None or base <= dec(b["up_to"]):
            return max(
                Decimal(0), base * dec(b["rate"]) - dec(b["deduction"])
            ).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    raise ValidationError("Tramos incompletos.")


def simulate(work, params):
    sim = Simulation.objects.filter(work=work).first()
    contributions = list(
        Contribution.objects.filter(
            work__client=work.client,
            work__party=work.party,
            date__year=work.period.year,
            date__lte=date(
                work.period.year,
                work.period.month,
                calendar.monthrange(work.period.year, work.period.month)[1],
            ),
        ).order_by("date", "pk")
    )
    result = {
        "status": "Simulación parcial",
        "notes": [],
        "contributions": [serialized(c) for c in contributions],
        "inputs": serialized(sim) if sim else None,
        "deduction": None,
        "excess": None,
        "tax_before": None,
        "tax_after": None,
        "saving": None,
        "base_before": None,
        "base_after": None,
    }
    if not sim:
        result["notes"].append("Falta ficha de simulación.")
        return result
    cfg = params.data.get("apv", {}).get(sim.category) if params else None
    if (
        not cfg
        or cfg.get("eligibility_verified") is not True
        or not cfg.get("basis")
        or not cfg.get("withdrawals")
        or "annual_cap_clp" not in cfg
        or "monthly_payroll_cap_clp" not in cfg
        or not cfg.get("brackets", {}).get(sim.horizon)
    ):
        result["notes"].append(
            "Procedencia, límites, tramos o retiros no verificados para esta calidad y período. Cálculo tributario bloqueado."
        )
        return result
    if not sim.annual_complete:
        result["notes"].append(
            "Falta confirmar la integridad de rentas y aportes. Cálculo bloqueado."
        )
        return result
    if sim.mandatory > sim.income:
        result["notes"].append(
            "Cotizaciones deducibles superiores a la renta; revise antecedentes."
        )
        return result
    # Never infer an APV legal category from ownership or a labor result.
    cap = dec(cfg["annual_cap_clp"])
    monthly = dec(cfg["monthly_payroll_cap_clp"])
    month_caps = cfg.get("monthly_payroll_caps_clp", {})

    def cap_for(month):
        if str(month) in month_caps:
            return dec(month_caps[str(month)])
        if cfg.get("monthly_cap_mode") == "fixed_verified":
            return monthly
        return None

    apv = [c for c in contributions if c.instrument == "APV"]
    other_cap = Decimal(0)
    for instrument in ("APVC", "DC"):
        others = [c for c in contributions if c.instrument == instrument]
        if not others:
            continue
        coordination = cfg.get("coordination", {}).get(instrument)
        if coordination not in ("consume_cap_only", "excluded_verified"):
            result["notes"].append(
                "Falta verificar coordinación de "
                + instrument
                + " con los límites APV. Cálculo bloqueado."
            )
            return result
        if coordination == "consume_cap_only":
            other_cap += sum((c.amount for c in others), Decimal(0))
        result["notes"].append(
            instrument
            + ": coordinación parametrizada "
            + coordination
            + ". Este cálculo estima solo el beneficio incremental del APV registrado."
        )
    if sim.prior_deductions:
        result["notes"].append(
            "La rebaja y ahorro son adicionales a las rebajas externas declaradas. La renta de entrada debe estar neta de esas rebajas para no duplicarlas."
        )
    sums = {}
    direct = Decimal(0)
    for c in apv:
        if c.channel == "payroll":
            sums[c.date.month] = sums.get(c.date.month, Decimal(0)) + c.amount
        else:
            direct += c.amount
    if any(cap_for(m) is None for m in sums):
        result["notes"].append(
            "Faltan topes por mes para los aportes por planilla; no se reutiliza automáticamente el valor UF de otro período."
        )
        return result
    if sim.horizon == "monthly" and cap_for(work.period.month) is None:
        result["notes"].append("Falta el tope de planilla verificado para el mes.")
        return result
    if sim.horizon == "annual" and work.period.month != 12:
        result["notes"].append(
            "Simulación anual parcial: registro de aportes hasta el mes seleccionado, no cierre anual."
        )
    if sim.prior_deductions > cap:
        result["notes"].append(
            "Las rebajas externas declaradas superan el límite anual."
        )
        return result
    if sim.horizon == "monthly":
        total = sums.get(work.period.month, Decimal(0))
        # Prior months entered in the ledger also consume the annual limit.
        used = (
            sim.prior_deductions
            + other_cap
            + sum(min(v, cap_for(m)) for m, v in sums.items() if m < work.period.month)
        )
        admissible = min(total, cap_for(work.period.month), max(Decimal(0), cap - used))
        if direct:
            result["notes"].append(
                "Los aportes directos se reservan para la determinación anual; sin rebaja mensual en este cálculo."
            )
    else:
        total = sum(sums.values(), Decimal(0)) + direct
        admissible = min(
            sum((min(v, cap_for(m)) for m, v in sums.items()), Decimal(0)) + direct,
            max(Decimal(0), cap - sim.prior_deductions - other_cap),
        )
    base_before = max(Decimal(0), sim.income - sim.mandatory)
    deduction = min(admissible, base_before)
    before = tax(base_before, cfg["brackets"][sim.horizon])
    after = tax(base_before - deduction, cfg["brackets"][sim.horizon])
    if after > before:
        result["notes"].append(
            "Los tramos configurados producen un impuesto creciente tras la rebaja. Revisar parámetros."
        )
        return result
    result.update(
        status=(
            "Simulación anual parcial"
            if sim.horizon == "annual" and work.period.month != 12
            else "Estimación parametrizada; sujeta a revisión profesional"
        ),
        deduction=str(clp(deduction)),
        excess=str(clp(total - deduction)),
        tax_before=str(before),
        tax_after=str(after),
        saving=str(before - after),
        base_before=str(clp(base_before)),
        base_after=str(clp(base_before - deduction)),
        annual_cap=str(cap),
        monthly_cap=str(monthly),
        withdrawals=cfg["withdrawals"],
        basis=cfg["basis"],
    )
    return result


CONCEPTS = [
    "AFP y comisión",
    "Salud",
    "SIS",
    "Seguro de cesantía",
    "Accidentes del trabajo y enfermedades profesionales",
    "SANNA",
    "Nuevos aportes graduales",
    "Otras obligaciones",
]


def build_snapshot(work):
    company = work.company
    party = work.party
    day = work.period
    ownerships = list(
        active(Ownership.objects.filter(client=work.client, company=company), day)
    )
    authorities = list(
        active(
            Authority.objects.filter(client=work.client, company=company, party=party),
            day,
        )
    )
    facts = {f: getattr(work, f, "unknown") for f in FIELDS}
    direct = [o for o in ownerships if o.party_id == party.pk and not o.via_id]
    facts["direct_majority"] = (
        "yes" if sum(o.capital for o in direct) > 50 else "unknown"
    )
    for name in ("general_admin", "legal_rep"):
        values = {getattr(a, name) for a in authorities}
        facts[name] = (
            "yes" if "yes" in values else "no" if values == {"no"} else "unknown"
        )
    facts["joint_admin"] = (
        "yes" if any(a.exercise == "joint" for a in authorities) else "unknown"
    )
    facts["contradictions"] = "yes" if work.discrepancies.strip() else "unknown"
    facts["tax_support"] = "yes" if work.tax_support.strip() else "unknown"
    facts["reasonableness"] = "yes" if work.reasonableness.strip() else "unknown"
    results = []
    rules = []
    source_map = {}
    pending = []
    for scope in ("labor", "tax", "pension"):
        matches = []
        blocked = []
        unknown = []
        candidates = list(
            active(
                Rule.objects.filter(client=work.client, scope=scope).prefetch_related(
                    "sources"
                ),
                day,
            )
        )
        codes = [r.code for r in candidates]
        for rule in candidates:
            rules.append(
                {**serialized(rule), "sources": [s.pk for s in rule.sources.all()]}
            )
            for source in rule.sources.all():
                source_map[source.pk] = serialized(source)
            cond = match(rule.conditions, facts)
            exception = match(rule.exceptions, facts) if rule.exceptions else False
            ready = sources_ready(rule, day) and codes.count(rule.code) == 1
            if cond is True and exception is False:
                (matches if ready else blocked).append(
                    {
                        "rule": str(rule),
                        "result": rule.result,
                        "explanation": rule.explanation,
                        "sources": [s.pk for s in rule.sources.all()],
                    }
                )
            elif cond is None or exception is None:
                unknown.append(str(rule))
        if len(matches) > 1:
            status = (
                "Antecedentes contradictorios / reglas concurrentes: requiere revisión"
            )
        elif len(matches) == 1:
            status = matches[0]["result"]
        else:
            status = "Información insuficiente · conclusión pendiente de validación"
        if scope == "labor" and work.discrepancies.strip():
            status = "Antecedentes contradictorios · revisión requerida"
        results.append(
            {
                "scope": scope,
                "status": status,
                "matched": matches,
                "blocked": blocked,
                "unknown": unknown,
            }
        )
        if not matches:
            pending.append(
                f"{scope}: verificar fuentes, reglas y antecedentes antes de concluir."
            )
    for field in (
        "effective_work",
        "instructions",
        "supervision",
        "discipline",
        "leave",
        "availability",
        "autonomy",
        "contribution_work",
    ):
        if getattr(work, field) == "unknown":
            pending.append(
                str(work._meta.get_field(field).verbose_name) + ": no determinado."
            )
    totals = {
        f: str(sum((getattr(o, f) for o in ownerships if not o.via_id), Decimal(0)))
        for f in ("capital", "profits", "votes")
    }
    if any(Decimal(v) != 100 for v in totals.values()):
        pending.append(
            "Composición directa incompleta o sin confirmar al período: " + str(totals)
        )
    if not authorities:
        pending.append("Faltan poderes y administración vigentes para la persona.")
    params, why = applicable_parameters(work)
    if why:
        pending.append(why)
    if params:
        for s in params.sources.all():
            source_map[s.pk] = serialized(s)
    sim = Simulation.objects.filter(work=work).first()
    category = sim.category if sim else "unknown"
    matrix = []
    for concept in CONCEPTS:
        rows = (
            [
                r
                for r in params.data.get("contributions", [])
                if r["concept"] == concept and r["category"] == category
            ]
            if params
            else []
        )
        if len(rows) == 1 and rows[0]["source_id"] in {
            s.pk for s in params.sources.all()
        }:
            row = dict(rows[0])
            row["valid_from"] = str(params.valid_from)
            row["valid_to"] = str(params.valid_to or "")
            rate = row["rate"]
            cap = row["cap"]
            row["estimated_amount"] = (
                str(clp(min(work.amount, dec(cap)) * dec(rate)))
                if row["base"] == "assignment"
                and rate is not None
                and cap is not None
                and row["status"] == "Obligatorio"
                else None
            )
        else:
            row = dict(
                concept=concept,
                status="Pendiente",
                payer="Por verificar",
                cost="Por verificar",
                base="Por verificar",
                rate=None,
                cap=None,
                payment="Por verificar",
                coverage="Por verificar",
                requirements="Verificar calidad previsional, otras rentas y vigencia gradual.",
                source_id=None,
                estimated_amount=None,
                valid_from="",
                valid_to="",
            )
        matrix.append(row)
    pending.append(
        "Verificar razonabilidad, trabajo efectivo, pago/devengo, contabilidad e IUSC; aplicabilidad de LRE, DJ 1887 y F22. El tope previsional no es un límite tributario automático."
    )
    if any(r["status"] == "Pendiente" for r in matrix):
        pending.append(
            "Completar matriz previsional con tasas, sujetos y coberturas vigentes. La aceptación tributaria no determina voluntariedad de cotizaciones."
        )
    branding = Branding.objects.filter(client=work.client).first()
    return dict(
        schema="1.0",
        engine="1.0.0",
        period=str(day),
        company=serialized(company),
        party=serialized(party),
        work=serialized(work),
        ownership=[
            {
                **serialized(o),
                "party_name": o.party.name,
                "via_name": o.via.name if o.via else "",
            }
            for o in ownerships
        ],
        authorities=[serialized(a) for a in authorities],
        facts=facts,
        results=results,
        contributions=matrix,
        simulation=simulate(work, params),
        parameters=serialized(params) if params else None,
        sources=list(source_map.values()),
        rules=rules,
        pending=pending,
        branding={
            **serialized(branding),
            "logo_path": branding.logo.name if branding.logo else "",
        }
        if branding
        else {},
        documents=[
            {"id": d.pk, "title": d.title, "page": d.page}
            for d in Document.objects.filter(
                client=work.client, company=company
            ).filter(Q(party=party) | Q(party__isnull=True))
        ],
        scenarios=[
            {
                "name": "Con subordinación efectiva",
                "assumptions": "Instrucciones, control y poder disciplinario acreditados. No cambia automáticamente la calidad tributaria o previsional.",
                "outcome": "Requiere aplicar doctrina vigente y revisar poderes; sin conclusión automática.",
            },
            {
                "name": "Con autonomía efectiva",
                "assumptions": "Autonomía real acreditada; sin control ni sujeción disciplinaria. La ausencia de horario por sí sola no basta.",
                "outcome": "Requiere valorar todos los hechos y antecedentes contradictorios.",
            },
        ],
    )


def digest(snapshot):
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
