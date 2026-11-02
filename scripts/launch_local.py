"""Bootstrap Nexo on the user's machine and open its local browser, without publishing it."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def interpreter(root=ROOT):
    return root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def choose_port(preferred):
    for port in range(preferred, min(preferred + 10, 65536)):
        try:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
    raise RuntimeError(
        "No hay puertos locales disponibles. Cierre otra instancia de Nexo."
    )


def wait_ready(process, url, timeout=30):
    # Only a loopback request; avoid sending the user's local login page through a proxy.
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "El servidor no pudo iniciarse. Revise el mensaje anterior."
            )
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200 and b"Nexo" in response.read(10000):
                    return
        except (URLError, OSError):
            pass
        time.sleep(0.2)
    raise RuntimeError("El servidor no respondió a tiempo.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Solo para desarrollo con dependencias instaladas.",
    )
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        raise RuntimeError(
            "Instale Python 3.12 o posterior desde python.org y vuelva a iniciar."
        )
    if not 1024 <= args.port <= 65526:
        raise RuntimeError("El puerto debe estar entre 1024 y 65526.")
    env = dict(
        os.environ,
        DEBUG="1",
        ALLOWED_HOSTS="127.0.0.1,localhost",
        PIP_DISABLE_PIP_VERSION_CHECK="1",
    )
    # This launcher always uses its own local data, rather than inherited deployment paths.
    env["DATABASE_PATH"] = str(ROOT / "db.sqlite3")
    env["PRIVATE_MEDIA_ROOT"] = str(ROOT / "private-media")
    env["SECURE_SSL_REDIRECT"] = "0"
    env["SECURE_HSTS_SECONDS"] = "0"
    python = interpreter()
    if not python.exists():
        if args.skip_install:
            raise RuntimeError("Falta el entorno .venv. Ejecute sin --skip-install.")
        subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
    requirements = ROOT / "requirements.txt"
    stamp = ROOT / ".venv" / ".nexo-requirements.sha256"
    expected = hashlib.sha256(requirements.read_bytes()).hexdigest()
    if not args.skip_install and (not stamp.exists() or stamp.read_text() != expected):
        print(
            "Preparando dependencias. La primera vez requiere conexión a Internet.",
            flush=True,
        )
        subprocess.run(
            [str(python), "-m", "pip", "install", "-r", str(requirements)],
            cwd=ROOT,
            env=env,
            check=True,
        )
        stamp.write_text(expected)
    for command in ("migrate", "seed_demo"):
        subprocess.run(
            [str(python), "manage.py", command], cwd=ROOT, env=env, check=True
        )
    port = choose_port(args.port)
    url = f"http://127.0.0.1:{port}/ingresar/"
    process = subprocess.Popen(
        [str(python), "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"],
        cwd=ROOT,
        env=env,
    )
    try:
        wait_ready(process, url)
        print(f"\nNexo está disponible en ESTE computador: {url}", flush=True)
        print(
            "Usuario: demo. Contraseña: archivo .demo-password en la carpeta Nexo.",
            flush=True,
        )
        print(
            "Mantenga esta ventana abierta. Para detener, presione Ctrl+C.", flush=True
        )
        if not args.no_browser:
            webbrowser.open(url)
            password_file = ROOT / ".demo-password"
            if os.name == "nt" and password_file.exists():
                subprocess.Popen(["notepad.exe", str(password_file)])
        process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nNexo detenido.")
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"No se pudo iniciar Nexo: {exc}", file=sys.stderr)
        sys.exit(1)
