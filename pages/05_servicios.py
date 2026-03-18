import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.servicio_repository import ServicioRepository
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

st.set_page_config(page_title="Servicios", page_icon="🔧", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Servicios")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.srv_records = None
@st.cache_resource
def get_repo():
    return ServicioRepository(get_supabase_client())

repo = get_repo()

for k, v in {"srv_modo": None, "srv_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("servicios")

if st.session_state.srv_records is None:
    with st.spinner("Cargando servicios..."):
        st.session_state.srv_records = repo.get_all(condominio_id)

records = st.session_state.srv_records

st.markdown("## 🔧 Servicios")

col_main, col_help = st.columns([3, 1])

with col_help:
    render_help_panel(
        icono="🔧",
        titulo="Servicios",
        descripcion_corta="Servicios ofrecidos por el condominio.",
        descripcion_larga=(
            "Registre los servicios que el condominio ofrece a los condóminos, "
            "como alquiler de parrillera, salón de fiestas, cancha deportiva, etc. "
            "Los cobros del servicio son variables (no se maneja un precio unitario fijo)."
        ),
        tips=[
            "El monto del servicio se registra al momento del movimiento.",
            "Desactive servicios que no estén disponibles temporalmente.",
        ],
    )

with col_main:
    render_toolbar(
        key="servicios",
        total=len(records),
        on_incluir  = lambda: st.session_state.update({"srv_modo": "incluir"}),
        on_modificar= lambda: st.session_state.update({"srv_modo": "modificar"}),
        on_eliminar = lambda: st.session_state.update({"srv_modo": "eliminar"}),
    )

    sel_idx = render_data_table(
        data=records,
        columns_config={
            "id":               {"label": "Id",             "width": 55},
            "nombre":           {"label": "Servicio",       "width": 280},
            "activo":           {"label": "Activo",         "width": 65,  "format": "boolean"},
        },
        search_field="nombre",
        key="servicios",
        empty_state_title="Este condominio no tiene servicios registrados aún",
        empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
    )
    if sel_idx is not None:
        set_current_index("servicios", sel_idx)

    check_close_detail("servicios")
    idx = get_current_index("servicios")
    current_rec = records[idx] if records and 0 <= idx < len(records) else None
    modo        = st.session_state.srv_modo

    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(f"### {'✏️ Modificar' if is_edit else '➕ Nuevo'} Servicio")
        st.markdown("<hr style='margin:4px 0 12px 0;'>", unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        with st.form("form_servicio"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre del servicio *", value=cr.get("nombre", ""), max_chars=150)
                activo = st.checkbox("Activo", value=cr.get("activo", True))
            with col2:
                st.caption("El servicio no tiene precio fijo.")

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.srv_modo = None
            st.rerun()

        if guardar:
            errors = validate_form({"nombre": nombre}, {"nombre": {"required": True, "max_length": 150}})
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {"condominio_id": condominio_id, "nombre": (nombre or "").strip(),
                           "activo": activo}
                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Servicio actualizado.")
                    else:
                        repo.create(payload)
                        st.success("✅ Servicio creado.")
                    st.session_state.srv_modo    = None
                    st.session_state.srv_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione un servicio.")
            st.session_state.srv_modo = None
        else:
            st.warning(f"⚠️ ¿Eliminar el servicio **{current_rec.get('nombre')}**?")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="srv_del_y"):
                    try:
                        repo.delete(current_rec["id"])
                        st.success("✅ Servicio eliminado.")
                        st.session_state.srv_modo    = None
                        st.session_state.srv_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="srv_del_n"):
                    st.session_state.srv_modo = None
                    st.rerun()
