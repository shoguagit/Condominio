"""
Sidebar de navegación corporativo y CSS global del sistema.
Paleta: blanco puro + azules corporativos cálidos. Texto oscuro siempre visible.
"""
import streamlit as st

# =============================================================================
# PALETA CORPORATIVA
#   Fondo:        #FFFFFF  (blanco puro)
#   Superficie:   #F4F9FD  (azul muy suave)
#   Primario:     #1F618D  (azul corporativo cálido)
#   Medio:        #2471A3
#   Claro:        #2E86C1
#   Activo bg:    #EBF5FB
#   Borde:        #D6EAF8
#   Texto oscuro: #1C2833
#   Texto medio:  #2C3E50
#   Texto suave:  #5D6D7E
# =============================================================================
GLOBAL_CSS = """
<style>
/* ── Ocultar nav automático de Streamlit ────────────── */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavSeparator"],
div[data-testid="stSidebarNav"] { display: none !important; }

/* ── Base y layout (ancho completo para listados) ─────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1rem 1.8rem 1.8rem !important; max-width: 100% !important; width: 100% !important; }
[data-testid="stAppViewContainer"] { max-width: 100% !important; }
body, .stApp, .main > div { background-color: #FFFFFF !important; }
/* Columnas de tabla: permitir que flex use bien el espacio */
.record-table-actions-row [data-testid="column"] > div { min-width: 0 !important; }

/* Sidebar: ancho mínimo para que no colapse por completo (usuario puede reabrir con flecha) */
section[data-testid="stSidebar"] {
    min-width: 250px !important;
}

/* ── Tipografía global (más compacta) ───────────────── */
html, body, .stApp { font-size: 13px !important; }
h1 { font-size: 1.3rem !important; font-weight: 700 !important; color: #1A5276 !important; }
h2 { font-size: 1.1rem !important; font-weight: 700 !important; color: #1A5276 !important; }
h3 { font-size: 1rem !important;   font-weight: 600 !important; color: #1A5276 !important; }
p  { font-size: 13px !important; color: #2C3E50; }

/* ── Header corporativo global ─────────────────────────────────────────────── */
.main-header {
    background: #1B4F72;
    color: #FFFFFF;
    padding: 10px 18px;
    border-radius: 10px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.20);
}
.mh-left {
    display: flex;
    align-items: center;
    gap: 10px;
}
.mh-logo {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: linear-gradient(135deg, #2E86C1, #1B4F72);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
}
.mh-condo-name {
    font-weight: 700;
    font-size: 14px;
    letter-spacing: -0.2px;
}
.mh-right {
    display: flex;
    align-items: center;
    gap: 12px;
}
.mh-item {
    display: flex;
    flex-direction: column;
}
.mh-item-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    color: #AED6F1;
}
.mh-item-value {
    font-size: 12px;
    font-weight: 600;
    color: #FFFFFF;
}
.mh-user .mh-item-value {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}
.mh-role-badge {
    display: inline-block;
    color: #FFFFFF;
    padding: 2px 9px;
    border-radius: 999px;
    font-size: 10px;
    font-weight: 700;
}
.mh-separator {
    width: 1px;
    height: 26px;
    background: #2E86C1;
    opacity: 0.9;
}
/* ── Labels de inputs — SIEMPRE oscuros y legibles ──── */
label,
.stTextInput  > label,
.stTextArea   > label,
.stSelectbox  > label,
.stNumberInput > label,
.stCheckbox   > label,
.stRadio      > label,
.stDateInput  > label,
.stTimeInput  > label,
.stMultiSelect > label,
[data-testid="stWidgetLabel"] {
    color: #2C3E50 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
}

/* ── Inputs ──────────────────────────────────────────── */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background: #FFFFFF !important;
    color: #1C2833 !important;
    border-color: #AED6F1 !important;
    border-radius: 6px !important;
    font-size: 13px !important;
}
[data-baseweb="input"] input:focus,
[data-baseweb="textarea"] textarea:focus {
    border-color: #2471A3 !important;
    box-shadow: 0 0 0 2px rgba(36,113,163,0.15) !important;
}
/* Select */
[data-baseweb="select"] { border-radius: 6px !important; }
[data-baseweb="select"] div { color: #1C2833 !important; font-size: 13px !important; }

/* ── Sidebar ─────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #1B4F72 !important;
    border-right: none !important;
}
section[data-testid="stSidebar"] > div:first-child {
    background: #1B4F72 !important;
    padding-top: 0 !important;
}
/* Textos base en sidebar: por defecto tonos claros para buen contraste */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
    color: #AED6F1 !important;
}

/* ── Links de navegación en sidebar ────────────────── */
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
    color: #EAF2F8 !important;
    background: transparent !important;
    border-radius: 6px !important;
    padding: 6px 12px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
    margin: 1px 0 !important;
    display: flex !important;
    align-items: center !important;
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] * {
    color: #EAF2F8 !important;
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover {
    background: #2E86C1 !important;
    color: #FFFFFF !important;
    text-decoration: none !important;
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover * {
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] {
    background: #2E86C1 !important;
    color: #FFFFFF !important;
    border-left: 3px solid #AED6F1 !important;
    padding-left: 9px !important;
    font-weight: 700 !important;
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] * {
    color: #FFFFFF !important;
}
/* Ocultar ícono externo de page_link */
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] svg {
    display: none !important;
}

/* ── Botón logout en sidebar ────────────────────────── */
section[data-testid="stSidebar"] .stButton > button {
    background: #FDEDEC !important;
    color: #C0392B !important;
    border: 1px solid #F5B7B1 !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    transition: all 0.15s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #FADBD8 !important;
    color: #922B21 !important;
}

/* ── Dividers en sidebar ────────────────────────────── */
section[data-testid="stSidebar"] hr {
    border-color: #D6EAF8 !important;
    margin: 8px 0 !important;
}

/* ── Botones globales (alineados con styles.py) ───────────────────────────── */
.stButton > button[kind="primary"] {
    background: #1B4F72 !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    color: #FFFFFF !important;
    transition: background 0.2s ease, box-shadow 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    background: #154360 !important;
    box-shadow: 0 2px 8px rgba(27,79,114,0.25) !important;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: #1B4F72 !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    color: #FFFFFF !important;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
    background: #154360 !important;
}

/* Tablas: ver components.styles (borderless, hover, fade-in) */

/* ── Expanders ───────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #D6EAF8 !important;
    border-radius: 8px !important;
    background: white !important;
}

/* ── Tabs ────────────────────────────────────────────── */
[data-testid="stTabs"] [data-testid="stTab"] {
    font-weight: 500;
    font-size: 14px;
    color: #2C3E50;
}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
    color: #1F618D !important;
    border-bottom-color: #2471A3 !important;
}

/* ── Dashboard: module cards (corporativas, borde izquierdo sutil) ─────────── */
.mod-card {
    background: #FFFFFF;
    border-radius: 8px;
    padding: 18px 16px 14px;
    border: 1px solid #E5E7EB;
    border-left: 4px solid #2E86C1;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
    cursor: default;
    margin-bottom: 8px;
    min-height: 92px;
}
.mod-card:hover {
    border-color: #2E86C1;
    border-left-color: #2E86C1;
    box-shadow: 0 4px 12px rgba(27,79,114,0.12);
}
/* Unificado: mismo borde para todas las categorías */
.mod-card.c-admin,
.mod-card.c-people,
.mod-card.c-fin,
.mod-card.c-prov,
.mod-card.c-report { border-left-color: #2E86C1; }

.mod-icon  { font-size: 1.5rem; line-height: 1; margin-bottom: 6px; color: #1B4F72; }
.mod-title { font-size: 13px; font-weight: 700; color: #1C2833; margin: 0; line-height: 1.25; }
.mod-desc  { font-size: 11px; color: #5D6D7E; margin-top: 2px; line-height: 1.4; }

/* Botón "Abrir módulo" en dashboard: estilo primario corporativo */
.block-container .mod-card + div a[data-testid="stPageLink-NavLink"],
.block-container div:has(.mod-card) + div a {
    display: inline-block !important;
    background: #2E86C1 !important;
    color: #FFFFFF !important;
    padding: 6px 14px !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-decoration: none !important;
    transition: background 0.2s ease !important;
}
.block-container .mod-card + div a[data-testid="stPageLink-NavLink"]:hover,
.block-container div:has(.mod-card) + div a:hover {
    background: #1B4F72 !important;
    color: #FFFFFF !important;
}

/* ── Dashboard: KPI strip (contexto corporativo) ────────────────────────────── */
.kpi-strip {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    margin-bottom: 14px;
}
.kpi-item { flex: 1; text-align: center; padding: 0 12px; }
.kpi-item + .kpi-item { border-left: 1px solid #E8E8E8; }
.kpi-val { font-size: 13px; font-weight: 700; color: #1B4F72; line-height: 1.05; }
.kpi-lbl {
    font-size: 10px;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-top: 2px;
}

/* ── Dashboard: accesos rápidos en chips/pills ─────────────────────────────── */
.quick-links-marker { display:none; }
.quick-links-marker + div[data-testid="stHorizontalBlock"] a[data-testid="stPageLink-NavLink"],
.quick-links-marker + div[data-testid="stHorizontalBlock"] a {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    background: #EBF5FB !important;
    color: #1B4F72 !important;
    border-radius: 20px !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    text-decoration: none !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    width: 100% !important;
}
.quick-links-marker + div[data-testid="stHorizontalBlock"] a:hover {
    background: #2E86C1 !important;
    color: #FFFFFF !important;
}
.quick-links-marker + div[data-testid="stHorizontalBlock"] a:hover * {
    color: #FFFFFF !important;
}

/* ── Dashboard: category header ───────────────────────────────────────────── */
.cat-hdr {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #1B4F72;
    padding: 16px 0 8px;
    border-bottom: 1px solid #D5D8DC;
    margin-bottom: 10px;
}

/* ── Spinner de carga en cambio de página ────────────── */
@keyframes _spin { to { transform: rotate(360deg); } }

/* Overlay blanco semitransparente mientras Streamlit recarga */
[data-testid="stApp"][data-stale="true"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background: rgba(255,255,255,0.75);
    z-index: 9998;
    backdrop-filter: blur(1px);
}
/* Spinner azul girando en el centro */
[data-testid="stApp"][data-stale="true"]::after {
    content: '';
    position: fixed;
    top: 50%;
    left: 50%;
    width: 44px;
    height: 44px;
    margin: -22px 0 0 -22px;
    border: 4px solid #D6EAF8;
    border-top-color: #2471A3;
    border-radius: 50%;
    z-index: 9999;
    animation: _spin 0.75s linear infinite;
}

/* Ocultar el spinner nativo de Streamlit (ya tenemos el nuestro) */
[data-testid="stStatusWidget"] { display: none !important; }

/* Fade-in suave al cargar cada página */
.block-container {
    animation: _fadeIn 0.25s ease;
}
@keyframes _fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
"""


def render_sidebar() -> None:
    """
    Renderiza el sidebar de navegación corporativo.
    Llamado desde render_header() al inicio de cada página.
    """
    from utils.auth import logout

    condominio = st.session_state.get("condominio_nombre", "—")
    email      = st.session_state.get("user_email", "—")
    rol        = st.session_state.get("user_role", "operador")
    if rol == "consulta":
        rol = "operador"

    rol_bg = {
        "admin":    "#28B463",
        "operador": "#2471A3",
    }.get(rol, "#717D7E")
    rol_label = {
        "admin":    "Administrador",
        "operador": "Operador",
    }.get(rol, rol)

    def _group(title: str) -> None:
        st.markdown(
            f'<p style="font-size:11px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.8px;color:#AED6F1;padding:10px 4px 3px;margin:0;'
            f'border-top:1px solid #2E86C1;margin-top:6px;">'
            f'{title}</p>',
            unsafe_allow_html=True,
        )

    with st.sidebar:
        # ── Brand ──────────────────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="padding:16px 12px 14px;
                        background:#1B4F72;
                        margin-bottom:8px;">
                <div style="font-size:1.8rem; line-height:1;">🏢</div>
                <div style="font-weight:700; color:#FFFFFF; font-size:13px;
                            margin-top:6px; line-height:1.3; word-break:break-word;">
                    {condominio}
                </div>
                <div style="font-size:10px; color:#AED6F1; margin-top:3px;">
                    {email}
                </div>
                <span style="display:inline-block; font-size:10px; font-weight:700;
                             color:#FFFFFF; background:{rol_bg};
                             padding:2px 9px; border-radius:10px; margin-top:5px;">
                    {rol_label}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── General ────────────────────────────────────────────────────────────
        _group("General")
        st.page_link("app.py",                        label="🏠  Inicio")
        st.page_link("pages/01_condominios.py",       label="🏢  Condominios")
        st.page_link("pages/12_usuarios.py",          label="🔐  Usuarios")

        _group("Unidades y Personas")
        st.page_link("pages/02_unidades.py",          label="🏠  Unidades")
        st.page_link("pages/11_propietarios.py",      label="👥  Propietarios")
        st.page_link("pages/10_empleados.py",         label="👷  Empleados")

        _group("Configuración Financiera")
        st.page_link("pages/03_alicuotas.py",         label="📊  Alícuotas")
        st.page_link("pages/06_conceptos.py",         label="📋  Conceptos")
        st.page_link("pages/05_servicios.py",         label="🔧  Servicios")
        st.page_link("pages/07_gastos_fijos.py",      label="📌  Gastos Fijos")

        _group("Operación mensual")
        st.page_link("pages/20_pagos.py",             label="💳  Pagos y Cobros")
        st.page_link("pages/16_movimientos.py",       label="🏦  Movimientos Bancarios")
        st.page_link("pages/17_proceso_mensual.py",   label="🗓️  Proceso Mensual")
        st.page_link("pages/18_estado_cuenta.py",     label="🧾  Estado de Cuenta")
        st.page_link("pages/08_conceptos_consumo.py", label="⚡  Consumo")
        st.page_link("pages/09_cuentas_bancos.py",    label="🏦  Cuentas / Bancos")

        _group("Proveedores")
        st.page_link("pages/13_proveedores.py",       label="📄  Proveedores")
        st.page_link("pages/14_facturas.py",          label="🧾  Facturas")

        _group("Reportes")
        st.page_link("pages/19_recibos.py",           label="🧾  Recibos")
        st.page_link("pages/15_reportes.py",          label="📈  Reportes")

        # ── Logout ─────────────────────────────────────────────────────────────
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.divider()
        if st.button("🚪  Cerrar sesión", use_container_width=True, key="_sidebar_logout"):
            logout()
