import streamlit as st
from datetime import date

from config.supabase_client import get_supabase_client
from repositories.proveedor_repository import ProveedorRepository
from repositories.factura_repository import FacturaRepository
from repositories.pais_repository import PaisRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import (
    init_toolbar_state,
    get_current_index,
    set_current_index,
    render_toolbar,
)
from components.help_panel import render_help_panel, render_help_shortcuts
from components.record_table import render_record_table
from components.data_table import render_data_table
from components.detail_panel import check_close_detail, render_detail_panel
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form
from utils.formatters import format_date, format_currency

# ── Protección ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Proveedores", page_icon="📄", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Proveedores")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.prov_records = None
    st.session_state.fact_records = None
mes_proceso   = st.session_state.get("mes_proceso")

# ── Repositorios ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return (
        ProveedorRepository(client),
        FacturaRepository(client),
        PaisRepository(client),
    )

repo_prov, repo_fact, repo_pais = get_repos()

# ── Estado ────────────────────────────────────────────────────────────────────
for key, val in {
    "prov_modo":     None,
    "prov_records":  None,
    "fact_modo":     None,
    "fact_records":  None,
    "tab_activa":    "proveedores",
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

init_toolbar_state("proveedores")
init_toolbar_state("facturas")

# ── Carga ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def load_tipos_doc():
    return repo_pais.get_all_tipos_documento()

def load_proveedores():
    with st.spinner("Cargando proveedores..."):
        return repo_prov.get_all(condominio_id)

def load_facturas(solo_mes: bool = True):
    with st.spinner("Cargando facturas..."):
        if solo_mes and mes_proceso:
            mp = mes_proceso[:7] + "-01" if len(mes_proceso) > 7 else mes_proceso
            return repo_fact.get_by_mes_proceso(condominio_id, mp)
        return repo_fact.get_all(condominio_id)

if st.session_state.prov_records is None:
    st.session_state.prov_records = load_proveedores()
if st.session_state.fact_records is None:
    st.session_state.fact_records = load_facturas(solo_mes=True)

prov_records = st.session_state.prov_records
fact_records = st.session_state.fact_records
tipos_doc    = load_tipos_doc()

st.markdown("## 📄 Proveedores")

# ── Tabs principales ──────────────────────────────────────────────────────────
tab_prov, tab_fact = st.tabs(["📄 Proveedores", "🧾 Facturas de Proveedor"])

# =============================================================================
# TAB 1 — PROVEEDORES
# =============================================================================
with tab_prov:
    col_main, col_help = st.columns([4, 1])

    with col_help:
        render_help_panel(
            icono="📄",
            titulo="Proveedores",
            descripcion_corta="Empresas y personas que prestan servicios al condominio.",
            descripcion_larga=(
                "Registre los proveedores con sus datos de contacto y "
                "documento fiscal. El saldo refleja el monto pendiente "
                "de pago según las facturas registradas."
            ),
            tips=[
                "El RIF venezolano tiene formato J-XXXXXXXX-X.",
                "El saldo se actualiza al registrar facturas.",
                "Use 'Inactivo' en lugar de eliminar proveedores con historial.",
            ],
        )
        render_help_shortcuts({
            "Nuevo":     "Nuevo proveedor",
            "Ver":       "Ver detalle",
            "Editar":    "Editar en cada tarjeta",
            "Eliminar":  "Eliminar (confirmación)",
        })

    PROV_COLUMNS = {
        "id":               {"label": "Id",         "width": 55},
        "nombre":           {"label": "Proveedor",  "width": 230},
        "_tipo_doc":        {"label": "Tipo Doc",   "width": 75},
        "numero_documento": {"label": "Documento",  "width": 130},
        "telefono_fijo":    {"label": "Tel. Fijo",  "width": 110},
        "telefono_celular": {"label": "Celular",    "width": 110},
        "correo":           {"label": "Correo",     "width": 180},
        "saldo":            {"label": "Saldo",      "width": 90, "format": "currency"},
        "activo":           {"label": "Activo",     "width": 65, "format": "boolean"},
    }

    with col_main:
        check_close_detail("proveedores")
        for r in prov_records:
            r["_tipo_doc"] = (r.get("tipos_documento") or {}).get("nombre", "")

        current_idx = get_current_index("proveedores")
        current_rec = prov_records[current_idx] if prov_records and 0 <= current_idx < len(prov_records) else None
        modo        = st.session_state.prov_modo

        if modo not in ("incluir", "modificar", "eliminar"):
            render_record_table(
                data=prov_records,
                key="proveedores",
                columns_config=PROV_COLUMNS,
                search_field="nombre",
                caption="Listado de proveedores",
                modo_key="prov_modo",
                on_incluir=lambda: st.session_state.update({"prov_modo": "incluir"}),
                on_modificar=lambda: st.session_state.update({"prov_modo": "modificar"}),
                on_eliminar=lambda: st.session_state.update({"prov_modo": "eliminar"}),
                empty_state_icon="📄",
                empty_state_title="Este condominio no tiene proveedores registrados aún",
                empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
                page_size=20,
                right_align_columns=["saldo"],
            )

        # ── Formulario Incluir / Modificar ────────────────────────────────────
        if modo in ("incluir", "modificar"):
            is_edit = modo == "modificar"
            st.markdown(
                f'<p class="form-card-title">{"Modificar" if is_edit else "Nuevo"} proveedor</p>',
                unsafe_allow_html=True,
            )
            st.markdown('<p class="form-card-hint">Campos marcados con * son obligatorios</p>', unsafe_allow_html=True)

            cr = current_rec if is_edit and current_rec else {}

            tipos_nombres = [t["nombre"] for t in tipos_doc]
            tipos_ids     = [t["id"]     for t in tipos_doc]
            def_tipo_id   = cr.get("tipo_documento_id")
            try:
                tipo_idx = tipos_ids.index(def_tipo_id) if def_tipo_id in tipos_ids else 0
            except (ValueError, TypeError):
                tipo_idx = 0

            with st.form("form_proveedor"):
                st.markdown(
                    '<p class="form-section-hdr">Datos del proveedor</p>',
                    unsafe_allow_html=True,
                )
                col1, col2 = st.columns(2)
                with col1:
                    nombre   = st.text_input("Nombre / Razón Social *",
                                             value=cr.get("nombre", ""), max_chars=200)

                    st.markdown(
                        '<p class="form-section-hdr">Documento fiscal</p>',
                        unsafe_allow_html=True,
                    )
                    tipo_sel = st.selectbox("Tipo de documento",
                                            options=tipos_nombres if tipos_nombres else ["—"],
                                            index=tipo_idx)
                    tipo_id  = tipos_ids[tipos_nombres.index(tipo_sel)] if tipos_nombres else None

                    formatos = {"RIF": "J-12345678-9", "NIT": "123456789-1",
                                "RUC": "1234567890001", "CUIT": "20-12345678-9"}
                    num_doc  = st.text_input(
                        f"Número de {tipo_sel} *",
                        value=cr.get("numero_documento", ""),
                        placeholder=formatos.get(tipo_sel, "Número"),
                        max_chars=30,
                    )
                    direccion = st.text_area("Dirección", value=cr.get("direccion", ""),
                                             height=80)

                with col2:
                    st.markdown(
                        '<p class="form-section-hdr">Contacto y estado</p>',
                        unsafe_allow_html=True,
                    )
                    tel_fijo    = st.text_input("Teléfono fijo",
                                                value=cr.get("telefono_fijo", ""),    max_chars=20)
                    tel_cel     = st.text_input("Teléfono celular",
                                                value=cr.get("telefono_celular", ""), max_chars=20)
                    correo      = st.text_input("Correo electrónico",
                                                value=cr.get("correo", ""),           max_chars=100)
                    contacto    = st.text_input("Persona de contacto",
                                                value=cr.get("contacto", ""),         max_chars=150)
                    notas       = st.text_area("Notas", value=cr.get("notas", ""),   height=80)
                    activo      = st.checkbox("Activo", value=cr.get("activo", True))

                col_s, col_c = st.columns(2)
                with col_s:
                    guardar  = st.form_submit_button("Guardar",
                                                     use_container_width=True, type="primary")
                with col_c:
                    cancelar = st.form_submit_button("Cancelar", use_container_width=True)

            if cancelar:
                st.session_state.prov_modo = None
                st.rerun()

            if guardar:
                errors = validate_form(
                    {"nombre": nombre, "numero_documento": num_doc, "correo": correo},
                    {
                        "nombre":           {"required": True, "max_length": 200},
                        "numero_documento": {"required": True, "max_length": 30},
                        "correo":           {"required": False, "type": "email"},
                    },
                )
                if errors:
                    for e in errors:
                        st.error(f"❌ {e}")
                else:
                    payload = {
                        "condominio_id":    condominio_id,
                        "nombre":           (nombre or "").strip(),
                        "tipo_documento_id":tipo_id,
                        "numero_documento": (num_doc or "").strip(),
                        "direccion":        (direccion or "").strip() or None,
                        "telefono_fijo":    (tel_fijo or "").strip() or None,
                        "telefono_celular": (tel_cel or "").strip() or None,
                        "correo":           (correo or "").strip() or None,
                        "contacto":         (contacto or "").strip() or None,
                        "notas":            (notas or "").strip() or None,
                        "activo":           activo,
                    }
                    try:
                        if is_edit and current_rec:
                            repo_prov.update(current_rec["id"], payload)
                            st.success("✅ Proveedor actualizado correctamente.")
                        else:
                            repo_prov.create(payload)
                            st.success("✅ Proveedor creado exitosamente.")
                        st.session_state.prov_modo    = None
                        st.session_state.prov_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")

        # ── Eliminar ──────────────────────────────────────────────────────────
        elif modo == "eliminar":
            if not current_rec:
                st.warning("⚠️ Seleccione un registro para eliminar.")
                st.session_state.prov_modo = None
            else:
                st.markdown("### 🗑️ Eliminar Proveedor")
                st.warning(
                    f"⚠️ ¿Eliminar el proveedor **{current_rec.get('nombre')}**? "
                    "Esta acción no se puede deshacer."
                )
                col_y, col_n = st.columns(2)
                with col_y:
                    if st.button("✅ Sí, eliminar", type="primary", use_container_width=True,
                                 key="prov_confirm_del"):
                        try:
                            repo_prov.delete(current_rec["id"])
                            st.success("✅ Proveedor eliminado.")
                            st.session_state.prov_modo    = None
                            st.session_state.prov_records = None
                            st.rerun()
                        except DatabaseError as e:
                            st.error(f"❌ {e}")
                with col_n:
                    if st.button("✖ Cancelar", use_container_width=True, key="prov_cancel_del"):
                        st.session_state.prov_modo = None
                        st.rerun()

        # ── Detalle (panel slide-in) ──────────────────────────────────────────
        elif current_rec and modo is None:
            tipo_nombre = (current_rec.get("tipos_documento") or {}).get("nombre", "—")
            doc_str = f"{tipo_nombre} {current_rec.get('numero_documento', '')}".strip() or "—"
            saldo = float(current_rec.get("saldo") or 0)
            detail_fields = [
                ("Nombre", current_rec.get("nombre") or "—"),
                ("Documento", doc_str),
                ("Dirección", current_rec.get("direccion") or "—"),
                ("Tel. Fijo", current_rec.get("telefono_fijo") or "—"),
                ("Celular", current_rec.get("telefono_celular") or "—"),
                ("Correo", current_rec.get("correo") or "—"),
                ("Contacto", current_rec.get("contacto") or "—"),
                ("Saldo", format_currency(saldo)),
                ("Estado", "Activo" if current_rec.get("activo") else "Inactivo"),
            ]
            if current_rec.get("notas"):
                detail_fields.append(("Notas", current_rec["notas"]))
            render_detail_panel(detail_fields, "proveedores", "Detalle del proveedor")


# =============================================================================
# TAB 2 — FACTURAS DE PROVEEDOR
# =============================================================================
with tab_fact:
    col_main_f, col_help_f = st.columns([4, 1])

    with col_help_f:
        render_help_panel(
            icono="🧾",
            titulo="Facturas",
            descripcion_corta="Facturas emitidas por proveedores del condominio.",
            descripcion_larga=(
                "Registre y controle las facturas de proveedores. "
                "El saldo se calcula automáticamente como Total − Pagado. "
                "Filtre por el mes en proceso o consulte el historial completo."
            ),
            tips=[
                "El saldo se actualiza automáticamente en la base de datos.",
                "Use 'Todo' para ver facturas de meses anteriores.",
                "La fecha de vencimiento permite controlar pagos pendientes.",
            ],
        )
        render_help_shortcuts({
            "➕ Incluir":   "Nueva factura",
            "✏️ Modificar": "Editar seleccionada",
            "🗑️ Eliminar":  "Eliminar (con confirmación)",
        })

    with col_main_f:
        check_close_detail("facturas")
        # ── Filtro Mes en proceso / Todo ──────────────────────────────────────
        col_f1, col_f2 = st.columns([2, 3])
        with col_f1:
            filtro_mes = st.radio(
                "Mes:",
                options=["En proceso", "Todo"],
                horizontal=True,
                key="fact_filtro_mes",
            )
        with col_f2:
            if st.button("🔄 Recargar facturas", key="btn_reload_fact"):
                st.session_state.fact_records = None
                st.rerun()

        if st.session_state.fact_records is None or \
                st.session_state.get("_last_fact_filtro") != filtro_mes:
            st.session_state.fact_records    = load_facturas(solo_mes=(filtro_mes == "En proceso"))
            st.session_state._last_fact_filtro = filtro_mes
            fact_records = st.session_state.fact_records

        # ── Toolbar ───────────────────────────────────────────────────────────
        render_toolbar(
            key="facturas",
            total=len(fact_records),
            on_incluir  = lambda: st.session_state.update({"fact_modo": "incluir"}),
            on_modificar= lambda: st.session_state.update({"fact_modo": "modificar"}),
            on_eliminar = lambda: st.session_state.update({"fact_modo": "eliminar"}),
        )

        # ── Enriquecer para la tabla ──────────────────────────────────────────
        for r in fact_records:
            r["_proveedor"] = (r.get("proveedores") or {}).get("nombre", "")
            r["_fecha"]     = format_date(r.get("fecha"))
            r["_vence"]     = format_date(r.get("fecha_vencimiento"))

        # ── Tabla ─────────────────────────────────────────────────────────────
        sel_fact_idx = render_data_table(
            data=fact_records,
            columns_config={
                "id":          {"label": "Id",          "width": 55},
                "numero":      {"label": "Número",      "width": 100},
                "_fecha":      {"label": "Fecha",       "width": 90},
                "_vence":      {"label": "Vencimiento", "width": 100},
                "_proveedor":  {"label": "Proveedor",   "width": 200},
                "descripcion": {"label": "Descripción", "width": 180},
                "total":       {"label": "Total",       "width": 90, "format": "currency"},
                "pagado":      {"label": "Pagado",      "width": 90, "format": "currency"},
                "saldo":       {"label": "Saldo",       "width": 90, "format": "currency"},
            },
            search_field="_proveedor",
            key="facturas",
            empty_state_icon="🧾",
            empty_state_title="Este condominio no tiene facturas registradas aún",
            empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
        )
        if sel_fact_idx is not None:
            set_current_index("facturas", sel_fact_idx)

        fact_current_idx = get_current_index("facturas")
        fact_current_rec = fact_records[fact_current_idx] if fact_records and 0 <= fact_current_idx < len(fact_records) else None
        fact_modo        = st.session_state.fact_modo

        # ── Formulario Incluir / Modificar ────────────────────────────────────
        if fact_modo in ("incluir", "modificar"):
            is_edit_f = fact_modo == "modificar"
            st.markdown(
                f'<p class="form-card-title">{"Modificar" if is_edit_f else "Nueva"} factura</p>',
                unsafe_allow_html=True,
            )
            st.markdown('<p class="form-card-hint">Campos marcados con * son obligatorios</p>', unsafe_allow_html=True)

            fc = fact_current_rec if is_edit_f and fact_current_rec else {}

            # Dropdown de proveedores activos
            provs_activos = [p for p in prov_records if p.get("activo")]
            prov_nombres  = [p["nombre"] for p in provs_activos]
            prov_ids      = [p["id"]     for p in provs_activos]
            def_prov_id   = fc.get("proveedor_id")
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
                    numero      = st.text_input("Número de factura *",
                                                value=fc.get("numero", ""), max_chars=30)
                    proveedor_sel = st.selectbox(
                        "Proveedor *",
                        options=prov_nombres if prov_nombres else ["—"],
                        index=prov_idx,
                    )
                    proveedor_id = prov_ids[prov_nombres.index(proveedor_sel)] if prov_nombres else None
                    descripcion = st.text_area("Descripción",
                                               value=fc.get("descripcion", ""), height=80)

                with col2:
                    st.markdown(
                        '<p class="form-section-hdr">Fechas y montos</p>',
                        unsafe_allow_html=True,
                    )
                    def_fecha  = date.fromisoformat(fc["fecha"][:10]) if fc.get("fecha") else date.today()
                    def_vence  = date.fromisoformat(fc["fecha_vencimiento"][:10]) \
                        if fc.get("fecha_vencimiento") else None
                    fecha       = st.date_input("Fecha de emisión *", value=def_fecha)
                    vencimiento = st.date_input("Fecha de vencimiento", value=def_vence)
                    total       = st.number_input("Total *",
                                                  value=float(fc.get("total") or 0),
                                                  min_value=0.0, step=0.01, format="%.2f")
                    pagado      = st.number_input("Monto pagado",
                                                  value=float(fc.get("pagado") or 0),
                                                  min_value=0.0, step=0.01, format="%.2f")

                # Mes proceso
                mp_value = mes_proceso[:7] + "-01" if mes_proceso and len(mes_proceso) >= 7 else None

                col_s, col_c = st.columns(2)
                with col_s:
                    guardar_f  = st.form_submit_button("Guardar",
                                                       use_container_width=True, type="primary")
                with col_c:
                    cancelar_f = st.form_submit_button("Cancelar", use_container_width=True)

            if cancelar_f:
                st.session_state.fact_modo = None
                st.rerun()

            if guardar_f:
                errors_f = validate_form(
                    {"numero": numero, "proveedor_id": proveedor_id, "total": total},
                    {
                        "numero":       {"required": True, "max_length": 30},
                        "proveedor_id": {"required": True},
                        "total":        {"required": True},
                    },
                )
                if pagado > total:
                    errors_f.append("El monto pagado no puede ser mayor al total.")
                if errors_f:
                    for e in errors_f:
                        st.error(f"❌ {e}")
                else:
                    payload_f = {
                        "condominio_id":    condominio_id,
                        "numero":           (numero or "").strip(),
                        "fecha":            fecha.isoformat(),
                        "fecha_vencimiento": vencimiento.isoformat() if vencimiento else None,
                        "proveedor_id":     proveedor_id,
                        "descripcion":      (descripcion or "").strip() or None,
                        "total":            total,
                        "pagado":           pagado,
                        "mes_proceso":      mp_value,
                        "activo":           True,
                    }
                    try:
                        if is_edit_f and fact_current_rec:
                            repo_fact.update(fact_current_rec["id"], payload_f)
                            st.success("✅ Factura actualizada correctamente.")
                        else:
                            repo_fact.create(payload_f)
                            st.success("✅ Factura creada exitosamente.")
                        st.session_state.fact_modo    = None
                        st.session_state.fact_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")

        # ── Eliminar factura ──────────────────────────────────────────────────
        elif fact_modo == "eliminar":
            if not fact_current_rec:
                st.warning("⚠️ Seleccione una factura para eliminar.")
                st.session_state.fact_modo = None
            else:
                st.markdown("### 🗑️ Eliminar Factura")
                st.warning(
                    f"⚠️ ¿Eliminar la factura N° **{fact_current_rec.get('numero', '—')}** "
                    f"del proveedor **{fact_current_rec.get('_proveedor', '—')}**?"
                )
                col_y, col_n = st.columns(2)
                with col_y:
                    if st.button("✅ Sí, eliminar", type="primary",
                                 use_container_width=True, key="fact_confirm_del"):
                        try:
                            repo_fact.delete(fact_current_rec["id"])
                            st.success("✅ Factura eliminada.")
                            st.session_state.fact_modo    = None
                            st.session_state.fact_records = None
                            st.rerun()
                        except DatabaseError as e:
                            st.error(f"❌ {e}")
                with col_n:
                    if st.button("✖ Cancelar", use_container_width=True, key="fact_cancel_del"):
                        st.session_state.fact_modo = None
                        st.rerun()

        # ── Detalle factura (panel slide-in) ───────────────────────────────────
        elif fact_current_rec and fact_modo is None:
            total  = float(fact_current_rec.get("total") or 0)
            pagado = float(fact_current_rec.get("pagado") or 0)
            saldo  = float(fact_current_rec.get("saldo") or total - pagado)
            detail_fields = [
                ("N° Factura", fact_current_rec.get("numero") or "—"),
                ("Proveedor", fact_current_rec.get("_proveedor") or "—"),
                ("Descripción", fact_current_rec.get("descripcion") or "—"),
                ("Fecha", fact_current_rec.get("_fecha") or "—"),
                ("Vencimiento", fact_current_rec.get("_vence") or "—"),
                ("Total", format_currency(total)),
                ("Pagado", format_currency(pagado)),
                ("Saldo", format_currency(saldo)),
            ]
            render_detail_panel(detail_fields, "facturas", "Detalle de la factura")
