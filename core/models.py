import uuid
import calendar
from datetime import date
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from .validators import validate_rut, normalize_rut, percent, nonnegative

TRI = [("unknown", "No determinado"), ("yes", "Sí"), ("no", "No")]
VALIDATION = [
    ("pending", "Pendiente de validación"),
    ("verified", "Verificado"),
    ("retired", "Sustituido / sin vigencia"),
]


class Client(models.Model):
    name = models.CharField("Cliente / consultora", max_length=180)

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLES = [
        ("admin", "Administrador"),
        ("analyst", "Analista"),
        ("reviewer", "Revisor"),
        ("reader", "Lector"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    role = models.CharField(max_length=12, choices=ROLES)


class Scoped(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Company(Scoped):
    name = models.CharField("Razón social", max_length=180)
    rut = models.CharField("RUT", max_length=15, validators=[validate_rut])
    legal_type = models.CharField(
        "Tipo jurídico",
        max_length=50,
        choices=[
            ("Ltda.", "Ltda."),
            ("SpA", "SpA"),
            ("SA", "SA"),
            ("EIRL", "EIRL"),
            ("Otra", "Otra"),
        ],
    )
    tax_regime = models.CharField("Régimen tributario", max_length=150, blank=True)
    income_method = models.CharField(
        "Determinación de renta", max_length=150, blank=True
    )
    professional_company = models.CharField(
        "Sociedad de profesionales", max_length=8, choices=TRI, default="unknown"
    )
    tax_category = models.CharField("Categoría tributaria", max_length=80, blank=True)
    notes = models.TextField("Observaciones", blank=True)

    def clean(self):
        self.rut = normalize_rut(self.rut)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["client", "rut"], name="company_rut_client")
        ]


class Party(Scoped):
    name = models.CharField("Nombre / razón social", max_length=180)
    rut = models.CharField("RUT", max_length=15, validators=[validate_rut])
    kind = models.CharField(
        "Tipo de persona",
        max_length=10,
        choices=[("natural", "Natural"), ("legal", "Jurídica")],
    )
    notes = models.TextField("Observaciones", blank=True)

    def clean(self):
        self.rut = normalize_rut(self.rut)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["client", "rut"], name="party_rut_client")
        ]


class Dated(Scoped):
    valid_from = models.DateField("Vigente desde")
    valid_to = models.DateField("Vigente hasta", null=True, blank=True)

    class Meta:
        abstract = True

    def clean(self):
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError("La fecha final es anterior a la inicial.")


class Ownership(Dated):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Empresa"
    )
    party = models.ForeignKey(Party, on_delete=models.CASCADE, verbose_name="Titular")
    via = models.ForeignKey(
        Party,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="indirect_holdings",
        verbose_name="A través de (vacío = directo)",
    )
    capital = models.DecimalField(
        "Capital %", max_digits=7, decimal_places=4, validators=[percent]
    )
    profits = models.DecimalField(
        "Utilidades %", max_digits=7, decimal_places=4, validators=[percent]
    )
    votes = models.DecimalField(
        "Votos %", max_digits=7, decimal_places=4, validators=[percent]
    )
    share_class = models.CharField("Clase de acciones", max_length=100, blank=True)
    special_rights = models.TextField("Derechos especiales / respaldo", blank=True)

    def __str__(self):
        return f"{self.party} → {self.company}"

    def clean(self):
        super().clean()
        if self.via_id == self.party_id:
            raise ValidationError("El intermediario debe ser distinto del titular.")
        if (
            not self.company_id
            or not self.valid_from
            or any(getattr(self, f) is None for f in ("capital", "profits", "votes"))
        ):
            return
        overlapping = Ownership.objects.filter(
            client_id=self.client_id, company_id=self.company_id, via_id=self.via_id
        ).exclude(pk=self.pk)
        overlapping = overlapping.filter(
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=self.valid_from)
        )
        if self.valid_to:
            overlapping = overlapping.filter(valid_from__lte=self.valid_to)
        if overlapping.filter(
            party_id=self.party_id, share_class=self.share_class
        ).exists():
            raise ValidationError(
                "Participación duplicada para fechas y clase superpuestas."
            )
        if self.via_id:
            return
        # Evaluate actual dated compositions, including future boundaries; no double-counting disjoint holdings.
        rows = list(overlapping)
        dates = {self.valid_from} | {
            r.valid_from
            for r in rows
            if r.valid_from >= self.valid_from
            and (not self.valid_to or r.valid_from <= self.valid_to)
        }
        for day in dates:
            active = [
                r
                for r in rows
                if r.valid_from <= day and (not r.valid_to or r.valid_to >= day)
            ]
            for field in ("capital", "profits", "votes"):
                if getattr(self, field) + sum(getattr(r, field) for r in active) > 100:
                    raise ValidationError(
                        f"La composición directa supera 100% en {field} a {day}."
                    )


class Authority(Dated):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Empresa"
    )
    party = models.ForeignKey(Party, on_delete=models.CASCADE, verbose_name="Persona")
    legal_rep = models.CharField(
        "Representación legal", max_length=8, choices=TRI, default="unknown"
    )
    general_admin = models.CharField(
        "Administración general", max_length=8, choices=TRI, default="unknown"
    )
    exercise = models.CharField(
        "Ejercicio",
        max_length=20,
        choices=[
            ("unknown", "No determinado"),
            ("individual", "Individual"),
            ("joint", "Conjunto"),
            ("indistinct", "Indistinto"),
        ],
        default="unknown",
    )
    hire_fire_pay = models.CharField(
        "Contratar, despedir y fijar remuneraciones",
        max_length=8,
        choices=TRI,
        default="unknown",
    )
    disciplinary = models.CharField(
        "Poder disciplinario", max_length=8, choices=TRI, default="unknown"
    )
    board = models.CharField(
        "Participación en directorio", max_length=8, choices=TRI, default="unknown"
    )
    appoint_remove = models.CharField(
        "Designar / remover administradores",
        max_length=8,
        choices=TRI,
        default="unknown",
    )
    effective_direction = models.CharField(
        "Dirección efectiva", max_length=8, choices=TRI, default="unknown"
    )
    powers = models.TextField(
        "Poderes específicos, delegaciones y evidencia", blank=True
    )

    def __str__(self):
        return f"{self.party} · {self.company}"


class Work(Scoped):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Empresa"
    )
    party = models.ForeignKey(Party, on_delete=models.CASCADE, verbose_name="Persona")
    period = models.DateField("Período (primer día del mes)")
    functions = models.TextField("Funciones y dedicación")
    amount = models.DecimalField(
        "Asignación mensual CLP",
        max_digits=18,
        decimal_places=0,
        default=0,
        validators=[nonnegative],
    )
    pay_setting = models.TextField(
        "Forma de fijación, pago, devengo y contabilización", blank=True
    )
    reports_to = models.CharField("A quién reporta", max_length=180, blank=True)
    effective_work = models.CharField(
        "Trabajo efectivo", max_length=8, choices=TRI, default="unknown"
    )
    instructions = models.CharField(
        "Instrucciones obligatorias", max_length=8, choices=TRI, default="unknown"
    )
    supervision = models.CharField(
        "Control y evaluación", max_length=8, choices=TRI, default="unknown"
    )
    discipline = models.CharField(
        "Sujeción a poder disciplinario", max_length=8, choices=TRI, default="unknown"
    )
    leave = models.CharField(
        "Permisos y vacaciones autorizados",
        max_length=8,
        choices=TRI,
        default="unknown",
    )
    availability = models.CharField(
        "Disponibilidad frente a la empresa",
        max_length=8,
        choices=TRI,
        default="unknown",
    )
    autonomy = models.CharField(
        "Autonomía para aceptar y organizar tareas",
        max_length=8,
        choices=TRI,
        default="unknown",
    )
    contribution_work = models.CharField(
        "Trabajo como aporte societario", max_length=8, choices=TRI, default="unknown"
    )
    discrepancies = models.TextField("Diferencias documentos / realidad", blank=True)
    evidence = models.TextField(
        "Observaciones generales y evidencia (documento y página)", blank=True
    )
    response_evidence = models.JSONField(
        "Evidencia y observaciones por respuesta", default=dict, blank=True
    )
    other_income = models.TextField("Otras actividades y rentas", blank=True)
    reasonableness = models.TextField(
        "Razonabilidad de la asignación y comparables", blank=True
    )
    tax_support = models.TextField(
        "Respaldo IUSC, LRE, DJ 1887 y F22 / aplicabilidad", blank=True
    )

    def clean(self):
        if self.period and self.period.day != 1:
            raise ValidationError("Use el primer día del mes para el período.")
        if self.party_id and self.party.kind != "natural":
            raise ValidationError("La ficha laboral requiere una persona natural.")

    def __str__(self):
        return f"{self.party} · {self.period:%Y-%m} · {self.company}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "company", "party", "period"], name="one_work_period"
            )
        ]


class Source(Dated):
    institution = models.CharField("Institución", max_length=100)
    document = models.CharField("Tipo y número de documento", max_length=180)
    date = models.DateField("Fecha del documento", null=True, blank=True)
    subjects = models.CharField("Materias y artículos", max_length=250)
    summary = models.TextField("Resumen")
    excerpt = models.TextField("Extracto pertinente", blank=True)
    url = models.URLField("URL", max_length=600)
    official = models.BooleanField("Fuente oficial", default=True)
    verified_on = models.DateField("Fecha de verificación", null=True, blank=True)
    status = models.CharField(
        "Validación", max_length=10, choices=VALIDATION, default="pending"
    )
    related = models.TextField(
        "Documentos relacionados / sustituidos y reglas sustentadas", blank=True
    )
    backup = models.FileField(
        "Archivo de respaldo privado (opcional)", upload_to="sources/%Y/%m/", blank=True
    )

    def clean(self):
        from urllib.parse import urlparse

        super().clean()
        parsed = urlparse(self.url)
        if parsed.scheme != "https":
            raise ValidationError("Las fuentes requieren URL HTTPS.")
        host = (parsed.hostname or "").lower()
        official_hosts = [
            "sii.cl",
            "dt.gob.cl",
            "spensiones.cl",
            "suseso.cl",
            "superdesalud.gob.cl",
            "afc.cl",
            "fonasa.cl",
            "bcn.cl",
            "diariooficial.interior.gob.cl",
        ]
        if self.official and not any(
            host == h or host.endswith("." + h) for h in official_hosts
        ):
            raise ValidationError(
                "La URL no pertenece a una institución oficial admitida."
            )
        if self.status == "verified" and (
            not self.official or not self.verified_on or not self.excerpt
        ):
            raise ValidationError(
                "Verificar requiere fuente oficial, fecha y extracto."
            )

    def __str__(self):
        return f"{self.institution} · {self.document}"


class Rule(Dated):
    code = models.CharField("Identificador", max_length=60)
    version = models.PositiveIntegerField("Versión", default=1)
    scope = models.CharField(
        "Ámbito",
        max_length=20,
        choices=[
            ("labor", "Laboral"),
            ("tax", "Tributario"),
            ("pension", "Previsional"),
        ],
    )
    conditions = models.JSONField(
        "Condiciones JSON (all/any, campo y valor)", default=dict
    )
    exceptions = models.JSONField("Excepciones JSON", default=dict, blank=True)
    result = models.CharField("Resultado", max_length=250)
    explanation = models.TextField("Fundamento y hechos que podrían modificarlo")
    sources = models.ManyToManyField(Source, verbose_name="Fuentes")
    status = models.CharField(
        "Validación", max_length=10, choices=VALIDATION, default="pending"
    )

    def clean(self):
        from .engine import validate_condition

        super().clean()
        validate_condition(self.conditions)

        def fields(node):
            if "field" in node:
                return {node["field"]}
            return set().union(
                *(fields(n) for n in node.get("all", node.get("any", [])))
            )

        if self.scope == "labor" and fields(self.conditions) <= {
            "direct_majority",
            "legal_rep",
        }:
            raise ValidationError(
                "La clasificación laboral no puede basarse solo en porcentaje de propiedad o representación legal."
            )
        if self.exceptions:
            validate_condition(self.exceptions)

    def __str__(self):
        return f"{self.code} v{self.version}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "code", "version"], name="unique_rule_version"
            )
        ]


class Parameters(Dated):
    label = models.CharField("Nombre / versión", max_length=150)
    status = models.CharField(
        "Validación", max_length=10, choices=VALIDATION, default="pending"
    )
    data = models.JSONField(
        "Parámetros decimales como texto; esquema en README", default=dict
    )
    sources = models.ManyToManyField(Source, verbose_name="Fuentes")

    def clean(self):
        from .engine import validate_parameters

        super().clean()
        validate_parameters(self.data)

    def __str__(self):
        return self.label


class Contribution(Scoped):
    work = models.ForeignKey(
        Work, on_delete=models.CASCADE, verbose_name="Ficha de persona / período"
    )
    instrument = models.CharField(
        "Instrumento",
        max_length=10,
        choices=[
            ("APV", "APV régimen B"),
            ("APVC", "APVC"),
            ("DC", "Depósito convenido"),
        ],
    )
    institution = models.CharField("Institución", max_length=140)
    channel = models.CharField(
        "Modalidad",
        max_length=12,
        choices=[("payroll", "Planilla"), ("direct", "Directo")],
    )
    date = models.DateField("Fecha del aporte")
    amount = models.DecimalField(
        "Aporte CLP", max_digits=18, decimal_places=0, validators=[nonnegative]
    )

    def clean(self):
        if (
            self.work_id
            and self.date
            and (
                self.date.year != self.work.period.year
                or self.date
                > date(
                    self.work.period.year,
                    self.work.period.month,
                    calendar.monthrange(self.work.period.year, self.work.period.month)[
                        1
                    ],
                )
            )
        ):
            raise ValidationError(
                "El aporte debe pertenecer al año y no ser posterior al período analizado."
            )

    def __str__(self):
        return f"{self.instrument} · {self.institution} · {self.amount}"


class Simulation(Scoped):
    work = models.OneToOneField(
        Work, on_delete=models.CASCADE, verbose_name="Ficha de persona / período"
    )
    category = models.CharField(
        "Calidad para APV",
        max_length=20,
        choices=[
            ("unknown", "No determinada"),
            ("dependent", "Dependiente"),
            ("independent", "Independiente"),
            ("business", "Sueldo empresarial"),
        ],
        default="unknown",
    )
    horizon = models.CharField(
        "Base del cálculo",
        max_length=10,
        choices=[("annual", "Anual"), ("monthly", "Mensual")],
        default="annual",
    )
    income = models.DecimalField(
        "Renta relevante CLP del horizonte (neta de rebajas externas ya utilizadas)",
        max_digits=18,
        decimal_places=0,
        default=0,
        validators=[nonnegative],
    )
    mandatory = models.DecimalField(
        "Cotizaciones deducibles CLP",
        max_digits=18,
        decimal_places=0,
        default=0,
        validators=[nonnegative],
    )
    prior_deductions = models.DecimalField(
        "Rebajas APV externas ya utilizadas en el año CLP (no duplicar aportes del registro)",
        max_digits=18,
        decimal_places=0,
        default=0,
        validators=[nonnegative],
    )
    annual_complete = models.BooleanField(
        "Confirmo aportes y rentas completos del horizonte y todas las instituciones",
        default=False,
    )
    notes = models.TextField(
        "Supuestos, calidad previsional y respaldo de procedencia", blank=True
    )

    def __str__(self):
        return str(self.work)


class Evaluation(Scoped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work = models.ForeignKey(Work, on_delete=models.PROTECT)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    snapshot = models.JSONField()
    digest = models.CharField(max_length=64)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "Las evaluaciones son inmutables. Genere una nueva versión."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.id)


class Branding(Scoped):
    name = models.CharField("Nombre consultora", max_length=160)
    author = models.CharField("Autor del informe", max_length=140)
    reviewer = models.CharField("Revisor", max_length=140, blank=True)
    logo = models.ImageField("Logo PNG/JPEG", upload_to="logos/%Y/%m/", blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["client"], name="one_branding")]


class Document(Scoped):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, verbose_name="Empresa"
    )
    party = models.ForeignKey(
        Party, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Persona"
    )
    title = models.CharField("Título y tipo de respaldo", max_length=180)
    page = models.CharField("Página / cláusula pertinente", max_length=80, blank=True)
    file = models.FileField("Archivo privado", upload_to="documents/%Y/%m/")
    notes = models.TextField("Observaciones", blank=True)

    def __str__(self):
        return self.title


class Audit(Scoped):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80)
    detail = models.JSONField(default=dict)
