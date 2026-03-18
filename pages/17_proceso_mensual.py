import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.movimiento_repository import MovimientoRepository
from repositories.proceso_repository import ProcesoMensualRepository
from repositories.alicuota_repository import AlicuotaRepository
from repositories.unidad_repository import UnidadRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_periodo, validate_suma_alicuotas
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
        AlicuotaRepository(client),
        UnidadRepository(client),
    )


repo_proc, repo_mov, repo_ali, repo_uni = get_repos()

st.markdown("## 🗓️ Proceso Mensual")

periodo = st.text_input("Período (YYYY-MM-01) *", value=str(st.session_state.get("mes_proceso") or "").strip())
ok_p, msg_p = validate_periodo(periodo)
if not ok_p:
    st.error(f"❌ {msg_p}")
    st.stop()

try:
    proceso = repo_proc.get_or_create(condominio_id, periodo)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

st.markdown(f"**Estado:** {proceso.get('estado', '—')}")
if proceso.get("estado") == "cerrado":
    st.warning("Mes CERRADO. No se puede reprocesar ni recalcular.")
st.divider()

try:
    movimientos = repo_mov.get_all(condominio_id, periodo=periodo)
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

st.markdown("### 📊 Validación de alícuotas")
alicuotas = repo_ali.get_all(condominio_id, solo_activos=True)
valores = [float(a.get("total_alicuota") or 0) for a in alicuotas]
ok_s, msg_s = validate_suma_alicuotas(valores)
if not ok_s:
    st.error(f"❌ {msg_s}")
    st.stop()
st.success("✅ Suma de alícuotas válida (≈ 1.00).")

st.divider()

st.markdown("### ⚙️ Procesar mes (calcular cuotas por unidad)")

if st.button("Procesar mes", type="primary", use_container_width=True, disabled=(proceso.get("estado") == "cerrado")):
    try:
        # actualizar resumen del proceso
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
        # Map alícuota_id -> valor
        ali_val = {a["id"]: float(a.get("total_alicuota") or 0) for a in alicuotas}

        pagos_por_unidad = repo_mov.sum_ingresos_por_unidad(condominio_id, periodo)

        for u in unidades:
            alicuota_id = u.get("alicuota_id")
            v = float(ali_val.get(alicuota_id) or 0)
            cuota = round(total_facturable_bs * v, 2)
            pagos_mes = round(float(pagos_por_unidad.get(int(u.get("id")), 0) or 0), 2)
            saldo_ant = round(float(u.get("saldo") or 0), 2)
            total_a_pagar = round(cuota + saldo_ant - pagos_mes, 2)
            repo_proc.upsert_cuota(
                {
                    "proceso_id": proceso["id"],
                    "unidad_id": u.get("id"),
                    "propietario_id": u.get("propietario_id"),
                    "condominio_id": condominio_id,
                    "periodo": periodo,
                    "alicuota_valor": v,
                    "total_gastos_bs": total_facturable_bs,
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

        cuotas = repo_proc.get_cuotas(condominio_id, periodo)
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
        repo_mov.mark_periodo_procesado(condominio_id, periodo)

        st.success("✅ Mes cerrado. Saldos actualizados y movimientos procesados.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {e}")

st.markdown("### 📄 Cuotas generadas")
try:
    cuotas = repo_proc.get_cuotas(condominio_id, periodo)
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

