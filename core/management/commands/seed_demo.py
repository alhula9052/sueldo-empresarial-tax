import os
import secrets
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from core.models import (
    Client,
    Membership,
    Company,
    Party,
    Ownership,
    Authority,
    Work,
    Simulation,
    Branding,
    Rule,
    Evaluation,
    Audit,
)
from core.engine import build_snapshot, digest


class Command(BaseCommand):
    help = "Crea un espacio ficticio idempotente. Nunca habilita reglas jurídicas ni tasas no verificadas."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("La demostración se habilita solo con DEBUG=1.")
        client, _ = Client.objects.get_or_create(
            name="Consultora Demo · Datos ficticios"
        )
        user, created = get_user_model().objects.get_or_create(username="demo")
        if created:
            password = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(20)
            user.set_password(password)
            user.save()
            # Store a generated password in an ignored local file; never print secrets.
            if not os.environ.get("DEMO_PASSWORD"):
                target = settings.BASE_DIR / ".demo-password"
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write(password + "\n")
        elif not Membership.objects.filter(user=user, client=client).exists():
            raise CommandError(
                "El usuario demo ya existe en otro contexto; no se modifica."
            )
        Membership.objects.get_or_create(
            user=user, defaults={"client": client, "role": "admin"}
        )
        company, _ = Company.objects.get_or_create(
            client=client,
            rut="760000000",
            defaults={
                "name": "Horizonte Consultores Ltda. · FICTICIA",
                "legal_type": "Ltda.",
                "tax_regime": "No determinado · demostración",
                "income_method": "Por verificar",
                "notes": "EJEMPLO FICTICIO. RUT sintético de formato válido, sin afirmar identidad real.",
            },
        )
        ana, _ = Party.objects.get_or_create(
            client=client,
            rut="111111111",
            defaults={"name": "Ana Ejemplo · socia 90%", "kind": "natural"},
        )
        diego, _ = Party.objects.get_or_create(
            client=client,
            rut="222222222",
            defaults={
                "name": "Diego Ejemplo · socio administrador 10%",
                "kind": "natural",
            },
        )
        for party, capital in ((ana, "90"), (diego, "10")):
            Ownership.objects.get_or_create(
                client=client,
                company=company,
                party=party,
                valid_from=date(2026, 1, 1),
                defaults={
                    "capital": capital,
                    "profits": capital,
                    "votes": capital,
                    "special_rights": "Participación ficticia para probar el flujo.",
                },
            )
        for party, admin in ((ana, "no"), (diego, "yes")):
            Authority.objects.get_or_create(
                client=client,
                company=company,
                party=party,
                valid_from=date(2026, 1, 1),
                defaults={
                    "legal_rep": admin,
                    "general_admin": admin,
                    "exercise": "individual",
                    "hire_fire_pay": admin,
                    "disciplinary": admin,
                    "board": "no",
                    "appoint_remove": "unknown",
                    "effective_direction": admin,
                    "powers": "Sin facultades de administración ni representación (Ana). Administración individual (Diego). Ejemplo ficticio; falta escritura real.",
                },
            )
        for month, sub in ((10, "yes"), (11, "no")):
            work, _ = Work.objects.get_or_create(
                client=client,
                company=company,
                party=ana,
                period=date(2026, month, 1),
                defaults={
                    "functions": (
                        "Escenario ficticio CON subordinación: "
                        if sub == "yes"
                        else "Escenario ficticio SIN subordinación: "
                    )
                    + "asesoría técnica, 30 horas semanales. Participación 90% sin administración ni representación.",
                    "amount": "2500000",
                    "reports_to": "Diego Ejemplo",
                    "effective_work": "yes",
                    "instructions": sub,
                    "supervision": sub,
                    "discipline": sub,
                    "leave": sub,
                    "availability": "yes",
                    "autonomy": "no" if sub == "yes" else "yes",
                    "contribution_work": "no",
                    "evidence": "Antecedentes sintéticos para comparar. Ningún documento ni conclusión representan un caso real.",
                    "reasonableness": "Pendiente: obtener comparables y respaldo.",
                },
            )
            Simulation.objects.get_or_create(
                client=client,
                work=work,
                defaults={
                    "income": "30000000",
                    "notes": "Datos ficticios. Calidad previsional, procedencia y parámetros pendientes.",
                },
            )
            if not Evaluation.objects.filter(work=work).exists():
                snapshot = build_snapshot(work)
                ev = Evaluation.objects.create(
                    client=client,
                    work=work,
                    author=user,
                    snapshot=snapshot,
                    digest=digest(snapshot),
                )
                Audit.objects.create(
                    client=client,
                    actor=user,
                    action="crear_demo",
                    model="evaluation",
                    object_id=str(ev.pk),
                    detail={"fictitious": True},
                )
        Branding.objects.get_or_create(
            client=client,
            defaults={
                "name": "Consultora Demo · Ficticia",
                "author": "Equipo de demostración",
                "reviewer": "Pendiente",
            },
        )
        # These are candidate logic structures, NOT verified legal rules.
        proposals = [
            (
                "LAB-DEPENDENCIA",
                {
                    "all": [
                        {"field": "effective_work", "eq": "yes"},
                        {"field": "instructions", "eq": "yes"},
                        {"field": "supervision", "eq": "yes"},
                        {"field": "discipline", "eq": "yes"},
                    ]
                },
                "Indicios suficientes de relación laboral dependiente",
            ),
            (
                "LAB-AUTONOMIA",
                {
                    "all": [
                        {"field": "effective_work", "eq": "yes"},
                        {"field": "autonomy", "eq": "yes"},
                        {"field": "supervision", "eq": "no"},
                        {"field": "discipline", "eq": "no"},
                    ]
                },
                "Indicios de prestación autónoma sin vínculo laboral",
            ),
        ]
        for code, conditions, result in proposals:
            Rule.objects.get_or_create(
                client=client,
                code=code,
                version=1,
                defaults={
                    "scope": "labor",
                    "conditions": conditions,
                    "result": result,
                    "explanation": "Plantilla lógica NO VALIDADA. Contrastar con doctrina oficial, poderes, aporte de trabajo, contradicciones y hechos adicionales. No emite esta conclusión hasta revisión.",
                    "valid_from": date(2026, 1, 1),
                    "status": "pending",
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Demostración lista. Usuario: demo. Contraseña: DEMO_PASSWORD o archivo local .demo-password (no versionado)."
            )
        )
