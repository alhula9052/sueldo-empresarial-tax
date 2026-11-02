from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model, password_validation
from . import models as m

REGISTRY = {
    "empresas": (m.Company, "Empresas"),
    "personas": (m.Party, "Personas y entidades"),
    "composicion": (m.Ownership, "Composición societaria"),
    "poderes": (m.Authority, "Administración y poderes"),
    "trabajo": (m.Work, "Trabajo efectivo"),
    "aportes": (m.Contribution, "Aportes APV / APVC / depósitos"),
    "simulacion": (m.Simulation, "Simulación de APV B"),
    "normativa": (m.Source, "Biblioteca normativa"),
    "reglas": (m.Rule, "Reglas versionadas"),
    "parametros": (m.Parameters, "Parámetros por período"),
    "documentos": (m.Document, "Documentos privados"),
    "consultora": (m.Branding, "Personalizar informes"),
}


class ScopedForm(forms.ModelForm):
    def __init__(self, *args, client, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.client = client
        for name, field in self.fields.items():
            if isinstance(
                field, (forms.ModelChoiceField, forms.ModelMultipleChoiceField)
            ):
                field.queryset = field.queryset.filter(client=client)
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(
                    attrs={"type": "date"}, format="%Y-%m-%d"
                )
            if isinstance(field, forms.JSONField):
                field.widget = forms.Textarea(attrs={"rows": 10, "class": "code"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs["rows"] = 3
        if isinstance(self.instance, m.Work):
            self.fields.pop("response_evidence", None)
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
                self.fields[key + "_evidence"] = forms.CharField(
                    label="Observaciones y evidencia: "
                    + str(m.Work._meta.get_field(key).verbose_name),
                    required=False,
                    widget=forms.Textarea(attrs={"rows": 2}),
                    initial=(self.instance.response_evidence or {}).get(key, ""),
                )

    def save(self, commit=True):
        if isinstance(self.instance, m.Work):
            self.instance.response_evidence = {
                key: self.cleaned_data.get(key + "_evidence", "")
                for key in (
                    "effective_work",
                    "instructions",
                    "supervision",
                    "discipline",
                    "leave",
                    "availability",
                    "autonomy",
                    "contribution_work",
                )
            }
        return super().save(commit=commit)

    def clean(self):
        data = super().clean()
        for name in ("file", "logo", "backup"):
            file = data.get(name)
            if file and hasattr(file, "size") and file.size > 5 * 1024 * 1024:
                self.add_error(name, "Máximo 5 MB por archivo.")
        logo = data.get("logo")
        if (
            logo
            and getattr(logo, "content_type", None)
            and logo.content_type not in ("image/png", "image/jpeg")
        ):
            self.add_error("logo", "Use PNG o JPEG.")
        if (
            logo
            and hasattr(logo, "image")
            and (logo.image.width > 2048 or logo.image.height > 2048)
        ):
            self.add_error("logo", "El logo debe medir hasta 2048 × 2048 píxeles.")
        return data


def form_for(model):
    return forms.modelform_factory(
        model, form=ScopedForm, exclude=["client", "created_at"]
    )


class TeamForm(forms.Form):
    username = forms.CharField(label="Usuario", max_length=150)
    password = forms.CharField(label="Contraseña inicial", widget=forms.PasswordInput)
    role = forms.ChoiceField(label="Rol", choices=m.Membership.ROLES)

    def clean_username(self):
        value = self.cleaned_data["username"]
        get_user_model()._meta.get_field("username").run_validators(value)
        if get_user_model().objects.filter(username=value).exists():
            raise ValidationError("El usuario ya existe.")
        return value

    def clean(self):
        data = super().clean()
        if data.get("password"):
            password_validation.validate_password(
                data["password"], get_user_model()(username=data.get("username", ""))
            )
        return data


class UploadForm(forms.Form):
    company = forms.ModelChoiceField(label="Empresa", queryset=m.Company.objects.none())
    file = forms.FileField(label="Archivo .xlsx o .csv (máximo 2 MB / 1.000 filas)")

    def __init__(self, *args, client, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = m.Company.objects.filter(client=client)

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > 2 * 1024 * 1024:
            raise ValidationError("Máximo 2 MB.")
        if not f.name.lower().endswith((".csv", ".xlsx")):
            raise ValidationError("Use CSV UTF-8 o Excel .xlsx.")
        return f
