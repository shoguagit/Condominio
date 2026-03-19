import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.concepto_consumo_repository import ConceptoConsumoRepository
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

st.set_page_config(page_title="Conceptos de Consumo", page_icon="⚡", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Conceptos de Consumo")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.cc_records = None
@st.cache_resource
def get_repo():
    return ConceptoConsumoRepository(get_supabase_client())

repo = get_repo()

for k, v in {"cc_modo": None, "cc_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("conceptos_consumo")

if st.session_state.cc_records is None:
    with st.spinner("Cargando conceptos de consumo..."):
        st.session_state.cc_records = repo.get_all(condominio_id)

records = st.session_state.cc_records

UNIDADES_MEDIDA = ["m³", "kWh", "litros", "unidad", "kg", "otro"]
TIPOS_PRECIO    = ["fijo", "tabulador"]

st.markdown("## ⚡ Conceptos de Consumo")

col_main, col_help = st.columns([4, 1])

with col_help:
    render_help_panel(
        icono="⚡",
        titulo="Consumo",
        descripcion_corta="Servicios que dependen de la cantidad consumida.",
        descripcion_larga=(
            "Los conceptos de consumo son servicios cuyo costo varía según "
            "el uso: agua, gas, electricidad, etc. "
            "Precio fijo = un precio único. "
            "Tabulador = precio variable por rango de consumo."
        ),
        tips=[
            "Precio fijo: se multiplica por las unidades consumidas.",
            "Tabulador: el precio varía según el rango de consumo.",
            "La unidad de medida define cómo se registra el consumo (m³, kWh…).",
        ],
    )
    render_help_shortcuts({
        "➕ Incluir":   "Nuevo concepto de consumo",
        "✏️ Modificar": "Editar seleccionado",
        "🗑️ Eliminar":  "Eliminar (con confirmación)",
    })

with col_main:
    render_toolbar(
        key="conceptos_consumo",
        total=len(records),
        on_incluir  = lambda: st.session_state.update({"cc_modo": "incluir"}),
        on_modificar= lambda: st.session_state.update({"cc_modo": "modificar"}),
        on_eliminar = lambda: st.session_state.update({"cc_modo": "eliminar"}),
    )

    for r in records:
        r["_tipo_precio_label"] = "Fijo" if r.get("tipo_precio") == "fijo" else "Tabulador"

    sel_idx = render_data_table(
        data=records,
        columns_config={
            "id":                   {"label": "Id",           "width": 55},
            "nombre":               {"label": "Concepto",     "width": 230},
            "unidad_medida":        {"label": "Unidad",       "width": 75},
            "precio_unitario":      {"label": "Precio Unit.", "width": 110, "format": "currency"},
            "_tipo_precio_label":   {"label": "Tipo Precio",  "width": 100},
            "activo":               {"label": "Activo",       "width": 65,  "format": "boolean"},
        },
        search_field="nombre",
        key="conceptos_consumo",
        empty_state_title="Este condominio no tiene conceptos de consumo registrados aún",
        empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
    )
    if sel_idx is not None:
        set_current_index("conceptos_consumo", sel_idx)

    check_close_detail("conceptos_consumo")
    idx = get_current_index("conceptos_consumo")
    current_rec = records[idx] if records and 0 <= idx < len(records) else None
    modo        = st.session_state.cc_modo

    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(f"### {'✏️ Modificar' if is_edit else '➕ Nuevo'} Concepto de Consumo")
        st.markdown("<hr style='margin:4px 0 12px 0;'>", unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        um_default   = UNIDADES_MEDIDA.index(cr["unidad_medida"]) \
            if cr.get("unidad_medida") in UNIDADES_MEDIDA else 0
        tipo_default = TIPOS_PRECIO.index(cr["tipo_precio"]) \
            if cr.get("tipo_precio") in TIPOS_PRECIO else 0

        with st.form("form_concepto_consumo"):
            col1, col2 = st.columns(2)
            with col1:
                nombre         = st.text_input("Nombre del concepto *", value=cr.get("nombre", ""), max_chars=150)
                unidad_medida  = st.selectbox("Unidad de medida *", options=UNIDADES_MEDIDA, index=um_default)
                activo         = st.checkbox("Activo", value=cr.get("activo", True))
            with col2:
                tipo_precio    = st.selectbox(
                    "Tipo de precio *",
                    options=TIPOS_PRECIO,
                    index=tipo_default,
                    format_func=lambda t: "Precio fijo" if t == "fijo" else "Tabulador por rango",
                )
                precio_unitario = st.number_input(
                    "Precio unitario",
                    value=float(cr.get("precio_unitario") or 0),
                    min_value=0.0, step=0.0001, format="%.4f",
                    help="Aplica cuando tipo = Precio fijo.",
                    disabled=(tipo_precio == "tabulador"),
                )
                if tipo_precio == "tabulador":
                    st.info("ℹ️ Para tabulador, configure los rangos de precio en el módulo correspondiente.")

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.cc_modo = None
            st.rerun()

        if guardar:
            errors = validate_form({"nombre": nombre}, {"nombre": {"required": True, "max_length": 150}})
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {
                    "condominio_id":  condominio_id,
                    "nombre":         (nombre or "").strip(),
                    "unidad_medida":  unidad_medida,
                    "precio_unitario":precio_unitario if tipo_precio == "fijo" else 0,
                    "tipo_precio":    tipo_precio,
                    "activo":         activo,
                }
                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Concepto de consumo actualizado.")
                    else:
                        repo.create(payload)
                        st.success("✅ Concepto de consumo creado.")
                    st.session_state.cc_modo    = None
                    st.session_state.cc_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione un concepto.")
            st.session_state.cc_modo = None
        else:
            st.warning(f"⚠️ ¿Eliminar **{current_rec.get('nombre')}**?")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="cc_del_y"):
                    try:
                        repo.delete(current_rec["id"])
                        st.success("✅ Concepto eliminado.")
                        st.session_state.cc_modo    = None
                        st.session_state.cc_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="cc_del_n"):
                    st.session_state.cc_modo = None
                    st.rerun()
