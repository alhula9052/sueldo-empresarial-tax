"""Private on-host configuration for the PythonAnywhere WSGI application."""

import json
import os
from pathlib import Path
import re
import secrets


def validate_host(host):
    host = host.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.(?:eu\.)?pythonanywhere\.com", host):
        raise ValueError(
            "Use el dominio exacto asignado por PythonAnywhere, sin https:// ni ruta."
        )
    return host


def initialize(root, host):
    root = Path(root).resolve()
    host = validate_host(host)
    folder = root / ".runtime"
    folder.mkdir(mode=0o700, exist_ok=True)
    os.chmod(folder, 0o700)
    config = folder / "site.json"
    if config.exists():
        current = json.loads(config.read_text())
        if current != {"version": 1, "host": host}:
            raise ValueError(
                "Ya existe configuración para otro dominio. No se reemplazó."
            )
    else:
        with config.open("x") as target:
            target.write(json.dumps({"version": 1, "host": host}, indent=2))
        os.chmod(config, 0o600)
    secret = folder / "django-secret"
    if not secret.exists():
        fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as target:
            target.write(secrets.token_urlsafe(64))
    if len(secret.read_text().strip()) < 50:
        raise ValueError("La clave privada existente no es válida. No se reemplazó.")
    (folder / "private-media").mkdir(mode=0o700, exist_ok=True)
    return runtime_environment(root)


def runtime_environment(root):
    root = Path(root).resolve()
    folder = root / ".runtime"
    config = json.loads((folder / "site.json").read_text())
    if config.get("version") != 1:
        raise ValueError("Versión de configuración no compatible.")
    host = validate_host(config["host"])
    secret = (folder / "django-secret").read_text().strip()
    if len(secret) < 50:
        raise ValueError("Falta una clave Django privada válida.")
    return {
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "DEBUG": "0",
        "DJANGO_SECRET_KEY": secret,
        "ALLOWED_HOSTS": host,
        "DATABASE_PATH": str(folder / "nexo.sqlite3"),
        "PRIVATE_MEDIA_ROOT": str(folder / "private-media"),
        "SECURE_SSL_REDIRECT": "1",
        "SECURE_HSTS_SECONDS": "3600",
        # Enable only behind PythonAnywhere's trusted reverse proxy.
        "NEXO_TRUST_PROXY": "1",
    }
