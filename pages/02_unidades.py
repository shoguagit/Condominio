import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.unidad_repository import UnidadRepository
from repositories.propietario_repository import PropietarioRepository
from repositories.unidad_propietario_repository import UnidadPropietarioRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.record_table import render_record_table
from components.detail_panel import check_close_detail, render_detail_panel
from components.styles import render_table_skeleton
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form, validate_email, validate_cedula_o_rif, validate_telefono_venezolano
from utils.indiviso_cuota import valida_no_supera_100_pct, valida_suma_exacta_100_pct, TOLERANCIA_INDIVISO_PCT

st.set_page_config(page_title="Unidades", page_icon="🏠", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Unidades")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.uni_records = None


@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return (
        UnidadRepository(client),
        PropietarioRepository(client),
        UnidadPropietarioRepository(client),
    )


repo_unidad, repo_prop, repo_unidad_prop = get_repos()

for k, v in {"uni_modo": None, "uni_records": None, "uni_filtro_estado": "Todos"}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("unidades")

TIPOS_UNIDAD = ["Apartamento", "Casa", "Local comercial", "Estacionamiento"]
TIPOS_CONDOMINO = ["Propietario", "Arrendatario"]
FILTROS_ESTADO = ["Todos", "Al día", "Moroso", "Parcial"]

MAP_ESTADO_DB = {"Al día": "al_dia", "Moroso": "moroso", "Parcial": "parcial"}
MAP_DB_ESTADO = {v: k for k, v in MAP_ESTADO_DB.items()}


def _estado_label(db_val: str) -> str:
    if (db_val or "") == "al_dia":
        return "🟢 Al día"
    if db_val == "moroso":
        return "🔴 Moroso"
    if db_val == "parcial":
        return "🟡 Parcial"
    return "—"


def load_unidades():
    pres = float(st.session_state.get("presupuesto_mes") or 0)
    return repo_unidad.get_with_cuota(condominio_id, pres)


st.markdown("## 🏠 Unidades")

col_main, col_help = st.columns([4, 1])

if st.session_state.uni_records is None:
    with col_main:
        render_table_skeleton(column_count=3, row_count=6)
    st.session_state.uni_records = load_unidades()
    st.rerun()

records = st.session_state.uni_records

try:
    indicadores = repo_unidad.get_indicadores(condominio_id)
except DatabaseError:
    indicadores = {"total": 0, "al_dia": 0, "morosos": 0, "pct_asignado": 0.0}

with col_main:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total unidades", indicadores.get("total", 0))
    m2.metric('Unidades "Al día"', indicadores.get("al_dia", 0))
    m3.metric("Morosas", indicadores.get("morosos", 0))
    m4.metric("% indiviso asignado", f"{indicadores.get('pct_asignado', 0):.2f}%")

with col_help:
    render_help_panel(
        icono="🏠",
        titulo="Unidades",
        descripcion_corta="Padrón de unidades con indiviso % y propietario.",
        descripcion_larga=(
            "La suma de indivisos del condominio debe ser 100,00% (±0,01%). "
            "La cuota en Bs. usa el presupuesto del mes del estado de sesión."
        ),
        tips=[
            "Indiviso: porcentaje del reglamento; no se recalcula salvo cambio formal.",
            "Configure el presupuesto en Proceso mensual.",
        ],
    )
    render_help_shortcuts({
        "Nuevo": "Registrar nueva unidad",
        "Ver": "Ver detalle",
        "Editar": "Editar",
        "Eliminar": "Eliminar",
    })

with col_main:
    check_close_detail("unidades")

    filtro_col, _ = st.columns([1, 3])
    with filtro_col:
        st.session_state.uni_filtro_estado = st.selectbox(
            "Estado de pago",
            options=FILTROS_ESTADO,
            index=FILTROS_ESTADO.index(st.session_state.uni_filtro_estado)
            if st.session_state.uni_filtro_estado in FILTROS_ESTADO
            else 0,
            key="uni_filtro_estado_sb",
        )

    for r in records:
        prop = r.get("propietarios") or {}
        r["_propietario"] = prop.get("nombre", "—")
        r["_cedula"] = prop.get("cedula", "")
        tipo_u = r.get("tipo") or r.get("tipo_propiedad") or "—"
        r["_tipo_display"] = tipo_u
        ep = r.get("estado_pago") or "al_dia"
        r["_estado_label"] = _estado_label(ep)
        cu = r.get("_cuota_bs")
        r["_cuota_display"] = f"{cu:,.2f}" if cu is not None else "—"

    filtro = st.session_state.uni_filtro_estado
    if filtro != "Todos":
        key = MAP_ESTADO_DB.get(filtro, "")
        display_list = [r for r in records if (r.get("estado_pago") or "al_dia") == key]
    else:
        display_list = list(records)

    UNI_COLUMNS = {
        "codigo": {"label": "Código", "width": 100},
        "_propietario": {"label": "Propietario", "width": 200},
        "_tipo_display": {"label": "Tipo", "width": 130},
        "indiviso_pct": {"label": "Indiviso %", "width": 90},
        "_cuota_display": {"label": "Cuota Bs.", "width": 100},
        "_estado_label": {"label": "Estado", "width": 120},
    }

    current_idx = get_current_index("unidades")
    if display_list and current_idx >= len(display_list):
        set_current_index("unidades", 0)
        current_idx = 0
    current_rec = (
        display_list[current_idx]
        if display_list and 0 <= current_idx < len(display_list)
        else None
    )
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
        st.markdown('<p class="form-card-hint">Campos con * son obligatorios</p>', unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        exclude_id = cr.get("id") if is_edit else None
        try:
            suma_otros = repo_unidad.get_suma_indivisos(condominio_id, exclude_id=exclude_id)
            disponible = repo_unidad.get_disponible_indiviso(condominio_id, exclude_id=exclude_id)
        except DatabaseError:
            suma_otros = 0.0
            disponible = 100.0

        try:
            tipo_default = TIPOS_UNIDAD.index(
                (cr.get("tipo") or cr.get("tipo_propiedad") or "Apartamento")
            )
        except ValueError:
            tipo_default = 0

        prop = cr.get("propietarios") or {}

        with st.form("form_unidad"):
            st.markdown('<p class="form-section-hdr">Datos de la unidad</p>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                codigo = st.text_input(
                    "Código *",
                    value=cr.get("codigo", ""),
                    placeholder="Ej: Apto 3B, Local 01",
                    max_chars=30,
                )
                tipo_unidad = st.selectbox("Tipo *", options=TIPOS_UNIDAD, index=tipo_default)
            with col2:
                indiviso_pct = st.number_input(
                    "Indiviso (%) *",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.01,
                    format="%.4f",
                    value=float(cr.get("indiviso_pct", 0) or 0),
                    help=(
                        "Porcentaje de participación según el reglamento. "
                        "Ejemplo: si la unidad tiene 0.45% → escribir 0.45. "
                        "La suma de todos los indivisos debe ser exactamente 100."
                    ),
                )
                st.caption(
                    "💡 Valores típicos: entre 0.30 y 1.50 según el tamaño "
                    "de la unidad. La suma total del condominio = 100.00"
                )
                st.caption(f"Disponible para asignar (resto del condominio): **{disponible:.2f}%**")

            st.markdown('<p class="form-section-hdr">Datos del propietario</p>', unsafe_allow_html=True)
            colp1, colp2 = st.columns(2)
            with colp1:
                nombre_prop = st.text_input(
                    "Nombre completo *",
                    value=prop.get("nombre", ""),
                    max_chars=200,
                )
                cedula_rif = st.text_input(
                    "Cédula / RIF",
                    value=prop.get("cedula", ""),
                    placeholder="V-12345678 o J-12345678-9",
                )
            with colp2:
                telefono = st.text_input(
                    "Teléfono",
                    value=prop.get("telefono", ""),
                    placeholder="04XX-XXXXXXX",
                )
                correo = st.text_input(
                    "Correo electrónico",
                    value=prop.get("correo", ""),
                )

            st.markdown('<p class="form-section-hdr">Otros</p>', unsafe_allow_html=True)
            colo1, colo2 = st.columns(2)
            with colo1:
                tipo_condomino = st.selectbox(
                    "Tipo de condómino *",
                    options=TIPOS_CONDOMINO,
                    index=TIPOS_CONDOMINO.index(cr["tipo_condomino"])
                    if cr.get("tipo_condomino") in TIPOS_CONDOMINO
                    else 0,
                )
                piso = st.text_input("Piso", value=cr.get("piso", ""), max_chars=10)
            with colo2:
                activo = st.checkbox("Activo", value=cr.get("activo", True))

            col_s, col_c = st.columns(2)
            with col_s:
                guardar = st.form_submit_button("Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.uni_modo = None
            st.rerun()

        if guardar:
            errs = validate_form(
                {"codigo": codigo, "nombre_prop": nombre_prop},
                {"codigo": {"required": True, "max_length": 30}, "nombre_prop": {"required": True, "max_length": 200}},
            )
            ok_ced, msg_ced = validate_cedula_o_rif(cedula_rif)
            if not ok_ced:
                errs.append(msg_ced)
            ok_mail, msg_mail = validate_email(correo)
            if correo and not ok_mail:
                errs.append(msg_mail)
            ok_tel, msg_tel = validate_telefono_venezolano(telefono)
            if telefono and not ok_tel:
                errs.append(msg_tel)

            nueva_suma = suma_otros + float(indiviso_pct or 0)
            ok_lim, msg_lim = valida_no_supera_100_pct(nueva_suma)
            if not ok_lim:
                errs.append(msg_lim)

            if errs:
                for e in errs:
                    st.error(f"❌ {e}")
            else:
                try:
                    pid = (cr.get("propietarios") or {}).get("id") or cr.get("propietario_id")
                    prop_payload = {
                        "condominio_id": condominio_id,
                        "nombre": (nombre_prop or "").strip(),
                        "cedula": (cedula_rif or "").strip() or None,
                        "telefono": (telefono or "").strip() or None,
                        "correo": (correo or "").strip() or None,
                        "activo": True,
                    }
                    if pid:
                        repo_prop.update(int(pid), prop_payload)
                        propietario_id = int(pid)
                    else:
                        created = repo_prop.create(prop_payload)
                        propietario_id = int(created["id"])

                    cod = (codigo or "").strip()
                    payload = {
                        "condominio_id": condominio_id,
                        "codigo": cod,
                        "numero": cod,
                        "tipo": tipo_unidad,
                        "tipo_propiedad": tipo_unidad,
                        "indiviso_pct": float(indiviso_pct),
                        "estado_pago": cr.get("estado_pago") or "al_dia",
                        "propietario_id": propietario_id,
                        "alicuota_id": None,
                        "tipo_condomino": tipo_condomino,
                        "piso": (piso or "").strip() or None,
                        "activo": activo,
                        "saldo": float(cr.get("saldo") or 0),
                    }

                    if is_edit and current_rec:
                        repo_unidad.update(current_rec["id"], payload)
                        st.success("✅ Unidad actualizada.")
                    else:
                        repo_unidad.create(payload)
                        st.success("✅ Unidad registrada.")

                    total_condo = repo_unidad.get_suma_indivisos(condominio_id, exclude_id=None)
                    ok_100, msg_100 = valida_suma_exacta_100_pct(total_condo)
                    if not ok_100:
                        st.warning(
                            f"⚠️ {msg_100} "
                            f"(tolerancia ±{TOLERANCIA_INDIVISO_PCT:.2f} puntos porcentuales)."
                        )

                    st.session_state.uni_modo = None
                    st.session_state.uni_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

        if is_edit and current_rec and current_rec.get("id"):
            uid = current_rec["id"]
            st.markdown('<p class="form-section-hdr">Propietarios adicionales de esta unidad</p>', unsafe_allow_html=True)
            try:
                asignaciones = repo_unidad_prop.get_by_unidad(uid)
            except Exception:
                asignaciones = []
            propietarios_list = repo_prop.get_all(condominio_id, solo_activos=True)
            asignados_ids = {a.get("propietario_id") for a in asignaciones}
            prop_disponibles = [p for p in propietarios_list if p["id"] not in asignados_ids]

            for a in asignaciones:
                p_as = a.get("propietarios") or {}
                nombre_a = p_as.get("nombre", "—")
                es_p = a.get("es_principal")
                act_a = a.get("activo", True)
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(
                        f"{nombre_a}"
                        + (" *(principal)*" if es_p else "")
                        + ("" if act_a else " *(inactivo)*")
                    )
                with c2:
                    if not es_p and st.button("Principal", key=f"up_pr_{a['id']}_{uid}", use_container_width=True):
                        try:
                            repo_unidad_prop.set_principal(uid, a["id"])
                            pid = a.get("propietario_id")
                            if pid:
                                repo_unidad.update(uid, {"propietario_id": pid})
                            st.session_state.uni_records = None
                            st.rerun()
                        except DatabaseError as e:
                            st.error(str(e))
                    if st.button("Quitar", key=f"up_q_{a['id']}_{uid}", use_container_width=True):
                        try:
                            repo_unidad_prop.remove(a["id"])
                            if a.get("es_principal") and current_rec.get("propietario_id") == a.get("propietario_id"):
                                repo_unidad.update(uid, {"propietario_id": None})
                            st.session_state.uni_records = None
                            st.rerun()
                        except DatabaseError as e:
                            st.error(str(e))

            if prop_disponibles:
                sel = st.selectbox(
                    "Añadir propietario",
                    options=[p["nombre"] for p in prop_disponibles],
                    key=f"up_add_{uid}",
                )
                if st.button("Añadir propietario", key=f"up_add_btn_{uid}"):
                    prop_id = prop_disponibles[[p["nombre"] for p in prop_disponibles].index(sel)]["id"]
                    try:
                        es_prim = len(asignaciones) == 0
                        repo_unidad_prop.add(uid, prop_id, activo=True, es_principal=es_prim)
                        if es_prim:
                            repo_unidad.update(uid, {"propietario_id": prop_id})
                        st.session_state.uni_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(str(e))

        st.markdown("</div>", unsafe_allow_html=True)

    elif modo not in ("eliminar",):
        render_record_table(
            data=display_list,
            key="unidades",
            columns_config=UNI_COLUMNS,
            search_field="codigo",
            search_fields=["codigo", "_propietario"],
            caption="Listado de unidades",
            modo_key="uni_modo",
            on_incluir=lambda: st.session_state.update({"uni_modo": "incluir"}),
            on_modificar=lambda: st.session_state.update({"uni_modo": "modificar"}),
            on_eliminar=lambda: st.session_state.update({"uni_modo": "eliminar"}),
            empty_state_icon="🏠",
            empty_state_title="No hay unidades",
            empty_state_subtitle="Use + Nuevo para agregar.",
            page_size=20,
            right_align_columns=["indiviso_pct"],
        )

    if modo == "eliminar":
        if not current_rec:
            st.warning("Seleccione una unidad.")
            st.session_state.uni_modo = None
        else:
            label = current_rec.get("codigo") or current_rec.get("numero", "")
            st.markdown("### Eliminar unidad")
            st.warning(f"¿Eliminar la unidad **{label}**?")
            c_y, c_n = st.columns(2)
            with c_y:
                if st.button("Sí, eliminar", type="primary", use_container_width=True, key="uni_dy"):
                    try:
                        repo_unidad.delete(current_rec["id"])
                        st.success("Unidad eliminada.")
                        st.session_state.uni_modo = None
                        st.session_state.uni_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(str(e))
            with c_n:
                if st.button("Cancelar", use_container_width=True, key="uni_dn"):
                    st.session_state.uni_modo = None
                    st.rerun()

    elif current_rec and modo is None:
        prop = current_rec.get("propietarios") or {}
        detail_fields = [
            ("Código", current_rec.get("codigo") or "—"),
            ("Tipo", current_rec.get("tipo") or current_rec.get("tipo_propiedad") or "—"),
            ("Indiviso %", str(current_rec.get("indiviso_pct") or "0")),
            ("Propietario", prop.get("nombre") or "—"),
            ("Estado pago", _estado_label(current_rec.get("estado_pago") or "al_dia")),
            ("Saldo (Bs.)", str(current_rec.get("saldo") or "0")),
        ]
        render_detail_panel(detail_fields, "unidades", "Detalle de la unidad")
