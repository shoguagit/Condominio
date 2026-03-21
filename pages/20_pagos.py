import streamlit as st
import pandas as pd

from config.supabase_client import get_supabase_client
from repositories.presupuesto_repository import fetch_presupuesto_si_existe
from repositories.pago_repository import PagoRepository
from repositories.unidad_repository import UnidadRepository
from repositories.condominio_repository import CondominioRepository
from repositories.presupuesto_repository import PresupuestoRepository
from repositories.proceso_repository import ProcesoMensualRepository
from repositories.mora_repository import MoraRepository
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
        ProcesoMensualRepository(client),
        MoraRepository(client),
    )


repo_pago, repo_uni, repo_cond, repo_pres, repo_proc, repo_mora = get_repos()

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
    proc_existente = repo_proc.get_existing(condominio_id, periodo_db)
except DatabaseError:
    proc_existente = None
if proc_existente and str(proc_existente.get("estado") or "").lower() == "cerrado":
    st.error("Este período está cerrado. No se pueden registrar nuevos pagos.")
    st.stop()

try:
    condominio = repo_cond.get_by_id(condominio_id)
except DatabaseError as e:
    st.error(str(e))
    st.stop()

def _tasa_efectiva() -> float:
    """Prioriza tasa en sesión (sidebar/global); si no hay, usa la del condominio."""
    ts = float(st.session_state.get("tasa_cambio") or 0)
    if ts > 0:
        return ts
    return float(condominio.get("tasa_cambio") or 0) if condominio else 0.0


tasa = _tasa_efectiva()


def _monto_usd_desde_bs(monto_bs_val: float, tasa_val: float) -> float:
    if tasa_val and tasa_val > 0:
        return round(float(monto_bs_val) / float(tasa_val), 2)
    return 0.0

pres_row = fetch_presupuesto_si_existe(
    get_supabase_client(), condominio_id, periodo_db
)
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
try:
    mora_cfg = repo_mora.obtener_config(condominio_id)
except DatabaseError:
    mora_cfg = {"activa": False, "pct_mora": 0.0}
_anio = int(periodo_db[:4])
_mes = int(periodo_db[5:7])
try:
    mora_aplica = repo_mora.mora_aplica_hoy(condominio_id, _anio, _mes)
except Exception:
    mora_aplica = False
mora_monto = 0.0
if mora_aplica and mora_cfg.get("activa") and saldo_u > 0:
    mora_monto = MoraRepository.calcular_mora_unidad(
        saldo_u, cuota_m, float(mora_cfg.get("pct_mora") or 0)
    )
pct_mora_disp = float(mora_cfg.get("pct_mora") or 0)
try:
    ya_pagado = repo_pago.get_total_pagado_unidad(unidad_id, periodo_db)
except DatabaseError:
    ya_pagado = 0.0

total_a_pagar = round(saldo_u + cuota_m + mora_monto - ya_pagado, 2)
total_a_pagar_usd = _monto_usd_desde_bs(total_a_pagar, tasa)

st.markdown("### Resumen de cuenta (unidad seleccionada)")
total_bs_fmt = f"{total_a_pagar:,.2f}"
if tasa and tasa > 0:
    total_row_bs = f"Bs. {total_bs_fmt}  ≈ USD {total_a_pagar_usd:,.2f}"
else:
    total_row_bs = f"Bs. {total_bs_fmt}"

label_intereses = f"Intereses de mora ({pct_mora_disp:g}%)"
df_resumen = pd.DataFrame(
    {
        "Concepto": [
            "Saldo mes anterior",
            "Cuota del mes",
            label_intereses,
            "TOTAL A PAGAR",
            "Pagado hoy (formulario)",
            "SALDO RESULTANTE",
        ],
        "Monto Bs.": [
            f"Bs. {saldo_u:,.2f}",
            f"Bs. {cuota_m:,.2f}",
            f"Bs. {mora_monto:,.2f}",
            total_row_bs,
            "(al registrar)",
            "(al registrar)",
        ],
    }
)
st.dataframe(df_resumen, hide_index=True, use_container_width=True)
if mora_monto == 0.0 and not mora_cfg.get("activa"):
    st.caption("_Intereses de mora: sin mora configurada._")
elif mora_monto == 0.0 and saldo_u <= 0:
    st.caption("_Intereses de mora: crédito a favor — sin mora._")
if tasa and tasa > 0:
    st.caption(
        f"**TOTAL A PAGAR:** Bs. {total_a_pagar:,.2f} ≈ USD {total_a_pagar_usd:,.2f} "
        f"(tasa: Bs. {tasa:,.2f})"
    )

# Fuera del form: el monto actualiza el equivalente USD en cada interacción (dentro del form no rerun).
monto_bs = st.number_input(
    "Monto recibido (Bs.) *",
    min_value=0.0,
    value=max(0.0, float(total_a_pagar)),
    step=0.01,
    format="%.2f",
    help="Precarga el total adeudado; ajuste si es pago parcial.",
    key="pago_monto_bs_input",
)
monto_usd_calc = _monto_usd_desde_bs(monto_bs, tasa)
if tasa and tasa > 0:
    st.caption(f"≈ USD {monto_usd_calc:,.2f} (tasa: Bs. {tasa:,.2f})")
else:
    st.caption(
        "Sin tasa de cambio: defina **tasa_cambio** en la sesión (sidebar) o en datos del condominio."
    )

with st.form("form_pago"):
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
        monto_usd = _monto_usd_desde_bs(float(monto_bs), tasa)
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
        mbs = float(h.get("monto_bs") or 0)
        musd = float(h.get("monto_usd") or 0)
        tc_row = float(h.get("tasa_cambio") or 0)
        if musd == 0 and tc_row > 0 and mbs > 0:
            musd = round(mbs / tc_row, 2)
        rows.append(
            {
                "fecha_pago": h.get("fecha_pago"),
                "unidad": cod,
                "metodo": h.get("metodo"),
                "referencia": h.get("referencia") or "—",
                "monto_bs": f"{mbs:,.2f}",
                "monto_usd": f"{musd:,.2f}",
                "estado": h.get("estado"),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
