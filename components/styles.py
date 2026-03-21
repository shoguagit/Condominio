"""
Estilos globales: login, tablas (Notion/Linear), skeleton, formularios,
panel de detalle slide-in, estado vacío, botón Guardar.

Uso: inject_global_styles() en header; LOGIN_CSS en app.py (login).
"""
import streamlit as st

# =============================================================================
# LOGIN — Centrado 100vh, sin scroll, ocultar hint "Press Enter"
# =============================================================================
LOGIN_CSS = """
<style>
/* Login: centrado perfecto sin scroll */
.stApp [data-testid="stAppViewContainer"] {
    height: 100vh !important;
    overflow: hidden !important;
}
.stApp .block-container {
    padding: 0 !important;
    max-width: 100% !important;
    height: 100vh !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
/* Ocultar COMPLETAMENTE el mensaje "Press Enter to submit form" */
[data-testid="stForm"] + div,
[data-testid="stForm"] ~ div[data-testid="stCaptionContainer"],
div[data-testid="stForm"] small,
p:has(+ [data-testid="stForm"]),
[data-testid="stForm"] p.stCaption {
    display: none !important;
    visibility: hidden !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #9CA3AF !important;
}
</style>
"""

# =============================================================================
# CSS: tablas corporativas, skeleton, formularios, panel detalle, vacío, botones
# =============================================================================
TABLE_FORMS_EMPTY_CSS = """
<style>
/* ── TABLA: estilo Tremor (sin bordes, header gris, filas limpias, hover sutil) ─ */
[data-testid="stDataFrame"] {
    border: none !important;
    border-radius: 0 !important;
    overflow: hidden !important;
    box-shadow: none !important;
    width: 100% !important;
}
[data-testid="stDataFrame"] table {
    border-collapse: collapse !important;
    border: none !important;
    width: 100% !important;
}
[data-testid="stDataFrame"] thead tr th {
    background: transparent !important;
    color: #6B7280 !important;
    font-weight: 500 !important;
    font-size: 12px !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    border: none !important;
    border-bottom: 1px solid #F3F4F6 !important;
    padding: 12px 16px !important;
}
[data-testid="stDataFrame"] tbody tr td {
    border: none !important;
    border-bottom: 1px solid #F3F4F6 !important;
    padding: 12px 16px !important;
    color: #374151 !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    transition: background 0.12s ease !important;
}
[data-testid="stDataFrame"] tbody tr:nth-child(even) td,
[data-testid="stDataFrame"] tbody tr:nth-child(odd) td {
    background: #FFFFFF !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: #F9FAFB !important;
}
[data-testid="stDataFrame"] tbody tr td:first-child {
    color: #6B7280 !important;
    font-weight: 400 !important;
}
[data-testid="stDataFrame"] input[type="checkbox"],
[data-testid="stDataFrame"] [role="checkbox"] {
    border-radius: 4px !important;
}
[data-testid="stDataFrame"] .stButton > button {
    background: #F4F4F5 !important;
    color: #374151 !important;
    border: 1px solid #E5E7EB !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 6px 12px !important;
    box-shadow: none !important;
    border-radius: 6px !important;
}
[data-testid="stDataFrame"] .stButton > button:hover {
    background: #E4E4E7 !important;
    color: #1F2937 !important;
    border-color: #D1D5DB !important;
}

/* ── SKELETON LOADER (shimmer) ───────────────────────────────────────────── */
@keyframes skeletonShimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
.skeleton-table {
    border-radius: 12px;
    overflow: hidden;
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.skeleton-row {
    display: flex;
    align-items: center;
    min-height: 52px;
    border-bottom: 1px solid #F0F0F0;
    padding: 0 14px;
}
.skeleton-row:last-child { border-bottom: none; }
.skeleton-cell {
    height: 18px;
    border-radius: 6px;
    background: linear-gradient(
        90deg,
        #E8E8E8 0%,
        #F5F5F5 50%,
        #E8E8E8 100%
    );
    background-size: 200% 100%;
    animation: skeletonShimmer 1.5s ease-in-out infinite;
}
.skeleton-cell.id { width: 48px; margin-right: 16px; flex-shrink: 0; }
.skeleton-cell.short { flex: 0 0 120px; max-width: 120px; margin-right: 16px; }
.skeleton-cell.medium { flex: 1; min-width: 100px; margin-right: 16px; }
.skeleton-cell.long { flex: 2; min-width: 160px; }

/* ── CONTENEDORES: tabla vs formulario (reemplazo con fade) ────────────────── */
.table-container {
    animation: fadeIn 0.3s ease forwards;
}
.form-replace-container {
    animation: fadeIn 0.3s ease forwards;
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}

/* ── PANEL DETALLE: slide-in desde la derecha + overlay ────────────────────── */
/* Overlay visual que también permite cerrar el panel al hacer clic. */
.detail-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.35);
    z-index: 999;
    animation: overlayFadeIn 0.25s ease forwards;
    pointer-events: auto;
}
.detail-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: 420px;
    max-width: 100vw;
    height: 100vh;
    background: #FFFFFF;
    box-shadow: -4px 0 24px rgba(0,0,0,0.12);
    z-index: 1000;
    overflow-y: auto;
    animation: panelSlideIn 0.3s ease forwards;
}
@keyframes overlayFadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes panelSlideIn {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
}
.detail-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid #F0F0F0;
    background: #FAFAFA;
}
.detail-panel-title { font-size: 15px; font-weight: 600; color: #1B4F72; margin: 0; }
.detail-panel-close {
    width: 32px;
    height: 32px;
    border: none;
    background: #EEEEEE;
    color: #5D6D7E;
    font-size: 18px;
    line-height: 1;
    border-radius: 8px;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s, color 0.2s;
}
.detail-panel-close:hover {
    background: #E0E0E0;
    color: #2C3E50;
}
/* Botón × de Streamlit posicionado sobre el panel (evita link que pierde sesión) */
.detail-panel-close-anchor { display: none !important; }
.detail-panel-close-anchor ~ div [data-testid="stButton"] button {
    position: fixed !important;
    right: 20px !important;
    top: 20px !important;
    z-index: 1001 !important;
    width: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    font-size: 20px !important;
    line-height: 1 !important;
    border-radius: 8px !important;
    background: #EEEEEE !important;
    color: #5D6D7E !important;
    border: none !important;
}
.detail-panel-close-anchor ~ div [data-testid="stButton"] button:hover {
    background: #E0E0E0 !important;
    color: #2C3E50 !important;
}
.detail-panel-body { padding: 20px; }
.detail-panel-row {
    padding: 10px 0;
    border-bottom: 1px solid #F5F5F5;
    font-size: 13px;
}
.detail-panel-row:last-child { border-bottom: none; }
.detail-panel-label { color: #9CA3AF; font-weight: 500; margin-bottom: 2px; }
.detail-panel-value { color: #2C3E50; }

/* ── FORMULARIOS: aspecto corporativo (bordes definidos) ──────────────────── */
[data-testid="stForm"] {
    animation: formSlideDown 0.3s ease forwards;
}
@keyframes formSlideDown {
    from { opacity: 0; transform: translateY(-6px); }
    to   { opacity: 1; transform: translateY(0); }
}
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    border: 1px solid #D5D8DC !important;
    border-radius: 6px !important;
    background: #FFFFFF !important;
    color: #1C2833 !important;
    font-size: 13px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-baseweb="input"] input:focus,
[data-baseweb="textarea"] textarea:focus {
    border-color: #1B4F72 !important;
    box-shadow: 0 0 0 2px rgba(27,79,114,0.12) !important;
    outline: none !important;
}
[data-testid="stWidgetLabel"] {
    font-size: 12px !important;
    color: #2C3E50 !important;
    font-weight: 600 !important;
}

/* ── BOTONES — alta especificidad para sobreescribir Streamlit ── */
div[data-testid="stButton"] > button,
div[data-testid="stButton"] > button:focus,
div[data-testid="stButton"] > button:active,
section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    background-color: #1B4F8A !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.5rem 1.2rem !important;
}

div[data-testid="stButton"] > button:hover {
    background-color: #163d6e !important;
    color: #FFFFFF !important;
}

div[data-testid="stButton"] > button:disabled,
div[data-testid="stButton"] > button[disabled] {
    background-color: #8BA8C8 !important;
    color: #FFFFFF !important;
    opacity: 0.7 !important;
}

/* ── FORMULARIOS: secciones con subtítulo (Fase 2) ─────────────────────────── */
.form-section-hdr {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #1B4F72;
    margin: 16px 0 8px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid #E8E8E8;
}
.form-section-hdr:first-child { margin-top: 0; }
.form-card-title { font-size: 1rem; font-weight: 700; color: #1C2833; margin: 0 0 4px 0; }
.form-card-hint { font-size: 11px; color: #5D6D7E; margin: 0 0 12px 0; }

/* Breadcrumb: Inicio en azul clickeable */
.breadcrumb-wrap a { color: #2E86C1 !important; font-size: 12px !important; text-decoration: none !important; font-weight: 500 !important; }
.breadcrumb-wrap a:hover { text-decoration: underline !important; }

/* ── CRUD TABLE: estilo Tremor (sin bordes, header gris, filas limpias, hover sutil) ─ */
.table-root {
    width: 100%;
    margin-bottom: 1rem;
    font-size: 13px;
    border: none;
}
.table-caption {
    font-size: 12px;
    color: #6B7280;
    margin-bottom: 10px;
    padding: 0 2px;
}
.table-header-row,
.table-body-row {
    display: flex;
    align-items: stretch;
    border-bottom: 1px solid #F3F4F6;
    min-height: 44px;
}
.table-header-row {
    background: transparent;
}
.table-body-row:hover {
    background: #F8FAFC;
}
.table-th,
.table-td {
    padding: 12px 16px;
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 0;
}
.table-th {
    color: #6B7280;
    background: transparent;
    font-weight: 500;
    font-size: 12px;
    border-bottom: 1px solid #F3F4F6;
    text-transform: none;
    letter-spacing: 0;
}
.table-td {
    color: #374151;
    font-weight: 400;
}
.table-row-selected .table-td {
    background: #EBF5FB;
}
.table-td.text-right,
.table-th.text-right { justify-content: flex-end; text-align: right; }
.table-actions { flex: 0 0 180px; justify-content: flex-end; gap: 4px; min-width: 160px; }
.table-actions .stButton { margin-left: 2px; }
/* Botones de acción: estilo Tremor, legibles (fondo claro, texto oscuro) */
.table-root .table-actions .stButton > button,
.table-root .stButton > button {
    background: #F4F4F5 !important;
    color: #374151 !important;
    border: 1px solid #E5E7EB !important;
    font-weight: 500 !important;
    font-size: 12px !important;
    padding: 6px 12px !important;
    box-shadow: none !important;
}
.table-root .table-actions .stButton > button:hover,
.table-root .stButton > button:hover {
    background: #E4E4E7 !important;
    color: #1F2937 !important;
    border-color: #D1D5DB !important;
}
/* Botones de acción por fila: solo ícono, ancho fijo 40px */
.record-table-actions-row .stButton > button {
    min-width: 40px !important;
    width: 40px !important;
    padding: 6px !important;
}
/* Footer/totales: texto gris, separador sutil, sin fondo llamativo */
.table-foot .table-td,
.table-foot .table-th {
    border-top: 1px solid #E5E7EB;
    color: #6B7280;
    font-weight: 500;
    background: transparent;
}

/* Tabla HTML Tremor: 100% ancho, sin bordes externos, header gris, separadores sutiles */
.table-root table.tremor-table {
    width: 100%;
    border-collapse: collapse;
    border: none;
    font-size: 13px;
}
.table-root table.tremor-table thead tr th {
    background: transparent;
    color: #6B7280;
    font-weight: 500;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #F3F4F6;
    padding: 12px 16px;
    text-align: left;
}
.table-root table.tremor-table thead tr th.text-right { text-align: right; }
.table-root table.tremor-table tbody tr td {
    border: none;
    border-bottom: 1px solid #F3F4F6;
    padding: 12px 16px;
    color: #374151;
    font-weight: 400;
    transition: background 0.12s ease;
}
.table-root table.tremor-table tbody tr:hover td {
    background: #F8FAFC;
}
.table-root table.tremor-table tbody tr td.text-right { text-align: right; }
.table-root table.tremor-table .table-actions-col {
    white-space: nowrap;
    color: #6B7280;
    font-size: 12px;
}
.table-action-link {
    color: #4B5563;
    text-decoration: none;
    margin-right: 8px;
}
.table-action-link:hover {
    color: #1F2937;
    text-decoration: underline;
}

/* ── Columnas especiales: checkbox, ID, Acciones ───────────────────────────── */
.table-th-checkbox,
.table-td-checkbox {
    flex: 0 0 32px;
    max-width: 32px;
    text-align: center;
    justify-content: center;
    color: #6B7280;
}
.table-th-id,
.table-td-id {
    flex: 0 0 60px;
    max-width: 60px;
    color: #9CA3AF;
}
.table-th-actions,
.table-td-actions {
    flex: 0 0 150px;
    max-width: 150px;
    justify-content: flex-end;
}
.table-actions-inline {
    display: inline-flex;
    gap: 4px;
    align-items: center;
}
.action-ghost {
    font-size: 12px;
    color: #6B7280;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 4px;
}
.action-ghost:hover {
    background: #E5E7EB;
    color: #111827;
}
.action-ghost.action-danger {
    color: #E74C3C;
}
.action-ghost.action-danger:hover {
    background: #FDEDEC;
    color: #C0392B;
}

/* ── Badges Activo / Inactivo ─────────────────────────────────────────────── */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;
}
.badge-activo {
    background: #D1FAE5;
    color: #065F46;
}
.badge-inactivo {
    background: #F3F4F6;
    color: #6B7280;
}

/* ── CRUD CARDS: lista de registros en cards (sin grid) ────────────────────── */
.record-card {
    background: #FFFFFF;
    border: 1px solid #E8E8E8;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.record-card:hover {
    border-color: #1B4F72;
    box-shadow: 0 4px 12px rgba(27,79,114,0.08);
}
.record-card-title {
    font-size: 14px;
    font-weight: 700;
    color: #1C2833;
    margin: 0 0 8px 0;
    line-height: 1.3;
}
.record-card-subtitle {
    font-size: 12px;
    color: #5D6D7E;
    line-height: 1.5;
    margin: 0;
}

/* ── ESTADO VACÍO (mensaje simple y corporativo) ───────────────────────────── */
.empty-state {
    text-align: center;
    padding: 32px 24px;
    color: #5D6D7E;
    font-family: inherit;
    background: #FAFAFA;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
}
.empty-state-icon {
    font-size: 2rem;
    line-height: 1;
    margin-bottom: 12px;
    opacity: 0.8;
}
.empty-state-title {
    font-size: 14px;
    font-weight: 600;
    color: #2C3E50;
    margin: 0 0 4px 0;
}
.empty-state-subtitle {
    font-size: 12px;
    color: #5D6D7E;
    margin: 0;
    max-width: 280px;
    margin-left: auto;
    margin-right: auto;
}

/* ── FIX BOTONES ANCHO COMPLETO ── */
button[kind="primary"],
button[kind="secondary"],
.stButton button,
[data-testid="stButton"] button,
[data-baseweb="button"],
div[data-testid="stButton"] button:not(:disabled) {
    color: #FFFFFF !important;
}

/* Botón deshabilitado: texto gris claro legible */
div[data-testid="stButton"] button:disabled {
    color: #CCCCCC !important;
}
</style>
"""


def inject_global_styles() -> None:
    """Inyecta en la página el CSS de tablas, skeleton, formularios y estado vacío."""
    st.markdown(TABLE_FORMS_EMPTY_CSS, unsafe_allow_html=True)


def render_table_skeleton(
    column_count: int = 6,
    row_count: int = 5,
    column_widths: list[str] | None = None,
) -> None:
    """
    Muestra un skeleton loader con filas animadas (shimmer) mientras cargan los datos.
    Mismo layout visual que una tabla: N columnas, M filas.

    column_count: número de columnas (por defecto 6).
    row_count: número de filas esqueleto (por defecto 5).
    column_widths: opcional. Lista de clases por columna: "id", "short", "medium", "long".
    """
    if column_widths and len(column_widths) >= column_count:
        classes = column_widths[:column_count]
    else:
        classes = ["id"] + ["medium"] * (column_count - 1)

    rows_html = ""
    for _ in range(row_count):
        cells = "".join(
            f'<div class="skeleton-cell {cls}"></div>' for cls in classes
        )
        rows_html += f'<div class="skeleton-row">{cells}</div>'

    st.markdown(
        f'<div class="skeleton-table">{rows_html}</div>',
        unsafe_allow_html=True,
    )


def render_empty_state(
    icon: str = "📋",
    title: str = "No hay registros aún",
    subtitle: str = "Haz click en + Incluir para agregar el primero.",
) -> None:
    """
    Muestra el estado vacío de una tabla: ícono grande, título y subtexto.
    Colores grises suaves, no deprimentes.
    """
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-icon">{icon}</div>
            <p class="empty-state-title">{title}</p>
            <p class="empty-state-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
