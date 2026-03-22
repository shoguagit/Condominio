"""
Notificaciones por correo a morosos críticos (Fase 5-B).
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
    plantilla_correo_mora_editor_base,
    validar_config_smtp,
)
from utils.error_handler import DatabaseError
from utils.validators import periodo_to_date_str, validate_periodo


def _aplicar_marcadores_correo(
    asunto: str,
    cuerpo: str,
    moroso: dict,
    periodo_db: str,
    tasa: float,
) -> tuple[str, str]:
    """Sustituye marcadores en asunto y cuerpo."""
    per = periodo_a_mmyyyy(periodo_db)
    nom = str(moroso.get("propietario") or "—")
    uni = str(moroso.get("unidad") or "—")
    sb = float(moroso.get("saldo_bs") or 0)
    ma = int(moroso.get("meses_atraso") or 0)
    usd = f"{sb / tasa:,.2f}" if float(tasa or 0) > 0 else "N/D"

    def _r(s: str) -> str:
        t = s or ""
        t = t.replace("[Nombre del propietario]", nom)
        t = t.replace("[Unidad]", uni)
        t = t.replace("[Periodo]", per)
        t = t.replace("[Meses]", str(ma))
        t = t.replace("[Saldo]", f"{sb:,.2f}")
        t = t.replace("[USD]", usd)
        return t

    return _r(asunto), _r(cuerpo)


st.set_page_config(page_title="Notificaciones", page_icon="📧", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Notificaciones")

condominio_id = require_condominio()
cid = int(condominio_id)
condominio_nombre = str(st.session_state.get("condominio_nombre") or "—")
tasa_cambio = float(st.session_state.get("tasa_cambio") or 0)

periodo_raw = str(st.session_state.get("mes_proceso") or "").strip()
if not periodo_raw:
    st.warning("No hay período activo en sesión.")
    st.stop()
ok_p, _ = validate_periodo(periodo_raw)
if not ok_p:
    st.warning("Período en sesión no es válido.")
    st.stop()
ok_db, _, periodo_db = periodo_to_date_str(periodo_raw)
if not ok_db or not periodo_db:
    st.warning("No se pudo interpretar el período.")
    st.stop()

periodo_ym = periodo_db[:7]


@st.cache_resource
def _repos():
    c = get_supabase_client()
    return DashboardRepository(c), NotificacionRepository(c)


dashboard_repo, notif_repo = _repos()

try:
    config_smtp = notif_repo.obtener_config_smtp(cid)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

st.title("📧 Notificaciones a morosos")
st.caption(
    "Envía avisos por correo a propietarios con más de 1 mes de atraso "
    "(misma regla que el dashboard)."
)

if not config_smtp:
    st.warning(
        "⚠️ No hay correo configurado para este condominio. "
        "Configúralo en **Condominios** → **Modificar** → "
        "**📧 Configuración de correo**."
    )
    st.stop()

try:
    mor_data = dashboard_repo.obtener_morosos(cid, periodo_db)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

morosos = mor_data.get("lista") or []

if st.session_state.pop("_mor_sel_all", False):
    for m in morosos:
        uid = m.get("unidad_id")
        if uid is not None:
            st.session_state[f"chk_mor_{int(uid)}"] = True
    st.rerun()

if st.session_state.pop("_mor_sel_none", False):
    for m in morosos:
        uid = m.get("unidad_id")
        if uid is not None:
            st.session_state[f"chk_mor_{int(uid)}"] = False
    st.rerun()

# ── SECCIÓN 1 ────────────────────────────────────────────────────────────────
if not morosos:
    st.success("✅ No hay morosos con más de 1 mes de atraso.")
    seleccionados: list[dict] = []
else:
    st.subheader(f"📋 {len(morosos)} propietarios a notificar")
    st.caption("Selecciona a quién enviar la notificación:")

    seleccionados = []
    for idx, moroso in enumerate(morosos):
        uid = moroso.get("unidad_id")
        key = f"chk_mor_{int(uid)}" if uid is not None else f"chk_mor_na_{idx}"
        col1, col2, col3, col4, col5 = st.columns([0.5, 2, 2, 2, 2])
        with col1:
            check = st.checkbox("", key=key, label_visibility="collapsed")
        with col2:
            st.write(moroso.get("unidad", "—"))
        with col3:
            st.write(moroso.get("propietario", "—"))
        with col4:
            st.write(f"Bs. {float(moroso.get('saldo_bs') or 0):,.2f}")
        with col5:
            st.write(f"{int(moroso.get('meses_atraso') or 0)} mes(es)")
        if check:
            seleccionados.append(moroso)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("☑️ Seleccionar todos", key="mor_sel_all_btn"):
            st.session_state["_mor_sel_all"] = True
            st.rerun()
    with col_b:
        if st.button("⬜ Deseleccionar todos", key="mor_sel_none_btn"):
            st.session_state["_mor_sel_none"] = True
            st.rerun()

# ── SECCIÓN 2 ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("✏️ Editar mensaje antes de enviar")

plantilla = plantilla_correo_mora_editor_base(
    condominio_nombre,
    periodo_a_mmyyyy(periodo_db),
)

asunto_edit = st.text_input(
    "Asunto del correo",
    value=plantilla["asunto"],
    key="asunto_notif",
)
cuerpo_edit = st.text_area(
    "Cuerpo del correo",
    value=plantilla["cuerpo"],
    height=300,
    key="cuerpo_notif",
)
st.caption(
    "Marcadores: [Nombre del propietario], [Unidad], [Periodo], [Meses], "
    "[Saldo], [USD] — se sustituyen por los datos reales al enviar."
)

# ── SECCIÓN 3 ────────────────────────────────────────────────────────────────
st.divider()
if not seleccionados:
    st.info("Selecciona al menos un propietario para enviar.")
else:
    st.info(f"Se enviarán hasta **{len(seleccionados)}** correos (se omiten sin email).")

    if st.button("📨 Enviar notificaciones", type="primary", key="btn_send_notif"):
        cfg_chk = EmailConfig(
            config_smtp["smtp_email"],
            config_smtp["smtp_app_password"],
            config_smtp["smtp_nombre_remitente"],
        )
        v_err = validar_config_smtp(cfg_chk)
        if v_err:
            for e in v_err:
                st.error(e)
        else:
            exitosos = 0
            fallidos = 0
            bar = st.progress(0)
            total = len(seleccionados)

            for i, moroso in enumerate(seleccionados):
                email_dest = (moroso.get("email") or "").strip()
                asunto_f, cuerpo_f = _aplicar_marcadores_correo(
                    asunto_edit, cuerpo_edit, moroso, periodo_db, tasa_cambio
                )

                if not email_dest:
                    try:
                        notif_repo.registrar_envio(
                            condominio_id=cid,
                            periodo=periodo_ym,
                            unidad_id=moroso.get("unidad_id"),
                            email="",
                            nombre=str(moroso.get("propietario") or ""),
                            asunto=asunto_f,
                            cuerpo=cuerpo_f,
                            enviado=False,
                            error_msg="Sin correo registrado",
                        )
                    except DatabaseError:
                        pass
                    fallidos += 1
                else:
                    resultado = enviar_correo(
                        EmailConfig(
                            config_smtp["smtp_email"],
                            config_smtp["smtp_app_password"],
                            config_smtp["smtp_nombre_remitente"],
                        ),
                        EmailMessage(
                            destinatario_email=email_dest,
                            destinatario_nombre=str(moroso.get("propietario") or ""),
                            asunto=asunto_f,
                            cuerpo=cuerpo_f,
                        ),
                    )
                    try:
                        notif_repo.registrar_envio(
                            condominio_id=cid,
                            periodo=periodo_ym,
                            unidad_id=moroso.get("unidad_id"),
                            email=email_dest,
                            nombre=str(moroso.get("propietario") or ""),
                            asunto=asunto_f,
                            cuerpo=cuerpo_f,
                            enviado=bool(resultado.get("exito")),
                            error_msg=resultado.get("error"),
                        )
                    except DatabaseError:
                        pass
                    if resultado.get("exito"):
                        exitosos += 1
                    else:
                        fallidos += 1

                bar.progress(min((i + 1) / max(total, 1), 1.0))

            if exitosos > 0:
                st.success(f"✅ {exitosos} correo(s) enviado(s) correctamente.")
            if fallidos > 0:
                st.error(
                    f"❌ {fallidos} registro(s) fallidos u omitidos — "
                    "revisa el historial para detalles."
                )

# ── SECCIÓN 4 ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("📜 Historial de envíos del período")

try:
    historial = notif_repo.obtener_historial(cid, periodo_ym)
except DatabaseError as e:
    st.error(f"❌ {e}")
    historial = []

if historial:
    rows = []
    for h in historial:
        rows.append(
            {
                "Fecha": (h.get("created_at") or "")[:19],
                "Unidad_id": h.get("unidad_id"),
                "Email": h.get("propietario_email") or "—",
                "Enviado": "Sí" if h.get("enviado") else "No",
                "Error": (h.get("error_mensaje") or "")[:120],
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
else:
    st.caption("No hay envíos registrados en este período.")
