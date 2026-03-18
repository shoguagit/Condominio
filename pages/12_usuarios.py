import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.usuario_repository import UsuarioRepository
from repositories.condominio_repository import CondominioRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.record_table import render_record_table
from components.detail_panel import check_close_detail, render_detail_panel
from components.styles import render_table_skeleton
from utils.auth import check_authentication, check_permission, require_condominio
from utils.error_handler import DatabaseError, AuthError
from utils.validators import validate_form
from utils.formatters import format_date

# ── Protección: solo Administradores ─────────────────────────────────────────
st.set_page_config(page_title="Usuarios", page_icon="🔐", layout="wide")
check_authentication()
check_permission("admin")

render_header()
render_breadcrumb("Usuarios")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.usr_records = None
# ── Repositorios ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return UsuarioRepository(client), CondominioRepository(client)

repo_user, repo_condo = get_repos()

# ── Estado ────────────────────────────────────────────────────────────────────
for key, val in {
    "usr_modo":     None,   # "incluir" | "modificar" | "desactivar" | "cambiar_pass" | None
    "usr_records":  None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

init_toolbar_state("usuarios")

# ── Carga ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_condominios():
    return repo_condo.get_all(solo_activos=True)

def load_usuarios():
    return repo_user.get_all(condominio_id)

USR_COLUMNS = {
    "id":              {"label": "Id",            "width": 55},
    "nombre":          {"label": "Nombre",        "width": 200},
    "email":           {"label": "Email",         "width": 210},
    "rol":             {"label": "Rol",           "width": 100},
    "_condominio":     {"label": "Condominio",    "width": 160},
    "_ultimo_acceso":  {"label": "Último Acceso", "width": 120},
    "activo":          {"label": "Activo",        "width": 65, "format": "boolean"},
}

st.markdown("## 🔐 Usuarios del Sistema")

st.info(
    "🔐 **Módulo restringido.** Solo los administradores pueden crear, "
    "modificar o desactivar usuarios del sistema.",
    icon="ℹ️",
)

col_main, col_help = st.columns([3, 1])

if st.session_state.usr_records is None:
    with col_main:
        render_table_skeleton(column_count=3, row_count=6)
    st.session_state.usr_records = load_usuarios()
    st.rerun()

records     = st.session_state.usr_records
condominios = load_condominios()

with col_help:
    render_help_panel(
        icono="🔐",
        titulo="Usuarios",
        descripcion_corta="Gestión de usuarios con acceso al sistema.",
        descripcion_larga=(
            "Los usuarios son las personas que pueden iniciar sesión. "
            "Cada usuario tiene un rol que determina sus permisos: "
            "Administrador (acceso total), Operador (carga y edición) "
            "y Solo Consulta (lectura)."
        ),
        tips=[
            "La contraseña se gestiona en Supabase Auth.",
            "Use 'Desactivar' en lugar de eliminar para mantener historial.",
            "Solo el Administrador puede acceder a este módulo.",
            "El email es único en todo el sistema.",
        ],
    )
    render_help_shortcuts({
        "Nuevo":        "Crear usuario + contraseña",
        "Ver":          "Ver detalle",
        "Editar":       "Editar datos",
        "Desactivar":   "Activar/Desactivar (en tarjeta)",
        "Contraseña":   "Ver tarjeta → Cambiar contraseña",
    })

with col_main:
    check_close_detail("usuarios")
    for r in records:
        r["_condominio"]    = (r.get("condominios") or {}).get("nombre", "—")
        r["_ultimo_acceso"] = format_date(r.get("ultimo_acceso")) or "Nunca"

    current_idx = get_current_index("usuarios")
    current_rec = records[current_idx] if records and 0 <= current_idx < len(records) else None
    modo        = st.session_state.usr_modo

    if modo not in ("incluir", "modificar", "desactivar", "cambiar_pass"):
        render_record_table(
            data=records,
            key="usuarios",
            columns_config=USR_COLUMNS,
            search_field="nombre",
            caption="Listado de usuarios",
            modo_key="usr_modo",
            on_incluir=lambda: st.session_state.update({"usr_modo": "incluir"}),
            on_modificar=lambda: st.session_state.update({"usr_modo": "modificar"}),
            on_eliminar=lambda: st.session_state.update({"usr_modo": "desactivar"}),
            empty_state_icon="🔐",
            empty_state_title="Este condominio no tiene usuarios registrados aún",
            empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
            page_size=20,
        )

    # =========================================================================
    # FORMULARIO: INCLUIR nuevo usuario
    # =========================================================================
    if modo == "incluir":
        st.markdown('<p class="form-card-title">Nuevo usuario</p>', unsafe_allow_html=True)
        st.markdown('<p class="form-card-hint">Campos marcados con * son obligatorios</p>', unsafe_allow_html=True)

        condo_nombres = [c["nombre"] for c in condominios]
        condo_ids     = [c["id"]     for c in condominios]
        try:
            condo_default = condo_ids.index(condominio_id)
        except ValueError:
            condo_default = 0

        with st.form("form_user_new"):
            st.markdown(
                '<p class="form-section-hdr">Datos del usuario</p>',
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                nombre   = st.text_input("Nombre completo *", max_chars=150)
                email    = st.text_input("Email *",           max_chars=100,
                                         placeholder="usuario@email.com")
                condo_sel = st.selectbox(
                    "Condominio asignado *",
                    options=condo_nombres if condo_nombres else ["—"],
                    index=condo_default,
                )
                condo_id_sel = condo_ids[condo_nombres.index(condo_sel)] if condo_nombres else None

            with col2:
                rol = st.selectbox(
                    "Rol *",
                    options=["admin", "operador"],
                    format_func=lambda r: {"admin": "Administrador",
                                           "operador": "Operador"}[r],
                )
                st.markdown(
                    """
                    <div style='background:#EBF5FB; border-radius:6px; padding:10px 12px;
                                font-size:12px; color:#2C3E50; margin-top:4px;'>
                        <b>Permisos por rol:</b><br>
                        Administrador — acceso total<br>
                        Operador — carga y edición
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("")
            st.markdown(
                '<p class="form-section-hdr">Contraseña de acceso</p>',
                unsafe_allow_html=True,
            )
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                password  = st.text_input("Contraseña *", type="password",
                                           help="Mínimo 8 caracteres")
            with col_p2:
                password2 = st.text_input("Confirmar contraseña *", type="password")

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("Guardar",
                                                  use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.usr_modo = None
            st.rerun()

        if guardar:
            errors = validate_form(
                {"nombre": nombre, "email": email,
                 "password": password, "condo": condo_id_sel},
                {
                    "nombre":   {"required": True, "max_length": 150},
                    "email":    {"required": True, "type": "email"},
                    "password": {"required": True},
                    "condo":    {"required": True},
                },
            )
            if password and len(password) < 8:
                errors.append("La contraseña debe tener al menos 8 caracteres.")
            if password and password2 and password != password2:
                errors.append("Las contraseñas no coinciden.")

            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {
                    "nombre":        (nombre or "").strip(),
                    "email":         (email or "").strip().lower(),
                    "rol":           rol,
                    "condominio_id": condo_id_sel,
                    "activo":        True,
                }
                try:
                    repo_user.create(payload, password)
                    st.success(
                        f"✅ Usuario **{nombre}** creado exitosamente. "
                        "Puede iniciar sesión con su correo y contraseña."
                    )
                    st.session_state.usr_modo    = None
                    st.session_state.usr_records = None
                    st.rerun()
                except (DatabaseError, AuthError) as e:
                    st.error(f"❌ {e}")

    # =========================================================================
    # FORMULARIO: MODIFICAR usuario (sin contraseña)
    # =========================================================================
    elif modo == "modificar":
        if not current_rec:
            st.warning("⚠️ Seleccione un usuario para modificar.")
            st.session_state.usr_modo = None
        else:
            st.markdown(
                f'<p class="form-card-title">Modificar usuario — {current_rec.get("nombre", "")}</p>',
                unsafe_allow_html=True,
            )
            st.markdown('<p class="form-card-hint">El email no se puede modificar.</p>', unsafe_allow_html=True)

            condo_nombres = [c["nombre"] for c in condominios]
            condo_ids     = [c["id"]     for c in condominios]
            def_condo     = current_rec.get("condominio_id", condominio_id)
            try:
                condo_default = condo_ids.index(def_condo)
            except ValueError:
                condo_default = 0

            ROLES = ["admin", "operador"]
            rol_actual = current_rec.get("rol", "operador")
            if rol_actual == "consulta":
                rol_actual = "operador"
            rol_default = ROLES.index(rol_actual) if rol_actual in ROLES else 1

            with st.form("form_user_edit"):
                st.markdown(
                    '<p class="form-section-hdr">Datos del usuario</p>',
                    unsafe_allow_html=True,
                )
                col1, col2 = st.columns(2)
                with col1:
                    nombre = st.text_input("Nombre completo *",
                                           value=current_rec.get("nombre", ""), max_chars=150)
                    email  = st.text_input(
                        "Email",
                        value=current_rec.get("email", ""),
                        disabled=True,
                        help="El email no se puede modificar.",
                    )
                    condo_sel = st.selectbox(
                        "Condominio asignado *",
                        options=condo_nombres if condo_nombres else ["—"],
                        index=condo_default,
                    )
                    condo_id_sel = condo_ids[condo_nombres.index(condo_sel)] if condo_nombres else None

                with col2:
                    rol    = st.selectbox(
                        "Rol *",
                        options=ROLES,
                        index=rol_default,
                        format_func=lambda r: {"admin": "Administrador",
                                               "operador": "Operador"}[r],
                    )
                    activo = st.checkbox("Activo", value=current_rec.get("activo", True))
                    st.markdown(
                        "<div style='background:#F8F9FA; border-radius:6px; padding:10px 12px;"
                        "font-size:12px; color:#5D6D7E;'>"
                        "Para cambiar la contraseña use el botón <b>Cambiar contraseña</b> en la barra superior."
                        "</div>",
                        unsafe_allow_html=True,
                    )

                col_s, col_c = st.columns(2)
                with col_s:
                    guardar  = st.form_submit_button("Guardar",
                                                      use_container_width=True, type="primary")
                with col_c:
                    cancelar = st.form_submit_button("Cancelar", use_container_width=True)

            if cancelar:
                st.session_state.usr_modo = None
                st.rerun()

            if guardar:
                errors = validate_form(
                    {"nombre": nombre, "condo": condo_id_sel},
                    {
                        "nombre": {"required": True, "max_length": 150},
                        "condo":  {"required": True},
                    },
                )
                if errors:
                    for e in errors:
                        st.error(f"❌ {e}")
                else:
                    payload = {
                        "nombre":        (nombre or "").strip(),
                        "rol":           rol,
                        "condominio_id": condo_id_sel,
                        "activo":        activo,
                    }
                    try:
                        repo_user.update(current_rec["id"], payload)
                        st.success("✅ Usuario actualizado correctamente.")
                        st.session_state.usr_modo    = None
                        st.session_state.usr_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")

    # =========================================================================
    # DESACTIVAR / ACTIVAR usuario
    # =========================================================================
    elif modo == "desactivar":
        if not current_rec:
            st.warning("⚠️ Seleccione un usuario.")
            st.session_state.usr_modo = None
        else:
            es_activo = current_rec.get("activo", True)
            accion    = "desactivar" if es_activo else "activar"
            icono     = "🚫" if es_activo else "✅"

            st.markdown(f"### {icono} {accion.capitalize()} Usuario")
            if es_activo:
                st.warning(
                    f"⚠️ El usuario **{current_rec.get('nombre')}** perderá acceso al sistema. "
                    "Sus datos se conservarán."
                )
            else:
                st.info(
                    f"ℹ️ El usuario **{current_rec.get('nombre')}** recuperará acceso al sistema."
                )

            col_y, col_n = st.columns(2)
            with col_y:
                if st.button(
                    f"{icono} Sí, {accion}",
                    type="primary",
                    use_container_width=True,
                    key="usr_toggle_btn",
                ):
                    # No permitir desactivar al propio usuario logueado
                    if current_rec.get("email") == st.session_state.get("user_email"):
                        st.error("❌ No puede desactivar su propio usuario.")
                    else:
                        try:
                            repo_user.toggle_activo(current_rec["id"], not es_activo)
                            st.success(
                                f"✅ Usuario {'desactivado' if es_activo else 'activado'} correctamente."
                            )
                            st.session_state.usr_modo    = None
                            st.session_state.usr_records = None
                            st.rerun()
                        except DatabaseError as e:
                            st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="usr_toggle_cancel"):
                    st.session_state.usr_modo = None
                    st.rerun()

    # =========================================================================
    # CAMBIAR CONTRASEÑA
    # =========================================================================
    elif modo == "cambiar_pass":
        if not current_rec:
            st.warning("⚠️ Seleccione un usuario para cambiar su contraseña.")
            st.session_state.usr_modo = None
        else:
            st.markdown(
                f'<p class="form-card-title">Cambiar contraseña — {current_rec.get("nombre", "")}</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='background:#F8F9FA; border-radius:6px; padding:10px 14px;"
                f"font-size:13px; margin-bottom:12px; color:#2C3E50;'>"
                f"<b>{current_rec.get('nombre')}</b> — {current_rec.get('email')}"
                f"</div>",
                unsafe_allow_html=True,
            )

            with st.form("form_change_pass"):
                st.markdown(
                    '<p class="form-section-hdr">Nueva contraseña</p>',
                    unsafe_allow_html=True,
                )
                col1, col2 = st.columns(2)
                with col1:
                    new_pass  = st.text_input("Nueva contraseña *", type="password",
                                               help="Mínimo 8 caracteres")
                with col2:
                    new_pass2 = st.text_input("Confirmar nueva contraseña *", type="password")

                col_s, col_c = st.columns(2)
                with col_s:
                    guardar  = st.form_submit_button("Guardar",
                                                      use_container_width=True, type="primary")
                with col_c:
                    cancelar = st.form_submit_button("Cancelar", use_container_width=True)

            if cancelar:
                st.session_state.usr_modo = None
                st.rerun()

            if guardar:
                errors = []
                if not new_pass:
                    errors.append("La contraseña es obligatoria.")
                elif len(new_pass) < 8:
                    errors.append("La contraseña debe tener al menos 8 caracteres.")
                if new_pass != new_pass2:
                    errors.append("Las contraseñas no coinciden.")

                if errors:
                    for e in errors:
                        st.error(f"❌ {e}")
                else:
                    try:
                        repo_user.change_password(current_rec["email"], new_pass)
                        st.success(
                            f"✅ Contraseña de **{current_rec.get('nombre')}** "
                            "actualizada correctamente."
                        )
                        st.session_state.usr_modo = None
                        st.rerun()
                    except AuthError as e:
                        st.error(f"❌ {e}")

    # =========================================================================
    # VISTA DETALLE (panel slide-in)
    # =========================================================================
    elif current_rec and modo is None:
        rol_label = {"admin": "Administrador", "operador": "Operador",
                     "consulta": "Solo Consulta"}.get(current_rec.get("rol", ""), current_rec.get("rol", "—"))
        condo_nombre = (current_rec.get("condominios") or {}).get("nombre", "—")
        detail_fields = [
            ("Nombre", current_rec.get("nombre") or "—"),
            ("Email", current_rec.get("email") or "—"),
            ("Rol", rol_label),
            ("Condominio", condo_nombre),
            ("Último acceso", format_date(current_rec.get("ultimo_acceso")) or "Nunca"),
            ("Estado", "Activo" if current_rec.get("activo") else "Inactivo"),
        ]
        render_detail_panel(detail_fields, "usuarios", "Detalle del usuario")
        if st.button("Cambiar contraseña", key="usr_btn_cambiar_pass"):
            st.session_state.usr_modo = "cambiar_pass"
            st.rerun()
