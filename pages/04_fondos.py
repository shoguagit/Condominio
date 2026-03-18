import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.fondo_repository import FondoRepository
from repositories.alicuota_repository import AlicuotaRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import render_toolbar, init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.data_table import render_data_table
from components.detail_panel import check_close_detail
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form
from utils.formatters import format_currency

st.set_page_config(page_title="Fondos", page_icon="💰", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Fondos")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.fond_records = None
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return FondoRepository(client), AlicuotaRepository(client)

repo, repo_ali = get_repos()

for k, v in {"fond_modo": None, "fond_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("fondos")

@st.cache_data(ttl=120)
def load_alicuotas():
    return repo_ali.get_all(condominio_id, solo_activos=True)

def load():
    with st.spinner("Cargando fondos..."):
        return repo.get_all(condominio_id)

if st.session_state.fond_records is None:
    st.session_state.fond_records = load()

records   = st.session_state.fond_records
alicuotas = load_alicuotas()

TIPOS_FONDO = ["Reserva", "Operación", "Mantenimiento", "Emergencia", "Otro"]

st.markdown("## 💰 Fondos")

col_main, col_help = st.columns([3, 1])

with col_help:
    render_help_panel(
        icono="💰",
        titulo="Fondos",
        descripcion_corta="Fondos de reserva y operación del condominio.",
        descripcion_larga=(
            "Los fondos agrupan recursos financieros por propósito: "
            "reserva para imprevistos, operación mensual, mantenimiento, etc. "
            "Cada fondo está asociado a una alícuota para distribuir su costo."
        ),
        tips=[
            "El saldo inicial se registra una sola vez al crear el fondo.",
            "El saldo actual se actualiza según los movimientos del mes.",
            "Asocie cada fondo a la alícuota correspondiente.",
        ],
    )
    if records:
        total_fondos = sum(float(r.get("saldo") or 0) for r in records if r.get("activo"))
        st.markdown(
            f"<div style='background:#EBF5FB;border-radius:8px;padding:12px;"
            f"font-size:12px;color:#2C3E50;margin-top:8px;'>"
            f"<b>Total en fondos:</b><br>"
            f"<span style='font-size:16px;font-weight:700;color:#1B4F72;'>"
            f"{format_currency(total_fondos)}</span></div>",
            unsafe_allow_html=True,
        )

with col_main:
    render_toolbar(
        key="fondos",
        total=len(records),
        on_incluir  = lambda: st.session_state.update({"fond_modo": "incluir"}),
        on_modificar= lambda: st.session_state.update({"fond_modo": "modificar"}),
        on_eliminar = lambda: st.session_state.update({"fond_modo": "eliminar"}),
    )

    for r in records:
        r["_alicuota"] = (r.get("alicuotas") or {}).get("descripcion", "—")

    sel_idx = render_data_table(
        data=records,
        columns_config={
            "id":           {"label": "Id",           "width": 55},
            "nombre":       {"label": "Fondo",        "width": 200},
            "_alicuota":    {"label": "Alícuota",     "width": 180},
            "saldo_inicial":{"label": "Saldo Inicial","width": 110, "format": "currency"},
            "saldo":        {"label": "Saldo Actual", "width": 110, "format": "currency"},
            "tipo":         {"label": "Tipo",         "width": 110},
            "activo":       {"label": "Activo",       "width": 65,  "format": "boolean"},
        },
        search_field="nombre",
        key="fondos",
        empty_state_title="Este condominio no tiene fondos registrados aún",
        empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
    )
    if sel_idx is not None:
        set_current_index("fondos", sel_idx)

    check_close_detail("fondos")
    idx = get_current_index("fondos")
    current_rec = records[idx] if records and 0 <= idx < len(records) else None
    modo        = st.session_state.fond_modo

    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(f"### {'✏️ Modificar' if is_edit else '➕ Nuevo'} Fondo")
        st.markdown("<hr style='margin:4px 0 12px 0;'>", unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        ali_nombres = [a["descripcion"] for a in alicuotas]
        ali_ids     = [a["id"]          for a in alicuotas]
        def_ali_id  = cr.get("alicuota_id")
        try:
            ali_default = ali_ids.index(def_ali_id) if def_ali_id in ali_ids else 0
        except (ValueError, TypeError):
            ali_default = 0

        tipo_default = TIPOS_FONDO.index(cr["tipo"]) if cr.get("tipo") in TIPOS_FONDO else 0

        with st.form("form_fondo"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre del fondo *", value=cr.get("nombre", ""), max_chars=150)
                tipo   = st.selectbox("Tipo de fondo", options=TIPOS_FONDO, index=tipo_default)
                activo = st.checkbox("Activo", value=cr.get("activo", True))
            with col2:
                if not alicuotas:
                    st.warning("⚠️ No hay alícuotas activas. Créelas primero.")
                    alicuota_id = None
                else:
                    ali_sel     = st.selectbox("Alícuota asociada *", options=ali_nombres, index=ali_default)
                    alicuota_id = ali_ids[ali_nombres.index(ali_sel)]

                saldo_inicial = st.number_input(
                    "Saldo inicial",
                    value=float(cr.get("saldo_inicial") or 0),
                    min_value=0.0, step=0.01, format="%.2f",
                    disabled=is_edit,
                    help="Solo se define al crear el fondo.",
                )
                cantidad = st.number_input(
                    "Cantidad",
                    value=float(cr.get("cantidad") or 0),
                    min_value=0.0, step=0.0001, format="%.4f",
                )

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.fond_modo = None
            st.rerun()

        if guardar:
            errors = validate_form(
                {"nombre": nombre, "alicuota_id": alicuota_id},
                {
                    "nombre":      {"required": True, "max_length": 150},
                    "alicuota_id": {"required": True},
                },
            )
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {
                    "condominio_id": condominio_id,
                    "nombre":        (nombre or "").strip(),
                    "alicuota_id":   alicuota_id,
                    "tipo":          tipo,
                    "cantidad":      cantidad,
                    "activo":        activo,
                }
                if not is_edit:
                    payload["saldo_inicial"] = saldo_inicial
                    payload["saldo"]         = saldo_inicial
                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Fondo actualizado.")
                    else:
                        repo.create(payload)
                        st.success("✅ Fondo creado.")
                    st.session_state.fond_modo    = None
                    st.session_state.fond_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione un fondo para eliminar.")
            st.session_state.fond_modo = None
        else:
            st.warning(f"⚠️ ¿Eliminar el fondo **{current_rec.get('nombre')}**?")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="fond_del_yes"):
                    try:
                        repo.delete(current_rec["id"])
                        st.success("✅ Fondo eliminado.")
                        st.session_state.fond_modo    = None
                        st.session_state.fond_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="fond_del_no"):
                    st.session_state.fond_modo = None
                    st.rerun()
