import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.propietario_repository import PropietarioRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.record_table import render_record_table
from components.detail_panel import check_close_detail, render_detail_panel
from components.styles import render_table_skeleton
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form

st.set_page_config(page_title="Propietarios", page_icon="👥", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Propietarios")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.prop_records = None

# Sin cache_resource: si cambia el repository, la instancia no debe quedar desactualizada.
repo = PropietarioRepository(get_supabase_client())

for k, v in {"prop_modo": None, "prop_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("propietarios")

def load_propietarios():
    return repo.get_all(condominio_id)

PROP_COLUMNS = {
    "id":       {"label": "Id",           "width": 55},
    "nombre":   {"label": "Nombre",       "width": 230},
    "cedula":   {"label": "Cédula / Doc", "width": 130},
    "telefono": {"label": "Teléfono",     "width": 120},
    "correo":   {"label": "Correo",       "width": 190},
    "activo":   {"label": "Activo",       "width": 65, "format": "boolean"},
}

st.markdown("## 👥 Propietarios")

col_main, col_help = st.columns([4, 1])

if st.session_state.prop_records is None:
    with col_main:
        render_table_skeleton(column_count=3, row_count=6)
    st.session_state.prop_records = load_propietarios()
    st.rerun()

records = st.session_state.prop_records

with col_help:
    render_help_panel(
        icono="👥",
        titulo="Propietarios",
        descripcion_corta="Propietarios y condóminos registrados.",
        descripcion_larga=(
            "Registre los propietarios o arrendatarios de las unidades "
            "del condominio. Sus datos son utilizados en estados de cuenta, "
            "notificaciones y reportes de gestión."
        ),
        tips=[
            "Un propietario puede tener varias unidades asignadas.",
            "La cédula / documento identifica únicamente a cada propietario.",
            "Use 'Inactivo' para propietarios que ya no residen aquí.",
        ],
    )
    render_help_shortcuts({
        "Nuevo":       "Registrar nuevo propietario",
        "Ver":        "Ver detalle en panel lateral",
        "Editar":     "Editar en cada tarjeta",
        "Eliminar":   "Eliminar (confirmación)",
    })

with col_main:
    check_close_detail("propietarios")
    current_idx = get_current_index("propietarios")
    current_rec = records[current_idx] if records and 0 <= current_idx < len(records) else None
    modo        = st.session_state.prop_modo

    # ── Lista de cards (solo cuando no hay formulario ni eliminación) ─────────
    if modo not in ("incluir", "modificar", "eliminar"):
        render_record_table(
            data=records,
            key="propietarios",
            columns_config=PROP_COLUMNS,
            search_field="nombre",
            caption="Listado de propietarios",
            modo_key="prop_modo",
            on_incluir=lambda: st.session_state.update({"prop_modo": "incluir"}),
            on_modificar=lambda: st.session_state.update({"prop_modo": "modificar"}),
            on_eliminar=lambda: st.session_state.update({"prop_modo": "eliminar"}),
            empty_state_icon="👥",
            empty_state_title="Este condominio no tiene propietarios registrados aún",
            empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
            page_size=20,
        )

    # ── Formulario Incluir / Modificar ────────────────────────────────────────
    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(
            f'<p class="form-card-title">{"Modificar" if is_edit else "Nuevo"} propietario</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="form-card-hint">Campos marcados con * son obligatorios</p>', unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        with st.form("form_propietario"):
            st.markdown(
                '<p class="form-section-hdr">Datos personales</p>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre completo *", value=cr.get("nombre", ""), max_chars=200)
                cedula = st.text_input(
                    "Cédula / RIF *",
                    value=str(cr.get("cedula") or "").strip(),
                    placeholder="Ej: V6919271 o J-051151689",
                    max_chars=30,
                    help="Documento tal como debe figurar en reportes y estados de cuenta.",
                )
                direccion = st.text_area("Dirección", value=cr.get("direccion", ""), height=80)

            with col2:
                st.markdown(
                    '<p class="form-section-hdr">Contacto y estado</p>',
                    unsafe_allow_html=True,
                )
                telefono  = st.text_input("Teléfono",           value=cr.get("telefono", ""), max_chars=20)
                correo    = st.text_input("Correo electrónico", value=cr.get("correo", ""),   max_chars=100)
                notas     = st.text_area("Notas",               value=cr.get("notas", ""),    height=80)
                activo    = st.checkbox("Activo",               value=cr.get("activo", True))

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.prop_modo = None
            st.rerun()

        if guardar:
            cedula_val = (cedula or "").strip()
            errors = validate_form(
                {"nombre": nombre, "cedula": cedula_val, "correo": correo},
                {
                    "nombre": {"required": True, "max_length": 200},
                    "cedula": {"required": True, "max_length": 30},
                    "correo": {"required": False, "type": "email"},
                },
            )
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {
                    "condominio_id": condominio_id,
                    "nombre":        (nombre or "").strip(),
                    "cedula":        cedula_val,
                    "telefono":      (telefono or "").strip() or None,
                    "correo":        (correo or "").strip() or None,
                    "direccion":     (direccion or "").strip() or None,
                    "notas":         (notas or "").strip() or None,
                    "activo":        activo,
                }
                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Propietario actualizado.")
                    else:
                        repo.create(payload)
                        st.success("✅ Propietario registrado.")
                    st.session_state.prop_modo    = None
                    st.session_state.prop_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    # ── Eliminar ──────────────────────────────────────────────────────────────
    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione un propietario para eliminar.")
            st.session_state.prop_modo = None
        else:
            st.markdown("### 🗑️ Eliminar Propietario")
            st.warning(
                f"⚠️ ¿Eliminar a **{current_rec.get('nombre')}**? "
                "Si tiene unidades asignadas no podrá eliminarse."
            )
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="prop_del_yes"):
                    try:
                        repo.delete(current_rec["id"])
                        st.success("✅ Propietario eliminado.")
                        st.session_state.prop_modo    = None
                        st.session_state.prop_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="prop_del_no"):
                    st.session_state.prop_modo = None
                    st.rerun()

    # ── Detalle (panel slide-in) ─────────────────────────────────────────────
    elif current_rec and modo is None:
        detail_fields = [
            ("Nombre", current_rec.get("nombre") or "—"),
            ("Cédula/Doc", current_rec.get("cedula") or "—"),
            ("Teléfono", current_rec.get("telefono") or "—"),
            ("Correo", current_rec.get("correo") or "—"),
            ("Dirección", current_rec.get("direccion") or "—"),
            ("Estado", "Activo" if current_rec.get("activo") else "Inactivo"),
            ("Notas", current_rec.get("notas") or "—"),
        ]
        render_detail_panel(detail_fields, "propietarios", "Detalle del propietario")
