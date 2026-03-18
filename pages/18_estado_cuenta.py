import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.movimiento_repository import MovimientoRepository
from repositories.proceso_repository import ProcesoMensualRepository
from repositories.unidad_repository import UnidadRepository
from repositories.propietario_repository import PropietarioRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_periodo
from components.header import render_header
from components.breadcrumb import render_breadcrumb


st.set_page_config(page_title="Estado de Cuenta", page_icon="🧾", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Estado de Cuenta")

condominio_id = require_condominio()


@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return ProcesoMensualRepository(client), MovimientoRepository(client), UnidadRepository(client), PropietarioRepository(client)


repo_proc, repo_mov, repo_uni, repo_prop = get_repos()

st.markdown("## 🧾 Estado de Cuenta")

periodo = st.text_input("Período (YYYY-MM-01) *", value=str(st.session_state.get("mes_proceso") or "").strip())
ok_p, msg_p = validate_periodo(periodo)
if not ok_p:
    st.error(f"❌ {msg_p}")
    st.stop()

try:
    unidades = repo_uni.get_all(condominio_id)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

if not unidades:
    st.info("No hay unidades registradas.")
    st.stop()

opts = []
uid_map = {}
for u in unidades:
    codigo = (u.get("codigo") or u.get("numero") or "").strip()
    prop = (u.get("propietarios") or {})
    label = f"{codigo} — {prop.get('nombre','—')}"
    opts.append(label)
    uid_map[label] = u.get("id")

sel = st.selectbox("Unidad", options=opts)
unidad_id = uid_map[sel]

st.divider()

tab_resumen, tab_historico, tab_mov = st.tabs(["📌 Resumen del período", "🗂️ Histórico", "🏦 Movimientos del mes"])

with tab_resumen:
    try:
        cuotas_p = repo_proc.get_cuotas(condominio_id, periodo)
    except DatabaseError as e:
        st.error(f"❌ {e}")
        st.stop()

    cuota = next((c for c in cuotas_p if c.get("unidad_id") == unidad_id), None)
    if not cuota:
        st.info("No hay cuota calculada para esta unidad en el período. Procese el mes primero.")
        st.stop()

    cuota_calc = float(cuota.get("cuota_calculada_bs") or 0)
    saldo_ant = float(cuota.get("saldo_anterior_bs") or 0)
    pagos_mes = float(cuota.get("pagos_mes_bs") or 0)
    total_pagar = float(cuota.get("total_a_pagar_bs") or 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cuota (Bs)", f"{cuota_calc:,.2f}")
    col2.metric("Saldo anterior (Bs)", f"{saldo_ant:,.2f}")
    col3.metric("Pagos mes (Bs)", f"{pagos_mes:,.2f}")
    col4.metric("Saldo final / deuda (Bs)", f"{total_pagar:,.2f}")

    st.markdown("### Datos de la cuota")
    st.write(
        {
            "periodo": cuota.get("periodo"),
            "alicuota_valor": cuota.get("alicuota_valor"),
            "estado": cuota.get("estado"),
        }
    )

with tab_historico:
    st.markdown("### 🗂️ Histórico de cuotas")
    try:
        # Traer varios períodos y filtrar por unidad
        all_rows = (
            get_supabase_client()
            .table("cuotas_unidad")
            .select("*")
            .eq("condominio_id", condominio_id)
            .eq("unidad_id", unidad_id)
            .order("periodo", desc=True)
            .execute()
        ).data
    except Exception as e:
        st.error(f"❌ Error cargando histórico: {e}")
        all_rows = []

    if not all_rows:
        st.info("No hay histórico de cuotas para esta unidad.")
    else:
        st.dataframe(
            all_rows,
            use_container_width=True,
            hide_index=True,
            column_config={
                "periodo": st.column_config.DateColumn("Período"),
                "cuota_calculada_bs": st.column_config.NumberColumn("Cuota (Bs)", format="%.2f"),
                "saldo_anterior_bs": st.column_config.NumberColumn("Saldo anterior (Bs)", format="%.2f"),
                "pagos_mes_bs": st.column_config.NumberColumn("Pagos mes (Bs)", format="%.2f"),
                "total_a_pagar_bs": st.column_config.NumberColumn("Saldo final (Bs)", format="%.2f"),
                "estado": st.column_config.TextColumn("Estado"),
            },
        )

with tab_mov:
    st.markdown("### 🏦 Movimientos del período")
    try:
        movs = repo_mov.get_all(condominio_id, periodo=periodo)
    except DatabaseError as e:
        st.error(f"❌ {e}")
        st.stop()

    movs_u = [m for m in movs if m.get("unidad_id") == unidad_id]
    if not movs_u:
        st.info("No hay movimientos asociados a esta unidad en el período.")
    else:
        eg = [m for m in movs_u if m.get("tipo") == "egreso"]
        ing = [m for m in movs_u if m.get("tipo") == "ingreso"]

        col_a, col_b = st.columns(2)
        col_a.metric("Ingresos del mes (Bs)", f"{sum(float(m.get('monto_bs') or 0) for m in ing):,.2f}")
        col_b.metric("Egresos del mes (Bs)", f"{sum(float(m.get('monto_bs') or 0) for m in eg):,.2f}")

        for m in movs_u:
            m["_concepto"] = (m.get("conceptos") or {}).get("nombre")
        st.dataframe(
            movs_u,
            use_container_width=True,
            hide_index=True,
            column_config={
                "fecha": st.column_config.DateColumn("Fecha"),
                "tipo": st.column_config.TextColumn("Tipo"),
                "descripcion": st.column_config.TextColumn("Descripción", width="large"),
                "referencia": st.column_config.TextColumn("Ref"),
                "monto_bs": st.column_config.NumberColumn("Monto (Bs)", format="%.2f"),
                "_concepto": st.column_config.TextColumn("Concepto"),
                "estado": st.column_config.TextColumn("Estado"),
            },
        )

