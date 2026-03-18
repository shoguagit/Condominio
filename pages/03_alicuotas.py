import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.alicuota_repository import AlicuotaRepository
from repositories.unidad_repository import UnidadRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import render_toolbar, init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.data_table import render_data_table
from components.detail_panel import check_close_detail
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form

st.set_page_config(page_title="Alícuotas", page_icon="📊", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Alícuotas")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.ali_records = None
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return AlicuotaRepository(client), UnidadRepository(client)

repo, repo_uni = get_repos()

for k, v in {"ali_modo": None, "ali_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("alicuotas")

def load():
    with st.spinner("Cargando alícuotas..."):
        return repo.get_all(condominio_id)

if st.session_state.ali_records is None:
    st.session_state.ali_records = load()

records = st.session_state.ali_records

st.markdown("## 📊 Alícuotas")

col_main, col_help = st.columns([3, 1])

with col_help:
    render_help_panel(
        icono="📊",
        titulo="Alícuotas",
        descripcion_corta="Cuota parte de gastos por condómino.",
        descripcion_larga=(
            "La alícuota es el porcentaje de los gastos comunes que le "
            "corresponde a cada unidad. Puede calcularse automáticamente "
            "dividiendo 1 entre el total de unidades, o definirse manualmente."
        ),
        tips=[
            "Autocalcular = 1 ÷ cantidad de unidades activas.",
            "El total de todas las alícuotas debe sumar 1 (100%).",
            "Se usa en fondos y gastos fijos para distribuir costos.",
        ],
    )
    render_help_shortcuts({
        "➕ Incluir":    "Nueva alícuota",
        "✏️ Modificar":  "Editar seleccionada",
        "🗑️ Eliminar":   "Eliminar (con confirmación)",
        "🔄 Recalcular": "Actualiza desde unidades activas",
    })

with col_main:
    col_tb, col_recalc = st.columns([4, 1])
    with col_tb:
        render_toolbar(
            key="alicuotas",
            total=len(records),
            on_incluir  = lambda: st.session_state.update({"ali_modo": "incluir"}),
            on_modificar= lambda: st.session_state.update({"ali_modo": "modificar"}),
            on_eliminar = lambda: st.session_state.update({"ali_modo": "eliminar"}),
        )
    with col_recalc:
        st.markdown("")
        if st.button("🔄 Recalcular desde unidades", use_container_width=True,
                     disabled=not records, key="btn_recalc"):
            st.session_state.ali_modo = "recalcular"

    for r in records:
        r["_autocalc"] = "✅ Sí" if r.get("autocalcular") else "—"
        r["_total"]    = f"{float(r.get('total_alicuota') or 0):.6f}"

    sel_idx = render_data_table(
        data=records,
        columns_config={
            "id":                {"label": "Id",          "width": 55},
            "descripcion":       {"label": "Descripción", "width": 260},
            "_autocalc":         {"label": "Autocalc.",   "width": 90},
            "cantidad_unidades": {"label": "Cant. Unid.", "width": 100},
            "_total":            {"label": "Total Alíc.", "width": 110},
            "activo":            {"label": "Activo",      "width": 65, "format": "boolean"},
        },
        search_field="descripcion",
        key="alicuotas",
        empty_state_title="Este condominio no tiene alícuotas registradas aún",
        empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
    )
    if sel_idx is not None:
        set_current_index("alicuotas", sel_idx)

    check_close_detail("alicuotas")
    idx = get_current_index("alicuotas")
    current_rec = records[idx] if records and 0 <= idx < len(records) else None
    modo        = st.session_state.ali_modo

    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(f"### {'✏️ Modificar' if is_edit else '➕ Nueva'} Alícuota")
        st.markdown("<hr style='margin:4px 0 12px 0;'>", unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        with st.form("form_alicuota"):
            col1, col2 = st.columns(2)
            with col1:
                descripcion  = st.text_input("Descripción *", value=cr.get("descripcion", ""), max_chars=200)
                autocalcular = st.checkbox(
                    "Autocalcular (1 ÷ total unidades)",
                    value=cr.get("autocalcular", False),
                    help="Si activa esto, el sistema divide 1 entre la cantidad de unidades.",
                )
                activo = st.checkbox("Activo", value=cr.get("activo", True))
            with col2:
                cant_unidades  = st.number_input(
                    "Cantidad de unidades",
                    value=int(cr.get("cantidad_unidades") or 0),
                    min_value=0, step=1,
                    disabled=autocalcular,
                )
                total_alicuota = st.number_input(
                    "Total alícuota",
                    value=float(cr.get("total_alicuota") or 0),
                    min_value=0.0, max_value=1.0, step=0.000001, format="%.6f",
                    disabled=autocalcular,
                    help="Valor entre 0 y 1. Ej: 0.05 = 5%",
                )
                if autocalcular and cant_unidades > 0:
                    st.info(f"ℹ️ Total calculado: {1/cant_unidades:.6f}")

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.ali_modo = None
            st.rerun()

        if guardar:
            errors = validate_form(
                {"descripcion": descripcion},
                {"descripcion": {"required": True, "max_length": 200}},
            )
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                calc_total = round(1 / cant_unidades, 6) if autocalcular and cant_unidades > 0 else total_alicuota
                payload = {
                    "condominio_id":    condominio_id,
                    "descripcion":      (descripcion or "").strip(),
                    "autocalcular":     autocalcular,
                    "cantidad_unidades":cant_unidades if autocalcular else cant_unidades,
                    "total_alicuota":   calc_total,
                    "activo":           activo,
                }
                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Alícuota actualizada.")
                    else:
                        repo.create(payload)
                        st.success("✅ Alícuota creada.")
                    st.session_state.ali_modo    = None
                    st.session_state.ali_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    elif modo == "recalcular":
        if not current_rec:
            st.warning("⚠️ Seleccione una alícuota para recalcular.")
            st.session_state.ali_modo = None
        else:
            total_uni = len(repo_uni.get_all(condominio_id, solo_activos=True))
            if total_uni == 0:
                st.error("❌ No hay unidades activas para calcular.")
            else:
                st.info(
                    f"ℹ️ Se recalculará **{current_rec.get('descripcion')}** "
                    f"con {total_uni} unidades activas → {1/total_uni:.6f}"
                )
                col_y, col_n = st.columns(2)
                with col_y:
                    if st.button("✅ Confirmar", type="primary", use_container_width=True, key="ali_recalc_yes"):
                        try:
                            repo.recalcular_desde_unidades(current_rec["id"], total_uni)
                            st.success("✅ Alícuota recalculada.")
                            st.session_state.ali_modo    = None
                            st.session_state.ali_records = None
                            st.rerun()
                        except DatabaseError as e:
                            st.error(f"❌ {e}")
                with col_n:
                    if st.button("✖ Cancelar", use_container_width=True, key="ali_recalc_no"):
                        st.session_state.ali_modo = None
                        st.rerun()

    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione una alícuota para eliminar.")
            st.session_state.ali_modo = None
        else:
            st.warning(f"⚠️ ¿Eliminar **{current_rec.get('descripcion')}**? Si está en uso por fondos o gastos fijos no podrá eliminarse.")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="ali_del_yes"):
                    try:
                        repo.delete(current_rec["id"])
                        st.success("✅ Alícuota eliminada.")
                        st.session_state.ali_modo    = None
                        st.session_state.ali_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="ali_del_no"):
                    st.session_state.ali_modo = None
                    st.rerun()
