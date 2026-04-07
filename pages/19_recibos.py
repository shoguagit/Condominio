"""
Relación de Gastos (recibo por unidad).
Muestra cada concepto/gasto del mes como línea individual con su equivalente
en USD (tasa BCV de la fecha de pago) y la parte proporcional según alícuota.
"""
import streamlit as st
from datetime import date

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

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)


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

# ── Período ────────────────────────────────────────────────────────
periodo = st.text_input(
    "Período (YYYY-MM o YYYY-MM-01) *",
    value=str(st.session_state.get("mes_proceso") or "").strip(),
    placeholder="Ej: 2026-03",
)
ok_p, msg_p = validate_periodo(periodo)
if not ok_p:
    st.error(f"❌ {msg_p}")
    st.stop()
ok_db, msg_db, periodo_db = periodo_to_date_str(periodo)
if not ok_db or not periodo_db:
    st.error(f"❌ {msg_db}")
    st.stop()

try:
    y, m, _ = str(periodo_db).split("-")
    mes_nombre = MESES[int(m) - 1].upper()
    anio = y
except Exception:
    mes_nombre = periodo_db or ""
    anio = ""

# ── Condominio ─────────────────────────────────────────────────────
try:
    condominio = repo_cond.get_by_id(condominio_id)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()
if not condominio:
    st.error("Condominio no encontrado.")
    st.stop()

# ── Unidades ───────────────────────────────────────────────────────
try:
    unidades = repo_uni.get_all(condominio_id)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

unidades_con_alicuota = [u for u in unidades if float(u.get("indiviso_pct") or 0) > 0]
opts = ["— Todas las unidades —"]
uid_map: dict = {}
for u in unidades_con_alicuota:
    codigo = (u.get("codigo") or u.get("numero") or "").strip()
    prop = u.get("propietarios") or {}
    opts.append(f"{codigo} — {prop.get('nombre', '—')}")
    uid_map[opts[-1]] = u.get("id")

if len(opts) == 1:
    st.warning("No hay unidades con indiviso % en el módulo Unidades.")
    st.stop()

sel = st.selectbox("Unidad", options=opts)
todas = sel == "— Todas las unidades —"
unidades_a_mostrar = (
    unidades_con_alicuota
    if todas
    else [u for u in unidades_con_alicuota if u.get("id") == uid_map.get(sel)]
)
if not todas and not unidades_a_mostrar:
    st.warning("Seleccione una unidad.")
    st.stop()

# ── Egresos del período ────────────────────────────────────────────
try:
    movimientos = repo_mov.get_all(condominio_id, periodo=periodo_db)
except DatabaseError as e:
    st.error(f"❌ {e}")
    movimientos = []

egresos = [m for m in movimientos if m.get("tipo") == "egreso"]

# Construir líneas del recibo:
# - Si el movimiento tiene concepto_id → agrupar por concepto_id + nombre del catálogo
# - Si no tiene concepto_id → cada descripción es su propia línea (gastos importados)
# Clave de agrupación: (concepto_id, descripcion_normalizada)
lineas_dict: dict[tuple, dict] = {}
for m in egresos:
    cid = m.get("concepto_id")
    if cid is not None:
        # Gasto con concepto del catálogo → agrupar todos los del mismo concepto
        con = m.get("conceptos") or {}
        nombre = (con.get("nombre") or "Sin concepto").strip()
        key = (cid, None)
    else:
        # Gasto libre (importado o manual) → cada descripción es su propia línea
        nombre = (m.get("descripcion") or "Sin descripción").strip()
        key = (None, nombre)

    monto_bs = float(m.get("monto_bs") or 0)
    monto_usd = float(m.get("monto_usd") or 0)
    tasa = float(m.get("tasa_cambio") or 0)
    # Si no tiene monto_usd pero tiene tasa, calcularlo
    if monto_usd == 0 and tasa > 0:
        monto_usd = round(monto_bs / tasa, 4)

    if key not in lineas_dict:
        lineas_dict[key] = {
            "nombre": nombre,
            "total_bs": 0.0,
            "total_usd": 0.0,
            "tasa": tasa,
            "n": 0,
        }
    lineas_dict[key]["total_bs"]  += monto_bs
    lineas_dict[key]["total_usd"] += monto_usd
    lineas_dict[key]["n"] += 1
    # Para conceptos agrupados, la tasa pierde sentido; dejamos 0 como señal de "múltiples"
    if lineas_dict[key]["n"] > 1 and cid is not None:
        lineas_dict[key]["tasa"] = 0.0

lineas = sorted(
    lineas_dict.values(),
    key=lambda x: (-x["total_bs"], x["nombre"]),
)
lineas = [l for l in lineas if l["total_bs"] != 0]

total_gastos_bs  = round(sum(l["total_bs"]  for l in lineas), 2)
total_gastos_usd = round(sum(l["total_usd"] for l in lineas), 2)
fondo_reserva_bs  = round(total_gastos_bs  * 0.10, 2)
fondo_reserva_usd = round(total_gastos_usd * 0.10, 2)
total_relacionado_bs  = round(total_gastos_bs  + fondo_reserva_bs,  2)
total_relacionado_usd = round(total_gastos_usd + fondo_reserva_usd, 2)

# ── Cuotas calculadas (si ya se generaron) ─────────────────────────
try:
    cuotas_periodo = repo_proc.get_cuotas(condominio_id, periodo_db)
except DatabaseError:
    cuotas_periodo = []
cuotas_por_unidad = {c["unidad_id"]: c for c in cuotas_periodo}

cond_nombre  = (condominio.get("nombre") or "").strip()
cond_rif     = (condominio.get("numero_documento") or "").strip()
cond_email   = (condominio.get("email") or "").strip()
fecha_emision = date.today().strftime("%d-%m-%Y")


# ── Render por unidad ──────────────────────────────────────────────
def render_recibo(unidad: dict) -> None:
    uid          = unidad.get("id")
    codigo       = (unidad.get("codigo") or unidad.get("numero") or "").strip()
    prop         = unidad.get("propietarios") or {}
    nombre_prop  = (prop.get("nombre") or "—").strip()
    correo_prop  = (prop.get("correo") or "").strip()
    indiviso_pct = float(unidad.get("indiviso_pct") or 0)
    alicuota     = indiviso_pct / 100.0

    cuota_row = cuotas_por_unidad.get(uid)
    if cuota_row:
        cuota_mes_bs  = float(cuota_row.get("cuota_calculada_bs") or 0)
        acumulado_bs  = float(cuota_row.get("total_a_pagar_bs")   or 0)
    else:
        cuota_mes_bs  = round(total_relacionado_bs  * alicuota, 2)
        acumulado_bs  = round(float(unidad.get("saldo") or 0) + cuota_mes_bs, 2)

    cuota_mes_usd  = round(total_relacionado_usd * alicuota, 2)
    acumulado_usd  = round(cuota_mes_usd, 2)  # acumulado en USD ≈ cuota si no hay mora

    st.markdown("---")
    st.markdown(f"### Inmueble {codigo} — {nombre_prop}")

    # ── Encabezado ────────────────────────────────────────────────
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
        st.caption(f"Inmueble: {codigo}  |  Alícuota: {indiviso_pct:.2f}%")
        st.caption(
            f"Monto en USD: **{cuota_mes_usd:,.2f}**  |  "
            f"Acumulado USD: **{acumulado_usd:,.2f}**"
        )

    # ── Tabla de conceptos ────────────────────────────────────────
    st.markdown("**Concepto de gastos**")
    if not lineas:
        st.info(
            "No hay movimientos de egreso en el período. "
            "Registre gastos en Proceso Mensual → Gastos del período."
        )
    else:
        data = []
        for l in lineas:
            parte_usd = round(l["total_usd"] * alicuota, 4)
            parte_bs  = round(l["total_bs"]  * alicuota, 2)
            tasa_str  = f"{l['tasa']:,.2f}" if l["tasa"] > 0 else "—"
            data.append({
                "CONCEPTO DE GASTOS": l["nombre"],
                "Mes Acum. USD":      round(l["total_usd"], 2),
                "Parte (USD)":        round(parte_usd, 4),
                "Mes Acum. Bs.":      round(l["total_bs"],  2),
                "Parte (Bs.)":        parte_bs,
                "Tasa BCV":           tasa_str,
            })
        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True,
            column_config={
                "CONCEPTO DE GASTOS": st.column_config.TextColumn(width="large"),
                "Mes Acum. USD":      st.column_config.NumberColumn(format="%.2f"),
                "Parte (USD)":        st.column_config.NumberColumn(format="%.4f"),
                "Mes Acum. Bs.":      st.column_config.NumberColumn(format="%.2f"),
                "Parte (Bs.)":        st.column_config.NumberColumn(format="%.2f"),
                "Tasa BCV":           st.column_config.TextColumn(width="small"),
            },
        )

    # ── Totales ───────────────────────────────────────────────────
    tc_bs  = round(total_gastos_bs  * alicuota, 2)
    tc_usd = round(total_gastos_usd * alicuota, 4)
    fr_bs  = round(fondo_reserva_bs  * alicuota, 2)
    fr_usd = round(fondo_reserva_usd * alicuota, 4)

    st.markdown(
        f"""
| | **Total mes** | **Esta unidad** |
|---|---|---|
| **TOTAL GASTOS COMUNES {mes_nombre}** | Bs. {total_gastos_bs:,.2f} / USD {total_gastos_usd:,.2f} | **Bs. {tc_bs:,.2f} / USD {tc_usd:,.4f}** |
| **MÁS: FONDO DE RESERVA (10%)** | Bs. {fondo_reserva_bs:,.2f} / USD {fondo_reserva_usd:,.2f} | **Bs. {fr_bs:,.2f} / USD {fr_usd:,.4f}** |
| **TOTAL GASTOS RELACIONADOS** | Bs. {total_relacionado_bs:,.2f} / USD {total_relacionado_usd:,.2f} | |
| **CUOTA MES {mes_nombre} EN DIVISAS** | | **USD {cuota_mes_usd:,.2f}** |
| **CUOTA MES {mes_nombre} EN Bs.** | | **Bs. {cuota_mes_bs:,.2f}** |
| **Acumulado (Bs.)** | | **Bs. {acumulado_bs:,.2f}** |
        """
    )


for u in unidades_a_mostrar:
    render_recibo(u)

if unidades_a_mostrar:
    st.markdown("---")
    st.caption("Puede imprimir esta página (Ctrl+P / Cmd+P) para obtener el recibo.")
