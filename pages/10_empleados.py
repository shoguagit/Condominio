import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.empleado_repository import EmpleadoRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.record_table import render_record_table
from components.detail_panel import check_close_detail, render_detail_panel
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form, validate_telefono_venezolano

st.set_page_config(page_title="Empleados", page_icon="👷", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Empleados")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.emp_records = None
@st.cache_resource
def get_repo():
    return EmpleadoRepository(get_supabase_client())

repo = get_repo()

for k, v in {"emp_modo": None, "emp_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("empleados")

AREA_OPTS = ["Administración", "Mantenimiento", "Seguridad", "Limpieza", "Otro"]

def load_empleados():
    with st.spinner("Cargando empleados..."):
        return repo.get_all(condominio_id)

if st.session_state.emp_records is None:
    with st.spinner("Cargando empleados..."):
        st.session_state.emp_records = load_empleados()
    st.rerun()

records = st.session_state.emp_records
EMP_COLUMNS = {
    "id":               {"label": "Id",       "width": 55},
    "nombre":           {"label": "Empleado", "width": 220},
    "cargo":            {"label": "Cargo",    "width": 150},
    "telefono_fijo":    {"label": "Tel. Fijo","width": 115},
    "telefono_celular": {"label": "Celular",  "width": 115},
    "correo":           {"label": "Correo",   "width": 180},
    "activo":           {"label": "Activo",   "width": 65, "format": "boolean"},
}

st.markdown("## 👷 Empleados")

col_main, col_help = st.columns([4, 1])

with col_help:
    render_help_panel(
        icono="👷",
        titulo="Empleados",
        descripcion_corta="Personal que trabaja en el condominio.",
        descripcion_larga=(
            "Registre los empleados del condominio: conserjes, vigilantes, "
            "personal de mantenimiento, etc. Mantenga sus datos de contacto "
            "actualizados para facilitar la comunicación."
        ),
        tips=[
            "Use 'Inactivo' para empleados que ya no trabajan aquí.",
            "El cargo describe la función del empleado.",
        ],
    )
    render_help_shortcuts({
        "Nuevo":     "Registrar nuevo empleado",
        "Ver":       "Ver detalle",
        "Editar":    "Editar en cada tarjeta",
        "Eliminar":  "Eliminar (confirmación)",
    })

with col_main:
    check_close_detail("empleados")
    current_idx = get_current_index("empleados")
    current_rec = records[current_idx] if records and 0 <= current_idx < len(records) else None
    modo        = st.session_state.emp_modo

    if modo not in ("incluir", "modificar", "eliminar"):
        render_record_table(
            data=records,
            key="empleados",
            columns_config=EMP_COLUMNS,
            search_field="nombre",
            caption="Listado de empleados",
            modo_key="emp_modo",
            on_incluir=lambda: st.session_state.update({"emp_modo": "incluir"}),
            on_modificar=lambda: st.session_state.update({"emp_modo": "modificar"}),
            on_eliminar=lambda: st.session_state.update({"emp_modo": "eliminar"}),
            empty_state_icon="👷",
            empty_state_title="Este condominio no tiene empleados registrados aún",
            empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
            page_size=20,
        )

    # ── Formulario Incluir / Modificar ────────────────────────────────────────
    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(
            f'<p class="form-card-title">{"Modificar" if is_edit else "Nuevo"} empleado</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="form-card-hint">Campos marcados con * son obligatorios</p>', unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        with st.form("form_empleado"):
            st.markdown(
                '<p class="form-section-hdr">Datos del empleado</p>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                nombre    = st.text_input("Nombre completo *",  value=cr.get("nombre", ""),   max_chars=200)
                cargo     = st.text_input("Cargo *",            value=cr.get("cargo", ""),    max_chars=100)
                area      = st.selectbox(
                    "Área *",
                    options=AREA_OPTS,
                    index=AREA_OPTS.index(cr["area"]) if cr.get("area") in AREA_OPTS else 0,
                )
                direccion = st.text_area("Dirección",           value=cr.get("direccion", ""), height=80)
            with col2:
                st.markdown(
                    '<p class="form-section-hdr">Contacto y estado</p>',
                    unsafe_allow_html=True,
                )
                tel_fijo  = st.text_input("Teléfono fijo",      value=cr.get("telefono_fijo", ""),     max_chars=20)
                tel_cel   = st.text_input("Teléfono celular",   value=cr.get("telefono_celular", ""),  max_chars=20)
                correo    = st.text_input("Correo electrónico", value=cr.get("correo", ""),            max_chars=100)
                notas     = st.text_area("Notas",               value=cr.get("notas", ""),             height=60)
                activo    = st.checkbox("Activo",               value=cr.get("activo", False))

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.emp_modo = None
            st.rerun()

        if guardar:
            errors = validate_form(
                {"nombre": nombre, "cargo": cargo, "area": area, "correo": correo},
                {
                    "nombre": {"required": True, "max_length": 200},
                    "cargo":  {"required": True, "max_length": 100},
                    "area":   {"required": True},
                    "correo": {"required": False, "type": "email"},
                },
            )
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                ok_tel, msg_tel = validate_telefono_venezolano(tel_cel)
                if not ok_tel:
                    st.error(f"❌ {msg_tel}")
                    st.stop()
                payload = {
                    "condominio_id":    condominio_id,
                    "nombre":           (nombre or "").strip(),
                    "cargo":            (cargo or "").strip(),
                    "area":             (area or "").strip(),
                    "direccion":        (direccion or "").strip() or None,
                    "telefono_fijo":    (tel_fijo or "").strip() or None,
                    "telefono_celular": (tel_cel or "").strip() or None,
                    "correo":           (correo or "").strip() or None,
                    "notas":            (notas or "").strip() or None,
                    "activo":           activo,
                }
                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Empleado actualizado.")
                    else:
                        repo.create(payload)
                        st.success("✅ Empleado registrado.")
                    st.session_state.emp_modo    = None
                    st.session_state.emp_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    if modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione un empleado para eliminar.")
            st.session_state.emp_modo = None
        else:
            st.markdown("### 🗑️ Eliminar Empleado")
            st.warning(f"⚠️ ¿Eliminar a **{current_rec.get('nombre')}**? Esta acción no se puede deshacer.")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="emp_del_yes"):
                    try:
                        repo.delete(current_rec["id"])
                        st.success("✅ Empleado eliminado.")
                        st.session_state.emp_modo    = None
                        st.session_state.emp_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="emp_del_no"):
                    st.session_state.emp_modo = None
                    st.rerun()

    elif current_rec and modo is None:
        detail_fields = [
            ("Nombre", current_rec.get("nombre") or "—"),
            ("Cargo", current_rec.get("cargo") or "—"),
            ("Dirección", current_rec.get("direccion") or "—"),
            ("Tel. Fijo", current_rec.get("telefono_fijo") or "—"),
            ("Celular", current_rec.get("telefono_celular") or "—"),
            ("Correo", current_rec.get("correo") or "—"),
            ("Estado", "Activo" if current_rec.get("activo") else "Inactivo"),
            ("Notas", current_rec.get("notas") or "—"),
        ]
        render_detail_panel(detail_fields, "empleados", "Detalle del empleado")
