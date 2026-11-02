"""Synthetic fixtures test software behavior, never establish Chilean legal conclusions."""

import io
from copy import deepcopy
from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import load_workbook, Workbook
from . import models as m
from .engine import (
    match,
    validate_condition,
    validate_parameters,
    build_snapshot,
    digest,
    simulate,
    clp,
)
from .validators import validate_rut
from .importing import COLUMNS, read_upload, mapped_rows, save_rows, preview_rows
from .exports import excel_report, pdf_report, template_workbook, SHEETS
from .forms import form_for


class Base(TestCase):
    def setUp(self):
        self.tenant = m.Client.objects.create(name="Cliente A ficticio")
        self.other = m.Client.objects.create(name="Cliente B ficticio")
        self.user = get_user_model().objects.create_user(
            username="analista", password="Prueba-segura-294!"
        )
        self.membership = m.Membership.objects.create(
            user=self.user, client=self.tenant, role="admin"
        )
        self.company = m.Company.objects.create(
            client=self.tenant,
            name="Empresa ficticia",
            rut="760000000",
            legal_type="Ltda.",
        )
        self.party = m.Party.objects.create(
            client=self.tenant, name="Persona ficticia", rut="111111111", kind="natural"
        )
        self.work = m.Work.objects.create(
            client=self.tenant,
            company=self.company,
            party=self.party,
            period=date(2026, 10, 1),
            functions="Trabajo ficticio",
            amount=2500000,
            effective_work="yes",
        )
        self.client.force_login(self.user)

    def evaluation(self):
        s = build_snapshot(self.work)
        return m.Evaluation.objects.create(
            client=self.tenant,
            work=self.work,
            author=self.user,
            snapshot=s,
            digest=digest(s),
        )

    def source(self, status="verified"):
        return m.Source.objects.create(
            client=self.tenant,
            institution="Fixture de pruebas, NO normativa",
            document="Fixture sintético",
            subjects="Pruebas",
            summary="No constituye fuente jurídica",
            url="https://www.sii.cl/",
            official=True,
            verified_on=date(2026, 1, 1),
            valid_from=date(2026, 1, 1),
            excerpt="Fixture sintético",
            status=status,
        )

    def rule(self, condition, status="verified", scope="labor", code="TEST", **kwargs):
        rule = m.Rule.objects.create(
            client=self.tenant,
            code=code,
            scope=scope,
            conditions=condition,
            status=status,
            version=1,
            valid_from=date(2026, 1, 1),
            result="Resultado sintético de prueba",
            explanation="Fixture, sin significado jurídico",
            **kwargs,
        )
        rule.sources.add(self.source())
        return rule

    def parameters(self):
        # Artificial values exercise arithmetic; they are NOT Chilean rates or limits.
        p = m.Parameters.objects.create(
            client=self.tenant,
            label="Fixture matemático NO NORMATIVO",
            status="verified",
            valid_from=date(2026, 1, 1),
            data={
                "apv": {
                    "dependent": {
                        "eligibility_verified": True,
                        "basis": "Fixture de prueba",
                        "withdrawals": "No normativa",
                        "annual_cap_clp": "1000",
                        "monthly_payroll_cap_clp": "100",
                        "monthly_cap_mode": "fixed_verified",
                        "brackets": {
                            "annual": [
                                {"up_to": None, "rate": "0.10", "deduction": "0"}
                            ],
                            "monthly": [
                                {"up_to": None, "rate": "0.10", "deduction": "0"}
                            ],
                        },
                    }
                },
                "contributions": [],
            },
        )
        p.sources.add(self.source())
        return p

    def simulation(self, **kwargs):
        return m.Simulation.objects.create(
            client=self.tenant,
            work=self.work,
            category="dependent",
            income=10000,
            mandatory=1000,
            annual_complete=True,
            **kwargs,
        )

    def contribution(
        self, amount, channel="direct", instrument="APV", month=10, institution="Prueba"
    ):
        return m.Contribution.objects.create(
            client=self.tenant,
            work=self.work,
            instrument=instrument,
            institution=institution,
            channel=channel,
            date=date(2026, month, 1),
            amount=amount,
        )

    def row(self, **kwargs):
        d = dict(
            zip(
                COLUMNS,
                [
                    "Persona ficticia",
                    "11111111-1",
                    "natural",
                    "90",
                    "90",
                    "90",
                    "",
                    "",
                    "2026-01-01",
                    "",
                    "",
                ],
            )
        )
        d.update(kwargs)
        return d


class ValidationTests(Base):
    def test_rut(self):
        for rut in ("11.111.111-1", "76.000.000-0", "22222222-2"):
            validate_rut(rut)
        for rut in ("11111111-2", "00000000-0", "x"):
            with self.assertRaises(ValidationError):
                validate_rut(rut)

    def test_money_rounding(self):
        self.assertEqual(clp("10.5"), Decimal("11"))
        with self.assertRaises(ValidationError):
            clp(0.1)
        with self.assertRaises(ValidationError):
            clp("NaN")

    def test_import_complete_transaction(self):
        rows = [
            self.row(),
            self.row(
                nombre="Segundo ficticio",
                rut="22222222-2",
                capital="10",
                utilidades="10",
                votos="10",
            ),
        ]
        n, errors = preview_rows(self.tenant, self.company, rows)
        self.assertEqual((n, errors), (2, []))
        self.assertEqual(m.Ownership.objects.count(), 0)
        self.assertEqual(save_rows(self.tenant, self.company, rows), 2)
        self.assertEqual(m.Ownership.objects.count(), 2)

    def test_import_overflow_rollback(self):
        rows = [self.row(), self.row(nombre="Otro", rut="22222222-2", capital="20")]
        with self.assertRaises(ValidationError):
            save_rows(self.tenant, self.company, rows)
        self.assertEqual(m.Ownership.objects.count(), 0)
        self.assertFalse(m.Party.objects.filter(rut="222222222").exists())

    def test_import_duplicates(self):
        with self.assertRaises(ValidationError):
            save_rows(self.tenant, self.company, [self.row(), self.row()])

    def test_import_invalid_date_and_percent(self):
        for kwargs in (
            {"hasta": "2025-01-01"},
            {"capital": "NaN"},
            {"capital": "-1"},
            {"rut": "11111111-2"},
            {"desde": "no fecha"},
            {"capital": "1.12345"},
        ):
            _, errors = preview_rows(self.tenant, self.company, [self.row(**kwargs)])
            self.assertTrue(errors)

    def test_import_mapping(self):
        rows = mapped_rows(
            COLUMNS,
            [list(self.row().values())],
            {k: str(i) for i, k in enumerate(COLUMNS)},
        )
        self.assertEqual(rows[0]["capital"], "90")
        with self.assertRaises(ValidationError):
            mapped_rows(COLUMNS, [], {})

    def test_csv_xlsx(self):
        f = SimpleUploadedFile(
            "test.csv",
            (";".join(COLUMNS) + "\n" + ";".join(self.row().values())).encode(),
        )
        headers, rows = read_upload(f)
        self.assertEqual(headers, COLUMNS)
        self.assertEqual(len(rows), 1)
        x = template_workbook()
        x.name = "test.xlsx"
        h, r = read_upload(x)
        self.assertEqual(h, COLUMNS)
        self.assertEqual(len(r), 2)

    def test_xlsx_formula_rejected(self):
        wb = Workbook()
        wb.active.append(COLUMNS)
        wb.active.append(["=1+1"] + [""] * 10)
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        out.name = "bad.xlsx"
        with self.assertRaises(ValidationError):
            read_upload(out)

    def test_ownership_dates_do_not_double_count(self):
        m.Ownership.objects.create(
            client=self.tenant,
            company=self.company,
            party=self.party,
            capital=100,
            profits=100,
            votes=100,
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 5, 31),
        )
        item = m.Ownership(
            client=self.tenant,
            company=self.company,
            party=self.party,
            capital=100,
            profits=100,
            votes=100,
            valid_from=date(2026, 6, 1),
        )
        item.full_clean()
        item.valid_from = date(2026, 5, 31)
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_period_first_day(self):
        self.work.period = date(2026, 10, 2)
        with self.assertRaises(ValidationError):
            self.work.full_clean()

    def test_contribution_month_end(self):
        c = self.contribution(1)
        c.date = date(2026, 11, 1)
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_unofficial_cannot_verify(self):
        source = self.source()
        source.official = False
        with self.assertRaises(ValidationError):
            source.full_clean()
        source.official = True
        source.url = "https://example.com/"
        with self.assertRaises(ValidationError):
            source.full_clean()


class EngineTests(Base):
    def test_unknown_not_false(self):
        self.assertIsNone(
            match({"field": "instructions", "eq": "no"}, {"instructions": "unknown"})
        )
        self.assertFalse(
            match(
                {
                    "all": [
                        {"field": "instructions", "eq": "yes"},
                        {"field": "supervision", "eq": "yes"},
                    ]
                },
                {"instructions": "unknown", "supervision": "no"},
            )
        )

    def test_condition_syntax(self):
        for node in (
            {},
            {"field": "capital", "eq": "yes"},
            {"field": "instructions", "eq": "unknown"},
            {"all": []},
        ):
            with self.assertRaises(ValidationError):
                validate_condition(node)

    def test_rule_not_verified_blocks(self):
        self.rule({"field": "effective_work", "eq": "yes"}, status="pending")
        result = build_snapshot(self.work)["results"][0]
        self.assertFalse(result["matched"])
        self.assertEqual(len(result["blocked"]), 1)

    def test_unverified_source_blocks(self):
        rule = self.rule({"field": "effective_work", "eq": "yes"})
        rule.sources.update(status="pending")
        self.assertFalse(build_snapshot(self.work)["results"][0]["matched"])

    def test_version_expiry(self):
        rule = self.rule({"field": "effective_work", "eq": "yes"})
        self.assertEqual(len(build_snapshot(self.work)["results"][0]["matched"]), 1)
        rule.valid_to = date(2026, 9, 30)
        rule.save()
        self.assertFalse(build_snapshot(self.work)["results"][0]["matched"])

    def test_unknown_exception_blocks(self):
        self.rule(
            {"field": "effective_work", "eq": "yes"},
            exceptions={"field": "contribution_work", "eq": "yes"},
        )
        self.assertFalse(build_snapshot(self.work)["results"][0]["matched"])

    def test_concurrent_versions_block(self):
        rule = self.rule({"field": "effective_work", "eq": "yes"})
        second = m.Rule.objects.create(
            client=self.tenant,
            code="TEST",
            scope="labor",
            conditions=rule.conditions,
            status="verified",
            version=2,
            valid_from=date(2026, 1, 1),
            result="Otra versión",
            explanation="fixture",
        )
        second.sources.set(rule.sources.all())
        self.assertFalse(build_snapshot(self.work)["results"][0]["matched"])

    def test_dimensions_separate(self):
        self.rule({"field": "effective_work", "eq": "yes"})
        results = build_snapshot(self.work)["results"]
        self.assertTrue(results[0]["matched"])
        self.assertFalse(results[1]["matched"])
        self.assertFalse(results[2]["matched"])

    def test_percentages_never_decide_labor(self):
        for percent in (10, 50, 90):
            m.Ownership.objects.all().delete()
            m.Ownership.objects.create(
                client=self.tenant,
                company=self.company,
                party=self.party,
                capital=percent,
                profits=percent,
                votes=percent,
                valid_from=date(2026, 1, 1),
            )
            self.assertFalse(build_snapshot(self.work)["results"][0]["matched"])

    def test_indirect_not_direct(self):
        via = m.Party.objects.create(
            client=self.tenant, name="Holding ficticio", rut="222222222", kind="legal"
        )
        m.Ownership.objects.create(
            client=self.tenant,
            company=self.company,
            party=self.party,
            via=via,
            capital=90,
            profits=90,
            votes=90,
            valid_from=date(2026, 1, 1),
        )
        self.assertEqual(
            build_snapshot(self.work)["facts"]["direct_majority"], "unknown"
        )

    def test_joint_administration_not_automatic(self):
        m.Authority.objects.create(
            client=self.tenant,
            company=self.company,
            party=self.party,
            valid_from=date(2026, 1, 1),
            general_admin="yes",
            exercise="joint",
        )
        s = build_snapshot(self.work)
        self.assertEqual(s["facts"]["joint_admin"], "yes")
        self.assertFalse(s["results"][0]["matched"])

    def test_no_work_blocks_dependency_candidate(self):
        self.rule({"field": "effective_work", "eq": "yes"})
        self.work.effective_work = "no"
        self.work.save()
        self.assertFalse(build_snapshot(self.work)["results"][0]["matched"])

    def test_with_without_subordination_are_distinct(self):
        cond = {
            "all": [
                {"field": "instructions", "eq": "yes"},
                {"field": "supervision", "eq": "yes"},
                {"field": "discipline", "eq": "yes"},
            ]
        }
        self.rule(cond)
        self.work.instructions = self.work.supervision = self.work.discipline = "yes"
        self.work.save()
        self.assertTrue(build_snapshot(self.work)["results"][0]["matched"])
        self.work.instructions = self.work.supervision = self.work.discipline = "no"
        self.work.save()
        self.assertFalse(build_snapshot(self.work)["results"][0]["matched"])

    def test_contradictions(self):
        self.work.discrepancies = "Contrato y realidad no coinciden"
        self.work.save()
        self.rule({"field": "effective_work", "eq": "yes"})
        self.assertIn(
            "contradictorios", build_snapshot(self.work)["results"][0]["status"]
        )

    def test_snapshot_immutable(self):
        ev = self.evaluation()
        before = deepcopy(ev.snapshot)
        self.work.functions = "Cambio"
        self.work.save()
        ev.refresh_from_db()
        self.assertEqual(ev.snapshot, before)
        self.assertEqual(ev.digest, digest(before))
        with self.assertRaises(ValidationError):
            ev.save()


class APVTests(Base):
    def test_missing_parameters_blocks(self):
        self.simulation()
        self.contribution(400)
        sim = simulate(self.work, None)
        self.assertIsNone(sim["saving"])
        self.assertIsNone(sim["deduction"])

    def test_accumulate_institutions_caps_and_excess(self):
        p = self.parameters()
        self.simulation()
        self.contribution(150, "payroll", institution="A")
        self.contribution(120, "payroll", institution="B")
        self.contribution(1000)
        result = simulate(self.work, p)
        self.assertEqual(result["deduction"], "1000")
        self.assertEqual(result["excess"], "270")
        self.assertEqual(result["saving"], "100")
        self.assertEqual(result["tax_before"], "900")
        self.assertEqual(result["tax_after"], "800")

    def test_monthly_direct_not_deducted(self):
        p = self.parameters()
        self.simulation(horizon="monthly")
        self.contribution(150, "payroll")
        self.contribution(500)
        result = simulate(self.work, p)
        self.assertEqual(result["deduction"], "100")
        self.assertEqual(result["excess"], "50")

    def test_prior_annual_deductions(self):
        p = self.parameters()
        self.simulation(prior_deductions=950)
        self.contribution(1000)
        self.assertEqual(simulate(self.work, p)["deduction"], "50")

    def test_other_instruments_excluded(self):
        p = self.parameters()
        self.simulation()
        self.contribution(1000, instrument="DC")
        self.contribution(1000, instrument="APVC")
        self.assertIsNone(simulate(self.work, p)["deduction"])
        p.data["apv"]["dependent"]["coordination"] = {
            "DC": "excluded_verified",
            "APVC": "consume_cap_only",
        }
        self.assertEqual(simulate(self.work, p)["deduction"], "0")

    def test_quality_never_transferred(self):
        p = self.parameters()
        sim = self.simulation()
        sim.category = "business"
        sim.save()
        self.contribution(1000)
        self.assertIsNone(simulate(self.work, p)["saving"])

    def test_incomplete_data_blocks(self):
        p = self.parameters()
        sim = self.simulation()
        sim.annual_complete = False
        sim.save()
        self.assertIsNone(simulate(self.work, p)["saving"])

    def test_overlapping_parameters_blocks(self):
        self.parameters()
        self.parameters()
        snapshot = build_snapshot(self.work)
        self.assertIsNone(snapshot["parameters"])

    def test_parameter_validation(self):
        for data in (
            {"uf": 1.2},
            {"utm": "-1"},
            {"apv": {"bad": {}}},
            {
                "apv": {
                    "dependent": {
                        "brackets": {
                            "annual": [{"up_to": "1", "rate": "2", "deduction": "0"}]
                        }
                    }
                }
            },
        ):
            with self.assertRaises(ValidationError):
                validate_parameters(data)

    def test_other_company_apv_aggregated(self):
        # See documentation: aggregate all the person's institutions/companies in an annual ledger.
        p = self.parameters()
        self.simulation()
        self.contribution(400)
        company = m.Company.objects.create(
            client=self.tenant,
            name="Segunda empresa ficticia",
            rut="222222222",
            legal_type="SpA",
        )
        work = m.Work.objects.create(
            client=self.tenant,
            company=company,
            party=self.party,
            period=date(2026, 9, 1),
            functions="Otro trabajo",
        )
        m.Contribution.objects.create(
            client=self.tenant,
            work=work,
            instrument="APV",
            institution="Otra",
            channel="direct",
            date=date(2026, 9, 1),
            amount=700,
        )
        self.assertEqual(simulate(self.work, p)["deduction"], "1000")


class AccessTests(Base):
    def test_all_screens_render(self):
        for url in [
            "/",
            "/importar/",
            "/exportaciones/",
            "/equipo/",
            "/auditoria/",
            f"/casos/{self.work.pk}/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        from .forms import REGISTRY

        for kind in REGISTRY:
            with self.subTest(kind=kind):
                self.assertEqual(
                    self.client.get("/registros/" + kind + "/").status_code, 200
                )
                self.assertEqual(
                    self.client.get("/registros/" + kind + "/nuevo/").status_code, 200
                )

    def test_anonymous_redirect(self):
        self.client.logout()
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_cross_client_records(self):
        company = m.Company.objects.create(
            client=self.other, name="Secreto B", rut="760000000", legal_type="Ltda."
        )
        self.assertEqual(
            self.client.get(f"/registros/empresas/{company.pk}/").status_code, 404
        )
        self.assertNotContains(self.client.get("/registros/empresas/"), "Secreto B")
        form = form_for(m.Work)(client=self.tenant)
        self.assertNotIn(company, list(form.fields["company"].queryset))

    def test_cross_client_evaluation_export(self):
        ev = self.evaluation()
        ev.client = self.other
        m.Evaluation.objects.filter(pk=ev.pk).update(client=self.other)
        self.assertEqual(
            self.client.get(reverse("evaluation", args=[ev.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.post(
                "/exportar/", {"evaluations": [str(ev.pk)], "format": "xlsx"}
            ).status_code,
            404,
        )

    def test_cross_client_document(self):
        doc = m.Document.objects.create(
            client=self.other, company=self.company, title="Privado", file="fake.pdf"
        )
        self.assertEqual(
            self.client.get(f"/documentos/{doc.pk}/descargar/").status_code, 404
        )

    def test_roles(self):
        for role in ("reader", "analyst", "reviewer"):
            self.membership.role = role
            self.membership.save()
            self.assertEqual(
                self.client.post(
                    f"/registros/empresas/{self.company.pk}/eliminar/"
                ).status_code,
                403,
            )
            self.assertEqual(self.client.get("/equipo/").status_code, 403)
            self.assertEqual(
                self.client.get("/registros/reglas/nuevo/").status_code,
                200 if role == "reviewer" else 403,
            )
            self.assertEqual(
                self.client.post(f"/casos/{self.work.pk}/evaluar/").status_code,
                403 if role == "reader" else 302,
            )

    def test_export_and_audit(self):
        ev = self.evaluation()
        for fmt, magic in (("pdf", b"%PDF"), ("xlsx", b"PK")):
            response = self.client.post(
                "/exportar/", {"evaluations": [str(ev.pk)], "format": fmt}
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(b"".join(response.streaming_content).startswith(magic))
        self.assertEqual(
            m.Audit.objects.filter(action__startswith="exportar").count(), 2
        )

    def test_csrf(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(
            client.post(f"/casos/{self.work.pk}/evaluar/").status_code, 403
        )

    def test_integrity_check(self):
        ev = self.evaluation()
        m.Evaluation.objects.filter(pk=ev.pk).update(digest="tampered")
        self.assertEqual(
            self.client.post(
                "/exportar/", {"evaluations": [str(ev.pk)], "format": "pdf"}
            ).status_code,
            409,
        )

    def test_invalid_filters_and_ids(self):
        self.assertEqual(self.client.get("/?company=abc").status_code, 400)
        self.assertEqual(
            self.client.post("/exportar/", {"evaluations": ["bad"]}).status_code, 404
        )

    def test_private_cache_headers(self):
        self.assertEqual(self.client.get("/")["Cache-Control"], "private, no-store")

    def test_create_and_audit(self):
        response = self.client.post(
            "/registros/personas/nuevo/",
            {
                "name": "Nuevo ficticio",
                "rut": "22.222.222-2",
                "kind": "natural",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(m.Audit.objects.filter(action="crear", model="party").exists())

    def test_import_ui(self):
        csv = (";".join(COLUMNS) + "\n" + ";".join(self.row().values())).encode()
        response = self.client.post(
            "/importar/",
            {
                "stage": "upload",
                "company": self.company.pk,
                "file": SimpleUploadedFile("test.csv", csv),
            },
        )
        self.assertContains(response, "Mapeo de columnas")
        response = self.client.post(
            "/importar/",
            {"stage": "mapping", **{"map_" + k: str(i) for i, k in enumerate(COLUMNS)}},
        )
        self.assertContains(response, "Confirmar 1 participaciones")
        response = self.client.post("/importar/", {"stage": "confirm"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(m.Ownership.objects.count(), 1)

    def test_malformed_xlsx_ui(self):
        response = self.client.post(
            "/importar/",
            {
                "stage": "upload",
                "company": self.company.pk,
                "file": SimpleUploadedFile("test.xlsx", b"not a zip"),
            },
        )
        self.assertContains(response, "dañado")


class ExportTests(Base):
    def test_real_xlsx_tabs_filters_and_numeric_values(self):
        self.simulation()
        self.parameters()
        self.contribution(400)
        ev = self.evaluation()
        wb = load_workbook(excel_report([ev]))
        self.assertEqual(wb.sheetnames, SHEETS)
        for sheet in wb:
            self.assertEqual(sheet.freeze_panes, "A2")
        self.assertEqual(wb["APV régimen B"]["F2"].value, 400)
        self.assertEqual(wb["APV régimen B"]["L2"].value, 40)
        self.assertEqual(wb["APV régimen B"]["M2"].value, "=J2-K2")
        self.assertEqual(ev.snapshot["simulation"]["saving"], "40")

    def test_formula_injection_is_literal_string(self):
        self.company.name = '=HYPERLINK("https://evil.invalid","X")'
        self.company.save()
        self.party.name = "@SUM(1+1)"
        self.party.save()
        ev = self.evaluation()
        wb = load_workbook(excel_report([ev]))
        self.assertEqual(wb["Empresas"]["B2"].data_type, "s")
        self.assertEqual(wb["Resumen ejecutivo"]["C2"].data_type, "s")

    def test_pdf_real_and_multiple_people(self):
        ev = self.evaluation()
        output = pdf_report([ev, ev], complete=True)
        self.assertTrue(output.getvalue().startswith(b"%PDF"))
        self.assertGreater(len(output.getvalue()), 10000)

    def test_historical_export_uses_snapshot(self):
        ev = self.evaluation()
        self.company.name = "Nombre actualizado"
        self.company.save()
        wb = load_workbook(excel_report([ev]))
        self.assertEqual(wb["Empresas"]["B2"].value, "Empresa ficticia")


class AdditionalGuardsTests(Base):
    def test_property_or_representation_alone_not_labor_rule(self):
        for field in ("direct_majority", "legal_rep"):
            rule = m.Rule(
                client=self.tenant,
                code="ONLY-" + field,
                version=1,
                scope="labor",
                conditions={"field": field, "eq": "yes"},
                result="Prohibido",
                explanation="Fixture",
                valid_from=date(2026, 1, 1),
            )
            with self.assertRaises(ValidationError):
                rule.clean()

    def test_malformed_parameter_shapes_rejected(self):
        for value in (
            {"apv": []},
            {"apv": {"dependent": []}},
            {"contributions": [{}]},
            {"contributions": {}},
            {"apv": {"dependent": {"monthly_payroll_caps_clp": {"99": "100"}}}},
        ):
            with self.assertRaises(ValidationError):
                validate_parameters(value)

    def test_month_specific_payroll_caps(self):
        p = self.parameters()
        cfg = p.data["apv"]["dependent"]
        cfg.pop("monthly_cap_mode")
        cfg["monthly_payroll_caps_clp"] = {"9": "50", "10": "80"}
        self.simulation()
        self.contribution(100, "payroll", month=9)
        self.contribution(100, "payroll", month=10)
        self.assertEqual(simulate(self.work, p)["deduction"], "130")
        cfg["monthly_payroll_caps_clp"].pop("9")
        self.assertIsNone(simulate(self.work, p)["deduction"])

    def test_last_admin_cannot_be_disabled(self):
        response = self.client.post(
            f"/equipo/{self.membership.pk}/", {"role": "reader"}
        )
        self.assertEqual(response.status_code, 302)
        self.membership.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.membership.role, "admin")
        self.assertTrue(self.user.is_active)

    def test_cannot_manage_other_tenant_member(self):
        user = get_user_model().objects.create_user("otro")
        other = m.Membership.objects.create(user=user, client=self.other, role="admin")
        self.assertEqual(
            self.client.post(f"/equipo/{other.pk}/", {"role": "reader"}).status_code,
            404,
        )

    def test_large_text_xlsx_not_silently_lost(self):
        ev = self.evaluation()
        ev.snapshot["work"]["functions"] = "A" * 65000
        wb = load_workbook(excel_report([ev]))
        self.assertIn("Textos extensos", wb.sheetnames)
        self.assertEqual(
            sum(len(r[2].value) for r in list(wb["Textos extensos"].rows)[1:]), 65000
        )

    def test_sources_backup_is_private(self):
        source = self.source()
        source.client = self.other
        source.backup = "fixture.pdf"
        source.save()
        self.assertEqual(
            self.client.get(f"/normativa/{source.pk}/respaldo/").status_code, 404
        )

    def test_work_response_evidence_saved(self):
        data = {
            "company": self.company.pk,
            "party": self.party.pk,
            "period": "2026-10-01",
            "functions": "Trabajo ficticio",
            "amount": "1000",
        }
        for key in (
            "effective_work",
            "instructions",
            "supervision",
            "discipline",
            "leave",
            "availability",
            "autonomy",
            "contribution_work",
        ):
            data[key] = "unknown"
            data[key + "_evidence"] = "Documento de prueba, página 2"
        form = form_for(m.Work)(data, instance=self.work, client=self.tenant)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.work.refresh_from_db()
        self.assertEqual(
            self.work.response_evidence["instructions"], "Documento de prueba, página 2"
        )


class InvalidInputTests(Base):
    def test_all_empty_forms_show_errors(self):
        from .forms import REGISTRY

        for kind in REGISTRY:
            with self.subTest(kind=kind):
                self.assertEqual(
                    self.client.post("/registros/" + kind + "/nuevo/", {}).status_code,
                    200,
                )

    def test_ownership_invalid_dates_and_percent_do_not_crash(self):
        data = {
            "company": self.company.pk,
            "party": self.party.pk,
            "capital": "90",
            "profits": "90",
            "votes": "90",
            "valid_from": "invalid",
            "valid_to": "2026-11-01",
        }
        self.assertEqual(
            self.client.post("/registros/composicion/nuevo/", data).status_code, 200
        )
        data.update(valid_from="2026-01-01", capital="not a number")
        self.assertEqual(
            self.client.post("/registros/composicion/nuevo/", data).status_code, 200
        )

    def test_invalid_contribution_date_does_not_crash(self):
        self.assertEqual(
            self.client.post(
                "/registros/aportes/nuevo/",
                {
                    "work": self.work.pk,
                    "instrument": "APV",
                    "institution": "Prueba",
                    "channel": "direct",
                    "date": "invalid",
                    "amount": "100",
                },
            ).status_code,
            200,
        )

    def test_pdf_long_table_cells_split(self):
        ev = self.evaluation()
        ev.snapshot["contributions"][0]["requirements"] = (
            "Requisito sintético de prueba. " * 180
        )
        self.assertTrue(pdf_report([ev]).getvalue().startswith(b"%PDF"))


class DeploymentTests(TestCase):
    def test_pythonanywhere_host_validation(self):
        from deploy.runtime import validate_host

        for host in ("cuenta.pythonanywhere.com", "cuenta.eu.pythonanywhere.com"):
            self.assertEqual(validate_host(host), host)
        for host in (
            "*",
            "https://cuenta.pythonanywhere.com",
            "cuenta.pythonanywhere.com/",
            "evil.com",
            "user.pythonanywhere.com.evil.com",
            "user.pythonanywhere.com:443",
        ):
            with self.assertRaises(ValueError):
                validate_host(host)

    def test_host_configuration_is_repeatable_and_private(self):
        import tempfile
        from pathlib import Path
        from deploy.runtime import initialize

        with tempfile.TemporaryDirectory() as folder:
            first = initialize(folder, "cuenta.pythonanywhere.com")
            second = initialize(folder, "cuenta.pythonanywhere.com")
            self.assertEqual(first, second)
            self.assertEqual(first["DEBUG"], "0")
            self.assertEqual(first["SECURE_SSL_REDIRECT"], "1")
            self.assertTrue(len(first["DJANGO_SECRET_KEY"]) >= 50)
            self.assertEqual(
                (Path(folder) / ".runtime/django-secret").stat().st_mode & 0o777, 0o600
            )
            self.assertEqual(first["ALLOWED_HOSTS"], "cuenta.pythonanywhere.com")
            with self.assertRaises(ValueError):
                initialize(folder, "otra.pythonanywhere.com")

    def test_corrupted_secret_not_silently_replaced(self):
        import tempfile
        from pathlib import Path
        from deploy.runtime import initialize

        with tempfile.TemporaryDirectory() as folder:
            initialize(folder, "cuenta.pythonanywhere.com")
            secret = Path(folder) / ".runtime/django-secret"
            secret.write_text("invalid")
            with self.assertRaises(ValueError):
                initialize(folder, "cuenta.pythonanywhere.com")
            self.assertEqual(secret.read_text(), "invalid")

    def test_distribution_does_not_include_server_secrets(self):
        import tempfile
        from pathlib import Path
        from zipfile import ZipFile
        from scripts.package_local import build_package

        with tempfile.TemporaryDirectory() as folder:
            path = build_package(Path(folder) / "nexo.zip")
            with ZipFile(path) as archive:
                names = archive.namelist()
                self.assertIn("nexo/deploy/pythonanywhere_wsgi.py", names)
                self.assertIn("nexo/scripts/setup_pythonanywhere.py", names)
                self.assertFalse(
                    any(
                        "/.runtime/" in n
                        or "/.demo-password" in n
                        or n.endswith(".sqlite3")
                        for n in names
                    )
                )
