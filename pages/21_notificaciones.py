"""
Avisos por correo a morosos (Fase 5-B): plantilla editable, Gmail SMTP por condominio.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.breadcrumb import render_breadcrumb
from components.header import render_header
from config.supabase_client import get_supabase_client
from repositories.dashboard_repository import DashboardRepository
from repositories.notificacion_repository import NotificacionRepository
from utils.auth import check_authentication, require_condominio
from utils.dashboard_formatters import periodo_a_mmyyyy
from utils.email_sender import (
    EmailConfig,
    EmailMessage,
    enviar_correo,
    plantilla_mora_marcadores_inicial,
    sustituir_marcadores_plantilla,
    texto_linea_saldo_usd,
)
from utils.error_handler import DatabaseError
from utils.validators import periodo_to_date_str, validate_periodo

st.set_page_config(page_title="Notificaciones", page_icon="📧", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Notificaciones")

condominio_id = require_condominio()
cid = int(condominio_id)
condo_nombre = str(st.session_state.get("condominio_nombre") or "—")
tasa = float(st.session_state.get("tasa_cambio") or 0)

periodo_raw = str(st.session_state.get("mes_proceso") or "").strip()
if not periodo_raw:
    st.warning("No hay período activo (mes en proceso). Configúrelo en Proceso mensual o en el condominio.")
    st.stop()

ok_p, msg_p = validate_periodo(periodo_raw)
if not ok_p:
    st.warning(f"Período inválido: {msg_p}")
    st.stop()

ok_db, msg_db, periodo_db = periodo_to_date_str(periodo_raw)
if not ok_db or not periodo_db:
    st.warning(f"No se pudo interpretar el período: {msg_db}")
    st.stop()

periodo_db7 = str(periodo_db)[:7]
periodo_mmyyyy = periodo_a_mmyyyy(periodo_db)


@st.cache_resource
def _repos():
    c = get_supabase_client()
    return NotificacionRepository(c), DashboardRepository(c)


notif_repo, dash_repo = _repos()

st.markdown("## 📧 Notificaciones a morosos")
st.caption(f"Condominio: **{condo_nombre}** — Período: **{periodo_mmyyyy}**")

try:
    smtp_cfg = notif_repo.obtener_config_smtp(cid)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

if not smtp_cfg:
    st.warning(
        "No hay correo Gmail (SMTP) configurado para este condominio. "
        "Configúrelo en **Condominios** (expander de notificaciones) o al **modificar** el condominio."
    )
    st.page_link("pages/01_condominios.py", label="→ Ir a Condominios", icon="🏢")
    st.stop()

ec = EmailConfig(
    smtp_email=smtp_cfg["smtp_email"],
    app_password=smtp_cfg["smtp_app_password"],
    nombre_remitente=smtp_cfg["smtp_nombre_remitente"],
)

try:
    mor = dash_repo.obtener_morosos(cid, periodo_db)
except DatabaseError as e:
    st.error(f"❌ No se pudieron cargar morosos: {e}")
    st.stop()

lista = mor.get("lista") or []

if "notif_asunto_editor" not in st.session_state:
    _ini = plantilla_mora_marcadores_inicial()
    st.session_state.notif_asunto_editor = _ini["asunto"]
    st.session_state.notif_cuerpo_editor = _ini["cuerpo"]

c1, c2 = st.columns([1, 1])
with c1:
    if st.button("☑️ Seleccionar todos", key="notif_all"):
        for m in lista:
            uid = m.get("unidad_id")
            if uid is not None:
                st.session_state[f"notif_sel_{uid}"] = True
        st.rerun()
with c2:
    if st.button("⬜ Quitar selección", key="notif_none"):
        for m in lista:
            uid = m.get("unidad_id")
            if uid is not None:
                st.session_state[f"notif_sel_{uid}"] = False
        st.rerun()

if not lista:
    st.info("No hay morosos críticos (más de 1 mes de atraso) en este período.")
else:
    st.markdown("### Morosos")
    for m in lista:
        uid = m.get("unidad_id")
        if uid is None:
            continue
        k = f"notif_sel_{uid}"
        if k not in st.session_state:
            st.session_state[k] = True
        u = m.get("unidad") or "—"
        p = m.get("propietario") or "—"
        em = (m.get("email") or "").strip() or "—"
        cols = st.columns([3, 3, 4, 1])
        with cols[0]:
            st.markdown(f"**{u}**")
        with cols[1]:
            st.caption(p)
        with cols[2]:
            st.caption(em)
        with cols[3]:
            st.checkbox("Enviar", key=k, label_visibility="collapsed")

st.divider()
st.markdown("### Plantilla del mensaje")
st.caption(
    "Marcadores: `{{propietario_nombre}}`, `{{unidad_codigo}}`, `{{condominio_nombre}}`, "
    "`{{periodo}}`, `{{meses_atraso}}`, `{{saldo_bs}}`, `{{saldo_usd_linea}}`"
)
ta = st.text_input("Asunto", key="notif_asunto_editor")
tb = st.text_area("Cuerpo", key="notif_cuerpo_editor", height=280)

if st.button("↺ Restaurar plantilla por defecto", key="notif_reset_tpl"):
    ini = plantilla_mora_marcadores_inicial()
    st.session_state.notif_asunto_editor = ini["asunto"]
    st.session_state.notif_cuerpo_editor = ini["cuerpo"]
    st.rerun()

st.divider()

if st.button("📤 Enviar a seleccionados", type="primary", key="notif_send"):
    to_send = [
        m
        for m in lista
        if m.get("unidad_id") is not None
        and st.session_state.get(f"notif_sel_{m['unidad_id']}", False)
    ]
    if not to_send:
        st.warning("Selecciona al menos un propietario para enviar.")
    else:
        enviados = 0
        fallos = 0
        prog = st.progress(0, text="Preparando envío…")
        n = len(to_send)
        for idx, m in enumerate(to_send):
            uid = m.get("unidad_id")
            email = (m.get("email") or "").strip()
            nom = (m.get("propietario") or "").strip() or "—"
            unidad_c = (m.get("unidad") or "").strip() or "—"
            saldo = float(m.get("saldo_bs") or 0)
            meses = int(m.get("meses_atraso") or 0)
            saldo_usd_linea = texto_linea_saldo_usd(saldo, tasa)
            vals = {
                "propietario_nombre": nom,
                "unidad_codigo": unidad_c,
                "condominio_nombre": condo_nombre,
                "periodo": periodo_mmyyyy,
                "meses_atraso": str(meses),
                "saldo_bs": f"{saldo:,.2f}",
                "saldo_usd_linea": saldo_usd_linea,
            }
            asunto_f = sustituir_marcadores_plantilla(ta, vals)
            cuerpo_f = sustituir_marcadores_plantilla(tb, vals)
            if not email:
                try:
                    notif_repo.registrar_envio(
                        cid,
                        periodo_db7,
                        int(uid),
                        "",
                        nom,
                        asunto_f,
                        cuerpo_f,
                        False,
                        "Sin correo registrado",
                    )
                except DatabaseError as e:
                    st.error(f"❌ Registro fallido (sin correo): {e}")
                fallos += 1
            else:
                res = enviar_correo(
                    ec,
                    EmailMessage(
                        destinatario_email=email,
                        destinatario_nombre=nom,
                        asunto=asunto_f,
                        cuerpo=cuerpo_f,
                    ),
                )
                err = None if res.get("exito") else (res.get("error") or "Error desconocido")
                try:
                    notif_repo.registrar_envio(
                        cid,
                        periodo_db7,
                        int(uid),
                        email,
                        nom,
                        asunto_f,
                        cuerpo_f,
                        bool(res.get("exito")),
                        err,
                    )
                except DatabaseError as e:
                    st.error(f"❌ No se pudo registrar el envío: {e}")
                if res.get("exito"):
                    enviados += 1
                else:
                    fallos += 1
            prog.progress(
                (idx + 1) / max(n, 1),
                text=f"Enviando {idx + 1} de {n}…",
            )
        prog.progress(1.0, text="Listo.")
        if enviados or fallos:
            st.success(
                f"Proceso terminado: **{enviados}** enviados, **{fallos}** fallidos o sin correo."
            )

st.divider()
st.markdown("### Historial del período")
try:
    hist = notif_repo.obtener_historial(cid, periodo_db7)
except DatabaseError as e:
    st.warning(f"No se pudo cargar el historial: {e}")
    hist = []

if hist:
    df = pd.DataFrame(
        [
            {
                "Fecha": (r.get("created_at") or "")[:19],
                "Unidad id": r.get("unidad_id"),
                "Correo": r.get("propietario_email") or "",
                "Enviado": "Sí" if r.get("enviado") else "No",
                "Error": (r.get("error_mensaje") or "")[:120],
            }
            for r in hist
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.caption("Sin registros de envío en este período.")
