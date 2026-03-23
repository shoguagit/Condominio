"""
Estados de cuenta masivos: PDF Sisconin + envío Gmail (Fase 5-C mejorada).
Selección por grupos, tesorero con PDF combinado, alertas de coherencia.
"""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from components.breadcrumb import render_breadcrumb
from components.header import render_header
from config.supabase_client import get_supabase_client
from repositories.estado_cuenta_repository import EstadoCuentaRepository
from repositories.notificacion_repository import NotificacionRepository
from utils.agrupador_unidades import agrupar_unidades, detectar_numero
from utils.auth import check_authentication, require_condominio
from utils.dashboard_formatters import periodo_a_mmyyyy
from utils.email_sender import EmailConfig, enviar_correo_con_adjunto
from utils.error_handler import DatabaseError
from utils.estado_cuenta_coherencia import calcular_alertas_coherencia
from utils.estado_cuenta_pdf import generar_estado_cuenta_pdf
from utils.formatters import format_mes_proceso
from utils.pdf_combinado import combinar_pdfs
from utils.validators import periodo_to_date_str, validate_periodo, validate_email

_log_ec = logging.getLogger(__name__)

PIE_TITULAR_DEFAULT = (
    "De conformidad con lo aprobado por la Asamblea de propietarios, el recibo de condominio "
    "a partir del mes de noviembre 2025, se emitirá en divisas y cancelado a la tasa del BCV "
    "de la fecha de pago."
)
PIE_CUERPO_DEFAULT = (
    "De conformidad con lo aprobado por la Asamblea de propietarios, el 14 de Marzo de 2024 se "
    "ratificó y aprobó la cancelación de las divisas presentadas en los recibos, al tipo de cambio "
    "publicado por el BCV para su fecha de pago. RECUERDE LA IMPORTANCIA DE TENER SUS PAGOS AL DIA."
)

MODO_TESORERO_AMBOS = "Enviar al propietario Y al Tesorero"
MODO_TESORERO_SOLO = "Enviar SOLO al Tesorero (el propietario NO recibe)"


def _html_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _tiene_email(u: dict) -> bool:
    e = u.get("propietario_email")
    if e is None:
        return False
    if isinstance(e, list):
        return any(str(x or "").strip() for x in e)
    return bool(str(e).strip())


def _email_para_smtp(u: dict) -> str | None:
    e = u.get("propietario_email")
    if e is None:
        return None
    if isinstance(e, list):
        for x in e:
            s = str(x or "").strip()
            if s:
                return s
        return None
    s = str(e).strip()
    return s or None


st.set_page_config(page_title="Estados de cuenta masivo", page_icon="📄", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Estados de cuenta masivo")

condominio_id = require_condominio()
cid = int(condominio_id)
# Tasa en sesión (sidebar / contexto) tiene prioridad sobre BD para PDF y coherencia
tasa_para_pdf = float(st.session_state.get("tasa_cambio", 0) or 0)


@st.cache_resource
def _repos():
    c = get_supabase_client()
    return EstadoCuentaRepository(c), NotificacionRepository(c)


ec_repo, notif_repo = _repos()


def _obtener_datos_para_pdf(
    unidad_id: int,
    condominio_id_: int,
    periodo_sql: str,
) -> tuple[dict | None, str | None]:
    """
    Llama a ``obtener_datos_unidad_periodo`` sin propagar excepciones a Streamlit.
    Retorna ``(datos, None)`` o ``(None, mensaje)`` si falla (p. ej. ``DatabaseError``).
    """
    try:
        out = ec_repo.obtener_datos_unidad_periodo(unidad_id, condominio_id_, periodo_sql)
        return out, None
    except Exception as e:
        _log_ec.warning(
            "_obtener_datos_para_pdf: unidad_id=%s condominio_id=%s periodo=%r: %s",
            unidad_id,
            condominio_id_,
            periodo_sql,
            e,
        )
        return None, str(e)


st.title("📄 Estados de cuenta masivo")
st.caption(
    "Genera y envía PDFs de estado de cuenta (recibo venezolano). "
    "Selecciona unidades, revisa alertas y opcionalmente envía un PDF combinado al tesorero."
)

try:
    config = ec_repo.obtener_config_condominio_pdf(cid)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

if not config:
    st.error("No se pudo cargar la configuración del condominio.")
    st.stop()

if not (config.get("smtp_email") or "").strip():
    st.warning(
        "⚠️ Configura el correo SMTP en **Condominios** (detalle → notificaciones Gmail) "
        "antes de enviar."
    )
    st.page_link("pages/01_condominios.py", label="→ Ir a Condominios", icon="🏢")
    st.stop()

default_periodo = format_mes_proceso(st.session_state.get("mes_proceso")) or ""

# ═══════════════════════════════════════════════════════════════════════════
# PASO 1: CONFIGURACIÓN DEL ENVÍO
# ═══════════════════════════════════════════════════════════════════════════
st.subheader("⚙️ Configuración del envío")
c1, c2 = st.columns(2)
with c1:
    periodo_input = st.text_input(
        "Período (MM/YYYY)",
        value=default_periodo,
        help="Debe existir cuota generada en proceso mensual para cada unidad.",
    )
with c2:
    asunto_email = st.text_input(
        "Asunto del correo",
        value=f"Estado de cuenta — {periodo_input} — {st.session_state.get('condominio_nombre', '')}",
    )

ok_p, msg_p = validate_periodo(str(periodo_input).strip())
if not ok_p:
    st.warning(f"Período inválido: {msg_p}")
    st.stop()
ok_db, msg_db, periodo_db = periodo_to_date_str(str(periodo_input).strip())
if not ok_db or not periodo_db:
    st.warning(f"No se pudo interpretar el período: {msg_db}")
    st.stop()

periodo_db10 = str(periodo_db)[:10]
if len(periodo_db10) == 7:
    periodo_db10 = f"{periodo_db10}-01"
periodo_db7 = periodo_db10[:7]
periodo_mmyyyy = periodo_a_mmyyyy(periodo_db)

st.subheader("🏦 Tesorero / Administrador")
tesorero_guardado = (config.get("tesorero_email") or "").strip()
tesorero_email = st.text_input(
    "Correo del tesorero",
    value=tesorero_guardado,
    placeholder="tesorero@ejemplo.com",
    max_chars=255,
    help=(
        "El tesorero puede recibir un PDF con **todos** los recibos del envío. "
        "Obligatorio si activas el envío al tesorero."
    ),
    key="ec_tesorero_email_input",
)

if st.button("💾 Guardar correo del tesorero", key="ec_save_tesorero"):
    ok_em, msg_em = validate_email(tesorero_email.strip()) if tesorero_email.strip() else (True, "")
    if tesorero_email.strip() and not ok_em:
        st.error(f"❌ {msg_em or 'Correo inválido'}")
    else:
        try:
            ec_repo.actualizar_tesorero_email(cid, tesorero_email.strip() or None)
            st.success("✅ Guardado")
            _repos.clear()
            st.rerun()
        except DatabaseError as e:
            st.error(f"❌ {e}")

enviar_a_tesorero = st.checkbox(
    "Enviar estos recibos al tesorero (PDF combinado)",
    value=bool(tesorero_guardado),
    key="ec_enviar_tesorero",
)

modo_tesorero = MODO_TESORERO_AMBOS
if enviar_a_tesorero and tesorero_email.strip():
    modo_tesorero = st.radio(
        "Modo de envío al tesorero",
        options=[MODO_TESORERO_AMBOS, MODO_TESORERO_SOLO],
        key="ec_modo_tesorero",
    )
elif enviar_a_tesorero and not tesorero_email.strip():
    st.warning("⚠️ Ingresa el correo del tesorero y guárdalo para activar el envío al tesorero.")

st.subheader("📝 Pie de página del recibo")
st.caption("Edita antes de enviar. Se guardará en el condominio para futuros envíos.")

pie_titular = st.text_area(
    "Texto titular (fondo azul, negrita)",
    value=(config.get("pie_pagina_titular") or PIE_TITULAR_DEFAULT),
    height=90,
    key="ec_pie_titular",
)
pie_cuerpo = st.text_area(
    "Texto cuerpo (borde, letra pequeña)",
    value=(config.get("pie_pagina_cuerpo") or PIE_CUERPO_DEFAULT),
    height=140,
    key="ec_pie_cuerpo",
)

if st.button("💾 Guardar textos de pie de página", key="ec_save_pie"):
    try:
        ec_repo.actualizar_pie_pagina(cid, pie_titular, pie_cuerpo)
        st.success("✅ Textos guardados.")
        _repos.clear()
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {e}")

# ═══════════════════════════════════════════════════════════════════════════
# PASO 2: UNIDADES
# ═══════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📋 Selecciona las unidades a enviar")
st.caption(
    "Marca o desmarca según lo necesites. Las unidades sin correo no pueden recibir correo, "
    "pero pueden incluirse en el PDF combinado del tesorero."
)

try:
    todas_unidades = ec_repo.listar_todas_unidades(cid)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

if not todas_unidades:
    st.error("❌ No hay unidades activas en este condominio.")
    st.stop()

grupos = agrupar_unidades(todas_unidades)

col_a, col_b, col_c = st.columns([1, 1, 2])
with col_a:
    if st.button("☑️ Seleccionar TODOS", key="ec_sel_all"):
        for u in todas_unidades:
            if _tiene_email(u):
                st.session_state[f"sel_{u['unidad_id']}"] = True
        st.rerun()
with col_b:
    if st.button("⬜ Deseleccionar TODOS", key="ec_sel_none"):
        for u in todas_unidades:
            st.session_state[f"sel_{u['unidad_id']}"] = False
        st.rerun()

seleccionados = [u for u in todas_unidades if st.session_state.get(f"sel_{u['unidad_id']}", False)]

with col_c:
    if seleccionados:
        st.success(f"✅ **{len(seleccionados)}** seleccionados")
    else:
        st.warning("Ningún apartamento seleccionado aún.")

modo_vista = st.radio(
    "🔍 Buscar y visualizar por:",
    options=["Grupo (Letra)", "Número de apartamento"],
    horizontal=True,
    key="ec_modo_vista",
)

if modo_vista == "Grupo (Letra)":
    grupo_keys = sorted(grupos.keys(), key=lambda k: (k == "SIN_GRUPO", k))

    def _fmt_grupo(k: str) -> str:
        g = grupos[k]
        return f"Grupo {k} — {g.total} apartamentos ({g.con_email} con correo)"

    grupo_sel = st.selectbox(
        "Selecciona el grupo:",
        options=grupo_keys,
        format_func=_fmt_grupo,
        key="ec_grupo_selector",
    )
    unidades_mostrar = list(grupos[grupo_sel].unidades)
    col_g1, col_g2, col_g3 = st.columns([1, 1, 3])
    with col_g1:
        if st.button("☑️ Todos (este grupo)", key="ec_todos_grupo"):
            for u in unidades_mostrar:
                if _tiene_email(u):
                    st.session_state[f"sel_{u['unidad_id']}"] = True
            st.rerun()
    with col_g2:
        if st.button("⬜ Ninguno (este grupo)", key="ec_ninguno_grupo"):
            for u in unidades_mostrar:
                st.session_state[f"sel_{u['unidad_id']}"] = False
            st.rerun()
    with col_g3:
        con_em_g = sum(1 for u in unidades_mostrar if _tiene_email(u))
        sel_g = sum(
            1
            for u in unidades_mostrar
            if st.session_state.get(f"sel_{u['unidad_id']}", False)
        )
        st.caption(f"{sel_g} de {con_em_g} con correo seleccionados en este grupo")
else:
    unidades_mostrar = sorted(
        todas_unidades,
        key=lambda u: (len(detectar_numero(u["unidad_codigo"])), detectar_numero(u["unidad_codigo"])),
    )

st.markdown("---")
h0, h1, h2, h3 = st.columns([0.5, 1.5, 3, 3])
h0.markdown("**Enviar**")
h1.markdown("**Inmueble**")
h2.markdown("**Propietario**")
h3.markdown("**Correo(s)**")

for u in unidades_mostrar:
    cols = st.columns([0.5, 1.5, 3, 3])
    tiene_email = _tiene_email(u)
    with cols[0]:
        if tiene_email:
            st.checkbox(
                "",
                key=f"sel_{u['unidad_id']}",
                label_visibility="collapsed",
            )
        else:
            st.markdown("—")
    with cols[1]:
        st.markdown(f"{u['unidad_codigo']}")
    with cols[2]:
        st.write(u.get("propietario_nombre") or "—")
    with cols[3]:
        if tiene_email:
            emails = u["propietario_email"]
            if isinstance(emails, list):
                links = " , ".join(
                    f'<a href="mailto:{_html_escape(e)}">{_html_escape(e)}</a>'
                    for e in emails
                    if str(e).strip()
                )
                st.markdown(links, unsafe_allow_html=True)
            else:
                em = str(emails).strip()
                st.markdown(
                    f'<a href="mailto:{_html_escape(em)}">{_html_escape(em)}</a>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Sin correo")


# Refrescar seleccionados tras pintar checkboxes
seleccionados = [u for u in todas_unidades if st.session_state.get(f"sel_{u['unidad_id']}", False)]

# ═══════════════════════════════════════════════════════════════════════════
# PASO 3: RESUMEN DEL MES
# ═══════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📊 Resumen del mes")

total_apts = len(todas_unidades)
grupos_count = len(grupos)
con_email_total = sum(1 for u in todas_unidades if _tiene_email(u))
sel_count = len(seleccionados)

tasa_cfg = float(config.get("tasa_cambio") or 0)


def _fetch_datos(uid: int, condominio_id_: int, per: str):
    datos, _err = _obtener_datos_para_pdf(
        uid, condominio_id_, per, tasa_cambio=tasa_para_pdf
    )
    return datos


alertas = calcular_alertas_coherencia(
    seleccionados,
    cid,
    periodo_db10,
    _fetch_datos,
)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("🏠 Total apartamentos", total_apts)
m2.metric("🗂️ Grupos detectados", grupos_count)
m3.metric("📧 Con correo registrado", con_email_total)
m4.metric("📨 Seleccionados (checkbox)", sel_count)
if alertas:
    m5.metric("🔍 Alertas coherencia", len(alertas), delta="Revisar", delta_color="inverse")
else:
    m5.metric("🔍 Alertas coherencia", 0)

if tasa_cfg > 0:
    st.caption(f"Tasa BCV (referencia condominio): **Bs. {tasa_cfg:,.4f}**")

# ═══════════════════════════════════════════════════════════════════════════
# PASO 4: ALERTAS DE COHERENCIA
# ═══════════════════════════════════════════════════════════════════════════
if alertas:
    st.divider()
    st.subheader("🔍 Alerta de coherencia: saldo acumulado vs cuota del mes")
    st.caption(
        "Con **Mes(es) = 1**, lo habitual es que **Acumulado US$** coincida con **Monto USD** "
        "(cuota del mes). Si difieren, conviene revisar antes de enviar."
    )
    st.dataframe(pd.DataFrame(alertas), hide_index=True, use_container_width=True)
    st.warning(
        f"Se encontraron **{len(alertas)}** recibo(s) con discrepancia. "
        "Puedes continuar con el envío, pero se recomienda verificar estos valores."
    )

# ═══════════════════════════════════════════════════════════════════════════
# Logo + vista previa + envío
# ═══════════════════════════════════════════════════════════════════════════
_logo_url_raw = (config.get("logo_url") or "").strip()
logo_b = ec_repo.obtener_logo_bytes(_logo_url_raw or None)
# Si falla la preparación en bytes, el PDF aún puede usar la data URL como str
logo_para_pdf: bytes | str | None = (
    logo_b if logo_b else (_logo_url_raw if _logo_url_raw.startswith("data:") else None)
)

if _logo_url_raw and logo_para_pdf is None:
    st.warning(
        "⚠️ Hay **logo_url** en el condominio pero no se pudo preparar para el PDF. "
        "Revise los logs o vuelva a guardar el logo en **Condominios**."
    )

st.divider()
st.subheader("👁️ Vista previa")
st.caption("Genera el PDF de la **primera unidad seleccionada** con correo (misma plantilla que el envío).")

preview_targets = [u for u in seleccionados if _tiene_email(u)]
if not preview_targets:
    st.info("Selecciona al menos una unidad **con correo** para generar la vista previa.")
else:
    if st.button("🔍 Generar vista previa (primera seleccionada)", key="ec_preview"):
        primera = preview_targets[0]
        with st.spinner("Generando PDF…"):
            datos, err_pdf = _obtener_datos_para_pdf(
                primera["unidad_id"],
                cid,
                periodo_db10,
                tasa_cambio=tasa_para_pdf,
            )
            if err_pdf:
                st.error(
                    "❌ **No se pudo consultar la cuota** para generar el PDF.\n\n"
                    f"{err_pdf}\n\n"
                    "Revise el período, permisos (RLS) en Supabase o los logs del servidor."
                )
            elif not datos:
                st.warning(
                    "No hay datos de cuota para esa unidad en el período. "
                    "Genere cuotas en **Proceso mensual**."
                )
            else:
                pdf_bytes = generar_estado_cuenta_pdf(
                    condominio_nombre=config["nombre"],
                    condominio_rif=config["rif"],
                    condominio_email=config["email"],
                    logo_bytes=logo_para_pdf,
                    pie_titular=pie_titular,
                    pie_cuerpo=pie_cuerpo,
                    **datos,
                )
                safe_name = (
                    f"preview_{primera['unidad_codigo'].replace('/', '-')}_"
                    f"{periodo_mmyyyy.replace('/', '_')}.pdf"
                )
                st.download_button(
                    "⬇️ Descargar vista previa PDF",
                    data=pdf_bytes,
                    file_name=safe_name,
                    mime="application/pdf",
                    key="ec_dl_preview",
                )

st.divider()
st.subheader("📨 Enviar a los seleccionados")
st.warning(
    "⚠️ Esta acción enviará correos reales con PDF adjunto según el modo elegido "
    "(propietarios y/o tesorero)."
)

confirmar = st.checkbox("Confirmo que revisé la vista previa y quiero enviar", key="ec_confirm")

email_config = EmailConfig(
    smtp_email=config["smtp_email"],
    app_password=config["smtp_app_password"],
    nombre_remitente=config["smtp_nombre_remitente"],
)

solo_tesorero = enviar_a_tesorero and modo_tesorero == MODO_TESORERO_SOLO
necesita_propietarios = not solo_tesorero
puede_enviar = bool(seleccionados) and (
    (necesita_propietarios and any(_tiene_email(u) for u in seleccionados)) or solo_tesorero
)

if not seleccionados:
    st.error("Selecciona al menos una unidad.")
elif necesita_propietarios and not any(_tiene_email(u) for u in seleccionados):
    st.error("Para enviar a propietarios, al menos una unidad seleccionada debe tener correo.")
elif solo_tesorero and not (tesorero_email.strip()):
    st.error("Indica el correo del tesorero para el modo “solo tesorero”.")
elif confirmar and puede_enviar and st.button("🚀 Enviar estados de cuenta", type="primary", key="ec_send"):
    envios_ok = 0
    envios_fail = 0
    sin_datos = 0
    sin_correo_prop = 0
    pdfs_tesorero: list[bytes] = []
    orden_envio = list(seleccionados)
    n = len(orden_envio)
    prog = st.progress(0, text="Iniciando envío…")

    for i, unidad in enumerate(orden_envio):
        datos, _err_env = _obtener_datos_para_pdf(
            unidad["unidad_id"],
            cid,
            periodo_db10,
            tasa_cambio=tasa_para_pdf,
        )

        if not datos:
            sin_datos += 1
            try:
                em_log = _email_para_smtp(unidad) or ""
                notif_repo.registrar_envio(
                    condominio_id=cid,
                    periodo=periodo_db7,
                    unidad_id=unidad["unidad_id"],
                    email=em_log,
                    nombre=unidad.get("propietario_nombre") or "—",
                    asunto=asunto_email,
                    cuerpo="(sin PDF — sin cuota en período)",
                    enviado=False,
                    error="Sin datos de cuota para el período",
                    tipo="estado_cuenta",
                )
            except DatabaseError:
                pass
            prog.progress((i + 1) / max(n, 1), text=f"Sin datos: {unidad['unidad_codigo']}")
            continue

        pdf_bytes = generar_estado_cuenta_pdf(
            condominio_nombre=config["nombre"],
            condominio_rif=config["rif"],
            condominio_email=config["email"],
            logo_bytes=logo_para_pdf,
            pie_titular=pie_titular,
            pie_cuerpo=pie_cuerpo,
            **datos,
        )
        pdfs_tesorero.append(pdf_bytes)

        cuerpo_correo = (
            f"Estimado/a {unidad.get('propietario_nombre') or 'propietario'},\n\n"
            f"Adjunto encontrará su estado de cuenta correspondiente al período {periodo_mmyyyy}.\n\n"
            f"Para consultas comuníquese con la administración.\n\n"
            f"Atentamente,\n{config['smtp_nombre_remitente']}"
        )
        fn = (
            f"estado_cuenta_{unidad['unidad_codigo'].replace('/', '-')}_"
            f"{periodo_mmyyyy.replace('/', '_')}.pdf"
        )

        enviar_owner = not solo_tesorero
        dest = _email_para_smtp(unidad)

        if solo_tesorero:
            prog.progress((i + 1) / max(n, 1), text=f"PDF {unidad['unidad_codigo']} (tesorero)…")
            continue

        if dest:
            resultado = enviar_correo_con_adjunto(
                email_config,
                dest,
                unidad.get("propietario_nombre") or "Propietario",
                asunto_email,
                cuerpo_correo,
                pdf_bytes,
                fn,
            )
            err = None if resultado.get("exito") else (resultado.get("error") or "Error desconocido")
            try:
                notif_repo.registrar_envio(
                    condominio_id=cid,
                    periodo=periodo_db7,
                    unidad_id=unidad["unidad_id"],
                    email=dest,
                    nombre=unidad.get("propietario_nombre") or "—",
                    asunto=asunto_email,
                    cuerpo=cuerpo_correo,
                    enviado=bool(resultado.get("exito")),
                    error=err,
                    tipo="estado_cuenta",
                )
            except DatabaseError:
                pass
            if resultado.get("exito"):
                envios_ok += 1
            else:
                envios_fail += 1
        else:
            sin_correo_prop += 1
            try:
                notif_repo.registrar_envio(
                    condominio_id=cid,
                    periodo=periodo_db7,
                    unidad_id=unidad["unidad_id"],
                    email="",
                    nombre=unidad.get("propietario_nombre") or "—",
                    asunto=asunto_email,
                    cuerpo="(sin envío — sin correo de propietario)",
                    enviado=False,
                    error="Sin correo de propietario",
                    tipo="estado_cuenta",
                )
            except DatabaseError:
                pass

        prog.progress((i + 1) / max(n, 1), text=f"Procesando {unidad['unidad_codigo']}…")

    # PDF combinado al tesorero
    if (
        enviar_a_tesorero
        and tesorero_email.strip()
        and pdfs_tesorero
        and modo_tesorero in (MODO_TESORERO_AMBOS, MODO_TESORERO_SOLO)
    ):
        combinado = combinar_pdfs(pdfs_tesorero)
        if combinado:
            asunto_t = (
                f"Recibos completos {periodo_mmyyyy} — {config.get('nombre') or 'Condominio'}"
            )
            cuerpo_t = (
                f"Adjunto el PDF con **{len(pdfs_tesorero)}** estado(s) de cuenta del período "
                f"{periodo_mmyyyy}.\n\n"
                f"Condominio: {config.get('nombre') or '—'}"
            )
            fn_t = f"recibos_completos_{periodo_mmyyyy.replace('/', '_')}.pdf"
            res_t = enviar_correo_con_adjunto(
                email_config,
                tesorero_email.strip(),
                "Tesorero",
                asunto_t,
                cuerpo_t,
                combinado,
                fn_t,
            )
            if res_t.get("exito"):
                st.success("✅ PDF combinado enviado al tesorero.")
            else:
                st.error(f"❌ No se pudo enviar al tesorero: {res_t.get('error')}")
        else:
            st.warning("⚠️ No se pudo generar el PDF combinado para el tesorero.")

    prog.progress(1.0, text="Completado")
    n_pdf = len(pdfs_tesorero)
    if solo_tesorero:
        st.success(f"✅ **{n_pdf}** PDF(s) de recibo generado(s) para el paquete del tesorero.")
    else:
        st.success(f"✅ **{envios_ok}** correo(s) a propietarios enviado(s) correctamente.")
        if sin_correo_prop:
            st.info(f"ℹ️ **{sin_correo_prop}** unidad(es) seleccionada(s) sin correo (no se envió a propietario).")
    if envios_fail:
        st.error(f"❌ **{envios_fail}** envío(s) a propietarios fallaron.")
    if sin_datos:
        st.warning(f"⚠️ **{sin_datos}** unidad(es) sin cuota en el período (no se generó PDF).")
