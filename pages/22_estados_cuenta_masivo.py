"""
Estados de cuenta masivos: PDF estilo Sisconin + envío Gmail con adjunto (Fase 5-C).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.breadcrumb import render_breadcrumb
from components.header import render_header
from config.supabase_client import get_supabase_client
from repositories.estado_cuenta_repository import EstadoCuentaRepository
from repositories.notificacion_repository import NotificacionRepository
from utils.auth import check_authentication, require_condominio
from utils.dashboard_formatters import periodo_a_mmyyyy
from utils.email_sender import EmailConfig, enviar_correo_con_adjunto
from utils.error_handler import DatabaseError
from utils.estado_cuenta_pdf import generar_estado_cuenta_pdf
from utils.formatters import format_mes_proceso
from utils.validators import periodo_to_date_str, validate_periodo

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

st.set_page_config(page_title="Estados de cuenta masivo", page_icon="📄", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Estados de cuenta masivo")

condominio_id = require_condominio()
cid = int(condominio_id)


@st.cache_resource
def _repos():
    c = get_supabase_client()
    return EstadoCuentaRepository(c), NotificacionRepository(c)


ec_repo, notif_repo = _repos()

st.title("📄 Estados de cuenta masivo")
st.caption(
    "Genera y envía PDFs de estado de cuenta a los propietarios con correo registrado "
    "(diseño tipo recibo venezolano)."
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

periodo_db7 = str(periodo_db)[:7]
periodo_mmyyyy = periodo_a_mmyyyy(periodo_db)

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

st.divider()
st.subheader("📋 Unidades")

try:
    unidades = ec_repo.listar_unidades_con_email(cid)
    sin_email = ec_repo.listar_unidades_sin_email(cid)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

if sin_email:
    codigos = ", ".join(u["unidad_codigo"] for u in sin_email[:25])
    more = f" (+{len(sin_email) - 25} más)" if len(sin_email) > 25 else ""
    st.warning(
        f"⚠️ **{len(sin_email)}** unidades sin correo en el propietario no recibirán el PDF: "
        f"{codigos}{more}"
    )

if not unidades:
    st.error("❌ No hay unidades activas con correo del propietario.")
    st.stop()

st.info(f"Se enviarán **{len(unidades)}** estados de cuenta (una vez por unidad).")

df_u = pd.DataFrame(unidades)
st.dataframe(
    df_u[["unidad_codigo", "propietario_nombre", "propietario_email"]],
    hide_index=True,
    use_container_width=True,
)

st.divider()
st.subheader("👁️ Vista previa")
st.caption("Genera el PDF de la primera unidad del listado (misma plantilla que el envío masivo).")

logo_b = ec_repo.obtener_logo_bytes(config.get("logo_url"))

if st.button("🔍 Generar vista previa (primera unidad)", key="ec_preview"):
    primera = unidades[0]
    with st.spinner("Generando PDF…"):
        try:
            datos = ec_repo.obtener_datos_unidad_periodo(
                primera["unidad_id"], cid, periodo_db
            )
        except DatabaseError as e:
            st.error(f"❌ {e}")
            datos = None
        if not datos:
            st.warning(
                "No hay datos de cuota para esa unidad en el período. "
                "Genere cuotas en **Proceso mensual**."
            )
        else:
            pdf_bytes = generar_estado_cuenta_pdf(
                condominio_nombre=config["nombre"],
                condominio_rif=config["rif"],
                condominio_email=config["email"],
                logo_bytes=logo_b,
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
st.subheader("📨 Enviar a todos")

st.error(
    "⚠️ Esta acción enviará correos reales con PDF adjunto a **todos** los propietarios listados."
)

confirmar = st.checkbox("Confirmo que revisé la vista previa y quiero enviar", key="ec_confirm")

email_config = EmailConfig(
    smtp_email=config["smtp_email"],
    app_password=config["smtp_app_password"],
    nombre_remitente=config["smtp_nombre_remitente"],
)

if confirmar and st.button("🚀 Enviar estados de cuenta masivo", type="primary", key="ec_send_all"):
    exitosos = 0
    fallidos = 0
    sin_datos = 0
    n = len(unidades)
    prog = st.progress(0, text="Iniciando envío…")

    for i, unidad in enumerate(unidades):
        try:
            datos = ec_repo.obtener_datos_unidad_periodo(
                unidad["unidad_id"], cid, periodo_db
            )
        except DatabaseError:
            datos = None

        if not datos:
            sin_datos += 1
            try:
                notif_repo.registrar_envio(
                    condominio_id=cid,
                    periodo=periodo_db7,
                    unidad_id=unidad["unidad_id"],
                    email=unidad["propietario_email"],
                    nombre=unidad["propietario_nombre"],
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
            logo_bytes=logo_b,
            pie_titular=pie_titular,
            pie_cuerpo=pie_cuerpo,
            **datos,
        )

        cuerpo_correo = (
            f"Estimado/a {unidad['propietario_nombre']},\n\n"
            f"Adjunto encontrará su estado de cuenta correspondiente al período {periodo_mmyyyy}.\n\n"
            f"Para consultas comuníquese con la administración.\n\n"
            f"Atentamente,\n{config['smtp_nombre_remitente']}"
        )

        fn = (
            f"estado_cuenta_{unidad['unidad_codigo'].replace('/', '-')}_"
            f"{periodo_mmyyyy.replace('/', '_')}.pdf"
        )

        resultado = enviar_correo_con_adjunto(
            email_config,
            unidad["propietario_email"],
            unidad["propietario_nombre"],
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
                email=unidad["propietario_email"],
                nombre=unidad["propietario_nombre"],
                asunto=asunto_email,
                cuerpo=cuerpo_correo,
                enviado=bool(resultado.get("exito")),
                error=err,
                tipo="estado_cuenta",
            )
        except DatabaseError:
            pass

        if resultado.get("exito"):
            exitosos += 1
        else:
            fallidos += 1

        prog.progress((i + 1) / max(n, 1), text=f"Procesando {unidad['unidad_codigo']}…")

    prog.progress(1.0, text="Completado")
    st.success(f"✅ **{exitosos}** correos enviados con PDF.")
    if fallidos:
        st.error(f"❌ **{fallidos}** envíos fallaron (revisa auditoría en notificaciones).")
    if sin_datos:
        st.warning(f"⚠️ **{sin_datos}** unidades sin cuota en el período (no se envió PDF).")
