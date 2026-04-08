"""
Redistribución de Gastos — agrupa conceptos similares y asigna destino.

Flujo de 3 pasos:
  1. Revisión y agrupación: asigna cada ítem crudo a un "concepto consolidado".
     El sistema sugiere agrupaciones automáticas (similitud de tokens).
  2. Destino: para cada grupo, el administrador elige si va al Recibo del
     propietario, al Balance Mensual, a ambos, o a ninguno.
  3. Generar: descarga PDF de Balance y/o desencadena los Recibos (PDF por unidad).
"""

from __future__ import annotations

import difflib
import json
import re
from typing import Any

import pandas as pd
import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.condominio_repository import CondominioRepository
from repositories.movimiento_repository import MovimientoRepository
from repositories.proceso_repository import ProcesoMensualRepository
from repositories.agrupacion_gasto_repository import AgrupacionGastoRepository
from repositories.unidad_repository import UnidadRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_periodo, periodo_to_date_str
from components.header import render_header
from components.breadcrumb import render_breadcrumb

st.set_page_config(page_title="Redistribución de Gastos", page_icon="🔄", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Redistribución de Gastos")

condominio_id = require_condominio()

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)

# ── Repositorios ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return (
        CondominioRepository(client),
        MovimientoRepository(client),
        ProcesoMensualRepository(client),
        AgrupacionGastoRepository(client),
        UnidadRepository(client),
    )

repo_cond, repo_mov, repo_proc, repo_agr, repo_uni = get_repos()


# ── Algoritmo de agrupación automática ────────────────────────────────────────
_MESES_NOISE = {
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
}
_AÑOS_NOISE  = {"2023", "2024", "2025", "2026", "2027"}
_PALABRAS_NOISE = _MESES_NOISE | _AÑOS_NOISE | {
    "usd", "bsf", "bs", "de", "la", "el", "y", "en", "para", "los", "las",
    "del", "al", "con", "por", "mas", "menos", "pago", "pag", "fact",
    "factura", "nd", "ref", "nro", "no", "num",
}


def _tokens(text: str) -> frozenset[str]:
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    return frozenset(w for w in words if w not in _PALABRAS_NOISE and len(w) > 2)


def _similitud(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    # Jaccard sobre tokens exactos
    jaccard = len(a & b) / len(a | b)
    # SequenceMatcher sobre cadenas normalizadas (maneja typos)
    sa = " ".join(sorted(a))
    sb = " ".join(sorted(b))
    seq = difflib.SequenceMatcher(None, sa, sb).ratio()
    return max(jaccard, seq * 0.8)


def sugerir_grupos(
    descripciones: list[str], threshold: float = 0.55
) -> dict[str, str]:
    """Devuelve {descripcion: nombre_grupo_sugerido}."""
    tok_map: dict[str, frozenset] = {d: _tokens(d) for d in descripciones}
    grupos: dict[str, list[str]] = {}   # nombre_grupo → [descs]
    asignados: dict[str, str]    = {}   # desc → nombre_grupo

    for desc in descripciones:
        if desc in asignados:
            continue
        toks = tok_map[desc]
        mejor: str | None = None
        mejor_sim: float  = threshold

        for nombre_grupo in grupos:
            g_toks = tok_map.get(nombre_grupo, _tokens(nombre_grupo))
            s = _similitud(toks, g_toks)
            if s > mejor_sim:
                mejor_sim = s
                mejor = nombre_grupo

        if mejor:
            grupos[mejor].append(desc)
            asignados[desc] = mejor
        else:
            grupos[desc] = [desc]
            asignados[desc] = desc

    return asignados


# ── Helpers de estado ─────────────────────────────────────────────────────────

def _sk(key: str, periodo: str) -> str:
    """Clave de session_state namespaced por período."""
    return f"_agr_{key}_{periodo}"


def _inicializar_estado(periodo: str, egresos: list[dict], guardado: list[dict] | None) -> None:
    """Inicializa/restaura los dicts de asignación y destino en session_state."""
    sk_asig = _sk("asig", periodo)    # {mov_id: grupo_nombre}
    sk_dest = _sk("dest", periodo)    # {grupo_nombre: {recibo, balance}}

    if sk_asig in st.session_state:
        return  # ya inicializado

    if guardado:
        # Restaurar desde DB
        asig: dict[int, str] = {}
        dest: dict[str, dict] = {}
        for g in guardado:
            for mid in g.get("movimiento_ids") or []:
                asig[int(mid)] = g["nombre"]
            dest[g["nombre"]] = {
                "recibo":  bool(g.get("recibo",  True)),
                "balance": bool(g.get("balance", True)),
            }
        st.session_state[sk_asig] = asig
        st.session_state[sk_dest] = dest
    else:
        # Auto-sugerir
        descs = [m.get("descripcion") or "" for m in egresos]
        sugeridos = sugerir_grupos(descs)
        asig = {m["id"]: sugeridos.get(m.get("descripcion") or "", m.get("descripcion") or "")
                for m in egresos}
        dest = {g: {"recibo": True, "balance": True} for g in set(asig.values())}
        st.session_state[sk_asig] = asig
        st.session_state[sk_dest] = dest


def _calcular_grupos(egresos: list[dict], asig: dict, dest: dict) -> list[dict]:
    """Consolida egresos por grupo y adjunta flags de destino."""
    acc: dict[str, dict] = {}
    for m in egresos:
        nombre = asig.get(m["id"], m.get("descripcion") or "—")
        if nombre not in acc:
            acc[nombre] = {"nombre": nombre, "movimiento_ids": [], "total_bs": 0.0, "total_usd": 0.0}
        acc[nombre]["movimiento_ids"].append(m["id"])
        acc[nombre]["total_bs"]  += float(m.get("monto_bs")  or 0)
        acc[nombre]["total_usd"] += float(m.get("monto_usd") or 0)

    grupos: list[dict] = []
    for nombre, g in acc.items():
        d = dest.get(nombre, {"recibo": True, "balance": True})
        grupos.append({**g, "recibo": d["recibo"], "balance": d["balance"]})

    return sorted(grupos, key=lambda x: -x["total_bs"])


# ── UI principal ──────────────────────────────────────────────────────────────
st.markdown("## 🔄 Redistribución de Gastos")
st.caption(
    "Agrupa los gastos del período en conceptos consolidados, "
    "asigna cada grupo al **Recibo del propietario** y/o al **Balance Mensual**, "
    "y genera ambos reportes en PDF."
)

# Período
col_p, _ = st.columns([2, 5])
with col_p:
    periodo = st.text_input(
        "Período *",
        value=str(st.session_state.get("mes_proceso") or "").strip(),
        placeholder="Ej: 2026-03",
        key="agr_periodo",
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

# Condominio
try:
    condominio = repo_cond.get_by_id(condominio_id)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()
if not condominio:
    st.error("Condominio no encontrado.")
    st.stop()

# Egresos
try:
    movimientos = repo_mov.get_all(condominio_id, periodo=periodo_db)
except DatabaseError as e:
    st.error(f"❌ {e}")
    movimientos = []

egresos = [m for m in movimientos if m.get("tipo") == "egreso"]
if not egresos:
    st.warning(
        "No hay egresos registrados para este período. "
        "Carga los gastos primero en **Proceso Mensual**."
    )
    st.stop()

# Agrupación guardada (si existe)
try:
    guardado = repo_agr.get(condominio_id, periodo_db)
except Exception:
    guardado = None

_inicializar_estado(periodo_db, egresos, guardado)

sk_asig = _sk("asig", periodo_db)
sk_dest = _sk("dest", periodo_db)
asig_state: dict[int, str]       = st.session_state[sk_asig]
dest_state: dict[str, dict]      = st.session_state[sk_dest]

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# PASO 1 — AGRUPACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    "### 📋 Paso 1 — Agrupar conceptos",
    help="Edita la columna **Grupo** para consolidar ítems similares en un solo concepto.",
)

col_info, col_btn = st.columns([5, 2])
with col_info:
    grupos_actuales = sorted(set(asig_state.values()))
    st.caption(
        f"{len(egresos)} ítems → **{len(grupos_actuales)} grupos** detectados. "
        "Edita la columna **Grupo** para renombrar o consolidar."
    )
with col_btn:
    if st.button("🔁 Re-sugerir grupos automáticamente", use_container_width=True):
        descs = [e.get("descripcion") or "" for e in egresos]
        sugeridos = sugerir_grupos(descs)
        for e in egresos:
            asig_state[e["id"]] = sugeridos.get(e.get("descripcion") or "", e.get("descripcion") or "")
        # Reiniciar destinos para nuevos grupos
        for g in set(asig_state.values()):
            if g not in dest_state:
                dest_state[g] = {"recibo": True, "balance": True}
        st.rerun()

# Tabla editable (ítems raw)
df_raw = pd.DataFrame([
    {
        "ID": m["id"],
        "Descripción original": m.get("descripcion") or "—",
        "Bs.":  round(float(m.get("monto_bs")  or 0), 2),
        "USD":  round(float(m.get("monto_usd") or 0), 2),
        "Grupo": asig_state.get(m["id"], m.get("descripcion") or "—"),
    }
    for m in egresos
])

# Lista de grupos existentes para mostrar como hints
grupos_lista = sorted(set(asig_state.values()))

edited_df = st.data_editor(
    df_raw,
    column_config={
        "ID":                    st.column_config.NumberColumn(disabled=True, width="small"),
        "Descripción original":  st.column_config.TextColumn(disabled=True, width="large"),
        "Bs.":                   st.column_config.NumberColumn(disabled=True, format="%.2f", width="small"),
        "USD":                   st.column_config.NumberColumn(disabled=True, format="%.2f", width="small"),
        "Grupo":                 st.column_config.TextColumn(
            width="large",
            help="Escribe el nombre del grupo consolidado. Ítems con el mismo nombre se suman.",
        ),
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    key=f"editor_raw_{periodo_db}",
)

# Actualizar asig_state con lo que editó el usuario
for _, row in edited_df.iterrows():
    asig_state[int(row["ID"])] = str(row["Grupo"] or "—").strip()

# Sincronizar dest_state: añadir nuevos grupos, mantener flags de los existentes
grupos_nuevos = set(asig_state.values())
for gn in grupos_nuevos:
    if gn not in dest_state:
        dest_state[gn] = {"recibo": True, "balance": True}

# Grupos consolidados (preview)
grupos_consolidados = _calcular_grupos(egresos, asig_state, dest_state)

with st.expander("👁️ Vista previa de grupos consolidados", expanded=False):
    df_grupos = pd.DataFrame([
        {
            "Grupo": g["nombre"],
            "N ítems": len(g["movimiento_ids"]),
            "Total Bs.": round(g["total_bs"],  2),
            "Total USD": round(g["total_usd"], 2),
        }
        for g in grupos_consolidados
    ])
    st.dataframe(
        df_grupos,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Total Bs.": st.column_config.NumberColumn(format="%.2f"),
            "Total USD": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    total_bs  = sum(g["total_bs"]  for g in grupos_consolidados)
    total_usd = sum(g["total_usd"] for g in grupos_consolidados)
    st.markdown(
        f"**Total período:** Bs. {total_bs:,.2f}  |  USD {total_usd:,.2f}"
    )


st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# PASO 2 — DESTINO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    "### 🎯 Paso 2 — Asignar destino",
    help=(
        "**📄 Recibo**: el concepto aparecerá en el recibo que recibe el propietario.\n\n"
        "**📊 Balance**: el concepto aparecerá en el balance mensual administrativo."
    ),
)

st.info(
    "Activa/desactiva las columnas **📄 Recibo** y **📊 Balance** según "
    "corresponda para cada grupo. Los cambios se guardan con el botón al final.",
    icon="💡",
)

# Colores por destino para ayudar a leer la tabla rápido
# Verde claro = solo recibo | Azul claro = solo balance | Morado claro = ambos | Gris = ninguno

df_dest = pd.DataFrame([
    {
        "Grupo": g["nombre"],
        "Total Bs.": round(g["total_bs"],  2),
        "Total USD": round(g["total_usd"], 2),
        "📄 Recibo":  dest_state.get(g["nombre"], {}).get("recibo",  True),
        "📊 Balance": dest_state.get(g["nombre"], {}).get("balance", True),
    }
    for g in grupos_consolidados
])

edited_dest = st.data_editor(
    df_dest,
    column_config={
        "Grupo":       st.column_config.TextColumn(disabled=True, width="large"),
        "Total Bs.":   st.column_config.NumberColumn(disabled=True, format="%.2f"),
        "Total USD":   st.column_config.NumberColumn(disabled=True, format="%.2f"),
        "📄 Recibo":   st.column_config.CheckboxColumn(
            default=True,
            help="¿Este concepto aparece en el recibo del propietario?",
        ),
        "📊 Balance":  st.column_config.CheckboxColumn(
            default=True,
            help="¿Este concepto aparece en el balance mensual administrativo?",
        ),
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    key=f"editor_dest_{periodo_db}",
)

# Actualizar dest_state con ediciones
for _, row in edited_dest.iterrows():
    nombre = str(row["Grupo"])
    dest_state[nombre] = {
        "recibo":  bool(row["📄 Recibo"]),
        "balance": bool(row["📊 Balance"]),
    }

# Resumen visual de destinos
col_r, col_b, col_a, col_n = st.columns(4)
cnt_r = sum(1 for g in grupos_consolidados if dest_state.get(g["nombre"], {}).get("recibo",  True))
cnt_b = sum(1 for g in grupos_consolidados if dest_state.get(g["nombre"], {}).get("balance", True))
cnt_a = sum(1 for g in grupos_consolidados
            if dest_state.get(g["nombre"], {}).get("recibo", True)
            and dest_state.get(g["nombre"], {}).get("balance", True))
cnt_n = sum(1 for g in grupos_consolidados
            if not dest_state.get(g["nombre"], {}).get("recibo", True)
            and not dest_state.get(g["nombre"], {}).get("balance", True))

col_r.metric("📄 Solo/ambos Recibo",  cnt_r)
col_b.metric("📊 Solo/ambos Balance", cnt_b)
col_a.metric("📄📊 Ambos",           cnt_a)
col_n.metric("⬜ Ninguno",            cnt_n)

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# GUARDAR + PASO 3 — GENERAR
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### 💾 Guardar y generar reportes")

col_save, col_bal, col_rec = st.columns([2, 2, 2])

# ── Guardar en DB ──────────────────────────────────────────────────────────
with col_save:
    if st.button("💾 Guardar agrupaciones", type="primary", use_container_width=True):
        grupos_para_db = _calcular_grupos(egresos, asig_state, dest_state)
        try:
            repo_agr.upsert(condominio_id, periodo_db, grupos_para_db)
            st.success("✅ Agrupaciones guardadas correctamente.")
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")

# ── PDF Balance ────────────────────────────────────────────────────────────
with col_bal:
    if st.button("📊 Generar Balance PDF", use_container_width=True):
        from utils.balance_pdf import generar_balance_pdf
        grupos_balance = [
            g for g in _calcular_grupos(egresos, asig_state, dest_state)
            if dest_state.get(g["nombre"], {}).get("balance", True)
        ]
        if not grupos_balance:
            st.warning("Ningún grupo está marcado para Balance.")
        else:
            with st.spinner("Generando Balance..."):
                try:
                    pdf_bytes = generar_balance_pdf(
                        condominio_nombre=condominio.get("nombre") or "",
                        condominio_rif=condominio.get("numero_documento") or "",
                        mes_nombre=mes_nombre,
                        anio=anio,
                        grupos=grupos_balance,
                        pie_titular=condominio.get("pie_pagina_titular") or "",
                        pie_cuerpo=condominio.get("pie_pagina_cuerpo") or "",
                    )
                    st.session_state["_balance_pdf_bytes"] = pdf_bytes
                    st.session_state["_balance_pdf_nombre"] = f"Balance_{mes_nombre}_{anio}.pdf"
                except Exception as e:
                    st.error(f"❌ {e}")

    if st.session_state.get("_balance_pdf_bytes"):
        st.download_button(
            label="⬇️ Descargar Balance PDF",
            data=st.session_state["_balance_pdf_bytes"],
            file_name=st.session_state.get("_balance_pdf_nombre", "Balance.pdf"),
            mime="application/pdf",
            key="dl_balance",
        )

# ── PDF Recibos ────────────────────────────────────────────────────────────
with col_rec:
    if st.button("📄 Generar Recibos PDF", use_container_width=True):
        from utils.recibo_pdf import preparar_datos_recibo, generar_recibos_pdf

        grupos_recibo = [
            g for g in _calcular_grupos(egresos, asig_state, dest_state)
            if dest_state.get(g["nombre"], {}).get("recibo", True)
        ]
        if not grupos_recibo:
            st.warning("Ningún grupo está marcado para Recibo.")
        else:
            with st.spinner("Generando recibos..."):
                try:
                    unidades = repo_uni.get_all(condominio_id)
                    unidades_validas = [u for u in unidades if float(u.get("indiviso_pct") or 0) > 0]

                    try:
                        cuotas_periodo = repo_proc.get_cuotas(condominio_id, periodo_db)
                    except Exception:
                        cuotas_periodo = []
                    cuotas_por_unidad = {c["unidad_id"]: c for c in cuotas_periodo}

                    total_bs  = sum(g["total_bs"]  for g in grupos_recibo)
                    total_usd = sum(g["total_usd"] for g in grupos_recibo)
                    fr_bs  = round(total_bs  * 0.10, 2)
                    fr_usd = round(total_usd * 0.10, 2)
                    tot_rel_bs  = round(total_bs  + fr_bs,  2)
                    tot_rel_usd = round(total_usd + fr_usd, 2)

                    todos_datos: list[dict] = []
                    for u in unidades_validas:
                        uid      = u.get("id")
                        alic_pct = float(u.get("indiviso_pct") or 0) / 100.0
                        cuota_r  = cuotas_por_unidad.get(uid)

                        if cuota_r:
                            cuota_bs = float(cuota_r.get("cuota_calculada_bs") or 0)
                            saldo_ant = float(cuota_r.get("saldo_anterior_bs")  or u.get("saldo") or 0)
                        else:
                            cuota_bs  = round(tot_rel_bs * alic_pct, 2)
                            saldo_ant = float(u.get("saldo") or 0)

                        cuota_usd  = round(tot_rel_usd * alic_pct, 4)
                        saldo_nuevo = round(saldo_ant + cuota_bs, 2)

                        datos = preparar_datos_recibo(
                            condominio=condominio,
                            unidad=u,
                            mes_nombre=mes_nombre,
                            anio=anio,
                            lineas_gasto=grupos_recibo,
                            total_gastos_bs=total_bs,
                            total_gastos_usd=total_usd,
                            fondo_reserva_bs=fr_bs,
                            fondo_reserva_usd=fr_usd,
                            total_relacionado_bs=tot_rel_bs,
                            total_relacionado_usd=tot_rel_usd,
                            cuota_mes_bs=cuota_bs,
                            cuota_mes_usd=cuota_usd,
                            saldo_anterior_bs=saldo_ant,
                            pagos_mes_bs=0.0,
                            saldo_nuevo_bs=saldo_nuevo,
                            meses_acum=1,
                        )
                        todos_datos.append(datos)

                    pdf_bytes = generar_recibos_pdf(todos_datos)
                    st.session_state["_recibos_pdf_bytes"] = pdf_bytes
                    st.session_state["_recibos_pdf_nombre"] = f"Recibos_{mes_nombre}_{anio}.pdf"
                except Exception as e:
                    st.error(f"❌ {e}")

    if st.session_state.get("_recibos_pdf_bytes"):
        st.download_button(
            label="⬇️ Descargar Recibos PDF",
            data=st.session_state["_recibos_pdf_bytes"],
            file_name=st.session_state.get("_recibos_pdf_nombre", "Recibos.pdf"),
            mime="application/pdf",
            key="dl_recibos",
        )

# ── Indicador de agrupaciones guardadas ───────────────────────────────────
st.markdown("---")
if guardado is not None:
    st.success(
        f"✅ Este período tiene agrupaciones guardadas con **{len(guardado)} grupos**. "
        "Los Recibos y el Balance usarán estos grupos al generarse."
    )
else:
    st.info(
        "📝 No hay agrupaciones guardadas para este período. "
        "Al generar los PDFs se usará la distribución actual de la sesión. "
        "Usa **💾 Guardar agrupaciones** para persistirlas."
    )
