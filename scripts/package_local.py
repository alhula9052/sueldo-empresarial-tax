"""Package source for local use, explicitly excluding server data and credentials."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = [
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    ".env.example",
    ".gitignore",
    "manage.py",
    "iniciar_windows.bat",
]
DIRECTORIES = ["config", "core", "scripts", "docs", "deploy"]


def build_package(destination):
    files = [ROOT / name for name in ROOT_FILES]
    for folder in DIRECTORIES:
        files.extend(
            p
            for p in (ROOT / folder).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, "nexo/" + path.relative_to(ROOT).as_posix())
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            assert not any(
                part in name.split("/")
                for part in (
                    ".env",
                    ".demo-password",
                    ".venv",
                    ".git",
                    "private-media",
                    ".runtime",
                )
            )
            assert not name.endswith((".sqlite3", ".pyc"))
    return destination


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="nexo-windows.zip")
    name = parser.parse_args().output
    if Path(name).name != name or not name.endswith(".zip"):
        parser.error("Use un nombre de archivo .zip sin ruta.")
    path = build_package(ROOT / "artifacts" / name)
    print(
        f"Paquete creado: {path.name} ({path.stat().st_size} bytes); sin datos ni credenciales del servidor."
    )
