from django.urls import path
from django.contrib.auth import views as auth
from core import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "ingresar/",
        auth.LoginView.as_view(template_name="core/login.html"),
        name="login",
    ),
    path("salir/", auth.LogoutView.as_view(), name="logout"),
    path("registros/<str:kind>/", views.listing, name="listing"),
    path("registros/<str:kind>/nuevo/", views.edit, name="create"),
    path("registros/<str:kind>/<int:pk>/", views.edit, name="edit"),
    path("registros/<str:kind>/<int:pk>/eliminar/", views.delete, name="delete"),
    path("casos/<int:pk>/", views.case, name="case"),
    path("casos/<int:pk>/evaluar/", views.evaluate, name="evaluate"),
    path("evaluaciones/<uuid:pk>/", views.evaluation, name="evaluation"),
    path("documentos/<int:pk>/descargar/", views.download_document, name="document"),
    path("importar/", views.import_ownership, name="import"),
    path("plantilla/", views.import_template, name="template"),
    path("exportaciones/", views.exports, name="exports"),
    path("exportar/", views.export_file, name="export"),
    path("auditoria/", views.audit_log, name="audit"),
    path("normativa/<int:pk>/respaldo/", views.source_backup, name="source_backup"),
    path("equipo/<int:pk>/", views.update_member, name="update_member"),
    path("equipo/", views.team, name="team"),
]
