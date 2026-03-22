import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.condominio_repository import CondominioRepository
from repositories.notificacion_repository import NotificacionRepository
from repositories.pais_repository import PaisRepository
from utils.email_sender import EmailConfig, validar_config_smtp
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.record_table import render_record_table
from components.detail_panel import check_close_detail, render_detail_panel
from components.styles import render_table_skeleton
from utils.auth import check_authentication, require_condominio
from utils.error_handler import handle_create, handle_update, handle_delete, confirm_delete_dialog, DatabaseError
from utils.validators import validate_form, validate_email
from utils.formatters import format_date

# ── Protección de página ──────────────────────────────────────────────────────
check_authentication()

st.set_page_config(page_title="Condominios", page_icon="🏢", layout="wide")

# ── Repositorios ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return (
        CondominioRepository(client),
        PaisRepository(client),
        NotificacionRepository(client),
    )

repo_condo, repo_pais, repo_notif = get_repos()

# ── Estado de la página ───────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "condo_modo":         None,   # "incluir" | "modificar" | "eliminar" | None
        "condo_records":      None,   # cache local de registros
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()
init_toolbar_state("condominios")

# ── Carga de datos ────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_paises():
    return repo_pais.get_all()

def load_condominios():
    return repo_condo.get_all()

paises   = load_paises()
pais_map = {p["id"]: p for p in paises}   # id → dict completo

# País por defecto: Venezuela. Moneda/documento por país (etiqueta en formulario).
VENEZUELA_ID = next(
    (p["id"] for p in paises if p.get("nombre") == "Venezuela"),
    (paises[0]["id"] if paises else 1),
)
MONEDA_LABEL_BY_PAIS = {
    "Venezuela": "Bs.",
    "Colombia":  "$COP",
    "Ecuador":   "$USD",
    "Perú":      "S/",
    "Argentina": "$ARS",
    "Chile":     "$CLP",
    "México":    "$MXN",
}

# ── Header y breadcrumb ───────────────────────────────────────────────────────
render_header()
render_breadcrumb("Condominios")
st.markdown("## 🏢 Condominios")

# ── Layout: contenido principal (75%) + panel de ayuda (25%) ─────────────────
col_main, col_help = st.columns([4, 1])

CONDO_COLUMNS = {
    "id":               {"label": "Id",        "width": 60},
    "nombre":           {"label": "Nombre",    "width": 220},
    "direccion":        {"label": "Dirección", "width": 200},
    "_pais":            {"label": "País",      "width": 110},
    "_tipo_doc":        {"label": "Tipo Doc",  "width": 80},
    "numero_documento": {"label": "Documento", "width": 130},
    "telefono":         {"label": "Teléfono",  "width": 110},
    "email":            {"label": "Email",     "width": 160},
    "activo":           {"label": "Activo",    "width": 70, "format": "boolean"},
    "dia_limite_pago":  {"label": "Día límite", "width": 90},
}

# ── Carga inicial: skeleton y cargar ───────────────────────────────────────────
if st.session_state.condo_records is None:
    with col_main:
        render_table_skeleton(column_count=3, row_count=6)
    st.session_state.condo_records = load_condominios()
    st.rerun()

records = st.session_state.condo_records
# Enriquecer registros con campos de join para la tabla
for r in records:
    r["_pais"]     = (r.get("paises") or {}).get("nombre", "")
    r["_tipo_doc"] = (r.get("tipos_documento") or {}).get("nombre", "")

with col_main:
    check_close_detail("condominios")
    current_idx = get_current_index("condominios")
    current_rec = records[current_idx] if records and 0 <= current_idx < len(records) else None
    modo = st.session_state.condo_modo

    # ── Formulario Nuevo / Modificar ──────────────────────────────────────────
    if modo in ("incluir", "modificar"):
        if modo == "modificar" and current_rec is None:
            current_rec = {}
        is_edit  = modo == "modificar"
        form_key = "form_condo_edit" if is_edit else "form_condo_new"
        titulo_form = "Modificar condominio" if is_edit else "Nuevo condominio"

        st.markdown('<div class="form-replace-container">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="module-card" style="margin-top:0;">
                <p class="form-card-title">{titulo_form}</p>
                <p class="form-card-hint">Campos marcados con * son obligatorios</p>
            """,
            unsafe_allow_html=True,
        )

        # Valores por defecto al editar
        def_nombre   = current_rec.get("nombre", "")           if is_edit and current_rec else ""
        def_dir      = current_rec.get("direccion", "")        if is_edit and current_rec else ""
        # País por defecto: el del registro al editar, o Venezuela para nuevos
        def_pais_id  = (
            current_rec.get("pais_id", VENEZUELA_ID)
            if is_edit and current_rec
            else VENEZUELA_ID
        )
        def_telefono = current_rec.get("telefono", "")         if is_edit and current_rec else ""
        def_email    = current_rec.get("email", "")            if is_edit and current_rec else ""
        def_num_doc  = current_rec.get("numero_documento", "") if is_edit and current_rec else ""
        def_activo   = current_rec.get("activo", True)         if is_edit and current_rec else True
        def_dia_lim  = int(current_rec.get("dia_limite_pago") or 15) if is_edit and current_rec else 15

        with st.form(form_key):
            st.markdown(
                '<p class="form-section-hdr">Datos generales</p>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)

            with col1:
                nombre = st.text_input("Nombre del condominio *", value=def_nombre, max_chars=200)
                direccion = st.text_area("Dirección *", value=def_dir, height=80)

                # País → cambia tipo de documento dinámicamente
                pais_nombres = [p["nombre"] for p in paises]
                pais_ids     = [p["id"] for p in paises]
                try:
                    pais_default_idx = pais_ids.index(def_pais_id)
                except ValueError:
                    pais_default_idx = 0

                pais_sel = st.selectbox(
                    "País *",
                    options=pais_nombres,
                    index=pais_default_idx,
                    key=f"pais_sel_{form_key}",
                )
                pais_id_sel = pais_ids[pais_nombres.index(pais_sel)]

            with col2:
                telefono = st.text_input("Teléfono", value=def_telefono, max_chars=20)
                email    = st.text_input("Email", value=def_email, max_chars=100)

                # Moneda principal: se llena automático según país (no editable)
                pais_nombre_sel = pais_map.get(pais_id_sel, {}).get("nombre", "")
                info            = pais_map.get(pais_id_sel, {})
                moneda_label    = MONEDA_LABEL_BY_PAIS.get(
                    pais_nombre_sel,
                    f"{info.get('simbolo_moneda') or ''} ({info.get('moneda') or 'USD'})".strip() or "—",
                )
                st.text_input("Moneda principal", value=moneda_label, disabled=True)

                activo = st.checkbox("Activo", value=def_activo)

                dia_limite_pago = st.number_input(
                    "Día límite de pago (1-28)",
                    min_value=1,
                    max_value=28,
                    value=def_dia_lim,
                    step=1,
                    help=(
                        "Día del mes hasta el cual se acepta pago sin mora. "
                        "Pagos después de este día pueden generar intereses según la mora configurada."
                    ),
                )

            st.markdown(
                '<p class="form-section-hdr">Documento fiscal</p>',
                unsafe_allow_html=True,
            )
            col3, col4 = st.columns(2)
            with col3:
                tipos_doc      = repo_pais.get_tipos_documento_by_pais(pais_id_sel)
                tipos_nombres  = [t["nombre"] for t in tipos_doc]
                tipos_ids      = [t["id"] for t in tipos_doc]

                def_tipo_doc_id = current_rec.get("tipo_documento_id") if is_edit and current_rec else None
                try:
                    tipo_default_idx = tipos_ids.index(def_tipo_doc_id) if def_tipo_doc_id in tipos_ids else 0
                except (ValueError, TypeError):
                    tipo_default_idx = 0

                tipo_doc_sel = st.selectbox(
                    "Tipo de documento *",
                    options=tipos_nombres if tipos_nombres else ["—"],
                    index=tipo_default_idx,
                )
                tipo_doc_id = tipos_ids[tipos_nombres.index(tipo_doc_sel)] if tipos_nombres else None

            with col4:
                # Placeholder con formato según tipo de documento
                formatos = {
                    "RIF": "J-12345678-9",
                    "NIT": "123456789-1",
                    "RUC": "1234567890001",
                    "CUIT": "20-12345678-9",
                    "RUT": "12.345.678-9",
                    "RFC": "ABC123456T1",
                }
                placeholder = formatos.get(tipo_doc_sel, "Número de documento")
                num_doc = st.text_input(
                    f"Número de {tipo_doc_sel or 'documento'} *",
                    value=def_num_doc,
                    placeholder=placeholder,
                    max_chars=30,
                )

            _smtp_edit = bool(is_edit and current_rec)
            _smtp_cfg = None
            if _smtp_edit and current_rec.get("id"):
                _smtp_cfg = repo_notif.obtener_config_smtp(int(current_rec["id"]))
            with st.expander("📧 Configuración de correo (notificaciones)", expanded=False):
                if not _smtp_edit:
                    st.caption(
                        "Guarde el condominio primero y use **Modificar** para configurar "
                        "correo y notificaciones a morosos."
                    )
                else:
                    st.caption(
                        "Para enviar avisos desde **Notificaciones**. Cuenta **@gmail.com** "
                        "y **App Password** (no la contraseña normal)."
                    )
                def_smtp_em = (
                    (
                        (_smtp_cfg.get("smtp_email") if _smtp_cfg else "")
                        or (current_rec.get("smtp_email") or "")
                    )
                    if _smtp_edit
                    else ""
                )
                has_saved_pw = bool(
                    ((_smtp_cfg or {}).get("smtp_app_password") or "").strip()
                    or (current_rec.get("smtp_app_password") or "").strip()
                ) if _smtp_edit else False
                def_nom_rem = (
                    (
                        (_smtp_cfg.get("smtp_nombre_remitente") if _smtp_cfg else None)
                        or current_rec.get("smtp_nombre_remitente")
                        or "Administración del Condominio"
                    )
                    if _smtp_edit
                    else "Administración del Condominio"
                )
                smtp_email_in = st.text_input(
                    "Correo Gmail del administrador",
                    value=def_smtp_em,
                    placeholder="admin@gmail.com",
                    max_chars=255,
                    disabled=not _smtp_edit,
                    key=f"condo_smtp_email_{form_key}",
                )
                app_pw_in = st.text_input(
                    "App Password de Gmail",
                    value="",
                    type="password",
                    placeholder=(
                        "Dejar vacío para conservar la guardada"
                        if has_saved_pw
                        else "16 caracteres (p. ej. xxxx xxxx xxxx xxxx)"
                    ),
                    help="Generar en: https://myaccount.google.com/apppasswords",
                    disabled=not _smtp_edit,
                    key=f"condo_smtp_app_pw_{form_key}",
                )
                nombre_rem_in = st.text_input(
                    "Nombre del remitente",
                    value=str(def_nom_rem),
                    max_chars=255,
                    disabled=not _smtp_edit,
                    key=f"condo_smtp_nombre_rem_{form_key}",
                )

            col_save, col_cancel = st.columns([1, 1])
            with col_save:
                guardar = st.form_submit_button(
                    "Guardar", use_container_width=True, type="primary"
                )
            with col_cancel:
                cancelar = st.form_submit_button(
                    "Cancelar", use_container_width=True
                )
            guardar_smtp = st.form_submit_button(
                "💾 Guardar configuración de correo",
                use_container_width=True,
                disabled=not _smtp_edit,
            )

        st.markdown("</div></div>", unsafe_allow_html=True)

        if cancelar:
            st.session_state.condo_modo = None
            st.rerun()

        if guardar_smtp and is_edit and current_rec:
            _pw_row = repo_notif.obtener_config_smtp(int(current_rec["id"]))
            pw_stored = (
                (_pw_row.get("smtp_app_password") or "")
                if _pw_row
                else (current_rec.get("smtp_app_password") or "")
            )
            pw_eff = (app_pw_in or "").strip() or pw_stored
            cfg = EmailConfig(
                (smtp_email_in or "").strip(),
                pw_eff,
                (nombre_rem_in or "").strip(),
            )
            errs = validar_config_smtp(cfg)
            if errs:
                for e in errs:
                    st.error(e)
            else:
                try:
                    repo_notif.actualizar_config_smtp(
                        int(current_rec["id"]),
                        (smtp_email_in or "").strip(),
                        (app_pw_in or "").strip() or None,
                        (nombre_rem_in or "").strip(),
                    )
                    st.success("✅ Configuración de correo guardada.")
                    st.session_state.condo_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

        if guardar:
            # Validaciones
            errors = validate_form(
                {"nombre": nombre, "direccion": direccion,
                 "numero_documento": num_doc, "email": email},
                {
                    "nombre":           {"required": True,  "max_length": 200},
                    "direccion":        {"required": True},
                    "numero_documento": {"required": True,  "max_length": 30},
                    "email":            {"required": False, "type": "email"},
                },
            )
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                # Moneda a persistir: código ISO desde país (o valor existente)
                pais_info   = pais_map.get(pais_id_sel, {})
                moneda_code = (
                    pais_info.get("moneda")
                    or (current_rec.get("moneda_principal") if is_edit and current_rec else "USD")
                )

                payload = {
                    "nombre":             (nombre or "").strip(),
                    "direccion":          (direccion or "").strip(),
                    "pais_id":            pais_id_sel,
                    "tipo_documento_id":  tipo_doc_id,
                    "numero_documento":   (num_doc or "").strip(),
                    "telefono":           (telefono or "").strip() or None,
                    "email":              (email or "").strip() or None,
                    "moneda_principal":   moneda_code,
                    "activo":             activo,
                    # Incluido en el mismo update/create (evita AttributeError si el
                    # despliegue no tiene actualizar_dia_limite en el repositorio).
                    "dia_limite_pago":    int(dia_limite_pago),
                }
                if is_edit and current_rec:
                    try:
                        repo_condo.update(current_rec["id"], payload)
                        st.success("✅ Condominio actualizado correctamente.")
                        st.session_state.condo_modo    = None
                        st.session_state.condo_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
                else:
                    try:
                        repo_condo.create(payload)
                        st.success("✅ Condominio creado exitosamente.")
                        st.session_state.condo_modo    = None
                        st.session_state.condo_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")

    # ── Lista de cards (cuando no hay formulario ni eliminación) ─────────────
    elif modo not in ("eliminar",):
        render_record_table(
            data=records,
            key="condominios",
            columns_config=CONDO_COLUMNS,
            search_field="nombre",
            caption="Listado de condominios",
            modo_key="condo_modo",
            on_incluir=lambda: st.session_state.update({"condo_modo": "incluir"}),
            on_modificar=lambda: st.session_state.update({"condo_modo": "modificar"}),
            on_eliminar=lambda: st.session_state.update({"condo_modo": "eliminar"}),
            empty_state_icon="🏢",
            empty_state_title="No hay condominios registrados aún",
            empty_state_subtitle="Use el botón Nuevo para agregar el primero.",
            page_size=20,
        )

    # ── Confirmación de eliminación ─────────────────────────────────────────
    if modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione un registro para eliminar.")
            st.session_state.condo_modo = None
        else:
            st.markdown("### 🗑️ Eliminar Condominio")
            st.warning(
                f"⚠️ ¿Está seguro que desea eliminar el condominio "
                f"**{current_rec.get('nombre')}**? Esta acción no se puede deshacer."
            )
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True):
                    try:
                        repo_condo.delete(current_rec["id"])
                        st.success("✅ Condominio eliminado correctamente.")
                        st.session_state.condo_modo    = None
                        st.session_state.condo_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_no:
                if st.button("✖ Cancelar", use_container_width=True):
                    st.session_state.condo_modo = None
                    st.rerun()

    # ── Detalle en tarjeta fija bajo la tabla (sin panel lateral) ────────────
    elif current_rec and modo is None:
        tasa = current_rec.get("tasa_cambio") or 0
        estado = "Activo" if current_rec.get("activo") else "Inactivo"

        st.markdown("#### Detalle del condominio seleccionado")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Nombre**: {current_rec.get('nombre') or '—'}")
                st.markdown(f"**Dirección**: {current_rec.get('direccion') or '—'}")
                st.markdown(
                    f"**País**: "
                    f"{(current_rec.get('paises') or {}).get('nombre') or '—'}"
                )
                st.markdown(
                    f"**Tipo documento**: "
                    f"{(current_rec.get('tipos_documento') or {}).get('nombre') or '—'}"
                )
                st.markdown(
                    f"**Número documento**: "
                    f"{current_rec.get('numero_documento') or '—'}"
                )
            with col2:
                st.markdown(f"**Teléfono**: {current_rec.get('telefono') or '—'}")
                st.markdown(f"**Email**: {current_rec.get('email') or '—'}")
                st.markdown(f"**Moneda**: {current_rec.get('moneda_principal') or '—'}")
                st.markdown(f"**Tasa BCV**: Bs. {float(tasa):,.4f}")
                st.markdown(f"**Estado**: {estado}")
                dlp = current_rec.get("dia_limite_pago")
                st.markdown(
                    f"**Día límite de pago**: "
                    f"{int(dlp) if dlp is not None else 15} (del mes)"
                )
        cid_det = int(current_rec["id"])
        smtp_cfg_det = repo_notif.obtener_config_smtp(cid_det)
        with st.expander("📧 Notificaciones: correo Gmail (SMTP)", expanded=False):
            st.caption(
                "Cuenta **@gmail.com** con **App Password**. "
                "Vacío en contraseña = conservar la guardada."
            )
            de = (
                st.text_input(
                    "Correo Gmail del administrador",
                    value=(smtp_cfg_det or {}).get("smtp_email") or "",
                    max_chars=255,
                    key=f"condo_smtp_det_email_{cid_det}",
                )
            )
            st.text_input(
                "App Password de Gmail",
                type="password",
                placeholder=(
                    "Dejar vacío para conservar la guardada"
                    if (smtp_cfg_det and (smtp_cfg_det.get("smtp_app_password") or "").strip())
                    else "16+ caracteres"
                ),
                key=f"condo_smtp_det_pw_{cid_det}",
            )
            dn = st.text_input(
                "Nombre del remitente",
                value=(smtp_cfg_det or {}).get("smtp_nombre_remitente")
                or "Administración del Condominio",
                max_chars=255,
                key=f"condo_smtp_det_nom_{cid_det}",
            )
            if st.button("Guardar configuración SMTP", key=f"condo_smtp_det_save_{cid_det}"):
                pw_t = (st.session_state.get(f"condo_smtp_det_pw_{cid_det}") or "").strip()
                pw_keep = (smtp_cfg_det or {}).get("smtp_app_password") or ""
                pw_val = pw_t if pw_t else pw_keep
                ec = EmailConfig(
                    smtp_email=(de or "").strip(),
                    app_password=pw_val,
                    nombre_remitente=(dn or "").strip(),
                )
                verrs = validar_config_smtp(ec)
                if verrs:
                    for err in verrs:
                        st.error(f"❌ {err}")
                else:
                    try:
                        repo_notif.actualizar_config_smtp(
                            cid_det,
                            (de or "").strip(),
                            pw_t if pw_t else None,
                            (dn or "").strip(),
                        )
                        st.success("✅ Configuración SMTP guardada.")
                        st.session_state.condo_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")

with col_help:
    render_help_panel(
        icono="🏢",
        titulo="Condominios",
        descripcion_corta="Gestión de condominios registrados en el sistema.",
        descripcion_larga=(
            "Un condominio es la unidad principal del sistema. "
            "Todos los demás módulos (unidades, propietarios, proveedores, etc.) "
            "pertenecen a un condominio específico. Configure aquí el nombre, "
            "dirección, tipo de documento fiscal, tasa de cambio y mes en proceso."
        ),
        tips=[
            "El tipo de documento cambia según el país seleccionado.",
            "La tasa de cambio BCV se utiliza en reportes financieros.",
            "Solo puede haber un condominio activo por sesión.",
        ],
    )
    render_help_shortcuts({
        "➕ Incluir":   "Registrar nuevo condominio",
        "✏️ Modificar": "Editar condominio seleccionado",
        "🗑️ Eliminar":  "Eliminar (requiere confirmación)",
    })
