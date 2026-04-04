import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.concepto_repository import ConceptoRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import render_toolbar, init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.data_table import render_data_table
from components.detail_panel import check_close_detail
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form

st.set_page_config(page_title="Conceptos", page_icon="📋", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Conceptos")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.conc_records = None
@st.cache_resource
def get_repo():
    return ConceptoRepository(get_supabase_client())

repo = get_repo()

for k, v in {"conc_modo": None, "conc_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("conceptos")

if st.session_state.conc_records is None:
    with st.spinner("Cargando conceptos..."):
        st.session_state.conc_records = repo.get_all(condominio_id)

records = st.session_state.conc_records

TIPOS = {"gasto": "💸 Gasto", "ajuste": "🛠️ Ajuste"}

st.markdown("## 📋 Conceptos")

col_main, col_help = st.columns([4, 1])

with col_help:
    render_help_panel(
        icono="📋",
        titulo="Conceptos",
        descripcion_corta="Conceptos de gasto y ajustes del condominio.",
        descripcion_larga=(
            "Los conceptos clasifican los movimientos financieros del condominio. "
            "Ejemplos de gastos: 'Gastos Generales', 'Mantenimiento Ascensor'. "
            "Ejemplos de ajustes: 'Corrección de saldo', 'Ajuste por diferencia'."
        ),
        tips=[
            "Tipo 'Gasto': para egresos del condominio.",
            "Tipo 'Ajuste': para registrar correcciones o reclasificaciones.",
            "Se usan al registrar movimientos del mes.",
        ],
    )
    if records:
        gastos = sum(1 for r in records if r.get("tipo") == "gasto" and r.get("activo"))
        ajustes = sum(1 for r in records if r.get("tipo") == "ajuste" and r.get("activo"))
        st.markdown(
            f"<div style='background:#EBF5FB;border-radius:8px;padding:10px 12px;"
            f"font-size:12px;color:#2C3E50;margin-top:8px;'>"
            f"💸 Gastos activos: <b>{gastos}</b><br>"
            f"🛠️ Ajustes activos: <b>{ajustes}</b></div>",
            unsafe_allow_html=True,
        )

with col_main:
    col_tb, col_filtro = st.columns([3, 1])
    with col_tb:
        render_toolbar(
            key="conceptos",
            total=len(records),
            on_incluir  = lambda: st.session_state.update({"conc_modo": "incluir"}),
            on_modificar= lambda: st.session_state.update({"conc_modo": "modificar"}),
            on_eliminar = lambda: st.session_state.update({"conc_modo": "eliminar"}),
        )
    with col_filtro:
        filtro_tipo = st.selectbox("Filtrar por tipo:", ["Todos", "Gasto", "Ajuste"],
                                   key="conc_filtro", label_visibility="collapsed")

    filtered = records
    if filtro_tipo == "Gasto":
        filtered = [r for r in records if r.get("tipo") == "gasto"]
    elif filtro_tipo == "Ajuste":
        filtered = [r for r in records if r.get("tipo") == "ajuste"]

    for r in filtered:
        r["_tipo_label"] = TIPOS.get(r.get("tipo", ""), r.get("tipo", ""))

    sel_idx = render_data_table(
        data=filtered,
        columns_config={
            "id":           {"label": "Id",       "width": 55},
            "nombre":       {"label": "Concepto", "width": 320},
            "_tipo_label":  {"label": "Tipo",     "width": 110},
            "activo":       {"label": "Activo",   "width": 65, "format": "boolean"},
        },
        search_field="nombre",
        key="conceptos",
        empty_state_title="Este condominio no tiene conceptos registrados aún",
        empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
    )
    if sel_idx is not None:
        set_current_index("conceptos", sel_idx)

    check_close_detail("conceptos")
    idx = get_current_index("conceptos")
    current_rec = records[idx] if records and 0 <= idx < len(records) else None
    modo        = st.session_state.conc_modo

    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(f"### {'✏️ Modificar' if is_edit else '➕ Nuevo'} Concepto")
        st.markdown("<hr style='margin:4px 0 12px 0;'>", unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        TIPOS_OPT = ["gasto", "ajuste"]
        tipo_default = TIPOS_OPT.index(cr["tipo"]) if cr.get("tipo") in TIPOS_OPT else 0

        with st.form("form_concepto"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre del concepto *", value=cr.get("nombre", ""), max_chars=150)
                activo = st.checkbox("Activo", value=cr.get("activo", True))
            with col2:
                tipo = st.selectbox(
                    "Tipo *",
                    options=TIPOS_OPT,
                    index=tipo_default,
                    format_func=lambda t: TIPOS.get(t, t),
                )

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.conc_modo = None
            st.rerun()

        if guardar:
            errors = validate_form({"nombre": nombre}, {"nombre": {"required": True, "max_length": 150}})
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {"condominio_id": condominio_id, "nombre": (nombre or "").strip(),
                           "tipo": tipo, "activo": activo}
                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Concepto actualizado.")
                    else:
                        repo.create(payload)
                        st.success("✅ Concepto creado.")
                    st.session_state.conc_modo    = None
                    st.session_state.conc_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione un concepto.")
            st.session_state.conc_modo = None
        else:
            st.warning(f"⚠️ ¿Eliminar el concepto **{current_rec.get('nombre')}**?")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="conc_del_y"):
                    try:
                        can_del = repo.can_delete(current_rec["id"], condominio_id)
                        if not can_del:
                            st.error("No se puede eliminar un concepto si ya fue usado en movimientos del período activo.")
                            st.stop()
                        repo.delete(current_rec["id"])
                        st.success("✅ Concepto eliminado.")
                        st.session_state.conc_modo    = None
                        st.session_state.conc_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="conc_del_n"):
                    st.session_state.conc_modo = None
                    st.rerun()
