import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.pago_repository import PagoRepository
from repositories.unidad_repository import UnidadRepository
from repositories.condominio_repository import CondominioRepository
from repositories.presupuesto_repository import PresupuestoRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_periodo, periodo_to_date_str
from utils.indiviso_cuota import cuota_bs_desde_presupuesto
from components.header import render_header
from components.breadcrumb import render_breadcrumb

st.set_page_config(page_title="Pagos y Cobros", page_icon="💳", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Pagos y Cobros")

condominio_id = require_condominio()


@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return (
        PagoRepository(client),
        UnidadRepository(client),
        CondominioRepository(client),
        PresupuestoRepository(client),
    )


repo_pago, repo_uni, repo_cond, repo_pres = get_repos()

st.markdown("## 💳 Pagos y cobros")

periodo_str = st.text_input(
    "Mes que cancela (MM/YYYY) *",
    value=str(st.session_state.get("mes_proceso") or "").strip(),
    placeholder="03/2026",
)
ok_p, msg_p = validate_periodo(periodo_str)
if not ok_p:
    st.error(f"❌ {msg_p}")
    st.stop()
ok_db, msg_db, periodo_db = periodo_to_date_str(periodo_str)
if not ok_db or not periodo_db:
    st.error(f"❌ {msg_db}")
    st.stop()

try:
    condominio = repo_cond.get_by_id(condominio_id)
except DatabaseError as e:
    st.error(str(e))
    st.stop()

tasa = float(condominio.get("tasa_cambio") or 0) if condominio else 0.0

pres_row = None
try:
    pres_row = repo_pres.get_by_periodo(condominio_id, periodo_db)
except DatabaseError:
    pass
presupuesto_mes = float(pres_row["monto_bs"]) if pres_row else float(st.session_state.get("presupuesto_mes") or 0)
if pres_row:
    st.session_state.presupuesto_mes = presupuesto_mes

try:
    unidades = repo_uni.get_all(condominio_id, solo_activos=True)
except DatabaseError as e:
    st.error(str(e))
    st.stop()

suma_indiv = repo_uni.get_suma_indivisos(condominio_id, exclude_id=None)

try:
    ind_mes = repo_pago.get_indicadores_mes(
        condominio_id, periodo_db, presupuesto_mes, suma_indiv
    )
except DatabaseError as e:
    st.error(str(e))
    ind_mes = {
        "total_cobrado_bs": 0,
        "n_pagos": 0,
        "unidades_al_dia": 0,
        "pendiente_cobrar_bs": 0,
    }

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cobrado este mes (Bs.)", f"{ind_mes['total_cobrado_bs']:,.2f}")
c2.metric("N° pagos registrados", ind_mes["n_pagos"])
c3.metric("Unidades al día", ind_mes["unidades_al_dia"])
c4.metric("Pendiente por cobrar (Bs.)", f"{ind_mes['pendiente_cobrar_bs']:,.2f}")

st.divider()

if not unidades:
    st.info("No hay unidades activas.")
    st.stop()


def _label_unidad(u: dict) -> str:
    cod = (u.get("codigo") or u.get("numero") or "").strip()
    prop = (u.get("propietarios") or {})
    nom = prop.get("nombre", "—")
    moroso = (u.get("estado_pago") or "") == "moroso"
    suf = " [moroso]" if moroso else ""
    return f"{cod} — {nom}{suf}"


labels = [_label_unidad(u) for u in unidades]
uid_by_label = {labels[i]: unidades[i]["id"] for i in range(len(unidades))}

sel_lbl = st.selectbox("Unidad que paga *", options=labels, key="pago_sel_unidad")
unidad_id = int(uid_by_label[sel_lbl])
u_sel = next(x for x in unidades if int(x["id"]) == unidad_id)

saldo_u = float(u_sel.get("saldo") or 0)
pct = float(u_sel.get("indiviso_pct") or 0)
cuota_m = cuota_bs_desde_presupuesto(presupuesto_mes, pct) if presupuesto_mes else 0.0
mora = 0.0
try:
    ya_pagado = repo_pago.get_total_pagado_unidad(unidad_id, periodo_db)
except DatabaseError:
    ya_pagado = 0.0

total_a_pagar = round(saldo_u + cuota_m + mora - ya_pagado, 2)

st.markdown("### Resumen de cuenta (unidad seleccionada)")
st.table(
    {
        "Concepto": [
            "Saldo mes anterior",
            "Cuota del mes",
            "Intereses de mora",
            "TOTAL A PAGAR",
            "Pagado hoy (formulario)",
            "SALDO RESULTANTE",
        ],
        "Monto Bs.": [
            f"{saldo_u:,.2f}",
            f"{cuota_m:,.2f}",
            f"{mora:,.2f}",
            f"{total_a_pagar:,.2f}",
            "(al registrar)",
            "(al registrar)",
        ],
    }
)

with st.form("form_pago"):
    monto_bs = st.number_input(
        "Monto recibido (Bs.) *",
        min_value=0.0,
        value=max(0.0, float(total_a_pagar)),
        step=0.01,
        format="%.2f",
        help="Precarga el total adeudado; ajuste si es pago parcial.",
    )
    if tasa and tasa > 0:
        st.caption(f"Monto USD (automático): **{monto_bs / tasa:,.4f}** (tasa {tasa})")
    else:
        st.caption("Defina tasa de cambio en el condominio para ver monto USD.")
    fecha_pago = st.date_input("Fecha de pago *")
    metodo = st.radio(
        "Método de pago *",
        options=["transferencia", "deposito", "efectivo"],
        horizontal=True,
        format_func=lambda x: {"transferencia": "Transferencia", "deposito": "Depósito", "efectivo": "Efectivo"}[x],
    )
    if metodo == "efectivo":
        referencia = ""
        st.caption("Referencia: no aplica para efectivo.")
    else:
        referencia = st.text_input(
            "N° referencia" + (" *" if metodo == "transferencia" else " (opcional)"),
            value="",
        )
    obs = st.text_area("Observaciones", height=68)

    saldo_res_preview = round(total_a_pagar - float(monto_bs), 2)
    st.caption(f"Saldo resultante tras este monto: **{saldo_res_preview:,.2f}** Bs.")

    guardar = st.form_submit_button("Registrar pago", type="primary", use_container_width=True)

if guardar:
    if monto_bs <= 0:
        st.error("Ingrese un monto mayor a cero.")
    elif metodo == "transferencia" and not (referencia or "").strip():
        st.error("La referencia es obligatoria para transferencias.")
    else:
        saldo_res = round(total_a_pagar - float(monto_bs), 2)
        pid = u_sel.get("propietario_id")
        monto_usd = round(float(monto_bs) / float(tasa), 4) if tasa and tasa > 0 else 0.0
        data = {
            "condominio_id": condominio_id,
            "unidad_id": unidad_id,
            "propietario_id": int(pid) if pid else None,
            "periodo": periodo_db,
            "fecha_pago": str(fecha_pago),
            "monto_bs": float(monto_bs),
            "monto_usd": monto_usd,
            "tasa_cambio": tasa,
            "metodo": metodo,
            "referencia": (referencia or "").strip() or None,
            "observaciones": (obs or "").strip() or None,
            "estado": "confirmado",
        }
        try:
            repo_pago.create(data)
            if saldo_res <= 0:
                ep = "al_dia"
            else:
                ep = "parcial"
            repo_uni.update(unidad_id, {"saldo": saldo_res, "estado_pago": ep})
            st.success("Pago registrado y saldo actualizado.")
            st.rerun()
        except DatabaseError as e:
            st.error(str(e))

st.divider()
st.markdown("### Historial de pagos del mes")
try:
    hist = repo_pago.get_by_periodo(condominio_id, periodo_db)
except DatabaseError as e:
    st.error(str(e))
    hist = []

if not hist:
    st.caption("No hay pagos en este período.")
else:
    rows = []
    for h in hist:
        uu = h.get("unidades") or {}
        cod = (uu.get("codigo") or uu.get("numero") or "—")
        rows.append(
            {
                "fecha_pago": h.get("fecha_pago"),
                "unidad": cod,
                "metodo": h.get("metodo"),
                "referencia": h.get("referencia") or "—",
                "monto_bs": h.get("monto_bs"),
                "monto_usd": h.get("monto_usd"),
                "estado": h.get("estado"),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
