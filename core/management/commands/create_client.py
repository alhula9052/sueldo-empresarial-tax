import getpass
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
from core.models import Client, Membership


class Command(BaseCommand):
    help = "Crea un cliente aislado y su primer administrador. No imprime credenciales."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--username", required=True)

    @transaction.atomic
    def handle(self, *args, **opts):
        if get_user_model().objects.filter(username=opts["username"]).exists():
            raise CommandError("El usuario ya existe. No se modifica.")
        user = get_user_model()(username=opts["username"])
        try:
            user.full_clean(exclude=["password"])
            password = os.getenv("CLIENT_ADMIN_PASSWORD") or getpass.getpass(
                "Contraseña inicial: "
            )
            password_validation.validate_password(password, user)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages))
        client = Client.objects.create(name=opts["name"])
        user.set_password(password)
        user.save()
        Membership.objects.create(client=client, user=user, role="admin")
        self.stdout.write(self.style.SUCCESS("Cliente y administrador creados."))
