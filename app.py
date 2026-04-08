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
    # Login centrado sin scroll + un solo card
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarNavItems"],
        [data-testid="stSidebar"] { display: none !important; }
        #MainMenu, footer, header { visibility: hidden; }
        .main > div {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding-top: 0 !important;
        }
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        /* Ocultar "Press Enter to submit form" */
        input[aria-label="Contraseña"] + div { display: none !important; }
        .stTextInput div[data-baseweb="input"]::after { display: none !important; }
        [data-testid="stForm"] + div small,
        [data-testid="stForm"] ~ div [data-testid="stCaptionContainer"] { display: none !important; }
        /* Botón primario login */
        div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
            background: #1B4F72 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Un solo card centrado (max-width 420px) con logo + formulario
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="
                background: white;
                border-radius: 16px;
                padding: 40px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.10);
                max-width: 420px;
                margin: auto;
                text-align: center;
            ">
                <div style="font-size:56px; margin-bottom:8px;">🏢</div>
                <h2 style="color:#1B4F72; margin:0 0 4px 0;">
                    Sistema de Condominio</h2>
                <p style="color:#6B7280; margin:0 0 28px 0; font-size:14px;">
                    Acceso seguro para administradores y juntas</p>
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
                key="login_password",
                autocomplete="new-password",
            )
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Ingresar →",
                use_container_width=True,
                type="primary",
            )

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
                            from utils.formatters import format_mes_proceso
                            bcv_rate, bcv_source = fetch_bcv_rate()
                            st.session_state.condominio_id     = u.get("condominio_id")
                            st.session_state.condominio_nombre = condo.get("nombre", "—")
                            st.session_state.mes_proceso       = format_mes_proceso(condo.get("mes_proceso")) or ""
                            st.session_state.tasa_cambio       = bcv_rate or float(condo.get("tasa_cambio") or 0)
                            st.session_state.tasa_fuente       = bcv_source

                        st.rerun()
                    except Exception:
                        st.error("Credenciales incorrectas o usuario inactivo.")

    st.markdown(
        "<p style='text-align:center;color:#9CA3AF;font-size:10px;margin-top:12px;'>v1.0 · Sistema de Gestión de Condominios</p>",
        unsafe_allow_html=True,
    )
    st.stop()


# =============================================================================
# DASHBOARD (post-login)
# =============================================================================
from components.header import render_header
from utils.formatters import format_mes_proceso
from utils.auth import apply_condominio_to_session

# ── Admin: selección de condominio tras login (sin header, pantalla limpia) ───
if st.session_state.get("pending_admin_condominio_selection"):
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        .main > div { padding-top: 2rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="text-align:center; padding:60px 20px;">
            <div style="font-size:48px;">🏢</div>
            <h2 style="color:#1B4F72;">Seleccione un Condominio</h2>
            <p style="color:#6B7280;">
                Elija el condominio con el que desea trabajar</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    from config.supabase_client import get_supabase_client
    from repositories.condominio_repository import CondominioRepository
    repo = CondominioRepository(get_supabase_client())
    condominios = repo.get_all(solo_activos=True)
    condominios = sorted(condominios, key=lambda c: (c.get("nombre") or "").lower())
    if not condominios:
        st.warning("No hay condominios activos registrados. Cree uno en el módulo Condominios.")
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
        apply_condominio_to_session(condominios[idx]["id"])
        st.session_state.pending_admin_condominio_selection = False
        st.rerun()
    st.stop()

# render_header() solo cuando ya hay condominio seleccionado
render_header()

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
    "🗓️  Operaciones Mensuales": [
        ("c-ops",    "⚙️",  "Proceso Mensual",        "Gastos y cuotas del mes",    "pages/17_proceso_mensual.py"),
        ("c-ops",    "🔄",  "Redistribución Gastos",  "Agrupar y asignar destino",  "pages/24_redistribucion_gastos.py"),
        ("c-ops",    "🧾",  "Recibos",                "Recibo por propietario",     "pages/19_recibos.py"),
        ("c-ops",    "💳",  "Pagos",                  "Registrar cobros",           "pages/20_pagos.py"),
        ("c-ops",    "💰",  "Saldo Inicial",          "Saldos de apertura",         "pages/23_saldo_inicial.py"),
        ("c-ops",    "📋",  "Movimientos",            "Ingresos y egresos",         "pages/16_movimientos.py"),
    ],
    "📤  Estados de Cuenta": [
        ("c-report", "📑",  "Estado de Cuenta",       "Por propietario",            "pages/18_estado_cuenta.py"),
        ("c-report", "📦",  "Est. Cuenta Masivo",     "Envío masivo por email",     "pages/22_estados_cuenta_masivo.py"),
        ("c-report", "🔔",  "Notificaciones",         "Avisos a propietarios",      "pages/21_notificaciones.py"),
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
