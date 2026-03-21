"""
Relación de Gastos (recibo por unidad).
Condominio → mes → unidad → cabecera + tabla conceptos + totales + saldos.
"""
import streamlit as st
from datetime import date
from collections import defaultdict

from config.supabase_client import get_supabase_client
from repositories.condominio_repository import CondominioRepository
from repositories.unidad_repository import UnidadRepository
from repositories.movimiento_repository import MovimientoRepository
from repositories.proceso_repository import ProcesoMensualRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_periodo, periodo_to_date_str
from components.header import render_header
from components.breadcrumb import render_breadcrumb

st.set_page_config(page_title="Recibos", page_icon="🧾", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Recibos")

condominio_id = require_condominio()


@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return (
        CondominioRepository(client),
        UnidadRepository(client),
        MovimientoRepository(client),
        ProcesoMensualRepository(client),
    )


repo_cond, repo_uni, repo_mov, repo_proc = get_repos()

st.markdown("## 🧾 Relación de Gastos (Recibo)")

# Período
periodo = st.text_input(
    "Período (YYYY-MM o YYYY-MM-01) *",
    value=str(st.session_state.get("mes_proceso") or "").strip(),
    placeholder="Ej: 2026-02",
)
ok_p, msg_p = validate_periodo(periodo)
if not ok_p:
    st.error(f"❌ {msg_p}")
    st.stop()
ok_db, msg_db, periodo_db = periodo_to_date_str(periodo)
if not ok_db or not periodo_db:
    st.error(f"❌ {msg_db}")
    st.stop()

# Condominio
try:
    condominio = repo_cond.get_by_id(condominio_id)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()
if not condominio:
    st.error("Condominio no encontrado.")
    st.stop()

# Unidades con propietario y alícuota para el selector
try:
    unidades = repo_uni.get_all(condominio_id)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

# Unidades con indiviso % definido
unidades_con_alicuota = [u for u in unidades if float(u.get("indiviso_pct") or 0) > 0]
opts = ["— Todas las unidades —"]
uid_map = {}
for u in unidades_con_alicuota:
    codigo = (u.get("codigo") or u.get("numero") or "").strip()
    prop = u.get("propietarios") or {}
    nombre_prop = prop.get("nombre", "—")
    label = f"{codigo} — {nombre_prop}"
    opts.append(label)
    uid_map[label] = u.get("id")

if len(opts) == 1:
    st.warning("No hay unidades con indiviso % en el módulo Unidades.")
    st.stop()

sel = st.selectbox("Unidad", options=opts)
todas = sel == "— Todas las unidades —"
unidades_a_mostrar = unidades_con_alicuota if todas else [u for u in unidades_con_alicuota if u.get("id") == uid_map.get(sel)]
if not todas and not unidades_a_mostrar:
    st.warning("Seleccione una unidad.")
    st.stop()

# Gastos del mes (egresos) agrupados por concepto
try:
    movimientos = repo_mov.get_all(condominio_id, periodo=periodo_db)
except DatabaseError as e:
    st.error(f"❌ {e}")
    movimientos = []

egresos = [m for m in movimientos if m.get("tipo") == "egreso"]
# concepto_id -> { nombre, total_bs }
por_concepto = defaultdict(lambda: {"nombre": "Sin concepto", "total_bs": 0.0})
for m in egresos:
    cid = m.get("concepto_id")
    con = m.get("conceptos") or {}
    nombre = (con.get("nombre") or "Sin concepto").strip() or "Sin concepto"
    if cid not in por_concepto or por_concepto[cid]["nombre"] == "Sin concepto":
        por_concepto[cid]["nombre"] = nombre
    por_concepto[cid]["total_bs"] += float(m.get("monto_bs") or 0)

lineas = [{"concepto_id": k, "nombre": v["nombre"], "total_bs": v["total_bs"]} for k, v in por_concepto.items() if v["total_bs"] != 0]
lineas.sort(key=lambda x: (-x["total_bs"], x["nombre"]))

total_gastos_bs = sum(l["total_bs"] for l in lineas)
fondo_reserva_bs = round(total_gastos_bs * 0.10, 2)
total_relacionado_bs = round(total_gastos_bs + fondo_reserva_bs, 2)

# Cuotas ya calculadas (proceso mensual) si existen
try:
    cuotas_periodo = repo_proc.get_cuotas(condominio_id, periodo_db)
except DatabaseError:
    cuotas_periodo = []
cuotas_por_unidad = {c["unidad_id"]: c for c in cuotas_periodo}

# Mes en español
MESES = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
try:
    y, m, _ = str(periodo_db).split("-")
    mes_nombre = MESES[int(m) - 1].upper()
    anio = y
except Exception:
    mes_nombre = periodo_db or ""
    anio = ""

cond_nombre = (condominio.get("nombre") or "").strip()
cond_rif = (condominio.get("numero_documento") or "").strip()
cond_email = (condominio.get("email") or "").strip()
fecha_emision = date.today().strftime("%d-%m-%Y")

def render_recibo(unidad: dict):
    uid = unidad.get("id")
    codigo = (unidad.get("codigo") or unidad.get("numero") or "").strip()
    prop = unidad.get("propietarios") or {}
    nombre_prop = (prop.get("nombre") or "—").strip()
    correo_prop = (prop.get("correo") or "").strip()
    indiviso_pct = float(unidad.get("indiviso_pct") or 0)
    alicuota_valor = indiviso_pct / 100.0

    cuota_row = cuotas_por_unidad.get(uid)
    if cuota_row:
        cuota_mes_bs = float(cuota_row.get("cuota_calculada_bs") or 0)
        acumulado_bs = float(cuota_row.get("total_a_pagar_bs") or 0)
    else:
        cuota_mes_bs = round(total_relacionado_bs * alicuota_valor, 2)
        acumulado_bs = round(float(unidad.get("saldo") or 0) + cuota_mes_bs, 2)

    st.markdown("---")
    st.markdown(f"### Inmueble {codigo} — {nombre_prop}")

    # Cabecera en columnas
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{cond_nombre}**")
        if cond_rif:
            st.caption(f"RIF: {cond_rif}")
        if cond_email:
            st.caption(f"Email: {cond_email}")
    with c2:
        st.caption(f"Mes: {mes_nombre} {anio}")
        st.caption(f"Propietario: {nombre_prop}")
        if correo_prop:
            st.caption(f"Correo: {correo_prop}")
        st.caption(f"Emisión: {fecha_emision}")
        st.caption(f"Inmueble: {codigo}  |  Indiviso: {indiviso_pct}%")
        st.caption(f"Monto (Bs): **{cuota_mes_bs:,.2f}**  |  Acumulado (Bs): **{acumulado_bs:,.2f}**")

    # Tabla conceptos
    st.markdown("**Concepto de gastos**")
    if not lineas:
        st.info("No hay movimientos de egreso en el período. Registre gastos en Movimientos Bancarios.")
    else:
        data = []
        for l in lineas:
            ind_bs = round(l["total_bs"] * alicuota_valor, 2)
            data.append({
                "CONCEPTO DE GASTOS": l["nombre"],
                "Mes Acum. (Bs)": l["total_bs"],
                "Parte unidad (Bs)": ind_bs,
            })
        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "CONCEPTO DE GASTOS": st.column_config.TextColumn("Concepto", width="large"),
                "Mes Acum. (Bs)": st.column_config.NumberColumn("Mes Acum. (Bs)", format="%.2f"),
                "Parte unidad (Bs)": st.column_config.NumberColumn("Parte unidad (Bs)", format="%.2f"),
            },
        )

    # Totales
    total_comun_bs = round(total_gastos_bs * alicuota_valor, 2)
    reserva_bs = round(fondo_reserva_bs * alicuota_valor, 2)
    cuota_mes_calc = round(total_relacionado_bs * alicuota_valor, 2)

    st.markdown(
        f"""
        **TOTAL GASTOS COMUNES {mes_nombre}:** {total_gastos_bs:,.2f} (total) | **{total_comun_bs:,.2f}** (esta unidad)  
        **MÁS: FONDO DE RESERVA (10%):** {fondo_reserva_bs:,.2f} (total) | **{reserva_bs:,.2f}** (esta unidad)  
        **TOTAL GASTOS RELACIONADOS DEL MES:** {total_relacionado_bs:,.2f}  
        **CUOTA MES {mes_nombre} EN Bs:** **{cuota_mes_bs:,.2f}**  
        **Acumulado (Bs):** **{acumulado_bs:,.2f}**
        """
    )


for u in unidades_a_mostrar:
    render_recibo(u)

if unidades_a_mostrar:
    st.markdown("---")
    st.caption("Puede imprimir esta página (Ctrl+P / Cmd+P) para obtener el recibo en papel o PDF.")
