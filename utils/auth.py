import streamlit as st
import os

from config.supabase_client import get_supabase_client


def _inject_css() -> None:
    """Inyecta el CSS global (oculta nav automático, aplica tema).
    Llamado internamente para garantizar estilo incluso en páginas de error."""
    try:
        from components.sidebar import GLOBAL_CSS
        st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    except Exception:
        pass


def check_authentication() -> None:
    """
    Verifica sesión activa. Debe llamarse al inicio de cada página protegida,
    DESPUÉS de st.set_page_config() y ANTES de render_header().
    Inyecta el CSS global para que la página no quede con nav negro/feo.
    """
    _inject_css()

    if not st.session_state.get("authenticated", False):
        # DEV AUTOLOGIN (QA local): permite ejecutar módulos sin pasar por UI de login
        # Activar con CONDOSYS_DEV_AUTOLOGIN=1 y CONDOSYS_DEV_AUTOLOGIN_EMAIL=<email>.
        if os.getenv("CONDOSYS_DEV_AUTOLOGIN") == "1":
            dev_email = (os.getenv("CONDOSYS_DEV_AUTOLOGIN_EMAIL") or "").strip()
            if dev_email:
                try:
                    client = get_supabase_client()
                    resp = (
                        client.table("usuarios")
                        .select("*, condominios(nombre, mes_proceso, tasa_cambio)")
                        .eq("email", dev_email)
                        .eq("activo", True)
                        .single()
                        .execute()
                    )
                    u = resp.data
                    condo = (u.get("condominios") or {}) if isinstance(u, dict) else {}

                    # Cargar tasa BCV en tiempo real (si falla, se usa la del condominio)
                    try:
                        from utils.bcv_rate import fetch_bcv_rate
                        bcv_rate, bcv_source = fetch_bcv_rate()
                    except Exception:
                        bcv_rate, bcv_source = 0, ""

                    rol = u.get("rol", "consulta") if isinstance(u, dict) else "consulta"
                    st.session_state.authenticated = True
                    st.session_state.user_email = dev_email
                    st.session_state.user_role = rol
                    if rol == "admin":
                        st.session_state.pending_admin_condominio_selection = True
                        st.session_state.condominio_id = None
                        st.session_state.condominio_nombre = None
                        st.session_state.mes_proceso = None
                        st.session_state.tasa_cambio = 0.0
                        st.session_state.tasa_fuente = ""
                    else:
                        st.session_state.condominio_id = u.get("condominio_id") if isinstance(u, dict) else None
                        st.session_state.condominio_nombre = condo.get("nombre", "—")
                        from utils.formatters import format_mes_proceso
                        st.session_state.mes_proceso = format_mes_proceso(condo.get("mes_proceso")) or ""
                        st.session_state.tasa_cambio = bcv_rate or float(condo.get("tasa_cambio") or 0)
                        st.session_state.tasa_fuente = bcv_source

                    st.rerun()
                except Exception:
                    # Si falla, continuar con el flujo normal de "Sesión no iniciada".
                    pass

        st.markdown(
            """
            <div style="max-width:420px; margin:10vh auto; text-align:center;
                        background:white; border-radius:12px; padding:36px;
                        box-shadow:0 2px 16px rgba(31,97,141,0.10);
                        border-top:3px solid #2471A3;">
                <div style="font-size:2.5rem;">🔒</div>
                <h3 style="color:#1A5276; margin:12px 0 6px;">Sesión no iniciada</h3>
                <p style="color:#7F8C8D; font-size:13px; margin:0 0 20px;">
                    Por favor inicie sesión para continuar.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("app.py", label="← Ir al inicio de sesión")
        st.stop()


def require_condominio() -> str:
    """
    Verifica que haya un condominio activo en sesión.
    Devuelve el condominio_id o muestra error guiado y detiene la ejecución.
    """
    cid = st.session_state.get("condominio_id")
    if not cid:
        st.markdown(
            """
            <div style="max-width:480px; margin:4vh auto; text-align:center;
                        background:white; border-radius:12px; padding:32px;
                        box-shadow:0 2px 16px rgba(31,97,141,0.10);
                        border-top:3px solid #E74C3C;">
                <div style="font-size:2.5rem;">🏢</div>
                <h3 style="color:#1A5276; margin:12px 0 6px;">
                    Sin condominio activo
                </h3>
                <p style="color:#7F8C8D; font-size:13px; margin:0 0 6px;">
                    Para usar este módulo primero debe registrar un condominio
                    y asignarlo a su cuenta de usuario.
                </p>
                <p style="color:#5D6D7E; font-size:12px; margin:0 0 20px;">
                    <b>Paso 1:</b> Cree el condominio en el módulo
                    <em>Condominios</em>.<br>
                    <b>Paso 2:</b> En <em>Usuarios</em>, asigne ese condominio
                    a su cuenta y vuelva a iniciar sesión.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            st.page_link("pages/01_condominios.py", label="🏢  Ir a Condominios")
        with col2:
            st.page_link("pages/12_usuarios.py", label="🔐  Ir a Usuarios")
        st.stop()
    return cid


def check_permission(required_role: str) -> None:
    """Verifica que el usuario tenga el rol mínimo requerido."""
    role_hierarchy = {"admin": 3, "operador": 2, "consulta": 1}
    user_role = st.session_state.get("user_role", "consulta")

    if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 99):
        st.error("❌ No tiene permisos para realizar esta acción.")
        st.stop()


def login(email: str, password: str) -> tuple:
    """Autentica al usuario con Supabase Auth."""
    client = get_supabase_client()
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    return response.user, response.session


def apply_condominio_to_session(condominio_id: int) -> None:
    """
    Carga el condominio elegido en session_state (nombre, mes_proceso, tasa, etc.).
    Usado tras selección de condominio por admin (login o Cambiar).
    mes_proceso se guarda en formato MM/YYYY para pantalla.
    """
    from repositories.condominio_repository import CondominioRepository
    from utils.formatters import format_mes_proceso
    repo = CondominioRepository(get_supabase_client())
    condo = repo.get_by_id(condominio_id)
    if not condo:
        return
    pais = (condo.get("paises") or {}) if isinstance(condo.get("paises"), dict) else {}
    st.session_state.condominio_id = condominio_id
    st.session_state.condominio_nombre = condo.get("nombre", "—")
    st.session_state.condominio_pais = pais.get("nombre")
    st.session_state.condominio_moneda = pais.get("simbolo_moneda") or "Bs."
    st.session_state.mes_proceso = format_mes_proceso(condo.get("mes_proceso")) or ""
    try:
        from utils.bcv_rate import fetch_bcv_rate
        bcv_rate, bcv_source = fetch_bcv_rate()
        st.session_state.tasa_cambio = bcv_rate or float(condo.get("tasa_cambio") or 0)
        st.session_state.tasa_fuente = bcv_source
    except Exception:
        st.session_state.tasa_cambio = float(condo.get("tasa_cambio") or 0)
        st.session_state.tasa_fuente = ""


def logout() -> None:
    """Cierra la sesión en Supabase y limpia el estado de Streamlit."""
    try:
        client = get_supabase_client()
        client.auth.sign_out()
    except Exception:
        pass
    finally:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def init_session_state() -> None:
    """Inicializa las variables de sesión necesarias."""
    defaults = {
        "authenticated":                    False,
        "user_email":                       None,
        "user_role":                        None,
        "condominio_id":                    None,
        "condominio_nombre":                None,
        "condominio_pais":                  None,
        "condominio_moneda":                None,
        "mes_proceso":                      None,
        "tasa_cambio":                      0.0,
        "tasa_fuente":                      "",
        "pending_admin_condominio_selection": False,
        "show_condominio_switcher":         False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
