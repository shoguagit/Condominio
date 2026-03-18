import streamlit as st
import os

from utils.auth import init_session_state, logout

st.set_page_config(
    page_title="Sistema de Condominio",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

# =============================================================================
# DEV AUTOLOGIN (solo para QA local / Playwright)
# - Habilitar con: CONDOSYS_DEV_AUTOLOGIN=1 y CONDOSYS_DEV_AUTOLOGIN_EMAIL=<email>
# - Mantiene el login normal por defecto (sin env vars no hace nada).
# =============================================================================
if not st.session_state.authenticated and os.getenv("CONDOSYS_DEV_AUTOLOGIN") == "1":
    dev_email = (os.getenv("CONDOSYS_DEV_AUTOLOGIN_EMAIL") or "").strip()
    if dev_email:
        with st.spinner("Iniciando sesión de prueba…"):
            try:
                from config.supabase_client import get_supabase_client
                from utils.bcv_rate import fetch_bcv_rate

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

                bcv_rate, bcv_source = fetch_bcv_rate()

                st.session_state.authenticated = True
                st.session_state.user_email = dev_email
                st.session_state.user_role = u.get("rol", "consulta") if isinstance(u, dict) else "consulta"
                st.session_state.condominio_id = u.get("condominio_id") if isinstance(u, dict) else None
                st.session_state.condominio_nombre = condo.get("nombre", "—")
                st.session_state.mes_proceso = condo.get("mes_proceso")
                st.session_state.tasa_cambio = bcv_rate or float(condo.get("tasa_cambio") or 0)
                st.session_state.tasa_fuente = bcv_source

                st.rerun()
            except Exception:
                st.error("No se pudo iniciar sesión automática (verifique el email configurado).")

# =============================================================================
# LOGIN
# =============================================================================
if not st.session_state.authenticated:
    from components.styles import LOGIN_CSS

    # Ocultar navegación y centrado 100vh sin scroll
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarNavItems"],
        [data-testid="stSidebar"] { display: none !important; }
        #MainMenu, footer, header { visibility: hidden; }
        body, .stApp { background-color: #FFFFFF !important; color: #2C3E50 !important;
                       font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .login-wrapper {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: radial-gradient(circle at top left, #EBF5FB 0, #FFFFFF 52%);
        }

        /* Tarjeta corporativa */
        .login-card {
            width: 380px;
            max-width: 94vw;
            background: #FFFFFF;
            border-radius: 16px;
            padding: 28px 32px 22px;
            border: 1px solid #D5D8DC;
            border-top: 4px solid #1B4F72;
            box-shadow: 0 10px 35px rgba(0,0,0,0.10);
        }

        /* Cabecera con logo y nombre del sistema */
        .login-logo {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin-bottom: 20px;
        }
        .login-logo-icon {
            width: 56px;
            height: 56px;
            border-radius: 16px;
            background: linear-gradient(135deg, #1B4F72, #2E86C1);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 30px;
            color: #FFFFFF;
            box-shadow: 0 6px 18px rgba(27,79,114,0.45);
        }
        .login-logo-title {
            margin-top: 14px;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.2px;
            color: #1B4F72;
        }
        .login-logo-subtitle {
            margin-top: 2px;
            font-size: 12px;
            color: #717D7E;
        }

        /* Labels corporativos */
        label {
            color: #2C3E50 !important;
            font-size: 12px !important;
            font-weight: 600 !important;
        }

        /* Inputs limpios */
        [data-baseweb="input"] input {
            color: #1C2833 !important;
            background: #FFFFFF !important;
            font-size: 13px !important;
        }

        /* Ocultar sugerencias de contraseña del navegador */
        input[type="password"]::-webkit-credentials-auto-fill-button,
        input[type="password"]::-webkit-strong-password-auto-fill-button,
        input[type="password"]::-webkit-contacts-auto-fill-button {
            display: none !important;
        }

        /* Botón primario corporativo */
        div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
            background: #1B4F72 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 999px !important;
            font-weight: 700 !important;
            font-size: 14px !important;
            padding: 10px 14px !important;
            box-shadow: 0 4px 12px rgba(27,79,114,0.45);
            transition: background 0.15s ease-out, transform 0.08s ease-out,
                        box-shadow 0.15s ease-out !important;
        }
        div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
            background: #154360 !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(27,79,114,0.55);
        }
        div[data-testid="stForm"] button[kind="primaryFormSubmit"]:active {
            transform: translateY(0);
            box-shadow: 0 3px 8px rgba(27,79,114,0.40);
        }

        /* Texto de versión */
        .login-footer {
            text-align: center;
            color: #B3B6B7;
            font-size: 10px;
            margin-top: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # JS: forzar autocomplete=off en el campo de contraseña
    st.markdown(
        """
        <script>
        (function() {
            function disableAutofill() {
                document.querySelectorAll('input[type="password"]').forEach(function(el) {
                    el.setAttribute('autocomplete', 'new-password');
                    el.setAttribute('data-lpignore', 'true');
                });
            }
            if (document.readyState === 'complete') { disableAutofill(); }
            else { window.addEventListener('load', disableAutofill); }
            setTimeout(disableAutofill, 800);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

    # Wrapper para centrar la tarjeta sobre fondo blanco corporativo
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        # Cabecera con "logo" del sistema
        st.markdown(
            """
            <div class="login-card">
                <div class="login-logo">
                    <div class="login-logo-icon">🏢</div>
                    <div class="login-logo-title">Sistema de Condominio</div>
                    <div class="login-logo-subtitle">Acceso seguro para administradores y juntas</div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            email    = st.text_input("Correo electrónico", placeholder="usuario@email.com")
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••",
                help=None,
                autocomplete="new-password",
            )
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Ingresar →",
                use_container_width=True,
                type="primary",
            )

        # Cerrar tarjeta y wrapper
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            if not email or not password:
                st.error("Ingrese correo y contraseña.")
            else:
                with st.spinner("Verificando credenciales…"):
                    try:
                        from utils.auth import login
                        from config.supabase_client import get_supabase_client

                        login(email, password)

                        client = get_supabase_client()
                        resp = (
                            client.table("usuarios")
                            .select("*, condominios(nombre, mes_proceso, tasa_cambio)")
                            .eq("email", email)
                            .eq("activo", True)
                            .single()
                            .execute()
                        )
                        u     = resp.data
                        condo = u.get("condominios") or {}
                        rol   = u.get("rol", "consulta")

                        st.session_state.authenticated = True
                        st.session_state.user_email   = email
                        st.session_state.user_role    = rol

                        if rol == "admin":
                            # Admin debe elegir condominio antes de entrar al dashboard
                            st.session_state.pending_admin_condominio_selection = True
                            st.session_state.condominio_id     = None
                            st.session_state.condominio_nombre = None
                            st.session_state.mes_proceso       = None
                            st.session_state.tasa_cambio       = 0.0
                            st.session_state.tasa_fuente       = ""
                        else:
                            # Operador/consulta: un solo condominio asignado, entrar directo
                            st.session_state.pending_admin_condominio_selection = False
                            from utils.bcv_rate import fetch_bcv_rate
                            bcv_rate, bcv_source = fetch_bcv_rate()
                            st.session_state.condominio_id     = u.get("condominio_id")
                            st.session_state.condominio_nombre = condo.get("nombre", "—")
                            st.session_state.mes_proceso       = condo.get("mes_proceso")
                            st.session_state.tasa_cambio       = bcv_rate or float(condo.get("tasa_cambio") or 0)
                            st.session_state.tasa_fuente       = bcv_source

                        st.rerun()
                    except Exception:
                        st.error("Credenciales incorrectas o usuario inactivo.")

        st.markdown(
            "<p class='login-footer'>v1.0 · Sistema de Gestión de Condominios</p>",
            unsafe_allow_html=True,
        )

    st.stop()


# =============================================================================
# DASHBOARD (post-login)
# =============================================================================
from components.header import render_header
from utils.formatters import format_mes_proceso
from utils.auth import apply_condominio_to_session

# render_header() inyecta TODO el CSS global (sidebar.py GLOBAL_CSS) + sidebar + barra corporativa
render_header()

# ── Admin: selección de condominio tras login (solo si aún no eligió) ─────────
if st.session_state.get("pending_admin_condominio_selection"):
    from config.supabase_client import get_supabase_client
    from repositories.condominio_repository import CondominioRepository
    condominios = CondominioRepository(get_supabase_client()).get_all(solo_activos=False)
    if not condominios:
        st.warning("No hay condominios registrados. Cree uno en el módulo Condominios.")
        st.page_link("pages/01_condominios.py", label="Ir a Condominios")
        st.stop()
    options = [c.get("nombre") or f"Condominio #{c.get('id')}" for c in condominios]
    sel = st.selectbox(
        "Seleccione el condominio con el que desea trabajar",
        options,
        index=0,
        key="admin_condominio_selector",
    )
    if st.button("Entrar al dashboard", type="primary", key="admin_condominio_entrar"):
        idx = options.index(sel)
        cid = condominios[idx]["id"]
        apply_condominio_to_session(cid)
        st.session_state.pending_admin_condominio_selection = False
        st.rerun()
    st.stop()

# ── KPI strip (condominio, mes, tasa, rol, correo) ─────────────────────────────
mes_str     = format_mes_proceso(st.session_state.mes_proceso) or "—"
tasa        = st.session_state.tasa_cambio
tasa_fuente = st.session_state.get("tasa_fuente", "")
rol         = st.session_state.user_role.capitalize()
email       = st.session_state.get("user_email", "—")

tasa_color = "#1B4F72" if tasa > 0 else "#C0392B"
fuente_tag = (
    f'<span style="font-size:9px;color:#6B7280;display:block;margin-top:1px;">{tasa_fuente}</span>'
    if tasa_fuente else ""
)
st.markdown(
    f"""
    <div class="kpi-strip">
        <div class="kpi-item">
            <div class="kpi-lbl">Condominio</div>
            <div class="kpi-val">{st.session_state.condominio_nombre}</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-lbl">Mes en proceso</div>
            <div class="kpi-val">{mes_str}</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-lbl">Tasa BCV (USD/VES)</div>
            <div class="kpi-val" style="color:{tasa_color};">Bs. {tasa:,.4f}</div>
            {fuente_tag}
        </div>
        <div class="kpi-item">
            <div class="kpi-lbl">Rol</div>
            <div class="kpi-val">{rol}</div>
        </div>
        <div class="kpi-item">
            <div class="kpi-lbl">Usuario</div>
            <div class="kpi-val" style="font-size:12px;">{email}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Accesos rápidos ───────────────────────────────────────────────────────────
st.markdown(
    '<p class="cat-hdr" style="padding-top:4px;">Accesos rápidos</p>',
    unsafe_allow_html=True,
)
quick_links = [
    ("pages/14_facturas.py", "🧾 Facturas"),
    ("pages/09_cuentas_bancos.py", "🏦 Cuentas / Bancos"),
    ("pages/02_unidades.py", "🏠 Unidades"),
    ("pages/11_propietarios.py", "👥 Propietarios"),
    ("pages/15_reportes.py", "📈 Reportes"),
]
st.markdown('<div class="quick-links-marker"></div>', unsafe_allow_html=True)
quick_cols = st.columns(len(quick_links))
for col, (page_path, label) in zip(quick_cols, quick_links):
    with col:
        st.page_link(page_path, label=label, icon=None)

# =============================================================================
# MENÚ PRINCIPAL — organizado por categoría (cards corporativas)
# st.page_link mantiene session_state al navegar.
# =============================================================================
st.markdown(
    '<p class="cat-hdr" style="padding-top:8px;">Menú por categoría</p>',
    unsafe_allow_html=True,
)
MODULES = {
    "🏛️  General y Administración": [
        ("c-admin",  "🏢", "Condominios",   "Datos maestros",            "pages/01_condominios.py"),
        ("c-admin",  "🔐", "Usuarios",      "Cuentas y permisos",        "pages/12_usuarios.py"),
    ],
    "👥  Unidades y Personas": [
        ("c-people", "🏠", "Unidades",      "Apartamentos y locales",    "pages/02_unidades.py"),
        ("c-people", "👥", "Propietarios",  "Registro de propietarios",  "pages/11_propietarios.py"),
        ("c-people", "👷", "Empleados",     "Personal de planta",        "pages/10_empleados.py"),
    ],
    "💰  Configuración Financiera": [
        ("c-fin",    "📊", "Alícuotas",     "% de participación",        "pages/03_alicuotas.py"),
        ("c-fin",    "💰", "Fondos",        "Fondos de reserva",         "pages/04_fondos.py"),
        ("c-fin",    "📌", "Gastos Fijos",  "Egresos recurrentes",       "pages/07_gastos_fijos.py"),
        ("c-fin",    "📋", "Conceptos",     "Ítems ingreso/egreso",      "pages/06_conceptos.py"),
        ("c-fin",    "🔧", "Servicios",     "Servicios del condominio",  "pages/05_servicios.py"),
        ("c-fin",    "⚡", "Consumo",       "Conceptos por medición",    "pages/08_conceptos_consumo.py"),
        ("c-fin",    "🏦", "Cuentas/Bancos","Cuentas y saldos",          "pages/09_cuentas_bancos.py"),
    ],
    "📄  Proveedores y Facturación": [
        ("c-prov",   "📄", "Proveedores",   "Empresas proveedoras",      "pages/13_proveedores.py"),
        ("c-prov",   "🧾", "Facturas",      "Facturas y pagos",          "pages/14_facturas.py"),
    ],
    "📈  Reportes": [
        ("c-report", "📈", "Reportes",      "Informes financieros",      "pages/15_reportes.py"),
    ],
}

COLS_PER_ROW = 4

for cat_label, items in MODULES.items():
    st.markdown(f'<div class="cat-hdr">{cat_label}</div>', unsafe_allow_html=True)

    rows = [items[i : i + COLS_PER_ROW] for i in range(0, len(items), COLS_PER_ROW)]
    for row_items in rows:
        padded = row_items + [None] * (COLS_PER_ROW - len(row_items))
        cols = st.columns(COLS_PER_ROW)
        for col, item in zip(cols, padded):
            if item is None:
                continue
            css_cls, icon, name, desc, page_path = item
            with col:
                # Card visual + st.page_link interno para mantener la sesión
                st.markdown(
                    f"""
                    <div class="mod-card {css_cls}">
                        <div class="mod-icon">{icon}</div>
                        <div class="mod-title">{name}</div>
                        <div class="mod-desc">{desc}</div>
                    """,
                    unsafe_allow_html=True,
                )
                st.page_link(page_path, label="Abrir módulo", icon=None)
                st.markdown("</div>", unsafe_allow_html=True)
