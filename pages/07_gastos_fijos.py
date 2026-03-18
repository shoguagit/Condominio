import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.gasto_fijo_repository import GastoFijoRepository
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

st.set_page_config(page_title="Gastos Fijos", page_icon="📌", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Gastos Fijos")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.gf_records = None
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return GastoFijoRepository(client), AlicuotaRepository(client)

repo, repo_ali = get_repos()

for k, v in {"gf_modo": None, "gf_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("gastos_fijos")

@st.cache_data(ttl=120)
def load_alicuotas():
    return repo_ali.get_all(condominio_id, solo_activos=True)

if st.session_state.gf_records is None:
    with st.spinner("Cargando gastos fijos..."):
        st.session_state.gf_records = repo.get_all(condominio_id)

records   = st.session_state.gf_records
alicuotas = load_alicuotas()

st.markdown("## 📌 Gastos Fijos")

col_main, col_help = st.columns([3, 1])

with col_help:
    render_help_panel(
        icono="📌",
        titulo="Gastos Fijos",
        descripcion_corta="Gastos mensuales recurrentes del condominio.",
        descripcion_larga=(
            "Los gastos fijos son los egresos que se repiten cada mes: "
            "sueldos de empleados, servicios básicos, seguros, etc. "
            "Cada gasto se distribuye entre los condóminos según la alícuota asignada."
        ),
        tips=[
            "Asigne una alícuota para distribuir el gasto entre unidades.",
            "El monto es en la moneda principal del condominio.",
            "Desactive gastos temporales en lugar de eliminarlos.",
        ],
    )
    if records:
        total = sum(float(r.get("monto") or 0) for r in records if r.get("activo"))
        st.markdown(
            f"<div style='background:#EBF5FB;border-radius:8px;padding:10px 12px;"
            f"font-size:12px;color:#2C3E50;margin-top:8px;'>"
            f"<b>Total mensual:</b><br>"
            f"<span style='font-size:16px;font-weight:700;color:#E74C3C;'>"
            f"{format_currency(total)}</span></div>",
            unsafe_allow_html=True,
        )

with col_main:
    render_toolbar(
        key="gastos_fijos",
        total=len(records),
        on_incluir  = lambda: st.session_state.update({"gf_modo": "incluir"}),
        on_modificar= lambda: st.session_state.update({"gf_modo": "modificar"}),
        on_eliminar = lambda: st.session_state.update({"gf_modo": "eliminar"}),
    )

    for r in records:
        r["_alicuota"] = (r.get("alicuotas") or {}).get("descripcion", "Condominio")

    sel_idx = render_data_table(
        data=records,
        columns_config={
            "id":          {"label": "Id",                  "width": 55},
            "descripcion": {"label": "Descripción",         "width": 260},
            "monto":       {"label": "Monto",               "width": 110, "format": "currency"},
            "_alicuota":   {"label": "Alícuota / Cond.",    "width": 180},
            "activo":      {"label": "Activo",              "width": 65,  "format": "boolean"},
        },
        search_field="descripcion",
        key="gastos_fijos",
        empty_state_title="Este condominio no tiene gastos fijos registrados aún",
        empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
    )
    if sel_idx is not None:
        set_current_index("gastos_fijos", sel_idx)

    check_close_detail("gastos_fijos")
    idx = get_current_index("gastos_fijos")
    current_rec = records[idx] if records and 0 <= idx < len(records) else None
    modo        = st.session_state.gf_modo

    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(f"### {'✏️ Modificar' if is_edit else '➕ Nuevo'} Gasto Fijo")
        st.markdown("<hr style='margin:4px 0 12px 0;'>", unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        ali_nombres = ["— Condominio general —"] + [a["descripcion"] for a in alicuotas]
        ali_ids     = [None]                      + [a["id"]          for a in alicuotas]
        def_ali_id  = cr.get("alicuota_id")
        try:
            ali_default = ali_ids.index(def_ali_id)
        except (ValueError, TypeError):
            ali_default = 0

        with st.form("form_gasto_fijo"):
            col1, col2 = st.columns(2)
            with col1:
                descripcion = st.text_input("Descripción *", value=cr.get("descripcion", ""), max_chars=200)
                activo      = st.checkbox("Activo", value=cr.get("activo", True))
            with col2:
                monto   = st.number_input(
                    "Monto *",
                    value=float(cr.get("monto") or 0),
                    min_value=0.0, step=0.01, format="%.2f",
                )
                ali_sel = st.selectbox(
                    "Alícuota asociada",
                    options=ali_nombres,
                    index=ali_default,
                    help="Seleccione la alícuota o deje 'Condominio general' para distribuir equitativamente.",
                )
                alicuota_id = ali_ids[ali_nombres.index(ali_sel)]

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.gf_modo = None
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
                payload = {
                    "condominio_id": condominio_id,
                    "descripcion":   (descripcion or "").strip(),
                    "monto":         monto,
                    "alicuota_id":   alicuota_id,
                    "activo":        activo,
                }
                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Gasto fijo actualizado.")
                    else:
                        repo.create(payload)
                        st.success("✅ Gasto fijo creado.")
                    st.session_state.gf_modo    = None
                    st.session_state.gf_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione un gasto fijo.")
            st.session_state.gf_modo = None
        else:
            st.warning(f"⚠️ ¿Eliminar **{current_rec.get('descripcion')}**?")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="gf_del_y"):
                    try:
                        repo.delete(current_rec["id"])
                        st.success("✅ Gasto fijo eliminado.")
                        st.session_state.gf_modo    = None
                        st.session_state.gf_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="gf_del_n"):
                    st.session_state.gf_modo = None
                    st.rerun()
