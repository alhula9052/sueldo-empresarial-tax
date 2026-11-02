"""Optional real-browser smoke test for a running local demonstration instance."""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.getenv("CHROMIUM_PATH", "/usr/bin/chromium"),
        args=["--no-sandbox"],
    )
    page = browser.new_page(
        viewport={"width": 1440, "height": 1050}, device_scale_factor=1
    )
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8000/ingresar/")
    page.get_by_label("Nombre de usuario").fill("demo")
    password = (
        os.getenv("DEMO_PASSWORD") or (ROOT / ".demo-password").read_text().strip()
    )
    page.get_by_label("Contraseña").fill(password)
    page.get_by_role("button", name="Ingresar al espacio").click()
    page.wait_for_url("http://127.0.0.1:8000/")
    page.get_by_role("heading", name="Una mirada completa a cada caso.").wait_for()
    page.screenshot(
        path=str(ROOT / "artifacts/panel-escritorio.png"),
        full_page=True,
        animations="disabled",
    )
    page.get_by_role("link", name="Abrir caso").first.click()
    page.get_by_role("button", name="Guardar evaluación").click()
    page.get_by_text("Versión inmutable.").wait_for()
    with page.expect_download() as pending:
        page.get_by_role("button", name="Descargar PDF", exact=True).click()
    download = pending.value
    download.save_as(str(ROOT / "artifacts/browser-informe.pdf"))
    with page.expect_download() as pending:
        page.get_by_role("button", name="Descargar Excel", exact=True).click()
    pending.value.save_as(str(ROOT / "artifacts/browser-expediente.xlsx"))
    page.goto("http://127.0.0.1:8000/")
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_function(
        "document.querySelector('#sidebar').getBoundingClientRect().right <= 0"
    )
    page.screenshot(
        path=str(ROOT / "artifacts/panel-movil.png"),
        full_page=True,
        animations="disabled",
    )
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "Desbordamiento horizontal móvil"
    )
    page.get_by_role("button", name="Menú").click()
    page.get_by_role("link", name="Biblioteca normativa", exact=True).click()
    page.get_by_role("heading", name="Biblioteca normativa").wait_for()
    assert not errors, errors
    browser.close()
print("Navegación, autenticación, evaluación, descargas PDF/XLSX y móvil: OK")
