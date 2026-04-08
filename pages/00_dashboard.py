"""
Dashboard principal — métricas del período en proceso (Fase 5-A).
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from components.header import render_header
from config.supabase_client import get_supabase_client
from repositories.dashboard_repository import DashboardRepository
from repositories.notificacion_repository import NotificacionRepository
from utils.auth import check_authentication
from utils.dashboard_formatters import (
    color_cobranza,
    formato_bs_usd,
    pasos_proceso,
    periodo_a_mmyyyy,
)
from utils.error_handler import DatabaseError
from utils.validators import periodo_to_date_str, validate_periodo

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
check_authentication()
render_header()

condominio_id = st.session_state.get("condominio_id")
if not condominio_id:
    st.warning("Selecciona un condominio para ver el dashboard.")
    st.stop()

periodo_raw = str(st.session_state.get("mes_proceso") or "").strip()
tasa = float(st.session_state.get("tasa_cambio") or 0)

if not periodo_raw:
    st.warning("No hay período activo (mes en proceso). Configúrelo en el condominio o en Proceso mensual.")
    st.stop()

ok_p, msg_p = validate_periodo(periodo_raw)
if not ok_p:
    st.warning(f"Período inválido: {msg_p}")
    st.stop()

ok_db, msg_db, periodo_db = periodo_to_date_str(periodo_raw)
if not ok_db or not periodo_db:
    st.warning(f"No se pudo interpretar el período: {msg_db}")
    st.stop()

cid = int(condominio_id)


@st.cache_resource
def _repos() -> tuple[DashboardRepository, NotificacionRepository]:
    c = get_supabase_client()
    return DashboardRepository(c), NotificacionRepository(c)


repo, notif_repo = _repos()

try:
    _smtp_config_ok = notif_repo.obtener_config_smtp(cid) is not None
except DatabaseError:
    _smtp_config_ok = False

st.title("📊 Dashboard")
st.caption(
    f"Período activo: {periodo_a_mmyyyy(periodo_db)} — "
    f"{st.session_state.get('condominio_nombre', '')}"
)

if st.button("🔄 Actualizar", key="btn_refresh_dashboard"):
    st.rerun()

st.divider()

# ── Cargas con fallback seguro ──────────────────────────────────────────────
_z_cob = {
    "cuotas_esperadas_bs": 0.0,
    "cobros_extraordinarios_bs": 0.0,
    "total_esperado_bs": 0.0,
    "total_cobrado_bs": 0.0,
    "pct_cobranza": 0.0,
    "unidades_al_dia": 0,
    "unidades_morosas": 0,
    "unidades_parcial": 0,
}
_z_mor = {"total_morosos": 0, "monto_total_adeudado_bs": 0.0, "lista": []}
_z_flujo = {
    "total_ingresos_bs": 0.0,
    "total_egresos_bs": 0.0,
    "superavit_bs": 0.0,
    "es_superavit": True,
}
_z_banco = {
    "saldo_bs": 0.0,
    "movimientos_conciliados": 0,
    "movimientos_pendientes": 0,
    "tiene_conciliacion": False,
}
_z_info = {
    "periodo_actual": periodo_a_mmyyyy(periodo_db),
    "estado_proceso": "borrador",
    "pasos_completados": 0,
    "proximo_periodo": "—",
    "dias_para_fin_mes": 0,
    "presupuesto_definido": False,
    "cuotas_generadas": False,
    "presupuesto_ok": False,
    "cuotas_ok": False,
    "pagos_ok": False,
    "cierre_ok": False,
}

try:
    cob = repo.obtener_metricas_cobranza(cid, periodo_db)
except DatabaseError:
    cob = _z_cob

try:
    mor = repo.obtener_morosos(cid, periodo_db)
except DatabaseError:
    mor = _z_mor

try:
    flujo = repo.obtener_flujo_mes(cid, periodo_db)
except DatabaseError:
    flujo = _z_flujo

try:
    banco = repo.obtener_saldo_banco(cid, periodo_db)
except DatabaseError:
    banco = _z_banco

try:
    info = repo.obtener_info_cierre(cid, periodo_db)
except DatabaseError:
    info = _z_info

# ═══ SECCIÓN 1 — Cobranza ═══════════════════════════════════════════════════
st.markdown("### 🏦 Cobranza del mes")
st.markdown(
    '<p style="color:#717D7E;font-size:12px;margin-top:-8px;">'
    "────────────────────────────────────────────</p>",
    unsafe_allow_html=True,
)

pct = float(cob.get("pct_cobranza") or 0)
col_hex = color_cobranza(pct)
st.markdown(
    f'<div style="text-align:center;margin:12px 0 4px 0;">'
    f'<span style="font-size:3rem;font-weight:700;color:{col_hex};">{pct:.0f}%</span><br/>'
    f'<span style="color:#717D7E;font-size:14px;">Eficiencia de cobranza</span></div>',
    unsafe_allow_html=True,
)

total_esp = float(cob.get("total_esperado_bs") or 0)
total_cob = float(cob.get("total_cobrado_bs") or 0)
pendiente = max(0.0, round(total_esp - total_cob, 2))

c1, c2, c3 = st.columns(3)
with c1:
    st.caption("Total esperado")
    st.markdown(f"**{formato_bs_usd(total_esp, tasa)}**")
with c2:
    st.caption("Cobrado")
    st.markdown(f"**{formato_bs_usd(total_cob, tasa)}**")
with c3:
    st.caption("Pendiente")
    st.markdown(f"**{formato_bs_usd(pendiente, tasa)}**")

st.progress(min(max(pct / 100.0, 0.0), 1.0))

i1, i2, i3 = st.columns(3)
with i1:
    st.markdown(f"🟢 **Al día:** {int(cob.get('unidades_al_dia') or 0)} unidades")
with i2:
    st.markdown(f"🟡 **Parcial:** {int(cob.get('unidades_parcial') or 0)} unidades")
with i3:
    st.markdown(f"🔴 **Moroso:** {int(cob.get('unidades_morosas') or 0)} unidades")

st.divider()

# ═══ SECCIÓN 2 — Morosos críticos ════════════════════════════════════════════
st.markdown("### ⚠️ Morosos con más de 1 mes de atraso")
st.markdown(
    '<p style="color:#717D7E;font-size:12px;margin-top:-8px;">'
    "────────────────────────────────────────────</p>",
    unsafe_allow_html=True,
)

if int(mor.get("total_morosos") or 0) > 0:
    st.error(
        f"{mor['total_morosos']} unidades — "
        f"Bs. {float(mor.get('monto_total_adeudado_bs') or 0):,.2f} adeudados"
    )
    rows = mor.get("lista") or []
    df = pd.DataFrame(
        [
            {
                "Unidad": r.get("unidad"),
                "Propietario": r.get("propietario"),
                "Saldo Bs.": float(r.get("saldo_bs") or 0),
                "Meses atraso": int(r.get("meses_atraso") or 0),
            }
            for r in rows
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    if _smtp_config_ok:
        st.markdown(
            '<p style="margin:8px 0 4px 0;padding:8px 12px;border-radius:8px;'
            "background:#EBF5FB;border-left:4px solid #2E86C1;color:#1B4F72;"
            'font-size:13px;"><strong>📧 Aviso interno:</strong> puede enviar '
            "correos a morosos desde el menú <strong>Notificaciones</strong>.</p>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(
            "🔔 **Aviso interno:** configure el correo Gmail del condominio "
            "(Condominios → Modificar → 📧 Configuración de correo) para enviar avisos."
        )
    if st.button("📧 Notificar morosos", key="btn_notify_morosos"):
        st.switch_page("pages/21_notificaciones.py")
else:
    st.success("✅ Sin morosos con más de 1 mes de atraso")

st.divider()

# ═══ SECCIÓN 3 — Flujo y banco ════════════════════════════════════════════════
left, right = st.columns(2)

with left:
    st.markdown("#### 💰 Ingresos vs egresos")
    ing = float(flujo.get("total_ingresos_bs") or 0)
    egr = float(flujo.get("total_egresos_bs") or 0)
    sup = float(flujo.get("superavit_bs") or 0)
    st.markdown(f"Ingresos: **{formato_bs_usd(ing, tasa)}** ↑")
    st.markdown(f"Egresos: **{formato_bs_usd(egr, tasa)}** ↓")
    st.markdown("─────────────────────────")
    if flujo.get("es_superavit", True) and sup >= 0:
        st.markdown(f"**Superávit:** {formato_bs_usd(sup, tasa)}")
    else:
        st.markdown(
            f'<p style="color:#E74C3C;font-weight:600;margin:0;">'
            f"Déficit: {formato_bs_usd(abs(sup), tasa)}</p>",
            unsafe_allow_html=True,
        )

with right:
    st.markdown("#### 🏧 Saldo en banco (movimientos del mes)")
    sb = float(banco.get("saldo_bs") or 0)
    st.markdown(f"**{formato_bs_usd(sb, tasa)}**")
    st.markdown("**Conciliación**")
    mc = int(banco.get("movimientos_conciliados") or 0)
    mp = int(banco.get("movimientos_pendientes") or 0)
    if mc + mp == 0:
        st.caption("Sin movimientos bancarios cargados en el período.")
    else:
        st.markdown(f"✅ {mc} movimientos conciliados")
        st.markdown(f"⚠️ {mp} movimientos pendientes")
    if banco.get("tiene_conciliacion"):
        st.caption("Hay un registro de cierre de conciliación para este período.")

st.divider()

# ═══ SECCIÓN 4 — Proceso mensual ═════════════════════════════════════════════
st.markdown(f"### 📅 Proceso mensual — {info.get('periodo_actual', '—')}")
st.markdown(
    '<p style="color:#717D7E;font-size:12px;margin-top:-8px;">'
    "────────────────────────────────────────────</p>",
    unsafe_allow_html=True,
)

pasos = pasos_proceso(
    {
        "presupuesto_ok": info.get("presupuesto_ok"),
        "cuotas_ok": info.get("cuotas_ok"),
        "pagos_ok": info.get("pagos_ok"),
        "cierre_ok": info.get("cierre_ok"),
    }
)
cerrado = info.get("estado_proceso") == "cerrado"
pasos_completados = int(info.get("pasos_completados") or 0)

chips = []
for i, p in enumerate(pasos, start=1):
    if cerrado:
        sym, label = "✅", "listo"
    elif i <= pasos_completados:
        sym, label = "✅", "listo"
    elif i == pasos_completados + 1:
        sym, label = "⏳", "en curso"
    else:
        sym, label = "○", "pendiente"
    chips.append(f"{sym} **Paso {i}** — {p['nombre']} ({label})")

st.markdown("  \n".join(chips))

if cerrado:
    st.success(
        f"✅ Mes cerrado — próximo período: **{info.get('proximo_periodo', '—')}**"
    )
    estado_txt = "Cerrado"
elif pasos_completados >= 4:
    estado_txt = "Completado"
else:
    estado_txt = f"En proceso — Paso {pasos_completados + 1} de 4"

st.caption(f"Estado actual: **{estado_txt}**")
st.caption(f"Días hasta fin de mes (período activo): **{info.get('dias_para_fin_mes', 0)}** días")

if not cerrado:
    st.info("Continúa el cierre y las cuotas en **Proceso mensual**.")
    st.page_link("pages/17_proceso_mensual.py", label="→ Ir a Proceso mensual", icon="🗓️")

st.divider()

# ═══ SECCIÓN 5 — Pie ══════════════════════════════════════════════════════════
st.caption(
    f"Última actualización: **{datetime.now().strftime('%d/%m/%Y %H:%M')}**  \n"
    f"Tasa BCV: **Bs. {tasa:,.2f}**"
)
