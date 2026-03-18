"""
Módulo Facturas de Proveedor: listado, alta, edición, eliminación y filtro por mes.
"""
import streamlit as st
from datetime import date

from config.supabase_client import get_supabase_client
from repositories.factura_repository import FacturaRepository
from repositories.proveedor_repository import ProveedorRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.record_table import render_record_table
from components.detail_panel import check_close_detail, render_detail_panel
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form
from utils.formatters import format_date, format_currency

st.set_page_config(page_title="Facturas", page_icon="🧾", layout="wide")
check_authentication()
render_header()
condominio_id = require_condominio()
mes_proceso   = st.session_state.get("mes_proceso")

# ── Repositorios ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return FacturaRepository(client), ProveedorRepository(client)

repo_fact, repo_prov = get_repos()

# ── Estado ───────────────────────────────────────────────────────────────────
for key, val in {"fact_modo": None, "fact_records": None}.items():
    if key not in st.session_state:
        st.session_state[key] = val

init_toolbar_state("facturas")

def load_proveedores():
    return repo_prov.get_all(condominio_id)

def load_facturas(solo_mes: bool = True):
    if solo_mes and mes_proceso:
        mp = mes_proceso[:7] + "-01" if len(str(mes_proceso)) >= 7 else None
        if mp:
            return repo_fact.get_by_mes_proceso(condominio_id, mp)
    return repo_fact.get_all(condominio_id)

if st.session_state.fact_records is None:
    st.session_state.fact_records = load_facturas(solo_mes=True)

records    = st.session_state.fact_records
proveedores = load_proveedores()
prov_activos = [p for p in proveedores if p.get("activo")]

st.markdown("## 🧾 Facturas de Proveedor")

col_main, col_help = st.columns([3, 1])

with col_help:
    render_help_panel(
        icono="🧾",
        titulo="Facturas",
        descripcion_corta="Facturas de proveedores y control de pagos.",
        descripcion_larga=(
            "Registre las facturas recibidas de proveedores. "
            "Puede filtrar por mes en proceso o ver todas. "
            "El saldo se calcula como total menos pagado."
        ),
        tips=[
            "Filtre por 'En proceso' para ver solo el mes actual.",
            "Al modificar, puede actualizar el monto pagado.",
        ],
    )
    render_help_shortcuts({
        "➕ Incluir":   "Nueva factura",
        "✏️ Modificar": "Editar factura seleccionada",
        "🗑️ Eliminar":  "Eliminar (con confirmación)",
    })

FACT_COLUMNS = {
    "id":          {"label": "Id",          "width": 55},
    "numero":      {"label": "Número",      "width": 100},
    "_fecha":      {"label": "Fecha",       "width": 90},
    "_vence":      {"label": "Vencimiento", "width": 100},
    "_proveedor":  {"label": "Proveedor",   "width": 200},
    "descripcion": {"label": "Descripción", "width": 180},
    "total":       {"label": "Total",       "width": 90, "format": "currency"},
    "pagado":      {"label": "Pagado",      "width": 90, "format": "currency"},
    "saldo":       {"label": "Saldo",       "width": 90, "format": "currency"},
}

with col_main:
    check_close_detail("facturas")
    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        filtro_mes = st.radio(
            "Mostrar facturas",
            options=["En proceso", "Todo"],
            horizontal=True,
            key="fact_filtro_mes",
        )
    with col_f2:
        if st.button("Recargar", key="btn_reload_fact", use_container_width=True):
            st.session_state.fact_records = None
            st.rerun()

    if st.session_state.fact_records is None or st.session_state.get("_last_fact_filtro") != filtro_mes:
        st.session_state.fact_records   = load_facturas(solo_mes=(filtro_mes == "En proceso"))
        st.session_state._last_fact_filtro = filtro_mes
        records = st.session_state.fact_records

    for r in records:
        r["_proveedor"] = (r.get("proveedores") or {}).get("nombre", "")
        r["_fecha"]     = format_date(r.get("fecha"))
        r["_vence"]     = format_date(r.get("fecha_vencimiento"))

    current_idx = get_current_index("facturas")
    current_rec = records[current_idx] if records and 0 <= current_idx < len(records) else None
    modo        = st.session_state.fact_modo

    if modo not in ("incluir", "modificar", "eliminar"):
        render_record_table(
            data=records,
            key="facturas",
            columns_config=FACT_COLUMNS,
            search_field="_proveedor",
            caption="Listado de facturas",
            modo_key="fact_modo",
            on_incluir=lambda: st.session_state.update({"fact_modo": "incluir"}),
            on_modificar=lambda: st.session_state.update({"fact_modo": "modificar"}),
            on_eliminar=lambda: st.session_state.update({"fact_modo": "eliminar"}),
            empty_state_icon="🧾",
            empty_state_title="Este condominio no tiene facturas registradas aún",
            empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
            page_size=20,
            right_align_columns=["total", "pagado", "saldo"],
        )

    # ── Formulario Incluir / Modificar ────────────────────────────────────────
    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(
            f'<p class="form-card-title">{"Modificar" if is_edit else "Nueva"} factura</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="form-card-hint">Campos marcados con * son obligatorios</p>', unsafe_allow_html=True)
        fc = current_rec if is_edit and current_rec else {}

        prov_nombres = [p["nombre"] for p in prov_activos]
        prov_ids     = [p["id"] for p in prov_activos]
        def_prov_id  = fc.get("proveedor_id")
        try:
            prov_idx = prov_ids.index(def_prov_id) if def_prov_id in prov_ids else 0
        except (ValueError, TypeError):
            prov_idx = 0

        with st.form("form_factura"):
            st.markdown(
                '<p class="form-section-hdr">Datos de la factura</p>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                numero        = st.text_input("Número de factura *", value=fc.get("numero", ""), max_chars=30)
                proveedor_sel = st.selectbox(
                    "Proveedor *",
                    options=prov_nombres if prov_nombres else ["—"],
                    index=prov_idx,
                )
                proveedor_id = prov_ids[prov_nombres.index(proveedor_sel)] if prov_nombres else None
                descripcion  = st.text_area("Descripción", value=fc.get("descripcion", ""), height=80)
            with col2:
                st.markdown(
                    '<p class="form-section-hdr">Fechas y montos</p>',
                    unsafe_allow_html=True,
                )
                def_fecha = date.fromisoformat(str(fc["fecha"])[:10]) if fc.get("fecha") else date.today()
                def_vence = date.fromisoformat(str(fc["fecha_vencimiento"])[:10]) if fc.get("fecha_vencimiento") else None
                fecha       = st.date_input("Fecha de emisión *", value=def_fecha)
                vencimiento = st.date_input("Fecha de vencimiento", value=def_vence)
                total  = st.number_input("Total *", value=float(fc.get("total") or 0), min_value=0.0, step=0.01, format="%.2f")
                pagado = st.number_input("Monto pagado", value=float(fc.get("pagado") or 0), min_value=0.0, step=0.01, format="%.2f")

            mp_value = mes_proceso[:7] + "-01" if mes_proceso and len(str(mes_proceso)) >= 7 else None

            col_s, col_c = st.columns(2)
            with col_s:
                guardar = st.form_submit_button("Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.fact_modo = None
            st.rerun()

        if guardar:
            errors = validate_form(
                {"numero": numero, "proveedor_id": proveedor_id, "total": total},
                {
                    "numero":       {"required": True, "max_length": 30},
                    "proveedor_id": {"required": True},
                    "total":        {"required": True},
                },
            )
            if pagado > total:
                errors.append("El monto pagado no puede ser mayor al total.")
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {
                    "condominio_id":     condominio_id,
                    "numero":            (numero or "").strip(),
                    "fecha":             fecha.isoformat(),
                    "fecha_vencimiento": vencimiento.isoformat() if vencimiento else None,
                    "proveedor_id":      proveedor_id,
                    "descripcion":       (descripcion or "").strip() or None,
                    "total":             total,
                    "pagado":            pagado,
                    "mes_proceso":       mp_value,
                    "activo":            True,
                }
                try:
                    if is_edit and current_rec:
                        repo_fact.update(current_rec["id"], payload)
                        st.success("✅ Factura actualizada correctamente.")
                    else:
                        repo_fact.create(payload)
                        st.success("✅ Factura creada exitosamente.")
                    st.session_state.fact_modo    = None
                    st.session_state.fact_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    # ── Eliminar ──────────────────────────────────────────────────────────────
    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione una factura para eliminar.")
            st.session_state.fact_modo = None
        else:
            st.markdown("### 🗑️ Eliminar Factura")
            st.warning(
                f"⚠️ ¿Eliminar la factura N° **{current_rec.get('numero', '—')}** "
                f"del proveedor **{current_rec.get('_proveedor', '—')}**?"
            )
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="fact_del_yes"):
                    try:
                        repo_fact.delete(current_rec["id"])
                        st.success("✅ Factura eliminada.")
                        st.session_state.fact_modo    = None
                        st.session_state.fact_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="fact_del_no"):
                    st.session_state.fact_modo = None
                    st.rerun()

    # ── Detalle ───────────────────────────────────────────────────────────────
    elif current_rec and modo is None:
        total  = float(current_rec.get("total") or 0)
        pagado = float(current_rec.get("pagado") or 0)
        saldo  = float(current_rec.get("saldo") or total - pagado)
        detail_fields = [
            ("N° Factura", current_rec.get("numero") or "—"),
            ("Proveedor", current_rec.get("_proveedor") or "—"),
            ("Descripción", current_rec.get("descripcion") or "—"),
            ("Fecha", current_rec.get("_fecha") or "—"),
            ("Vencimiento", current_rec.get("_vence") or "—"),
            ("Total", format_currency(total)),
            ("Pagado", format_currency(pagado)),
            ("Saldo", format_currency(saldo)),
        ]
        render_detail_panel(detail_fields, "facturas", "Detalle de la factura")
