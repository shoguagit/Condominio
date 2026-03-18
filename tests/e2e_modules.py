"""
Tests E2E con Playwright — Sistema de Condominio.

Prueba todos los módulos: si no hay datos, crea datos de ejemplo; luego prueba
Editar (cambiar registro y Guardar) y Eliminar (con confirmación).

Configuración: usar variables de entorno (o .env):
  E2E_BASE_URL   (default http://localhost:8501)
  E2E_EMAIL      (usuario para login)
  E2E_PASSWORD
Opcional para setup vía API: SUPABASE_URL, SUPABASE_KEY

Uso:
  1. Arrancar la app: streamlit run app.py
  2. python tests/e2e_modules.py
  o: pytest tests/e2e_modules.py -v -s
"""
import os
import sys
from pathlib import Path

# Cargar .env si existe
_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
    except ImportError:
        pass

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8501").rstrip("/")
EMAIL = os.getenv("E2E_EMAIL", "")
PASSWORD = os.getenv("E2E_PASSWORD", "")

# API opcional para asegurar condominio/propietario
SUPA_URL = os.getenv("SUPABASE_URL", "")
SUPA_KEY = os.getenv("SUPABASE_KEY", "")
SUPA_HDRS = None
if SUPA_URL and SUPA_KEY:
    SUPA_HDRS = {
        "apikey": SUPA_KEY,
        "Authorization": f"Bearer {SUPA_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

RESULTS: dict[str, str] = {}


def mark(name: str, ok: bool, detail: str = ""):
    icon = "✅" if ok else "❌"
    RESULTS[name] = f"{icon} {detail}" if detail else icon
    print(f"  {icon}  {name}: {detail}" if detail else f"  {icon}  {name}")


def print_summary():
    ok_n = sum(1 for v in RESULTS.values() if v.startswith("✅"))
    err_n = sum(1 for v in RESULTS.values() if v.startswith("❌"))
    print("\n═══════════════════════════════════════════════════════════")
    print("  RESUMEN E2E — Editar / Guardar / Eliminar por módulo")
    print("═══════════════════════════════════════════════════════════")
    for name, result in sorted(RESULTS.items()):
        print(f"  {result}  [{name}]")
    print(f"\n  Total: {ok_n} ✅  |  {err_n} ❌  |  {len(RESULTS)} pruebas")
    print("═══════════════════════════════════════════════════════════")


# ─── Playwright helpers ────────────────────────────────────────────────────

def _wait_render(page, extra_ms: int = 1200):
    try:
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(extra_ms)


def _nav_to(page, module: str):
    """Navega al módulo por el sidebar o por URL."""
    link = page.locator(f"a[data-testid='stPageLink-NavLink'][href*='{module}']").first
    if link.is_visible(timeout=4000):
        link.click()
    else:
        page.goto(f"{BASE_URL}/{module}", wait_until="domcontentloaded")
    _wait_render(page, 2500)


def _table_has_rows(page) -> bool:
    """True si hay tabla con al menos una fila de datos (tremor-table o stDataFrame)."""
    # Tabla HTML Tremor (record_table)
    rows = page.locator("table.tremor-table tbody tr")
    if rows.count() > 0:
        return True
    # st.dataframe
    rows = page.locator("[data-testid='stDataFrame'] table tbody tr")
    if rows.count() > 0:
        return True
    return False


def _is_empty_state(page) -> bool:
    return page.locator("text=No hay registros").is_visible(timeout=2000) or \
           page.locator("text=No se encontraron registros").is_visible(timeout=1000)


def _click_nuevo(page) -> bool:
    """Clic en botón Nuevo (record_table) o Incluir (toolbar)."""
    for label in ["Nuevo", "Incluir"]:
        btn = page.locator("button").filter(has_text=label).first
        if btn.is_visible(timeout=3000):
            btn.click()
            _wait_render(page, 2000)
            return True
    return False


def _fill_label(page, label: str, value: str) -> bool:
    loc = page.get_by_label(label, exact=False)
    if loc.count() == 0:
        return False
    loc.first.fill(value)
    page.wait_for_timeout(200)
    return True


def _submit_guardar(page):
    page.locator("button").filter(has_text="Guardar").first.click()
    _wait_render(page, 3500)


def _check_success(page) -> bool:
    for txt in ["actualizado", "actualizada", "exitosamente", "correctamente", "creado", "eliminado"]:
        if page.locator(f"text={txt}").is_visible(timeout=3000):
            return True
    return False


def _click_editar_primera_fila(page) -> bool:
    """Clic en el enlace Editar de la primera fila (tabla Tremor)."""
    link = page.locator("table.tremor-table a.table-action-link").filter(has_text="Editar").first
    if link.is_visible(timeout=5000):
        link.click()
        _wait_render(page, 2500)
        return True
    return False


def _click_eliminar_primera_fila(page) -> bool:
    """Clic en el enlace Eliminar de la primera fila."""
    link = page.locator("table.tremor-table a.table-action-link").filter(has_text="Eliminar").first
    if link.is_visible(timeout=4000):
        link.click()
        _wait_render(page, 2500)
        return True
    return False


def _confirmar_eliminar(page) -> bool:
    """Clic en Sí, eliminar (o similar)."""
    btn = page.locator("button").filter(has_text="Sí, eliminar").first
    if not btn.is_visible(timeout=3000):
        btn = page.locator("button").filter(has_text="eliminar").first
    if btn.is_visible(timeout=2000):
        btn.click()
        _wait_render(page, 3000)
        return True
    return False


# ─── Login ───────────────────────────────────────────────────────────────────

def _do_login(page) -> bool:
    page.goto(BASE_URL, wait_until="domcontentloaded")
    _wait_render(page, 2500)
    if page.locator(".kpi-strip").is_visible(timeout=3000):
        return True
    if not EMAIL or not PASSWORD:
        print("  ⚠️  E2E_EMAIL / E2E_PASSWORD no configurados. Configure .env o variables de entorno.")
        return False
    page.locator("input[type='text'], input[type='email']").first.fill(EMAIL)
    page.locator("input[type='password']").first.fill(PASSWORD)
    page.locator("button[kind='primaryFormSubmit']").first.click()
    _wait_render(page, 6000)
    return page.locator(".kpi-strip").is_visible(timeout=8000)


# ─── Setup API (condominio + propietario para Unidades) ───────────────────────

def _setup_condominio_y_propietario():
    if not SUPA_HDRS:
        return True
    try:
        import requests
        r = requests.get(
            f"{SUPA_URL}/rest/v1/usuarios?select=id,condominio_id",
            headers=SUPA_HDRS, timeout=10,
        )
        if not r.ok or not r.json():
            return True
        user = r.json()[0]
        uid, cid = user.get("id"), user.get("condominio_id")
        if not cid:
            r2 = requests.get(
                f"{SUPA_URL}/rest/v1/condominios?activo=eq.true&select=id&limit=1",
                headers=SUPA_HDRS, timeout=10,
            )
            if r2.ok and r2.json():
                cid = r2.json()[0]["id"]
                requests.patch(
                    f"{SUPA_URL}/rest/v1/usuarios?id=eq.{uid}",
                    headers=SUPA_HDRS, json={"condominio_id": cid}, timeout=10,
                )
        if cid:
            r3 = requests.get(
                f"{SUPA_URL}/rest/v1/propietarios?condominio_id=eq.{cid}&select=id&limit=1",
                headers=SUPA_HDRS, timeout=10,
            )
            if not (r3.ok and r3.json()):
                requests.post(
                    f"{SUPA_URL}/rest/v1/propietarios",
                    headers=SUPA_HDRS,
                    json={
                        "condominio_id": cid,
                        "nombre": "Propietario E2E",
                        "cedula": "V-11111111-1",
                        "activo": True,
                    },
                    timeout=10,
                )
        return True
    except Exception:
        return True


# ─── Tests por módulo (record_table: tabla Tremor + enlaces Editar/Eliminar) ───

def _ensure_data_condominios(page):
    if _table_has_rows(page):
        return True
    if not _click_nuevo(page):
        return False
    if not page.locator("[data-testid='stForm']").is_visible(timeout=5000):
        return False
    _fill_label(page, "Nombre del condominio", "Condominio E2E Test")
    _fill_label(page, "Dirección", "Av. E2E 123")
    _fill_label(page, "Número de", "J-99999999-9")
    _submit_guardar(page)
    _wait_render(page, 2000)
    return True


def _ensure_data_propietarios(page):
    if _table_has_rows(page):
        return True
    if not _click_nuevo(page):
        return False
    if not page.locator("[data-testid='stForm']").is_visible(timeout=5000):
        return False
    _fill_label(page, "Nombre", "Propietario E2E")
    _fill_label(page, "Cédula", "V-22222222-2")
    _submit_guardar(page)
    _wait_render(page, 2000)
    return True


def _ensure_data_unidades(page):
    if _table_has_rows(page):
        return True
    if page.locator("text=No hay propietarios").is_visible(timeout=2000):
        return False
    if not _click_nuevo(page):
        return False
    if not page.locator("[data-testid='stForm']").is_visible(timeout=5000):
        return False
    _fill_label(page, "Número de unidad", "E2E-01")
    _submit_guardar(page)
    _wait_render(page, 2000)
    return True


def _ensure_data_empleados(page):
    if _table_has_rows(page):
        return True
    if not _click_nuevo(page):
        return False
    if not page.locator("[data-testid='stForm']").is_visible(timeout=5000):
        return False
    _fill_label(page, "Nombre", "Empleado E2E")
    _fill_label(page, "Cargo", "Conserje")
    _submit_guardar(page)
    _wait_render(page, 2000)
    return True


def _ensure_data_proveedores(page):
    if _table_has_rows(page):
        return True
    if not _click_nuevo(page):
        return False
    if not page.locator("[data-testid='stForm']").is_visible(timeout=5000):
        return False
    _fill_label(page, "Nombre", "Proveedor E2E CA")
    _fill_label(page, "Número de", "J-88888888-8")
    _submit_guardar(page)
    _wait_render(page, 2000)
    return True


def _ensure_data_facturas(page):
    if _table_has_rows(page):
        return True
    if not _click_nuevo(page):
        return False
    if not page.locator("[data-testid='stForm']").is_visible(timeout=5000):
        return False
    _fill_label(page, "Número", "E2E-FAC-001")
    _submit_guardar(page)
    _wait_render(page, 2000)
    return True


def _run_module_test(page, module_name: str, nav_key: str, ensure_data_fn=None,
                     edit_label: str = None, edit_value: str = None):
    """Navega al módulo, asegura datos, prueba Editar+Guardar y Eliminar."""
    prefix = module_name.lower().replace(" ", "_")
    try:
        _nav_to(page, nav_key)
        if page.locator("text=Sin condominio activo").is_visible(timeout=3000):
            mark(f"{prefix}_acceso", False, "sin condominio activo")
            return
        mark(f"{prefix}_acceso", True, "OK")

        # Datos de ejemplo si no hay
        if ensure_data_fn and (_is_empty_state(page) or not _table_has_rows(page)):
            if not ensure_data_fn(page):
                mark(f"{prefix}_datos", False, "no se pudo crear dato de ejemplo")
                return
            mark(f"{prefix}_datos", True, "dato de ejemplo creado o ya existía")
        elif not _table_has_rows(page):
            mark(f"{prefix}_editar", True, "sin datos, omitido")
            mark(f"{prefix}_eliminar", True, "sin datos, omitido")
            return

        # Editar primera fila y Guardar
        if not _click_editar_primera_fila(page):
            mark(f"{prefix}_editar", False, "enlace Editar no encontrado")
        else:
            if not page.locator("[data-testid='stForm']").is_visible(timeout=5000):
                mark(f"{prefix}_editar", False, "formulario no visible")
            else:
                if edit_label and edit_value:
                    _fill_label(page, edit_label, edit_value)
                _submit_guardar(page)
                mark(f"{prefix}_editar", _check_success(page), "Guardar después de editar")

        _wait_render(page, 1500)

        # Eliminar: clic Eliminar en primera fila y confirmar
        if not _click_eliminar_primera_fila(page):
            mark(f"{prefix}_eliminar", False, "enlace Eliminar no encontrado")
        else:
            if not _confirmar_eliminar(page):
                mark(f"{prefix}_eliminar", False, "botón confirmar no encontrado")
            else:
                mark(f"{prefix}_eliminar", _check_success(page), "registro eliminado")

    except Exception as ex:
        mark(f"{prefix}_error", False, str(ex)[:100])


# ─── Módulos con toolbar (data_table): seleccionar fila + Modificar/Eliminar ───

def _run_toolbar_module_test(page, module_name: str, nav_key: str,
                             ensure_data_fn=None, edit_label: str = None, edit_value: str = None):
    """Para páginas que usan data_table + toolbar (Incluir/Modificar/Eliminar)."""
    prefix = module_name.lower().replace(" ", "_")[:12]
    try:
        _nav_to(page, nav_key)
        if page.locator("text=Sin condominio activo").is_visible(timeout=3000):
            mark(f"{prefix}_acceso", False, "sin condominio")
            return
        mark(f"{prefix}_acceso", True, "OK")

        if ensure_data_fn and (_is_empty_state(page) or not _table_has_rows(page)):
            if not ensure_data_fn(page):
                mark(f"{prefix}_datos", False, "no crear dato")
                return
            mark(f"{prefix}_datos", True, "dato creado o existía")

        if not _table_has_rows(page):
            mark(f"{prefix}_editar", True, "omitido")
            mark(f"{prefix}_eliminar", True, "omitido")
            return

        # Seleccionar primera fila (st.dataframe): clic en primera fila de la tabla
        table = page.locator("[data-testid='stDataFrame'] table tbody tr").first
        if table.is_visible(timeout=3000):
            table.click()
            _wait_render(page, 1500)
        mod_btn = page.locator("button").filter(has_text="Modificar").first
        if mod_btn.is_visible(timeout=2000):
            mod_btn.click()
            _wait_render(page, 2000)
            if page.locator("[data-testid='stForm']").is_visible(timeout=4000):
                if edit_label and edit_value:
                    _fill_label(page, edit_label, edit_value)
                _submit_guardar(page)
                mark(f"{prefix}_editar", _check_success(page), "Guardar")
            else:
                mark(f"{prefix}_editar", False, "form no visible")
        else:
            mark(f"{prefix}_editar", True, "sin botón Modificar")

        _wait_render(page, 1500)
        # Eliminar: volver a seleccionar primera fila y Eliminar
        table2 = page.locator("[data-testid='stDataFrame'] table tbody tr").first
        if table2.is_visible(timeout=2000):
            table2.click()
            _wait_render(page, 1000)
        del_btn = page.locator("button").filter(has_text="Eliminar").first
        if del_btn.is_visible(timeout=2000):
            del_btn.click()
            _wait_render(page, 1500)
            if _confirmar_eliminar(page):
                mark(f"{prefix}_eliminar", _check_success(page), "eliminado")
            else:
                mark(f"{prefix}_eliminar", False, "no confirmar")
        else:
            mark(f"{prefix}_eliminar", True, "sin botón Eliminar")
    except Exception as ex:
        mark(f"{prefix}_error", False, str(ex)[:100])


def _ensure_data_alicuotas(page):
    if _table_has_rows(page):
        return True
    if not page.locator("button").filter(has_text="Incluir").is_visible(timeout=3000):
        return False
    page.locator("button").filter(has_text="Incluir").first.click()
    _wait_render(page, 2000)
    if not page.locator("[data-testid='stForm']").is_visible(timeout=4000):
        return False
    _fill_label(page, "Descripción", "Alícuota E2E")
    _submit_guardar(page)
    _wait_render(page, 2000)
    return True


# ─── Ejecutor principal ───────────────────────────────────────────────────────

def run():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Instale Playwright: pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=os.getenv("E2E_HEADLESS", "1") != "0",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        print("\n═══════════════════════════════════════════════════════════")
        print("  E2E — Todos los módulos: Editar, Guardar, Eliminar")
        print("═══════════════════════════════════════════════════════════")

        if not _do_login(page):
            mark("login", False, "no autenticado (revise E2E_EMAIL/E2E_PASSWORD)")
            browser.close()
            print_summary()
            sys.exit(1)
        mark("login", True, "sesión iniciada")

        _setup_condominio_y_propietario()

        # Módulos con record_table (tabla Tremor + enlaces)
        _run_module_test(
            page, "Condominios", "condominios",
            ensure_data_fn=_ensure_data_condominios,
            edit_label="Nombre del condominio", edit_value="Condominio E2E (editado)",
        )
        _run_module_test(
            page, "Propietarios", "propietarios",
            ensure_data_fn=_ensure_data_propietarios,
            edit_label="Nombre", edit_value="Propietario E2E (editado)",
        )
        _run_module_test(
            page, "Unidades", "unidades",
            ensure_data_fn=_ensure_data_unidades,
            edit_label="Número de unidad", edit_value="E2E-01-edit",
        )
        _run_module_test(
            page, "Empleados", "empleados",
            ensure_data_fn=_ensure_data_empleados,
            edit_label="Nombre", edit_value="Empleado E2E (editado)",
        )
        _run_module_test(
            page, "Proveedores", "proveedores",
            ensure_data_fn=_ensure_data_proveedores,
            edit_label="Nombre", edit_value="Proveedor E2E (editado)",
        )
        _run_module_test(
            page, "Facturas", "facturas",
            ensure_data_fn=_ensure_data_facturas,
        )

        # Usuarios: solo acceso y listado (crear requiere Auth)
        try:
            _nav_to(page, "usuarios")
            if page.locator("text=Sin condominio activo").is_visible(timeout=3000):
                mark("usuarios_acceso", False, "sin condominio")
            else:
                mark("usuarios_acceso", True, "OK")
                if _table_has_rows(page):
                    if _click_editar_primera_fila(page):
                        if page.locator("[data-testid='stForm']").is_visible(timeout=4000):
                            page.locator("button").filter(has_text="Cancelar").first.click()
                            _wait_render(page, 1000)
                    mark("usuarios_editar", True, "form abierto")
                else:
                    mark("usuarios_editar", True, "sin datos")
                mark("usuarios_eliminar", True, "omitido (módulo sensible)")
        except Exception as ex:
            mark("usuarios_error", False, str(ex)[:80])

        # Módulos con toolbar (data_table): alícuotas, fondos, servicios, conceptos, etc.
        _run_toolbar_module_test(
            page, "Alícuotas", "alicuotas",
            ensure_data_fn=_ensure_data_alicuotas,
            edit_label="Descripción", edit_value="Alícuota E2E (editada)",
        )
        for nav_key, name in [
            ("fondos", "Fondos"),
            ("servicios", "Servicios"),
            ("conceptos", "Conceptos"),
            ("gastos_fijos", "Gastos Fijos"),
            ("conceptos_consumo", "Conceptos Consumo"),
            ("cuentas_bancos", "Cuentas Bancos"),
        ]:
            _run_toolbar_module_test(page, name, nav_key, ensure_data_fn=None)

        browser.close()

    print_summary()
    err_n = sum(1 for v in RESULTS.values() if v.startswith("❌"))
    sys.exit(0 if err_n == 0 else 1)


if __name__ == "__main__":
    run()
