import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.unidad_repository import UnidadRepository
from repositories.propietario_repository import PropietarioRepository
from repositories.alicuota_repository import AlicuotaRepository
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
from utils.formatters import format_currency

st.set_page_config(page_title="Unidades", page_icon="🏠", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Unidades")
condominio_id = require_condominio()
# Invalidar datos del módulo si cambió el condominio activo
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.uni_records = None
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return UnidadRepository(client), PropietarioRepository(client), AlicuotaRepository(client)

repo_unidad, repo_prop, repo_ali = get_repos()

for k, v in {"uni_modo": None, "uni_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("unidades")

@st.cache_data(ttl=120)
def load_propietarios_activos(cid: int):
    return repo_prop.get_all(cid, solo_activos=True)

@st.cache_data(ttl=120)
def load_alicuotas_activos(cid: int):
    return repo_ali.get_all(cid, solo_activos=True)

def load_unidades():
    return repo_unidad.get_all(condominio_id)

TIPOS_PROPIEDAD = ["Apartamento", "Local", "Oficina", "Estacionamiento", "Maletero"]
TIPOS_CONDOMINO = ["Propietario", "Arrendatario"]

UNI_COLUMNS = {
    "id":              {"label": "Id",           "width": 55},
    "tipo_propiedad":  {"label": "Tipo",         "width": 130},
    "numero":          {"label": "Número",       "width": 80},
    "piso":            {"label": "Piso",         "width": 65},
    "_propietario":    {"label": "Propietario",  "width": 200},
    "tipo_condomino":  {"label": "Condómino",    "width": 110},
    "cuota_fija":      {"label": "Cuota Fija",   "width": 100, "format": "currency"},
    "activo":          {"label": "Activo",       "width": 65,  "format": "boolean"},
}

st.markdown("## 🏠 Unidades")

col_main, col_help = st.columns([3, 1])

# ── Carga inicial ────────────────────────────────────────────────────────────
if st.session_state.uni_records is None:
    with col_main:
        render_table_skeleton(column_count=3, row_count=6)
    st.session_state.uni_records = load_unidades()
    st.rerun()

records     = st.session_state.uni_records
propietarios = load_propietarios_activos(condominio_id)
alicuotas    = load_alicuotas_activos(condominio_id)

with col_help:
    render_help_panel(
        icono="🏠",
        titulo="Unidades",
        descripcion_corta="Apartamentos, locales y demás unidades del condominio.",
        descripcion_larga=(
            "Cada unidad pertenece a un propietario y tiene una cuota fija "
            "mensual que se utiliza para el cálculo de recibos. "
            "El tipo de condómino indica si el ocupante es el dueño o un arrendatario."
        ),
        tips=[
            "Tipos: Apartamento, Local, Oficina, Estacionamiento, Maletero.",
            "La cuota fija se usa en el cálculo de gastos comunes.",
            "Asigne primero el propietario en el módulo Propietarios.",
        ],
    )
    render_help_shortcuts({
        "Nuevo":     "Registrar nueva unidad",
        "Ver":       "Ver detalle en panel lateral",
        "Editar":    "Editar en cada tarjeta",
        "Eliminar":  "Eliminar (confirmación)",
    })

    if records:
        total_activas = sum(1 for r in records if r.get("activo"))
        por_tipo = {}
        for r in records:
            t = r.get("tipo_propiedad", "Otro") or "Otro"
            por_tipo[t] = por_tipo.get(t, 0) + 1
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style='background:#EBF5FB; border-radius:8px; padding:12px;
                        font-size:12px; color:#2C3E50;'>
                <b>Resumen</b><br>
                Total unidades: <b>{len(records)}</b><br>
                Activas: <b>{total_activas}</b><br>
                {"<br>".join(f"{t}: <b>{c}</b>" for t, c in por_tipo.items())}
            </div>
            """,
            unsafe_allow_html=True,
        )

with col_main:
    check_close_detail("unidades")
    for r in records:
        prop = r.get("propietarios") or {}
        r["_propietario"] = prop.get("nombre", "—")
        r["_cedula"]      = prop.get("cedula", "")

    current_idx = get_current_index("unidades")
    current_rec = records[current_idx] if records and 0 <= current_idx < len(records) else None
    modo = st.session_state.uni_modo

    if modo in ("incluir", "modificar"):
        if modo == "modificar" and current_rec is None:
            current_rec = {}
        is_edit = modo == "modificar"
        st.markdown('<div class="form-replace-container">', unsafe_allow_html=True)
        st.markdown(
            f'<p class="form-card-title">{"Modificar" if is_edit else "Nueva"} unidad</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="form-card-hint">Campos marcados con * son obligatorios</p>', unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        # Propietario seleccionado por defecto
        prop_nombres = [p["nombre"] for p in propietarios]
        prop_ids     = [p["id"]     for p in propietarios]
        def_prop_id  = (cr.get("propietarios") or {}).get("id") or cr.get("propietario_id")
        try:
            prop_default = prop_ids.index(def_prop_id) if def_prop_id in prop_ids else 0
        except (ValueError, TypeError):
            prop_default = 0

        # Índices por defecto
        tipo_prop_default = TIPOS_PROPIEDAD.index(cr["tipo_propiedad"]) \
            if cr.get("tipo_propiedad") in TIPOS_PROPIEDAD else 0
        tipo_cond_default = TIPOS_CONDOMINO.index(cr["tipo_condomino"]) \
            if cr.get("tipo_condomino") in TIPOS_CONDOMINO else 0

        # Alícuota por defecto
        ali_nombres = [a["descripcion"] for a in alicuotas] if alicuotas else []
        ali_ids     = [a["id"] for a in alicuotas] if alicuotas else []
        def_ali_id  = cr.get("alicuota_id")
        try:
            ali_default = ali_ids.index(def_ali_id) if def_ali_id in ali_ids else 0
        except (ValueError, TypeError):
            ali_default = 0

        with st.form("form_unidad"):
            st.markdown(
                '<p class="form-section-hdr">Identificación</p>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                tipo_propiedad = st.selectbox(
                    "Tipo de propiedad *",
                    options=TIPOS_PROPIEDAD,
                    index=tipo_prop_default,
                )
                codigo = st.text_input(
                    "Código *",
                    value=cr.get("codigo", ""),
                    placeholder="Ej: A01, B02",
                    max_chars=10,
                )
                numero = st.text_input(
                    "Número de unidad *",
                    value=cr.get("numero", ""),
                    placeholder="Ej: 3B, 101, P2-01",
                    max_chars=20,
                )
                piso   = st.text_input(
                    "Piso",
                    value=cr.get("piso", ""),
                    placeholder="Ej: 3, PB, M",
                    max_chars=10,
                )
                activo = st.checkbox("Activo", value=cr.get("activo", True))

            with col2:
                st.markdown(
                    '<p class="form-section-hdr">Propietario y cuota</p>',
                    unsafe_allow_html=True,
                )
                if not alicuotas:
                    st.warning("⚠️ No hay alícuotas registradas. Registre alícuotas primero.")
                    alicuota_id = None
                else:
                    ali_sel = st.selectbox(
                        "Alícuota *",
                        options=ali_nombres,
                        index=ali_default,
                    )
                    alicuota_id = ali_ids[ali_nombres.index(ali_sel)]

                if not propietarios:
                    st.warning("⚠️ No hay propietarios registrados. Registre uno primero.")
                    propietario_id = None
                else:
                    prop_sel = st.selectbox(
                        "Propietario *",
                        options=prop_nombres,
                        index=prop_default,
                    )
                    propietario_id = prop_ids[prop_nombres.index(prop_sel)]

                tipo_condomino = st.selectbox(
                    "Tipo de condómino *",
                    options=TIPOS_CONDOMINO,
                    index=tipo_cond_default,
                    help="Propietario = dueño ocupa la unidad. Arrendatario = inquilino.",
                )
                cuota_fija = st.number_input(
                    "Cuota fija mensual",
                    value=float(cr.get("cuota_fija") or 0),
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    help="Monto fijo mensual que paga esta unidad.",
                )

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.uni_modo = None
            st.rerun()

        if guardar:
            errors = validate_form(
                {"codigo": codigo, "alicuota_id": alicuota_id, "numero": numero, "propietario_id": propietario_id},
                {
                    "codigo":          {"required": True, "max_length": 10},
                    "alicuota_id":     {"required": True},
                    "numero":         {"required": True, "max_length": 20},
                    "propietario_id": {"required": True},
                },
            )
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {
                    "condominio_id":  condominio_id,
                    "codigo":         (codigo or "").strip(),
                    "alicuota_id":    alicuota_id,
                    "propietario_id": propietario_id,
                    "tipo_propiedad": tipo_propiedad,
                    "numero":         (numero or "").strip(),
                    "piso":           (piso or "").strip() or None,
                    "tipo_condomino": tipo_condomino,
                    "cuota_fija":     cuota_fija,
                    "saldo":          float(cr.get("saldo") or 0),
                    "activo":         activo,
                }
                try:
                    if is_edit and current_rec:
                        repo_unidad.update(current_rec["id"], payload)
                        st.success("✅ Unidad actualizada.")
                    else:
                        repo_unidad.create(payload)
                        st.success("✅ Unidad registrada.")
                    st.session_state.uni_modo    = None
                    st.session_state.uni_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")
        st.markdown("</div>", unsafe_allow_html=True)

    elif modo not in ("eliminar",):
        render_record_table(
            data=records,
            key="unidades",
            columns_config=UNI_COLUMNS,
            search_field="numero",
            caption="Listado de unidades",
            modo_key="uni_modo",
            on_incluir=lambda: st.session_state.update({"uni_modo": "incluir"}),
            on_modificar=lambda: st.session_state.update({"uni_modo": "modificar"}),
            on_eliminar=lambda: st.session_state.update({"uni_modo": "eliminar"}),
            empty_state_icon="🏠",
            empty_state_title="Este condominio no tiene unidades registradas aún",
            empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
            page_size=20,
            right_align_columns=["cuota_fija"],
        )

    # ── Eliminar ──────────────────────────────────────────────────────────────
    if modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione una unidad para eliminar.")
            st.session_state.uni_modo = None
        else:
            label = f"{current_rec.get('tipo_propiedad', '')} {current_rec.get('numero', '')}".strip()
            st.markdown("### 🗑️ Eliminar Unidad")
            st.warning(f"⚠️ ¿Eliminar la unidad **{label}**? Esta acción no se puede deshacer.")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="uni_del_yes"):
                    try:
                        repo_unidad.delete(current_rec["id"])
                        st.success("✅ Unidad eliminada.")
                        st.session_state.uni_modo    = None
                        st.session_state.uni_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="uni_del_no"):
                    st.session_state.uni_modo = None
                    st.rerun()

    elif current_rec and modo is None:
        prop = current_rec.get("propietarios") or {}
        detail_fields = [
            ("Tipo", current_rec.get("tipo_propiedad") or "—"),
            ("Número", current_rec.get("numero") or "—"),
            ("Piso", current_rec.get("piso") or "—"),
            ("Propietario", prop.get("nombre") or "—"),
            ("Cédula", prop.get("cedula") or "—"),
            ("Tipo condómino", current_rec.get("tipo_condomino") or "—"),
            ("Cuota fija", str(current_rec.get("cuota_fija") or "0")),
            ("Estado", "Activo" if current_rec.get("activo") else "Inactivo"),
        ]
        render_detail_panel(detail_fields, "unidades", "Detalle de la unidad")
