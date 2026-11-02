import uuid
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_POST
from . import models as m
from .forms import REGISTRY, form_for, TeamForm, UploadForm
from .engine import build_snapshot, digest
from .importing import read_upload, mapped_rows, preview_rows, save_rows, COLUMNS

WRITE = {"admin", "analyst", "reviewer"}
REVIEW = {"admin", "reviewer"}


def member(request):
    try:
        return request.user.membership
    except m.Membership.DoesNotExist:
        raise PermissionDenied("Usuario sin cliente asignado.")


def permit(request, roles):
    membership = member(request)
    if membership.role not in roles:
        raise PermissionDenied("Su rol no permite esta acción.")
    return membership


def audit(request, action, obj, detail=None):
    m.Audit.objects.create(
        client=member(request).client,
        actor=request.user,
        action=action,
        model=obj._meta.model_name,
        object_id=str(obj.pk),
        detail=detail or {},
    )


def require_kind(kind):
    if kind not in REGISTRY:
        raise Http404
    return REGISTRY[kind]


@login_required
def dashboard(request):
    client = member(request).client
    works = m.Work.objects.filter(client=client).select_related("company", "party")
    query = request.GET.get("q", "").strip()
    if query:
        works = works.filter(
            Q(company__name__icontains=query) | Q(party__name__icontains=query)
        )
    if request.GET.get("company"):
        if not request.GET["company"].isdigit():
            return HttpResponse("Empresa inválida.", status=400)
        works = works.filter(company_id=request.GET["company"])
    if request.GET.get("period"):
        try:
            works = works.filter(
                period=date.fromisoformat(request.GET["period"] + "-01")
            )
        except ValueError:
            messages.error(request, "Período inválido.")
    cards = []
    for work in works[:100]:
        latest = (
            m.Evaluation.objects.filter(work=work, client=client)
            .order_by("-created_at")
            .first()
        )
        cards.append(
            {
                "work": work,
                "latest": latest,
                "status": latest.snapshot["results"][0]["status"]
                if latest
                else "Sin evaluar · completar antecedentes",
                "pending": len(latest.snapshot["pending"]) if latest else 1,
            }
        )
    return render(
        request,
        "core/dashboard.html",
        dict(
            cards=cards,
            companies=m.Company.objects.filter(client=client),
            company_count=m.Company.objects.filter(client=client).count(),
            party_count=m.Party.objects.filter(client=client).count(),
            evaluation_count=m.Evaluation.objects.filter(client=client).count(),
            pending_count=sum(c["pending"] > 0 for c in cards),
        ),
    )


@login_required
def listing(request, kind):
    model, title = require_kind(kind)
    client = member(request).client
    objects = model.objects.filter(client=client).order_by("-pk")
    q = request.GET.get("q", "")
    text_fields = [
        f.name
        for f in model._meta.fields
        if f.get_internal_type() in ("CharField", "TextField")
    ]
    if q and text_fields:
        query = Q()
        for field in text_fields:
            query |= Q(**{field + "__icontains": q})
        objects = objects.filter(query)
    if kind == "normativa":
        if request.GET.get("official") in ("yes", "no"):
            objects = objects.filter(official=request.GET["official"] == "yes")
        if request.GET.get("status") in ("pending", "verified", "retired"):
            objects = objects.filter(status=request.GET["status"])
        if request.GET.get("institution"):
            objects = objects.filter(institution__icontains=request.GET["institution"])
    fields = [
        f for f in model._meta.fields if f.name not in ("id", "client", "created_at")
    ][:7]
    rows = []
    for obj in objects[:200]:
        cells = []
        for field in fields:
            display = getattr(obj, "get_" + field.name + "_display", None)
            value = display() if display else getattr(obj, field.name)
            cells.append(str(value)[:180] if value is not None else "—")
        rows.append((obj, cells))
    diagram = []
    if kind == "composicion":
        for obj in objects.select_related("company", "party", "via")[:100]:
            diagram.append(obj)
    return render(
        request,
        "core/list.html",
        dict(
            kind=kind,
            title=title,
            fields=fields,
            rows=rows,
            diagram=diagram,
            write=member(request).role in WRITE,
        ),
    )


@login_required
def edit(request, kind, pk=None):
    model, title = require_kind(kind)
    membership = permit(
        request, REVIEW if kind in ("reglas", "parametros", "normativa") else WRITE
    )
    obj = (
        get_object_or_404(model, pk=pk, client=membership.client)
        if pk
        else model(client=membership.client)
    )
    # Never modify existing objects referenced in historical snapshots by ID alone; snapshots include complete values.
    form = form_for(model)(
        request.POST or None,
        request.FILES or None,
        instance=obj,
        client=membership.client,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            saved = form.save()
            audit(
                request,
                "actualizar" if pk else "crear",
                saved,
                {"fields": form.changed_data},
            )
        messages.success(
            request,
            "Registro guardado. Las evaluaciones anteriores conservan sus datos originales.",
        )
        return redirect("listing", kind=kind)
    return render(
        request,
        "core/form.html",
        dict(form=form, title=("Editar " if pk else "Registrar ") + title, kind=kind),
    )


@login_required
@require_POST
def delete(request, kind, pk):
    model, _ = require_kind(kind)
    membership = permit(request, {"admin"})
    obj = get_object_or_404(model, pk=pk, client=membership.client)
    if model in (m.Source, m.Rule, m.Parameters):
        raise PermissionDenied(
            "Para preservar trazabilidad, retire la versión o fuente mediante su estado; no se permite eliminarla."
        )
    from django.db.models.deletion import ProtectedError

    try:
        with transaction.atomic():
            audit(request, "eliminar", obj)
            # Revoke a document by deleting its record; inaccessible binary retention is handled by documented maintenance.
            obj.delete()
        messages.success(
            request, "Registro eliminado. Los respaldos históricos no se sobrescriben."
        )
    except ProtectedError:
        messages.error(
            request, "El registro está protegido por una evaluación. No se eliminó."
        )
    return redirect("listing", kind=kind)


@login_required
def case(request, pk):
    client = member(request).client
    work = get_object_or_404(m.Work, pk=pk, client=client)
    evaluations = m.Evaluation.objects.filter(client=client, work=work).order_by(
        "-created_at"
    )
    return render(
        request,
        "core/case.html",
        dict(work=work, snapshot=build_snapshot(work), evaluations=evaluations),
    )


@login_required
@require_POST
def evaluate(request, pk):
    membership = permit(request, WRITE)
    work = get_object_or_404(m.Work, pk=pk, client=membership.client)
    with transaction.atomic():
        snapshot = build_snapshot(work)
        ev = m.Evaluation.objects.create(
            client=membership.client,
            work=work,
            author=request.user,
            snapshot=snapshot,
            digest=digest(snapshot),
        )
        audit(request, "evaluar", ev, {"digest": ev.digest})
    return redirect("evaluation", pk=ev.pk)


@login_required
def evaluation(request, pk):
    ev = get_object_or_404(m.Evaluation, pk=pk, client=member(request).client)
    return render(request, "core/evaluation.html", dict(ev=ev, snapshot=ev.snapshot))


@login_required
def download_document(request, pk):
    doc = get_object_or_404(m.Document, pk=pk, client=member(request).client)
    audit(request, "descargar_documento", doc)
    try:
        return FileResponse(
            doc.file.open("rb"),
            as_attachment=True,
            filename=doc.file.name.rsplit("/", 1)[-1],
            content_type="application/octet-stream",
        )
    except FileNotFoundError:
        raise Http404("Archivo no disponible.")


@login_required
def audit_log(request):
    permit(request, REVIEW)
    return render(
        request,
        "core/audit.html",
        dict(
            logs=m.Audit.objects.filter(client=member(request).client)
            .select_related("actor")
            .order_by("-created_at")[:300]
        ),
    )


@login_required
def team(request):
    membership = permit(request, {"admin"})
    form = TeamForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            entry = m.Membership.objects.create(
                user=user, client=membership.client, role=form.cleaned_data["role"]
            )
            audit(request, "crear_usuario", entry, {"role": entry.role})
        messages.success(
            request, "Usuario creado. Comparta la contraseña por un canal seguro."
        )
        return redirect("team")
    return render(
        request,
        "core/team.html",
        dict(
            form=form,
            team=m.Membership.objects.filter(client=membership.client).select_related(
                "user"
            ),
        ),
    )


@login_required
def import_ownership(request):
    membership = permit(request, WRITE)
    client = membership.client
    stage = request.POST.get("stage", "upload")
    if request.method == "POST" and stage == "upload":
        request.session.pop("import_validated", None)
        request.session.pop("import_data", None)
    form = UploadForm(request.POST or None, request.FILES or None, client=client)
    context = {"title": "Importar composición", "form": form, "columns": COLUMNS}
    try:
        if request.method == "POST" and stage == "upload" and form.is_valid():
            headers, rows = read_upload(form.cleaned_data["file"])
            request.session["import_data"] = {
                "company": form.cleaned_data["company"].pk,
                "headers": headers,
                "rows": rows,
            }
            context.update(
                stage="mapping", headers=list(enumerate(headers)), sample=rows[:5]
            )
        elif request.method == "POST" and stage in ("mapping", "confirm"):
            payload = request.session.get("import_data")
            if not payload:
                raise ValidationError(
                    "La importación expiró; cargue el archivo nuevamente."
                )
            company = get_object_or_404(m.Company, pk=payload["company"], client=client)
            if stage == "mapping":
                mapping = {k: request.POST.get("map_" + k, "") for k in COLUMNS}
                rows = mapped_rows(payload["headers"], payload["rows"], mapping)
                count, errors = preview_rows(client, company, rows)
                if not errors:
                    request.session["import_validated"] = rows
                else:
                    request.session.pop("import_validated", None)
                context.update(
                    stage="preview",
                    rows=rows[:100],
                    count=count,
                    errors=errors,
                    total=len(rows),
                )
            else:
                rows = request.session.get("import_validated")
                if not rows:
                    raise ValidationError("Valide el archivo antes de confirmar.")
                with transaction.atomic():
                    count = save_rows(client, company, rows)
                    audit(request, "importar_composicion", company, {"rows": count})
                request.session.pop("import_data", None)
                request.session.pop("import_validated", None)
                messages.success(request, f"{count} participaciones importadas.")
                return redirect("listing", kind="composicion")
    except (ValidationError, UnicodeError, ValueError, KeyError) as e:
        messages.error(
            request,
            "; ".join(e.messages)
            if isinstance(e, ValidationError)
            else "Archivo o mapeo inválido.",
        )
    except (
        BadZipFile,
        ParseError,
    ):
        messages.error(
            request, "El archivo Excel está dañado o no tiene el formato correcto."
        )
    return render(request, "core/import.html", context)


@login_required
def import_template(request):
    from .exports import template_workbook

    return FileResponse(
        template_workbook(), as_attachment=True, filename="plantilla-composicion.xlsx"
    )


@login_required
def exports(request):
    client = member(request).client
    query = (
        m.Evaluation.objects.filter(client=client)
        .select_related("work__company", "work__party")
        .order_by("-created_at")
    )
    if request.GET.get("company"):
        if not request.GET["company"].isdigit():
            return HttpResponse("Empresa inválida.", status=400)
        query = query.filter(work__company_id=request.GET["company"])
    if request.GET.get("person"):
        if not request.GET["person"].isdigit():
            return HttpResponse("Persona inválida.", status=400)
        query = query.filter(work__party_id=request.GET["person"])
    if request.GET.get("period"):
        try:
            query = query.filter(
                work__period=date.fromisoformat(request.GET["period"] + "-01")
            )
        except ValueError:
            messages.error(request, "Período inválido.")
    return render(
        request,
        "core/exports.html",
        dict(
            evaluations=query[:200],
            companies=m.Company.objects.filter(client=client),
            parties=m.Party.objects.filter(client=client),
        ),
    )


@login_required
@require_POST
def export_file(request):
    membership = permit(request, WRITE | {"reader"})
    ids = request.POST.getlist("evaluations")
    if not ids or len(ids) > 50:
        return HttpResponse("Seleccione entre 1 y 50 evaluaciones.", status=400)
    try:
        ids = [uuid.UUID(x) for x in ids]
    except ValueError:
        raise Http404
    evs = list(
        m.Evaluation.objects.filter(client=membership.client, pk__in=ids).order_by(
            "work__company__name", "work__party__name", "created_at"
        )
    )
    if len(evs) != len(set(ids)):
        raise Http404
    if any(digest(e.snapshot) != e.digest for e in evs):
        return HttpResponse(
            "Integridad del expediente no válida. Revise auditoría.", status=409
        )
    from .exports import pdf_report, excel_report

    fmt = request.POST.get("format", "pdf")
    complete = request.POST.get("mode") == "complete"
    if fmt not in ("pdf", "xlsx"):
        return HttpResponse(status=400)
    output = pdf_report(evs, complete) if fmt == "pdf" else excel_report(evs)
    for ev in evs:
        audit(request, "exportar_" + fmt, ev, {"complete": complete})
    return FileResponse(
        output,
        as_attachment=True,
        filename="expediente." + fmt,
        content_type="application/pdf"
        if fmt == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@login_required
def source_backup(request, pk):
    source = get_object_or_404(m.Source, pk=pk, client=member(request).client)
    if not source.backup:
        raise Http404
    audit(request, "descargar_respaldo_normativo", source)
    try:
        return FileResponse(
            source.backup.open("rb"),
            as_attachment=True,
            filename=source.backup.name.rsplit("/", 1)[-1],
            content_type="application/octet-stream",
        )
    except FileNotFoundError:
        raise Http404


@login_required
@require_POST
def update_member(request, pk):
    membership = permit(request, {"admin"})
    entry = get_object_or_404(m.Membership, pk=pk, client=membership.client)
    role = request.POST.get("role")
    if role not in dict(m.Membership.ROLES):
        return HttpResponse("Rol inválido.", status=400)
    active_user = request.POST.get("active") == "yes"
    with transaction.atomic():
        if (
            entry.role == "admin"
            and (role != "admin" or not active_user)
            and m.Membership.objects.filter(
                client=membership.client, role="admin", user__is_active=True
            ).count()
            <= 1
        ):
            messages.error(request, "Debe conservar al menos un administrador activo.")
        else:
            entry.role = role
            entry.save()
            entry.user.is_active = active_user
            entry.user.save(update_fields=["is_active"])
            audit(
                request,
                "actualizar_acceso",
                entry,
                {"role": role, "active": active_user},
            )
            messages.success(request, "Acceso actualizado.")
    return redirect("team")
