import re
from datetime import datetime

import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.condominio_repository import CondominioRepository
from repositories.estado_cuenta_repository import EstadoCuentaRepository
from repositories.reporte_repository import ReporteRepository
from repositories.reporte_saldos_repository import ReporteSaldosRepository
from repositories.unidad_repository import UnidadRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.reporte_saldos_pdf import generar_reporte_saldos_pdf
from utils.reportes_pdf import (
    pdf_balance_general,
    pdf_estado_cuenta_individual,
    pdf_libro_cobros,
    pdf_libro_gastos,
    pdf_libro_solventes,
    pdf_morosidad,
    pdf_origen_aplicacion,
)
from utils.validators import date_periodo_to_mm_yyyy, periodo_to_date_str, validate_periodo
from components.header import render_header
from components.breadcrumb import render_breadcrumb

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Reportes")

condominio_id = require_condominio()


@st.cache_resource
def _repos():
    c = get_supabase_client()
    return (
        CondominioRepository(c),
        UnidadRepository(c),
        ReporteRepository(c),
        ReporteSaldosRepository(c),
        EstadoCuentaRepository(c),
    )


repo_cond, repo_uni, repo_rep, repo_saldos, repo_ec = _repos()

st.markdown("## 📊 Reportes y estados de cuenta")

try:
    condominio = repo_cond.get_by_id(condominio_id)
except DatabaseError as e:
    st.error(str(e))
    st.stop()
if not condominio:
    st.error("Condominio no encontrado.")
    st.stop()


def tasa_efectiva() -> float:
    ts = float(st.session_state.get("tasa_cambio") or 0)
    if ts > 0:
        return ts
    return float(condominio.get("tasa_cambio") or 0)


def periodo_ui_a_db(periodo_str: str) -> tuple[bool, str, str | None]:
    ok_p, msg_p = validate_periodo(periodo_str)
    if not ok_p:
        return False, msg_p, None
    ok_db, msg_db, periodo_db = periodo_to_date_str(periodo_str)
    if not ok_db or not periodo_db:
        return False, msg_db, None
    return True, "", periodo_db


try:
    unidades_list = repo_uni.get_all(condominio_id, solo_activos=True)
except DatabaseError as e:
    st.error(str(e))
    unidades_list = []


def label_unidad(u: dict) -> str:
    cod = (u.get("codigo") or u.get("numero") or "").strip()
    return f"{cod} (id {u.get('id')})"


uid_options = {label_unidad(u): int(u["id"]) for u in unidades_list}

tasa = tasa_efectiva()
if tasa <= 0:
    st.caption("⚠️ Sin tasa de cambio en sesión ni en condominio: USD en PDFs saldrá en 0.")


def _render_saldos_acumulados_iniciales_section() -> None:
    """
    Colocada **arriba** de las pestañas para que siempre sea visible (sin desplazar al final).
    """
    st.subheader("💰 Saldos acumulados iniciales")
    st.caption(
        "Reporte de saldos históricos cargados como punto "
        "de partida del sistema. Incluye resumen y detalle "
        "por unidad ordenado por código."
    )

    if st.button("📄 Generar PDF — Saldos acumulados", key="btn_saldos_pdf"):
        try:
            unidades = repo_saldos.obtener_unidades_con_saldo(condominio_id, tasa)
            if not unidades:
                st.session_state.pop("saldos_acum_pdf", None)
                st.session_state.pop("saldos_acum_fn", None)
                st.warning("No hay saldos iniciales cargados.")
            else:
                config = repo_saldos.obtener_config_condominio(condominio_id)
                logo_b = repo_ec.obtener_logo_bytes(config.get("logo_url"))
                cn = (config.get("nombre") or condominio.get("nombre") or "condominio").strip()
                pdf_bytes = generar_reporte_saldos_pdf(
                    condominio_nombre=cn,
                    condominio_rif=config.get("rif") or "—",
                    logo_bytes=logo_b,
                    tasa_cambio=tasa,
                    unidades=unidades,
                    fecha_generacion=datetime.now().strftime("%d/%m/%Y %H:%M"),
                )
                fn_safe = re.sub(r"[^\w\-]+", "_", cn)[:60].strip("_") or "condominio"
                fn = f"saldos_acumulados_{fn_safe}_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.session_state["saldos_acum_pdf"] = pdf_bytes
                st.session_state["saldos_acum_fn"] = fn
                st.success("PDF generado. Usa el botón de descarga.")
        except DatabaseError as e:
            st.session_state.pop("saldos_acum_pdf", None)
            st.session_state.pop("saldos_acum_fn", None)
            st.error(str(e))

    if st.session_state.get("saldos_acum_pdf"):
        st.download_button(
            label="⬇️ Descargar PDF — Saldos acumulados",
            data=st.session_state["saldos_acum_pdf"],
            file_name=st.session_state.get("saldos_acum_fn") or "saldos_acumulados.pdf",
            mime="application/pdf",
            key="download_saldos_pdf",
        )

    try:
        resumen_rep = repo_saldos.obtener_resumen_saldos_reporte(condominio_id, tasa)
    except DatabaseError:
        resumen_rep = None
    if resumen_rep and resumen_rep.get("total_unidades", 0) > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Unidades", resumen_rep["total_unidades"])
        c2.metric("Total Bs.", f"Bs. {resumen_rep['suma_total_bs']:,.2f}")
        c3.metric("Total USD", f"${resumen_rep['suma_total_usd']:,.2f}")


st.caption(
    "Debajo: **PDF de saldos iniciales** (histórico). Luego, el resto de reportes por pestañas."
)
with st.container(border=True):
    _render_saldos_acumulados_iniciales_section()

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "Estado de cuenta individual",
        "Morosidad",
        "Balance general",
        "Libro de cobros",
        "Libro de gastos",
        "Origen y aplicación",
        "Libro de solventes",
    ]
)

# --- Tab 1 ---
with tab1:
    st.markdown("### Estado de cuenta individual")
    if not unidades_list:
        st.warning("No hay unidades activas.")
    else:
        sel = st.selectbox("Unidad", options=list(uid_options.keys()), key="rep_ec_unidad")
        per_str = st.text_input(
            "Período (MM/YYYY)",
            value=str(st.session_state.get("mes_proceso") or "").strip(),
            key="rep_ec_per",
        )
        ok, msg, periodo_db = periodo_ui_a_db(per_str)
        if not ok:
            st.error(msg)
        else:
            uid = uid_options[sel]
            mm_yyyy = date_periodo_to_mm_yyyy(periodo_db)
            estado = repo_rep.get_estado_cuenta(uid, periodo_db, condominio_id)
            hist = repo_rep.get_historico_unidad(uid, periodo_db, 3)
            pdf_bytes = pdf_estado_cuenta_individual(
                condominio, mm_yyyy, periodo_db, tasa, estado, hist
            )
            fn = f"estado_cuenta_{uid}_{mm_yyyy.replace('/', '_')}.pdf"
            st.download_button(
                "📥 Descargar PDF",
                data=pdf_bytes,
                file_name=fn,
                mime="application/pdf",
                key="dl_ec",
            )

# --- Tab 2 ---
with tab2:
    st.markdown("### Reporte de morosidad")
    per_str = st.text_input(
        "Período (MM/YYYY)",
        value=str(st.session_state.get("mes_proceso") or "").strip(),
        key="rep_mor_per",
    )
    filtro = st.selectbox(
        "Filtro",
        options=["todos", "morosos", "parciales"],
        format_func=lambda x: {
            "todos": "Todos con saldo > 0",
            "morosos": "Solo morosos",
            "parciales": "Solo parciales",
        }[x],
        key="rep_mor_filtro",
    )
    ok, msg, periodo_db = periodo_ui_a_db(per_str)
    if not ok:
        st.error(msg)
    else:
        mm_yyyy = date_periodo_to_mm_yyyy(periodo_db)
        filas = repo_rep.get_morosidad(condominio_id, periodo_db, filtro)
        n_activas = len(unidades_list)
        pdf_bytes = pdf_morosidad(condominio, mm_yyyy, tasa, filas, max(n_activas, 1))
        st.download_button(
            "📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"morosidad_{mm_yyyy.replace('/', '_')}.pdf",
            mime="application/pdf",
            key="dl_mor",
        )

# --- Tab 3 ---
with tab3:
    st.markdown("### Balance general")
    per_str = st.text_input(
        "Período (MM/YYYY)",
        value=str(st.session_state.get("mes_proceso") or "").strip(),
        key="rep_bal_per",
    )
    ok, msg, periodo_db = periodo_ui_a_db(per_str)
    if not ok:
        st.error(msg)
    else:
        mm_yyyy = date_periodo_to_mm_yyyy(periodo_db)
        bal = repo_rep.get_balance(condominio_id, periodo_db)
        pdf_bytes = pdf_balance_general(condominio, mm_yyyy, tasa, bal)
        st.download_button(
            "📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"balance_{mm_yyyy.replace('/', '_')}.pdf",
            mime="application/pdf",
            key="dl_bal",
        )

# --- Tab 4 ---
with tab4:
    st.markdown("### Libro de cobros")
    per_str = st.text_input(
        "Período (MM/YYYY)",
        value=str(st.session_state.get("mes_proceso") or "").strip(),
        key="rep_cob_per",
    )
    ok, msg, periodo_db = periodo_ui_a_db(per_str)
    if not ok:
        st.error(msg)
    else:
        mm_yyyy = date_periodo_to_mm_yyyy(periodo_db)
        pagos = repo_rep.get_libro_cobros(condominio_id, periodo_db)
        pdf_bytes = pdf_libro_cobros(condominio, mm_yyyy, tasa, pagos)
        st.download_button(
            "📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"libro_cobros_{mm_yyyy.replace('/', '_')}.pdf",
            mime="application/pdf",
            key="dl_cob",
        )

# --- Tab 5 ---
with tab5:
    st.markdown("### Libro de gastos")
    per_str = st.text_input(
        "Período (MM/YYYY)",
        value=str(st.session_state.get("mes_proceso") or "").strip(),
        key="rep_gas_per",
    )
    ok, msg, periodo_db = periodo_ui_a_db(per_str)
    if not ok:
        st.error(msg)
    else:
        mm_yyyy = date_periodo_to_mm_yyyy(periodo_db)
        movs = repo_rep.get_libro_gastos(condominio_id, periodo_db)
        pdf_bytes = pdf_libro_gastos(condominio, mm_yyyy, tasa, movs)
        st.download_button(
            "📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"libro_gastos_{mm_yyyy.replace('/', '_')}.pdf",
            mime="application/pdf",
            key="dl_gas",
        )

# --- Tab 6 ---
with tab6:
    st.markdown("### Origen y aplicación de fondos")
    per_str = st.text_input(
        "Período (MM/YYYY)",
        value=str(st.session_state.get("mes_proceso") or "").strip(),
        key="rep_oa_per",
    )
    ok, msg, periodo_db = periodo_ui_a_db(per_str)
    if not ok:
        st.error(msg)
    else:
        mm_yyyy = date_periodo_to_mm_yyyy(periodo_db)
        oa = repo_rep.get_origen_aplicacion(condominio_id, periodo_db)
        pdf_bytes = pdf_origen_aplicacion(condominio, mm_yyyy, tasa, oa)
        st.download_button(
            "📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"origen_aplicacion_{mm_yyyy.replace('/', '_')}.pdf",
            mime="application/pdf",
            key="dl_oa",
        )

# --- Tab 7 ---
with tab7:
    st.markdown("### Libro de solventes")
    per_str = st.text_input(
        "Período (MM/YYYY)",
        value=str(st.session_state.get("mes_proceso") or "").strip(),
        key="rep_sol_per",
    )
    ok, msg, periodo_db = periodo_ui_a_db(per_str)
    if not ok:
        st.error(msg)
    else:
        mm_yyyy = date_periodo_to_mm_yyyy(periodo_db)
        sol = repo_rep.get_solventes(condominio_id, periodo_db)
        n_activas = len(unidades_list)
        pdf_bytes = pdf_libro_solventes(condominio, mm_yyyy, tasa, sol, max(n_activas, 1))
        st.download_button(
            "📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"libro_solventes_{mm_yyyy.replace('/', '_')}.pdf",
            mime="application/pdf",
            key="dl_sol",
        )
