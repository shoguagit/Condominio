import streamlit as st
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

from config.supabase_client import get_supabase_client
from repositories.presupuesto_repository import (
    fetch_presupuesto_si_existe,
    upsert_presupuesto_seguro,
)
from repositories.unidad_repository import suma_indivisos_si_disponible
from repositories.movimiento_repository import MovimientoRepository
from repositories.proceso_repository import ProcesoMensualRepository
from repositories.unidad_repository import UnidadRepository
from repositories.condominio_repository import CondominioRepository
from repositories.pago_repository import PagoRepository
from repositories.mora_repository import MoraRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_periodo, periodo_to_date_str, date_periodo_to_mm_yyyy
from utils.indiviso_cuota import cuota_bs_desde_presupuesto, valida_suma_exacta_100_pct, TOLERANCIA_INDIVISO_PCT
from utils.cierre_mensual import (
    saldo_nuevo_tras_cierre,
    etiqueta_estado_cierre_ui,
    estado_pago_db,
    puede_generar_cuotas,
    puede_cerrar_mes,
    texto_pasos_cierre,
)
from components.header import render_header
from components.breadcrumb import render_breadcrumb


st.set_page_config(page_title="Proceso Mensual", page_icon="🗓️", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Proceso Mensual")

condominio_id = require_condominio()


@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return (
        ProcesoMensualRepository(client),
        MovimientoRepository(client),
        UnidadRepository(client),
        CondominioRepository(client),
        PagoRepository(client),
        MoraRepository(client),
    )


repo_proc, repo_mov, repo_uni, repo_cond, repo_pago, repo_mora = get_repos()

st.markdown("## 🗓️ Proceso Mensual")

periodo = st.text_input("Período (YYYY-MM-01) *", value=str(st.session_state.get("mes_proceso") or "").strip())
ok_p, msg_p = validate_periodo(periodo)
if not ok_p:
    st.error(f"❌ {msg_p}")
    st.stop()
ok_db, msg_db, periodo_db = periodo_to_date_str(periodo)
if not ok_db or not periodo_db:
    st.error(f"❌ {msg_db}")
    st.stop()

try:
    proceso = repo_proc.get_or_create(condominio_id, periodo_db)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

estado_proc = (proceso.get("estado") or "borrador").lower()
cerrado = estado_proc == "cerrado"

pres_existente = fetch_presupuesto_si_existe(
    get_supabase_client(), condominio_id, periodo_db
)
tiene_presupuesto = bool(pres_existente and float(pres_existente.get("monto_bs") or 0) > 0)

try:
    cuotas_actuales = repo_proc.get_cuotas(condominio_id, periodo_db)
except DatabaseError:
    cuotas_actuales = []

hay_cuotas = len(cuotas_actuales) > 0
cuotas_generadas = hay_cuotas

try:
    total_pagos_mes = repo_pago.sum_total_periodo(condominio_id, periodo_db)
except DatabaseError:
    total_pagos_mes = 0.0
hay_pagos_periodo = total_pagos_mes > 0

pasos_lines, paso_actual = texto_pasos_cierre(
    tiene_presupuesto,
    cuotas_generadas,
    hay_pagos_periodo,
    cerrado,
)

st.markdown("### Avance del período")
if cerrado:
    for linea in pasos_lines:
        st.write(f"✓ {linea} — listo")
else:
    for i, linea in enumerate(pasos_lines, start=1):
        if i < paso_actual:
            st.write(f"✓ {linea} — listo")
        elif i == paso_actual:
            st.write(f"→ **{linea}** — en curso / pendiente")
        else:
            st.write(f"○ {linea}")

if cerrado and proceso.get("closed_at"):
    fc = proceso.get("closed_at")
    if isinstance(fc, str) and "T" in fc:
        fc = fc.split("T")[0]
    try:
        y, m, d = str(fc)[:10].split("-")
        fecha_txt = f"{d}/{m}/{y}"
    except (ValueError, AttributeError):
        fecha_txt = str(fc)
    st.info(f"📌 Período cerrado el {fecha_txt}. Solo lectura.")

if st.session_state.pop("_flash_presupuesto_ok", False):
    st.success("✅ Presupuesto guardado en la base de datos.")
if st.session_state.pop("_flash_cierre_ok", False):
    nm = st.session_state.pop("_flash_cierre_periodo", "")
    st.success(f"✅ Mes cerrado. Nuevo período: **{nm}**")
if st.session_state.pop("_flash_generar_cuotas", False):
    st.success("✅ Cuotas generadas correctamente.")

st.markdown("### Presupuesto del mes")
st.caption(
    "Antes del cierre puede usar el monto guardado o ajustarlo al gasto real (egresos del período)."
)
default_pres = float(pres_existente["monto_bs"]) if pres_existente else float(
    st.session_state.get("presupuesto_mes") or 0
)

try:
    gasto_real_bs = repo_mov.sum_egresos_periodo(condominio_id, periodo_db)
except DatabaseError:
    gasto_real_bs = 0.0

col_pr, col_pb, col_pg = st.columns([2, 1, 1])
with col_pr:
    monto_pres = st.number_input(
        "Monto presupuesto (Bs.) *",
        min_value=0.0,
        value=max(0.0, default_pres),
        step=0.01,
        format="%.2f",
        help="Base para cuota por unidad: presupuesto × (indiviso % / 100).",
        disabled=cerrado,
        key="proc_presupuesto_input",
    )
with col_pb:
    if st.button("Guardar presupuesto", use_container_width=True, disabled=cerrado):
        try:
            upsert_presupuesto_seguro(
                get_supabase_client(),
                condominio_id,
                periodo_db,
                float(monto_pres),
                None,
            )
            st.session_state.presupuesto_mes = float(monto_pres)
            st.session_state["_flash_presupuesto_ok"] = True
            st.toast("Presupuesto guardado", icon="✅")
            st.rerun()
        except DatabaseError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error inesperado al guardar: {e}")
with col_pg:
    if st.button(
        "Usar gasto real del período",
        use_container_width=True,
        disabled=cerrado,
        help="Precarga la suma de movimientos tipo egreso del período (edite antes de guardar).",
    ):
        st.session_state["proc_presupuesto_input"] = round(float(gasto_real_bs), 2)
        st.session_state.presupuesto_mes = round(float(gasto_real_bs), 2)
        st.rerun()

st.session_state.presupuesto_mes = float(monto_pres)

if pres_existente:
    st.caption(
        f"💾 Presupuesto en base de datos para **{periodo_db}**: "
        f"**{float(pres_existente['monto_bs']):,.2f} Bs.**"
    )
else:
    st.caption("_Todavía no hay presupuesto guardado en BD para este período._")

st.caption(f"Suma de **egresos** registrados en el período: **{gasto_real_bs:,.2f}** Bs.")

st.markdown(f"**Estado proceso:** {proceso.get('estado', '—')}")
st.divider()

try:
    movimientos = repo_mov.get_all(condominio_id, periodo=periodo_db)
except DatabaseError as e:
    st.error(f"❌ {e}")
    movimientos = []

total_gastos_bs = sum(float(m.get("monto_bs") or 0) for m in movimientos if m.get("tipo") == "egreso")
fondo_reserva_bs = round(total_gastos_bs * 0.10, 2)
total_facturable_bs = round(total_gastos_bs + fondo_reserva_bs, 2)

col1, col2, col3 = st.columns(3)
col1.metric("Total gastos (Bs)", f"{total_gastos_bs:,.2f}")
col2.metric("Fondo reserva 10% (Bs)", f"{fondo_reserva_bs:,.2f}")
col3.metric("Total facturable (Bs)", f"{total_facturable_bs:,.2f}")

st.markdown("### 📊 Validación de indivisos (%)")
suma_ind = suma_indivisos_si_disponible(
    get_supabase_client(), condominio_id, exclude_id=None
)
ok_s, msg_s = valida_suma_exacta_100_pct(suma_ind)
if not ok_s:
    st.warning(
        f"⚠️ {msg_s} "
        f"(tolerancia ±{TOLERANCIA_INDIVISO_PCT:.2f} pp). "
        "Ajuste indivisos en Unidades antes de procesar."
    )
else:
    st.success("✅ Suma de indivisos = 100,00% (± tolerancia).")

# ── CONFIGURACIÓN DE MORA ──────────────────────────────────────────
try:
    config_mora = repo_mora.obtener_config(condominio_id)
except DatabaseError:
    config_mora = {"activa": False, "pct_mora": 0.0}
try:
    dia_limite = repo_cond.obtener_dia_limite(condominio_id)
except DatabaseError:
    dia_limite = 15

with st.expander("⚙️ Configuración de mora del período", expanded=False):
    col1, col2 = st.columns([1, 1])
    with col1:
        mora_activa = st.toggle(
            "Activar mora este mes",
            value=bool(config_mora.get("activa", False)),
            key="toggle_mora",
            disabled=cerrado,
        )
    with col2:
        pct_mora = st.number_input(
            "% mora mensual",
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            value=float(config_mora.get("pct_mora", 0.0)),
            key="input_pct_mora",
            disabled=cerrado,
        )

    if st.button(
        "💾 Guardar configuración de mora",
        key="btn_guardar_mora",
        disabled=cerrado,
    ):
        try:
            repo_mora.actualizar_config(
                condominio_id,
                float(pct_mora),
                bool(mora_activa),
            )
            st.success(
                f"Mora {'activada' if mora_activa else 'desactivada'} — "
                f"{pct_mora}% mensual guardado."
            )
            st.rerun()
        except DatabaseError as e:
            st.error(f"❌ {e}")
        except ValueError as e:
            st.error(f"❌ {e}")

    st.info(
        "📌 La mora aplica **solo** si el propietario tiene deuda "
        "anterior (saldo anterior > 0). Si tiene crédito a favor, "
        "mora = Bs. 0 aunque tenga cuota pendiente.\n\n"
        "**Base de cálculo:** saldo anterior + cuota del mes\n\n"
        f"**Día límite de pago configurado:** día {dia_limite} de cada mes"
    )

st.divider()

st.markdown("### ⚙️ Generar cuotas")
st.caption(
    "Genera filas en cuotas_unidad con pagos del mes en cero; al cerrar el mes se consolidan pagos y saldos."
)

chk_regen = False
if hay_cuotas and not cerrado:
    chk_regen = st.checkbox(
        "Ya existen cuotas para este período: marque para **regenerarlas** (reemplaza las actuales).",
        value=False,
        key="chk_regenerar_cuotas",
    )

gen_disabled = cerrado or not puede_generar_cuotas(estado_proc)
if st.button("Generar cuotas", type="primary", use_container_width=True, disabled=gen_disabled):
    try:
        pres_m = float(st.session_state.get("presupuesto_mes") or 0)
        if pres_m <= 0:
            st.error("❌ Defina y guarde un presupuesto del mes mayor a cero.")
            st.stop()

        suma_i = suma_indivisos_si_disponible(
            get_supabase_client(), condominio_id, exclude_id=None
        )
        ok_i, msg_i = valida_suma_exacta_100_pct(suma_i)
        if not ok_i:
            st.error(f"❌ Ajuste indivisos antes de generar cuotas. {msg_i}")
            st.stop()

        if hay_cuotas and not chk_regen:
            st.error(
                "❌ Ya existen cuotas para este período. ¿Desea regenerarlas? "
                "Marque la casilla de confirmación y vuelva a pulsar **Generar cuotas**."
            )
            st.stop()

        if hay_cuotas and chk_regen:
            repo_proc.delete_cuotas_for_proceso(int(proceso["id"]))

        proceso = repo_proc.update(
            proceso["id"],
            {
                "total_gastos_bs": total_gastos_bs,
                "fondo_reserva_bs": fondo_reserva_bs,
                "total_facturable_bs": total_facturable_bs,
                "estado": "procesado",
            },
        )

        unidades = repo_uni.get_all(condominio_id, solo_activos=True)
        for u in unidades:
            pct = float(u.get("indiviso_pct") or 0)
            v_frac = pct / 100.0
            cuota = cuota_bs_desde_presupuesto(pres_m, pct)
            saldo_ant = round(float(u.get("saldo") or 0), 2)
            total_a_pagar = round(saldo_ant + cuota, 2)
            repo_proc.upsert_cuota(
                {
                    "proceso_id": proceso["id"],
                    "unidad_id": u.get("id"),
                    "propietario_id": u.get("propietario_id"),
                    "condominio_id": condominio_id,
                    "periodo": periodo_db,
                    "alicuota_valor": v_frac,
                    "total_gastos_bs": pres_m,
                    "cuota_calculada_bs": cuota,
                    "saldo_anterior_bs": saldo_ant,
                    "pagos_mes_bs": 0.0,
                    "mora": 0.0,
                    "mora_bs": 0.0,
                    "pct_mora": 0.0,
                    "total_a_pagar_bs": total_a_pagar,
                    "estado": "pendiente",
                }
            )

        st.session_state["_flash_generar_cuotas"] = True
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {e}")

try:
    cuotas = repo_proc.get_cuotas(condominio_id, periodo_db)
except DatabaseError as e:
    st.error(f"❌ {e}")
    cuotas = []

pagos_por_unidad: dict[int, float] = {}
if cuotas:
    try:
        pagos_por_unidad = repo_pago.sum_por_unidad_periodo(condominio_id, periodo_db)
    except DatabaseError:
        pagos_por_unidad = {}

if cuotas:
    try:
        mora_cfg = repo_mora.obtener_config(condominio_id)
    except DatabaseError:
        mora_cfg = {"activa": False, "pct_mora": 0.0}
    anio_m = int(periodo_db[:4])
    mes_m = int(periodo_db[5:7])
    try:
        mora_aplica_fecha = repo_mora.mora_aplica_hoy(condominio_id, anio_m, mes_m)
    except DatabaseError:
        mora_aplica_fecha = False
    mora_activa_logica = (
        bool(mora_cfg.get("activa"))
        and float(mora_cfg.get("pct_mora") or 0) > 0
        and mora_aplica_fecha
    )
    pct_cfg = float(mora_cfg.get("pct_mora") or 0)

    st.markdown("#### Tabla de cuotas generadas")
    rows_cuotas = []
    for c in cuotas:
        u = c.get("unidades") or {}
        p = c.get("propietarios") or {}
        pct_u = float(c.get("alicuota_valor") or 0) * 100.0
        rows_cuotas.append(
            {
                "Unidad": u.get("codigo") or u.get("numero") or "—",
                "Propietario": (p.get("nombre") or "—"),
                "Indiviso %": round(pct_u, 4),
                "Saldo ant. Bs": float(c.get("saldo_anterior_bs") or 0),
                "Cuota Bs": float(c.get("cuota_calculada_bs") or 0),
                "Total Bs": float(c.get("total_a_pagar_bs") or 0),
                "Estado": c.get("estado") or "—",
            }
        )
    st.dataframe(rows_cuotas, use_container_width=True, hide_index=True)

    st.markdown("#### Saldos por unidad (vista pre-cierre)")
    rows_saldos = []
    for c in cuotas:
        u = c.get("unidades") or {}
        p = c.get("propietarios") or {}
        uid = int(c.get("unidad_id") or 0)
        saldo_ant = float(c.get("saldo_anterior_bs") or 0)
        cuota_v = float(c.get("cuota_calculada_bs") or 0)
        pagado = round(float(pagos_por_unidad.get(uid, 0) or 0), 2)
        mora_u = 0.0
        if mora_activa_logica and saldo_ant > 0:
            mora_u = MoraRepository.calcular_mora_unidad(saldo_ant, cuota_v, pct_cfg)
        saldo_nuevo = saldo_nuevo_tras_cierre(saldo_ant, cuota_v, pagado, mora_u)
        rows_saldos.append(
            {
                "Unidad": u.get("codigo") or u.get("numero") or "—",
                "Propietario": (p.get("nombre") or "—"),
                "Saldo ant.": saldo_ant,
                "Cuota": cuota_v,
                "Mora Bs.": mora_u,
                "Pagado": pagado,
                "Saldo nuevo": saldo_nuevo,
                "Estado": etiqueta_estado_cierre_ui(saldo_nuevo, pagado),
            }
        )
    st.dataframe(rows_saldos, use_container_width=True, hide_index=True)

    total_cuotas_emitidas = round(
        sum(float(c.get("cuota_calculada_bs") or 0) for c in cuotas), 2
    )
    total_mora_gen = round(sum(r["Mora Bs."] for r in rows_saldos), 2)
    total_cuotas_mora = round(total_cuotas_emitidas + total_mora_gen, 2)
    total_cobrado = round(total_pagos_mes, 2)
    total_pendiente = round(sum(r["Saldo nuevo"] for r in rows_saldos), 2)
    eff = (
        round((total_cobrado / total_cuotas_mora) * 100, 2)
        if total_cuotas_mora > 0
        else 0.0
    )

    st.markdown("#### Resumen financiero (pre-cierre)")
    r1a, r1b, r1c = st.columns(3)
    r1a.metric("Total mora generada (Bs.)", f"{total_mora_gen:,.2f}")
    r1b.metric("Total cuotas emitidas (Bs.)", f"{total_cuotas_emitidas:,.2f}")
    r1c.metric("Total cuotas + mora (Bs.)", f"{total_cuotas_mora:,.2f}")
    r2a, r2b, r2c = st.columns(3)
    r2a.metric("Total cobrado (Bs.)", f"{total_cobrado:,.2f}")
    r2b.metric("Total pendiente (Bs.)", f"{total_pendiente:,.2f}")
    r2c.metric("Eficiencia de cobro %", f"{eff:,.2f}%")

st.divider()

st.markdown("### 🔒 Cerrar mes")
st.caption("Consolida pagos del período, actualiza saldos de unidades y avanza mes_proceso. Irreversible.")

puede_cerrar = puede_cerrar_mes(estado_proc) and len(cuotas) > 0
cerrar_disabled = cerrado or not puede_cerrar

if st.session_state.get("confirmar_cierre_mes"):
    prox_mm_yyyy = date_periodo_to_mm_yyyy(
        (datetime.strptime(periodo_db[:10], "%Y-%m-%d").date() + relativedelta(months=1)).isoformat()
    )
    st.warning(
        f"⚠️ Esta acción es irreversible. Se cerrarán los saldos y se avanzará "
        f"al período **{prox_mm_yyyy}**. ¿Confirmar?"
    )
    c_yes, c_no = st.columns(2)
    if c_no.button("Cancelar", use_container_width=True):
        st.session_state.confirmar_cierre_mes = False
        st.rerun()
    if c_yes.button("Confirmar cierre definitivo", type="primary", use_container_width=True):
        try:
            if estado_proc != "procesado":
                st.error("❌ El proceso debe estar en estado procesado.")
                st.stop()
            if not cuotas:
                st.error("❌ No hay cuotas generadas.")
                st.stop()

            pagos_u = repo_pago.sum_por_unidad_periodo(condominio_id, periodo_db)

            try:
                mora_cfg_cierre = repo_mora.obtener_config(condominio_id)
            except DatabaseError:
                mora_cfg_cierre = {"activa": False, "pct_mora": 0.0}
            ay, am = int(periodo_db[:4]), int(periodo_db[5:7])
            try:
                mora_aplica_cierre = repo_mora.mora_aplica_hoy(condominio_id, ay, am)
            except DatabaseError:
                mora_aplica_cierre = False
            mora_activa_cierre = (
                bool(mora_cfg_cierre.get("activa"))
                and float(mora_cfg_cierre.get("pct_mora") or 0) > 0
                and mora_aplica_cierre
            )
            pct_cierre = float(mora_cfg_cierre.get("pct_mora") or 0)

            for c in cuotas:
                cid = int(c["id"])
                uid = int(c.get("unidad_id") or 0)
                saldo_ant = float(c.get("saldo_anterior_bs") or 0)
                cuota_v = float(c.get("cuota_calculada_bs") or 0)
                pagos_mes = round(float(pagos_u.get(uid, 0) or 0), 2)
                mora = 0.0
                if mora_activa_cierre and saldo_ant > 0:
                    mora = MoraRepository.calcular_mora_unidad(
                        saldo_ant, cuota_v, pct_cierre
                    )
                saldo_nuevo = saldo_nuevo_tras_cierre(
                    saldo_ant, cuota_v, pagos_mes, mora
                )
                repo_proc.update_cuota_row(
                    cid,
                    {
                        "pagos_mes_bs": pagos_mes,
                        "mora": mora,
                        "mora_bs": mora,
                        "pct_mora": pct_cierre if mora_activa_cierre else 0.0,
                        "total_a_pagar_bs": saldo_nuevo,
                        "estado": "cerrado",
                    },
                )
                repo_uni.update(
                    uid,
                    {
                        "saldo": saldo_nuevo,
                        "estado_pago": estado_pago_db(saldo_nuevo, pagos_mes),
                    },
                )

            repo_mov.mark_periodo_procesado(condominio_id, periodo_db)

            now_iso = datetime.now(timezone.utc).isoformat()
            repo_proc.update(
                int(proceso["id"]),
                {"estado": "cerrado", "closed_at": now_iso},
            )

            d_next = datetime.strptime(periodo_db[:10], "%Y-%m-%d").date() + relativedelta(months=1)
            repo_cond.update(condominio_id, {"mes_proceso": d_next.isoformat()})
            st.session_state.mes_proceso = date_periodo_to_mm_yyyy(d_next.isoformat())
            st.session_state.confirmar_cierre_mes = False
            st.session_state._flash_cierre_ok = True
            st.session_state._flash_cierre_periodo = date_periodo_to_mm_yyyy(d_next.isoformat())
            st.rerun()
        except DatabaseError as e:
            st.error(f"❌ {e}")

if st.button(
    "Cerrar mes",
    use_container_width=True,
    disabled=cerrar_disabled,
    type="primary",
    key="cerrar_mes_btn",
):
    if not puede_cerrar:
        st.error("❌ Solo disponible con proceso en estado **procesado** y cuotas generadas.")
    else:
        st.session_state.confirmar_cierre_mes = True
        st.rerun()

st.divider()
st.markdown("### 📜 Histórico de períodos")
try:
    hist_proc = repo_proc.list_by_condominio(condominio_id)
except DatabaseError as e:
    st.error(str(e))
    hist_proc = []

if not hist_proc:
    st.caption("No hay procesos mensuales registrados.")
else:
    rows_h = []
    for p in hist_proc:
        per = p.get("periodo")
        per_s = str(per)[:10] if per else ""
        try:
            pres_h = fetch_presupuesto_si_existe(get_supabase_client(), condominio_id, per_s)
            pres_bs = float(pres_h["monto_bs"]) if pres_h else 0.0
        except Exception:
            pres_bs = 0.0
        try:
            cob = repo_pago.sum_total_periodo(condominio_id, per_s)
        except DatabaseError:
            cob = 0.0
        try:
            cuotas_h = repo_proc.get_cuotas(condominio_id, per_s)
            pend = round(sum(float(x.get("total_a_pagar_bs") or 0) for x in cuotas_h), 2)
        except DatabaseError:
            pend = 0.0
        ca = p.get("closed_at")
        if ca:
            if isinstance(ca, str) and "T" in ca:
                ca = ca.split("T")[0]
            try:
                y, m, d = str(ca)[:10].split("-")
                ca_txt = f"{d}/{m}/{y}"
            except ValueError:
                ca_txt = str(ca)
        else:
            ca_txt = "—"
        rows_h.append(
            {
                "Período": date_periodo_to_mm_yyyy(per_s) if per_s else "—",
                "Presupuesto Bs.": f"{pres_bs:,.2f}",
                "Total cobrado": f"{cob:,.2f}",
                "Pendiente": f"{pend:,.2f}",
                "Estado": p.get("estado") or "—",
                "Fecha cierre": ca_txt,
            }
        )
    st.dataframe(rows_h, use_container_width=True, hide_index=True)
