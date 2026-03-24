"""
Fase 6-A — Carga de saldo inicial histórico por unidad (Excel + revisión manual).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit Cloud (y algunos entornos) ejecutan la página con cwd/path distinto;
# asegurar la raíz del repo en sys.path para `import utils.*`.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd

from components.header import render_header
from config.supabase_client import get_supabase_client
from repositories.saldo_inicial_repository import SaldoInicialRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.parser_historico import (
    detectar_formato_excel,
    parsear_historico_excel,
    parsear_morosos_excel,
)
from utils.pdf_generator import monto_bs_a_usd

st.set_page_config(page_title="Saldo inicial histórico", page_icon="💰", layout="wide")
check_authentication()
render_header()

condominio_id = require_condominio()
tasa_cambio = float(st.session_state.get("tasa_cambio") or 0)


@st.cache_resource
def _saldo_repo() -> SaldoInicialRepository:
    return SaldoInicialRepository(get_supabase_client())


saldo_repo = _saldo_repo()

st.title("💰 Carga de saldo inicial histórico")
st.caption(
    "Registra el saldo pendiente de cada unidad "
    "antes de comenzar a operar el sistema. "
    "Este saldo se convierte en el punto de partida "
    "del historial contable."
)

# ═══════════════════════════════════════
# SECCIÓN 1: INSTRUCCIONES
# ═══════════════════════════════════════
with st.expander("📋 ¿Cómo funciona este módulo?", expanded=False):
    st.markdown(
        """
        **¿Qué hace este módulo?**
        Carga el saldo pendiente de cada unidad a partir de
        un archivo Excel histórico. El saldo registrado será
        el punto de partida del sistema.

        **Formatos aceptados (detección automática):**

        1. **Solventes** — hoja `Hoja1` (historial de pagos):
        - Columna A: Código de unidad (ej: A01, B05)
        - Columna B: Nombre del propietario
        - Columna C: Alícuota (%)
        - Saldo febrero 2026 (col. AE) y columna Diferencias (col. AL)

        2. **Morosos acumulados** — hoja `Hoja2`:
        - Columnas de cuotas mensuales (dic 2023 – feb 2026); el saldo es la **suma** de cuotas &gt; 0
        - Columna de meses sin pagar; sin columna de diferencias (carga directa)

        **¿Qué pasa con las unidades marcadas ⚠️?** (solo formato solventes)
        Se cargan con el valor del archivo pero quedan
        marcadas para revisión manual. El admin puede
        corregir el saldo desde esta misma pantalla.
        """
    )

# ═══════════════════════════════════════
# SECCIÓN 2: CARGA DEL ARCHIVO
# ═══════════════════════════════════════
st.subheader("📤 Paso 1 — Cargar archivo Excel")

archivo = st.file_uploader(
    "Selecciona el archivo de saldos históricos",
    type=["xlsx"],
    key="uploader_historico",
)

if archivo:
    contenido = archivo.read()

    with st.spinner("Detectando formato del archivo..."):
        formato = detectar_formato_excel(contenido)

    if formato == "desconocido":
        st.error(
            "❌ Formato de archivo no reconocido. "
            "Se aceptan dos formatos:\n"
            "- Archivo de solventes (hoja **Hoja1** con columna Diferencias)\n"
            "- Archivo de morosos acumulados (hoja **Hoja2**)"
        )
        st.stop()

    if formato == "solventes":
        st.info("📋 Formato detectado: **Solventes** (historial de pagos)")
        with st.spinner("Analizando archivo..."):
            resultado = parsear_historico_excel(contenido)
    else:
        st.info("📋 Formato detectado: **Morosos acumulados** (deuda acumulada sin pagos)")
        with st.spinner("Analizando archivo..."):
            resultado = parsear_morosos_excel(contenido)

    ok = resultado["ok"]
    revisar = resultado["revisar"]
    errores = resultado["errores"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total unidades", resultado["total"])
    col2.metric("✅ Listas para cargar", len(ok))
    col3.metric("⚠️ Requieren revisión", len(revisar))
    col4.metric("❌ Errores de parseo", len(errores))

    if errores:
        with st.expander("❌ Ver errores de parseo"):
            for e in errores:
                st.error(e)

    st.subheader("✅ Unidades listas para cargar")
    if ok:
        if formato == "morosos":
            df_ok = pd.DataFrame(
                [
                    {
                        "Código": u.codigo,
                        "Propietario": u.propietario,
                        "Alícuota": f"{u.indiviso_pct:.2f}%",
                        "Meses sin pagar": u.meses,
                        "Saldo acum. Bs.": f"Bs. {u.saldo_bs:,.2f}",
                        "Saldo USD": (
                            f"${monto_bs_a_usd(u.saldo_bs, tasa_cambio):,.2f}"
                            if tasa_cambio > 0
                            else "N/D"
                        ),
                    }
                    for u in ok
                ]
            )
        else:
            df_ok = pd.DataFrame(
                [
                    {
                        "Código": u.codigo,
                        "Propietario": u.propietario,
                        "Alícuota": f"{u.indiviso_pct:.2f}%",
                        "Saldo Bs.": f"Bs. {u.saldo_bs:,.2f}",
                        "Saldo USD": (
                            f"${monto_bs_a_usd(u.saldo_bs, tasa_cambio):,.2f}"
                            if tasa_cambio > 0
                            else "N/D"
                        ),
                    }
                    for u in ok
                ]
            )
        st.dataframe(df_ok, hide_index=True, use_container_width=True)
    else:
        st.info(
            "No hay filas listas para cargar."
            if formato == "morosos"
            else "No hay filas sin diferencia por encima del umbral."
        )

    if revisar:
        st.subheader("⚠️ Unidades con diferencia — revisar")
        st.caption(
            "Estas unidades se cargarán con el valor del archivo "
            "pero quedarán marcadas para revisión manual."
        )
        df_rev = pd.DataFrame(
            [
                {
                    "Código": u.codigo,
                    "Propietario": u.propietario,
                    "Saldo Bs.": f"Bs. {u.saldo_bs:,.2f}",
                    "Diferencia": f"Bs. {u.diferencia:+,.2f}",
                    "Nota": u.nota,
                }
                for u in revisar
            ]
        )
        st.dataframe(df_rev, hide_index=True, use_container_width=True)

    # ═══════════════════════════════════════
    # SECCIÓN 3: CONFIRMAR Y CARGAR
    # ═══════════════════════════════════════
    st.divider()
    st.subheader("📥 Paso 2 — Confirmar carga")

    todas = ok + revisar
    cn = st.session_state.get("condominio_nombre") or "—"
    if formato == "morosos":
        st.info(
            f"Se intentará registrar **{len(todas)} saldos** en el condominio **{cn}**.\n\n"
            f"- Carga directa (sin revisión por diferencias)\n"
            f"- Las unidades que **ya tengan** saldo inicial **no cambiarán el saldo** salvo que "
            f"marques la opción de forzar (solo actualiza **meses sin pagar** y **primer período**)."
        )
    else:
        st.info(
            f"Se registrarán **{len(todas)} saldos iniciales** "
            f"en el condominio **{cn}**.\n\n"
            f"- {len(ok)} unidades se cargarán directamente\n"
            f"- {len(revisar)} quedarán marcadas para revisión"
        )

    confirmar = st.checkbox(
        "Confirmo que revisé la previsualización y "
        "quiero registrar los saldos iniciales",
        key="confirmar_saldo_inicial",
    )

    forzar_update = st.checkbox(
        "Actualizar meses y período aunque ya tengan saldo",
        help="Úsalo para corregir datos de meses sin pagar y primer período en unidades "
        "que ya tienen saldo inicial cargado. No modifica el monto del saldo.",
        key="forzar_update_metadatos_saldo",
    )
    st.caption(
        "Si falla el guardado por columnas faltantes, ejecuta en Supabase el SQL de "
        "**scripts/fase6a_saldo_inicial_migration.sql** (bloque final 6-B) o "
        "**scripts/fase6b_meses_sin_pagar_migration.sql**."
    )

    if confirmar and todas:
        if st.button("🚀 Registrar saldos iniciales", type="primary", key="btn_registrar_saldos"):
            cargadas = 0
            meta_actualizadas = 0
            no_encontradas: list[str] = []
            omitidas: list[str] = []
            errores_db: list[str] = []

            progress = st.progress(0, text="Cargando...")
            n = len(todas)

            for i, unidad in enumerate(todas):
                try:
                    resultado_reg = saldo_repo.registrar_saldo_inicial(
                        condominio_id=condominio_id,
                        codigo_unidad=unidad.codigo,
                        saldo_bs=unidad.saldo_bs,
                        requiere_revision=unidad.requiere_revision,
                        nota=unidad.nota if unidad.requiere_revision else None,
                        meses_sin_pagar=int(unidad.meses or 0),
                        primer_periodo=unidad.primer_periodo,
                        forzar_update=forzar_update,
                    )
                    if resultado_reg.get("solo_metadatos"):
                        meta_actualizadas += 1
                    elif resultado_reg.get("omitida"):
                        omitidas.append(unidad.codigo)
                    elif resultado_reg.get("encontrada"):
                        cargadas += 1
                    else:
                        no_encontradas.append(unidad.codigo)
                except DatabaseError as e:
                    errores_db.append(f"{unidad.codigo}: {e}")

                progress.progress((i + 1) / n, text=f"Procesando {unidad.codigo}...")

            progress.progress(1.0, text="✅ Completado")
            partes = [f"✅ {cargadas} saldos iniciales registrados"]
            if meta_actualizadas:
                partes.append(
                    f"✅ {meta_actualizadas} unidades con meses / primer período actualizados (sin cambiar saldo)"
                )
            st.success(" | ".join(partes))
            if omitidas:
                st.warning(
                    f"⚠️ {len(omitidas)} unidades omitidas porque "
                    f"ya tenían saldo inicial cargado: "
                    f"{', '.join(omitidas)}"
                )
            if no_encontradas:
                st.warning(
                    f"⚠️ {len(no_encontradas)} unidades no "
                    f"encontradas en el sistema: "
                    f"{', '.join(no_encontradas)}\n\n"
                    f"Verifica que estas unidades estén "
                    f"registradas en el módulo de Unidades."
                )
            if errores_db:
                with st.expander("❌ Errores al guardar en base de datos"):
                    for e in errores_db:
                        st.error(e)

# ═══════════════════════════════════════
# SECCIÓN 4: REVISIÓN Y CORRECCIÓN MANUAL
# ═══════════════════════════════════════
st.divider()
st.subheader("🔧 Paso 3 — Corregir saldos marcados")

try:
    pendientes = saldo_repo.listar_requieren_revision(condominio_id)
except DatabaseError as e:
    pendientes = []
    st.error(f"❌ No se pudo cargar la lista de revisión: {e}")

if not pendientes:
    st.success("✅ No hay saldos pendientes de revisión")
else:
    st.warning(
        f"⚠️ {len(pendientes)} unidades requieren "
        f"revisión manual de su saldo inicial"
    )
    for u in pendientes:
        uid = int(u["id"])
        with st.expander(
            f"⚠️ {u['numero_unidad']} — "
            f"{u.get('propietario_nombre', 'Sin propietario')}"
        ):
            st.caption(u.get("nota_revision", "") or "")

            col1, col2 = st.columns([2, 1])
            with col1:
                nuevo_saldo = st.number_input(
                    "Saldo correcto (Bs.)",
                    min_value=0.0,
                    value=float(u.get("saldo") or 0),
                    step=0.01,
                    format="%.2f",
                    key=f"saldo_manual_{uid}",
                )
            with col2:
                eq_usd = (
                    monto_bs_a_usd(nuevo_saldo, tasa_cambio) if tasa_cambio > 0 else None
                )
                st.metric(
                    "Equivalente USD",
                    f"${eq_usd:,.2f}" if eq_usd is not None else "N/D",
                )

            nota_manual = st.text_input(
                "Nota de corrección",
                placeholder="Ej: Corregido según estado de cuenta del banco",
                key=f"nota_manual_{uid}",
            )

            if st.button(
                "✅ Confirmar saldo correcto",
                key=f"btn_manual_{uid}",
            ):
                try:
                    saldo_repo.actualizar_saldo_manual(
                        unidad_id=uid,
                        saldo_bs=nuevo_saldo,
                        nota=nota_manual,
                    )
                    st.success(
                        f"✅ Saldo de {u['numero_unidad']} "
                        f"actualizado a Bs. {nuevo_saldo:,.2f}"
                    )
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

# ═══════════════════════════════════════
# SECCIÓN 5: RESUMEN FINAL
# ═══════════════════════════════════════
st.divider()
st.subheader("📊 Resumen de saldos cargados")

try:
    resumen = saldo_repo.obtener_resumen_saldos(condominio_id, tasa_cambio=tasa_cambio)
except DatabaseError as e:
    resumen = None
    st.error(f"❌ No se pudo obtener el resumen: {e}")

if resumen and resumen.get("con_saldo_inicial", 0) > 0:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unidades con saldo", resumen["con_saldo_inicial"])
    c2.metric("Pendientes revisión", resumen["requieren_revision"])
    c3.metric("Total Bs.", f"Bs. {resumen['suma_total_bs']:,.2f}")
    c4.metric("Total USD", f"${resumen['suma_total_usd']:,.2f}")
elif resumen is not None:
    st.info("Aún no se han cargado saldos iniciales.")

# ═══════════════════════════════════════
# ACCESO AL REPORTE PDF (Reportes)
# ═══════════════════════════════════════
st.divider()
col_r1, col_r2 = st.columns([1, 1])
with col_r1:
    if st.button(
        "📊 Ver reporte de saldos acumulados",
        key="btn_ir_reportes",
        use_container_width=True,
    ):
        st.switch_page("pages/15_reportes.py")
with col_r2:
    st.caption(
        "Genera el PDF con el detalle completo "
        "de todos los saldos iniciales cargados "
        "(pestaña **Saldos acumulados iniciales** en Reportes)."
    )
