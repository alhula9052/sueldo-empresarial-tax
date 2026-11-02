"""Prepare an uploaded Nexo source directory, without creating paid resources."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy.runtime import initialize  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        required=True,
        help="Dominio asignado por PythonAnywhere, sin esquema.",
    )
    parser.add_argument(
        "--username",
        default="asesor",
        help="Usuario de la aplicación; puede ser distinto del usuario de alojamiento.",
    )
    parser.add_argument("--consultora", default="Mi consultora")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        parser.error(
            "Seleccione Python 3.12 o posterior, igual que el entorno virtual de la aplicación Web."
        )
    os.umask(0o077)
    environment = dict(
        os.environ, **initialize(ROOT, args.host), PIP_DISABLE_PIP_VERSION_CHECK="1"
    )
    python = ROOT / ".venv" / "bin" / "python"
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
    subprocess.run(
        [str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    for command in (
        ["migrate", "--noinput"],
        ["collectstatic", "--noinput"],
        ["check"],
    ):
        subprocess.run(
            [str(python), "manage.py", *command], cwd=ROOT, env=environment, check=True
        )
    environment["NEXO_BOOTSTRAP_USERNAME"] = args.username
    environment["NEXO_BOOTSTRAP_CLIENT"] = args.consultora
    check_user = (
        "from django.contrib.auth import get_user_model; import os,sys; "
        "u=get_user_model().objects.filter(username=os.environ['NEXO_BOOTSTRAP_USERNAME']).first(); "
        "sys.exit(1 if u is None else 0 if u.is_active and hasattr(u,'membership') "
        "and u.membership.role=='admin' and u.membership.client.name==os.environ['NEXO_BOOTSTRAP_CLIENT'] else 2)"
    )
    exists = subprocess.run(
        [str(python), "manage.py", "shell", "-c", check_user],
        cwd=ROOT,
        env=environment,
    )
    if exists.returncode == 1:
        subprocess.run(
            [
                str(python),
                "manage.py",
                "create_client",
                "--name",
                args.consultora,
                "--username",
                args.username,
            ],
            cwd=ROOT,
            env=environment,
            check=True,
        )
    elif exists.returncode != 0:
        raise RuntimeError(
            "No se pudo comprobar el usuario. No se modificaron credenciales."
        )
    else:
        print("El usuario ya existe; se conserva su contraseña y pertenencia.")
    subprocess.run(
        [str(python), "manage.py", "check", "--deploy"],
        cwd=ROOT,
        env=environment,
        check=True,
    )
    print(
        "\nConfiguración local del alojamiento preparada; todavía falta activar la aplicación Web."
    )
    print(
        f"Versión Python a seleccionar: {sys.version_info.major}.{sys.version_info.minor}"
    )
    print(f"Entorno virtual: {ROOT / '.venv'}")
    print(f"Estáticos /static/: {ROOT / 'staticfiles'}")
    print(f"Archivo WSGI de referencia: {ROOT / 'deploy' / 'pythonanywhere_wsgi.py'}")
    print(
        "Siga docs/pythonanywhere.md. No comparta la carpeta .runtime ni su contenido."
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Preparación detenida: {exc}", file=sys.stderr)
        sys.exit(1)
