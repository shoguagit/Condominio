import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.movimiento_repository import MovimientoRepository
from repositories.proceso_repository import ProcesoMensualRepository
from repositories.unidad_repository import UnidadRepository
from repositories.presupuesto_repository import PresupuestoRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_periodo, periodo_to_date_str
from utils.indiviso_cuota import cuota_bs_desde_presupuesto, valida_suma_exacta_100_pct, TOLERANCIA_INDIVISO_PCT
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
        PresupuestoRepository(client),
    )


repo_proc, repo_mov, repo_uni, repo_pres = get_repos()

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

st.markdown("### Presupuesto del mes")
pres_existente = None
try:
    pres_existente = repo_pres.get_by_periodo(condominio_id, periodo_db)
except DatabaseError:
    pass
default_pres = float(pres_existente["monto_bs"]) if pres_existente else float(
    st.session_state.get("presupuesto_mes") or 0
)
col_pr, col_pb = st.columns([2, 1])
with col_pr:
    monto_pres = st.number_input(
        "Monto presupuesto (Bs.) *",
        min_value=0.0,
        value=max(0.0, default_pres),
        step=0.01,
        format="%.2f",
        help="Base para cuota por unidad: presupuesto × (indiviso % / 100).",
        disabled=(proceso.get("estado") == "cerrado"),
        key="proc_presupuesto_input",
    )
with col_pb:
    if st.button("Guardar presupuesto", use_container_width=True, disabled=(proceso.get("estado") == "cerrado")):
        try:
            repo_pres.upsert(condominio_id, periodo_db, monto_pres, None)
            st.session_state.presupuesto_mes = float(monto_pres)
            st.success("Presupuesto guardado.")
            st.rerun()
        except DatabaseError as e:
            st.error(str(e))

st.session_state.presupuesto_mes = float(monto_pres)

st.markdown(f"**Estado:** {proceso.get('estado', '—')}")
if proceso.get("estado") == "cerrado":
    st.warning("Mes CERRADO. No se puede reprocesar ni recalcular.")
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
suma_ind = repo_uni.get_suma_indivisos(condominio_id, exclude_id=None)
ok_s, msg_s = valida_suma_exacta_100_pct(suma_ind)
if not ok_s:
    st.warning(
        f"⚠️ {msg_s} "
        f"(tolerancia ±{TOLERANCIA_INDIVISO_PCT:.2f} pp). "
        "Ajuste indivisos en Unidades antes de procesar."
    )
else:
    st.success("✅ Suma de indivisos = 100,00% (± tolerancia).")

st.divider()

st.markdown("### ⚙️ Procesar mes (calcular cuotas por unidad)")

if st.button("Procesar mes", type="primary", use_container_width=True, disabled=(proceso.get("estado") == "cerrado")):
    try:
        pres_m = float(st.session_state.get("presupuesto_mes") or 0)
        if pres_m <= 0:
            st.error("❌ Defina y guarde un presupuesto del mes mayor a cero.")
            st.stop()

        suma_i = repo_uni.get_suma_indivisos(condominio_id, exclude_id=None)
        ok_i, msg_i = valida_suma_exacta_100_pct(suma_i)
        if not ok_i:
            st.error(f"❌ {msg_i}")
            st.stop()

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
        pagos_por_unidad = repo_mov.sum_ingresos_por_unidad(condominio_id, periodo_db)

        for u in unidades:
            pct = float(u.get("indiviso_pct") or 0)
            v_frac = pct / 100.0
            cuota = cuota_bs_desde_presupuesto(pres_m, pct)
            pagos_mes = round(float(pagos_por_unidad.get(int(u.get("id")), 0) or 0), 2)
            saldo_ant = round(float(u.get("saldo") or 0), 2)
            total_a_pagar = round(cuota + saldo_ant - pagos_mes, 2)
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
                    "pagos_mes_bs": pagos_mes,
                    "total_a_pagar_bs": total_a_pagar,
                    "estado": "pagado" if total_a_pagar <= 0 else "pendiente",
                }
            )

        st.success("✅ Proceso mensual calculado y cuotas generadas.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {e}")

st.divider()

st.markdown("### 🔒 Cerrar mes")
st.caption("Cierra el período: actualiza el saldo de cada unidad y marca movimientos como procesados.")

if st.button("Cerrar mes", use_container_width=True, disabled=(proceso.get("estado") == "cerrado"), type="primary", key="cerrar_mes_btn"):
    try:
        if proceso.get("estado") != "procesado":
            st.error("❌ Primero debe Procesar el mes antes de cerrarlo.")
            st.stop()

        cuotas = repo_proc.get_cuotas(condominio_id, periodo_db)
        if not cuotas:
            st.error("❌ No hay cuotas generadas para cerrar este mes.")
            st.stop()

        # Actualizar saldo de unidades: saldo_nuevo = total_a_pagar_bs
        for c in cuotas:
            uid = c.get("unidad_id")
            saldo_nuevo = round(float(c.get("total_a_pagar_bs") or 0), 2)
            repo_uni.update(int(uid), {"saldo": saldo_nuevo})

        # Marcar proceso como cerrado
        repo_proc.update(proceso["id"], {"estado": "cerrado"})

        # Marcar movimientos del período como procesados
        repo_mov.mark_periodo_procesado(condominio_id, periodo_db)

        st.success("✅ Mes cerrado. Saldos actualizados y movimientos procesados.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {e}")

st.markdown("### 📄 Cuotas generadas")
try:
    cuotas = repo_proc.get_cuotas(condominio_id, periodo_db)
except DatabaseError as e:
    st.error(f"❌ {e}")
    cuotas = []

if not cuotas:
    st.info("No hay cuotas aún para este período. Presiona “Procesar mes”.")
else:
    for c in cuotas:
        u = (c.get("unidades") or {})
        p = (c.get("propietarios") or {})
        c["_unidad"] = u.get("codigo") or u.get("numero")
        c["_propietario"] = p.get("nombre")
    st.dataframe(
        cuotas,
        use_container_width=True,
        hide_index=True,
        column_config={
            "_unidad": st.column_config.TextColumn("Unidad"),
            "_propietario": st.column_config.TextColumn("Propietario"),
            "alicuota_valor": st.column_config.NumberColumn("Alícuota", format="%.6f"),
            "cuota_calculada_bs": st.column_config.NumberColumn("Cuota (Bs)", format="%.2f"),
            "pagos_mes_bs": st.column_config.NumberColumn("Pagos mes (Bs)", format="%.2f"),
            "saldo_anterior_bs": st.column_config.NumberColumn("Saldo anterior (Bs)", format="%.2f"),
            "total_a_pagar_bs": st.column_config.NumberColumn("Total a pagar (Bs)", format="%.2f"),
            "estado": st.column_config.TextColumn("Estado"),
        },
    )

