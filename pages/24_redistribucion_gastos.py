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
from repositories.categoria_gasto_repository import CategoriaGastoRepository
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
        CategoriaGastoRepository(client),
    )

repo_cond, repo_mov, repo_proc, repo_agr, repo_uni, repo_cat = get_repos()


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


def _inicializar_estado(
    periodo: str,
    egresos: list[dict],
    guardado: list[dict] | None,
    subcats: list[dict],
    palabras: list[dict],
) -> None:
    """Inicializa/restaura los dicts de asignación, destino y categoría en session_state."""
    sk_asig = _sk("asig",  periodo)   # {mov_id: grupo_nombre}
    sk_dest = _sk("dest",  periodo)   # {grupo_nombre: {recibo, balance}}
    sk_cat  = _sk("cat",   periodo)   # {grupo_nombre: subcategoria_codigo}

    if sk_asig in st.session_state:
        return  # ya inicializado

    if guardado:
        # Restaurar desde DB
        asig: dict[int, str]    = {}
        dest: dict[str, dict]   = {}
        cats: dict[str, str]    = {}
        for g in guardado:
            for mid in g.get("movimiento_ids") or []:
                asig[int(mid)] = g["nombre"]
            dest[g["nombre"]] = {
                "recibo":  bool(g.get("recibo",  True)),
                "balance": bool(g.get("balance", True)),
            }
            cats[g["nombre"]] = g.get("subcategoria_codigo", "OTROS_SIN_CLASIFICAR")
        st.session_state[sk_asig] = asig
        st.session_state[sk_dest] = dest
        st.session_state[sk_cat]  = cats
    else:
        # Auto-sugerir agrupaciones y categorías
        descs     = [m.get("descripcion") or "" for m in egresos]
        sugeridos = sugerir_grupos(descs)
        asig = {m["id"]: sugeridos.get(m.get("descripcion") or "", m.get("descripcion") or "")
                for m in egresos}
        dest = {g: {"recibo": True, "balance": True} for g in set(asig.values())}

        # Sugerir categoría para cada grupo usando sus descripciones originales
        cats = {}
        for grupo_nombre in set(asig.values()):
            # Concatenar todas las descripciones de este grupo para mejor contexto
            descs_grupo = " ".join(
                m.get("descripcion") or "" for m in egresos
                if asig.get(m["id"]) == grupo_nombre
            )
            sug = repo_cat.sugerir_subcategoria(
                0, descs_grupo, subcats=subcats, palabras=palabras
            )
            cats[grupo_nombre] = sug["subcategoria_codigo"] if sug else "OTROS_SIN_CLASIFICAR"

        st.session_state[sk_asig] = asig
        st.session_state[sk_dest] = dest
        st.session_state[sk_cat]  = cats


def _calcular_grupos(
    egresos: list[dict], asig: dict, dest: dict, cats: dict | None = None
) -> list[dict]:
    """Consolida egresos por grupo y adjunta flags de destino y subcategoría."""
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
        subcat_codigo = (cats or {}).get(nombre, "OTROS_SIN_CLASIFICAR")
        grupos.append({
            **g,
            "recibo":             d["recibo"],
            "balance":            d["balance"],
            "subcategoria_codigo": subcat_codigo,
        })

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

# Inicialización idempotente de categorías del condominio
if not st.session_state.get(f"_cats_init_{condominio_id}"):
    repo_cat.inicializar_subcategorias_condominio(condominio_id)
    st.session_state[f"_cats_init_{condominio_id}"] = True

# Cargar datos de categorías para sugerencias (una sola vez por sesión/período)
@st.cache_data(ttl=300, show_spinner=False)
def _cargar_cats(cid: int):
    try:
        sc = repo_cat.listar_subcategorias(cid)
        pk = repo_cat.listar_palabras_clave(cid)
        return sc, pk
    except Exception:
        return [], []

_subcats_all, _palabras_all = _cargar_cats(condominio_id)

# Mapa código → label display: "Categoría › Subcategoría"
_subcat_opts: dict[str, str] = {}
for _s in _subcats_all:
    _ci = _s.get("categorias_gasto") or {}
    _subcat_opts[_s["codigo"]] = f"{_ci.get('nombre', '—')} › {_s['nombre']}"

_inicializar_estado(periodo_db, egresos, guardado, _subcats_all, _palabras_all)

sk_asig = _sk("asig", periodo_db)
sk_dest = _sk("dest", periodo_db)
sk_cat  = _sk("cat",  periodo_db)
asig_state: dict[int, str]       = st.session_state[sk_asig]
dest_state: dict[str, dict]      = st.session_state[sk_dest]
cat_state:  dict[str, str]       = st.session_state.setdefault(sk_cat, {})

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# PASO 1 — AGRUPACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    "### 📋 Paso 1 — Agrupar conceptos",
    help="Edita la columna **Grupo** para consolidar ítems similares en un solo concepto.",
)

_, col_btn = st.columns([5, 2])
with col_btn:
    if st.button("🔁 Re-sugerir grupos automáticamente", use_container_width=True):
        descs = [e.get("descripcion") or "" for e in egresos]
        sugeridos = sugerir_grupos(descs)
        for e in egresos:
            asig_state[e["id"]] = sugeridos.get(e.get("descripcion") or "", e.get("descripcion") or "")
        # Reiniciar destinos y categorías para nuevos grupos
        for g in set(asig_state.values()):
            if g not in dest_state:
                dest_state[g] = {"recibo": True, "balance": True}
            if g not in cat_state:
                descs_g = " ".join(
                    e.get("descripcion") or "" for e in egresos
                    if asig_state.get(e["id"]) == g
                )
                sug = repo_cat.sugerir_subcategoria(
                    0, descs_g, subcats=_subcats_all, palabras=_palabras_all
                )
                cat_state[g] = sug["subcategoria_codigo"] if sug else "OTROS_SIN_CLASIFICAR"
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

# Conteo coherente con la tabla (después del editor — mismo dato que la lista de 15)
_n_items_now  = len(egresos)
_n_grupos_now = len(set(asig_state.values()))
_n_diff_now   = _n_items_now - _n_grupos_now

st.caption(
    f"{_n_items_now} ítems → **{_n_grupos_now} grupos** distintos "
    f"(**{_n_diff_now} ítems** comparten grupo con otro; "
    f"no hay movimientos faltantes). Edita **Grupo** para renombrar o separar."
)

# Sincronizar dest_state y cat_state: añadir nuevos grupos, mantener flags
grupos_nuevos = set(asig_state.values())
for gn in grupos_nuevos:
    if gn not in dest_state:
        dest_state[gn] = {"recibo": True, "balance": True}
    if gn not in cat_state:
        descs_g = " ".join(
            e.get("descripcion") or "" for e in egresos
            if asig_state.get(e["id"]) == gn
        )
        sug = repo_cat.sugerir_subcategoria(
            0, descs_g, subcats=_subcats_all, palabras=_palabras_all
        )
        cat_state[gn] = sug["subcategoria_codigo"] if sug else "OTROS_SIN_CLASIFICAR"

# Grupos consolidados (preview)
grupos_consolidados = _calcular_grupos(egresos, asig_state, dest_state, cat_state)

# Ítems que explican (N ítems − N grupos): por cada grupo con varios movimientos,
# todos menos el primero (orden por ID) — son las filas “adicionales” por consolidación.
_por_grupo: dict[str, list[dict]] = {}
for _m in sorted(egresos, key=lambda x: int(x.get("id") or 0)):
    _gn = str(asig_state.get(_m["id"], "—")).strip()
    _por_grupo.setdefault(_gn, []).append(_m)

_filas_diff: list[dict] = []
for _rows in _por_grupo.values():
    if len(_rows) <= 1:
        continue
    for _r in _rows[1:]:
        _filas_diff.append({
            "ID":          int(_r["id"]),
            "Descripción": (str(_r.get("descripcion") or ""))[:220],
            "Grupo":       str(asig_state.get(_r["id"], "—")).strip(),
            "Bs.":         round(float(_r.get("monto_bs") or 0), 2),
            "USD":         round(float(_r.get("monto_usd") or 0), 2),
        })

with st.expander(
    f"📋 Solo estos {_n_diff_now} ítems (los que “sobran” al consolidar) — busca el **ID** en la tabla de arriba",
    expanded=bool(_filas_diff),
):
    st.caption(
        f"**No faltan movimientos:** los {_n_diff_now} ítems de abajo son los que **repiten** nombre de "
        "grupo con otro. En cada grupo solo mostramos aquí los que no son el **primer ID** (orden numérico). "
        "Si quieres **119 líneas distintas** en el recibo, pon un **Grupo** distinto a cada uno."
    )
    if _filas_diff:
        st.dataframe(
            pd.DataFrame(_filas_diff),
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID":          st.column_config.NumberColumn(width="small"),
                "Descripción": st.column_config.TextColumn(width="large"),
                "Grupo":       st.column_config.TextColumn(width="large"),
                "Bs.":         st.column_config.NumberColumn(format="%.2f"),
                "USD":         st.column_config.NumberColumn(format="%.2f"),
            },
        )
    else:
        st.info("No hay diferencia: un grupo distinto por cada ítem.")

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
        "Grupo":      g["nombre"],
        "Categoría":  cat_state.get(g["nombre"], "OTROS_SIN_CLASIFICAR"),
        "Total Bs.":  round(g["total_bs"],  2),
        "Total USD":  round(g["total_usd"], 2),
        "📄 Recibo":  dest_state.get(g["nombre"], {}).get("recibo",  True),
        "📊 Balance": dest_state.get(g["nombre"], {}).get("balance", True),
    }
    for g in grupos_consolidados
])

# Opciones para el selector de subcategoría
_subcat_codigos  = list(_subcat_opts.keys())
_subcat_displays = list(_subcat_opts.values())

edited_dest = st.data_editor(
    df_dest,
    column_config={
        "Grupo":       st.column_config.TextColumn(disabled=True, width="large"),
        "Categoría":   st.column_config.SelectboxColumn(
            options=_subcat_codigos,
            help="Subcategoría del gasto. El sistema pre-rellena con su sugerencia automática.",
            width="medium",
        ),
        "Total Bs.":   st.column_config.NumberColumn(disabled=True, format="%.2f", width="small"),
        "Total USD":   st.column_config.NumberColumn(disabled=True, format="%.2f", width="small"),
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

# Actualizar dest_state y cat_state con ediciones
for _, row in edited_dest.iterrows():
    nombre = str(row["Grupo"])
    dest_state[nombre] = {
        "recibo":  bool(row["📄 Recibo"]),
        "balance": bool(row["📊 Balance"]),
    }
    cat_state[nombre] = str(row.get("Categoría") or "OTROS_SIN_CLASIFICAR")

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
# GUARDAR
# ═══════════════════════════════════════════════════════════════════════════════
col_save, col_estado = st.columns([2, 5])
with col_save:
    if st.button("💾 Guardar agrupaciones", type="primary", use_container_width=True):
        grupos_para_db = _calcular_grupos(egresos, asig_state, dest_state, cat_state)
        try:
            repo_agr.upsert(condominio_id, periodo_db, grupos_para_db)
            st.success("✅ Agrupaciones guardadas.")
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")
with col_estado:
    if guardado is not None:
        st.success(
            f"✅ Agrupaciones guardadas — **{len(guardado)} grupos** para {mes_nombre} {anio}."
        )
    else:
        st.info("📝 Sin agrupaciones guardadas aún. Guarda antes de generar los PDFs.")

st.markdown("---")

# Grupos actualizados con destinos para las previsualizaciones
grupos_final    = _calcular_grupos(egresos, asig_state, dest_state, cat_state)
grupos_recibo   = [g for g in grupos_final if dest_state.get(g["nombre"], {}).get("recibo",  True)]
grupos_balance  = [g for g in grupos_final if dest_state.get(g["nombre"], {}).get("balance", True)]

# Carga unidades y cuotas (compartido entre previsualización y generación)
try:
    _unidades_todas   = repo_uni.get_all(condominio_id)
    _unidades_validas = [u for u in _unidades_todas if float(u.get("indiviso_pct") or 0) > 0]
except Exception:
    _unidades_validas = []

try:
    _cuotas_periodo   = repo_proc.get_cuotas(condominio_id, periodo_db)
except Exception:
    _cuotas_periodo   = []
_cuotas_por_unidad = {c["unidad_id"]: c for c in _cuotas_periodo}

# Totales de conceptos para Recibo
if grupos_recibo:
    _tr_total_bs  = sum(g["total_bs"]  for g in grupos_recibo)
    _tr_total_usd = sum(g["total_usd"] for g in grupos_recibo)
    _tr_fr_bs     = round(_tr_total_bs  * 0.10, 2)
    _tr_fr_usd    = round(_tr_total_usd * 0.10, 2)
    _tr_rel_bs    = round(_tr_total_bs  + _tr_fr_bs,  2)
    _tr_rel_usd   = round(_tr_total_usd + _tr_fr_usd, 2)
else:
    _tr_total_bs = _tr_total_usd = _tr_fr_bs = _tr_fr_usd = _tr_rel_bs = _tr_rel_usd = 0.0


def _datos_recibo_unidad(u: dict) -> dict:
    """Calcula el dict de datos del recibo para una unidad."""
    from utils.recibo_pdf import preparar_datos_recibo
    uid      = u.get("id")
    alic_dec = float(u.get("indiviso_pct") or 0) / 100.0
    cuota_r  = _cuotas_por_unidad.get(uid)
    if cuota_r:
        cuota_bs  = float(cuota_r.get("cuota_calculada_bs") or 0)
        saldo_ant = float(cuota_r.get("saldo_anterior_bs")  or u.get("saldo") or 0)
    else:
        cuota_bs  = round(_tr_rel_bs * alic_dec, 2)
        saldo_ant = float(u.get("saldo") or 0)
    cuota_usd   = round(_tr_rel_usd * alic_dec, 2)
    saldo_nuevo = round(saldo_ant + cuota_bs, 2)
    return preparar_datos_recibo(
        condominio=condominio, unidad=u,
        mes_nombre=mes_nombre, anio=anio,
        lineas_gasto=grupos_recibo,
        total_gastos_bs=_tr_total_bs,   total_gastos_usd=_tr_total_usd,
        fondo_reserva_bs=_tr_fr_bs,     fondo_reserva_usd=_tr_fr_usd,
        total_relacionado_bs=_tr_rel_bs, total_relacionado_usd=_tr_rel_usd,
        cuota_mes_bs=cuota_bs,          cuota_mes_usd=cuota_usd,
        saldo_anterior_bs=saldo_ant,    pagos_mes_bs=0.0,
        saldo_nuevo_bs=saldo_nuevo,     meses_acum=1,
    )


def _render_preview_recibo(d: dict) -> None:
    """Renderiza en Streamlit la vista previa de un recibo (sin PDF)."""
    alic = float(d.get("alicuota_fmt", "0").replace(",", ".") or 0)

    # Encabezado
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(
            f"**{d['org']}** &nbsp;·&nbsp; RIF: {d['rif']}",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"**Propietario:** {d['owner']}  \n"
            f"**Inmueble:** {d['inmueble']} &nbsp;·&nbsp; **Alícuota:** {d['alicuota_fmt']}%  \n"
            f"**Correo:** {d['email'] or '—'}  \n"
            f"**Emisión:** {d['emision']}  \n"
            f"**Monto USD:** ${d['monto_usd']:,.2f} &nbsp;·&nbsp; "
            f"**Acumulado:** ${d['acum_usd']:,.2f}",
        )

    # Tabla de ítems
    items = d.get("items") or []
    if items:
        rows = []
        for it in items:
            rows.append({
                "CONCEPTO DE GASTOS": it["conc"],
                "Mes US$":            round(float(it["bs"]),  2),
                "Acum. 1":            round(float(it["usd"]), 2),
            })
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
            column_config={
                "CONCEPTO DE GASTOS": st.column_config.TextColumn(width="large"),
                "Mes US$":            st.column_config.NumberColumn(format="$%.2f"),
                "Acum. 1":            st.column_config.NumberColumn(format="$%.2f"),
            },
        )

    # Totales
    for tot in (d.get("totals") or []):
        is_cuota = "CUOTA" in str(tot.get("lbl", "")).upper()
        label = f"**{tot['lbl']}**" if is_cuota else tot["lbl"]
        bs_v  = f"${float(tot['bs']):,.2f}"  if tot.get("bs")  is not None else ""
        usd_v = f"${float(tot['usd']):,.2f}" if tot.get("usd") is not None else ""
        if is_cuota:
            st.markdown(
                f"<div style='background:#2E74B5;color:white;padding:4px 8px;"
                f"border-radius:4px;margin:2px 0;font-weight:bold'>"
                f"{tot['lbl']} — Edificio: {bs_v} | Esta unidad: {usd_v}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption(f"{tot['lbl']}: edificio {bs_v} | unidad {usd_v}")

    # Saldos
    with st.expander("📊 Saldos acumulados", expanded=False):
        for s in (d.get("saldos") or []):
            edif = f"Bs. {float(s['edif']):,.2f}" if s.get("edif") is not None else "—"
            st.caption(f"**{s['lbl']}**: {edif}")


def _render_preview_balance(gb: list[dict]) -> None:
    """Renderiza en Streamlit la vista previa del balance mensual."""
    total_usd = sum(float(g["total_usd"]) for g in gb)
    total_bs  = sum(float(g["total_bs"])  for g in gb)
    fr_usd    = round(total_usd * 0.10, 2)
    fr_bs     = round(total_bs  * 0.10, 2)

    rows = [{"#": i + 1,
             "CONCEPTO": g["nombre"],
             "Total Bs.": round(float(g["total_bs"]),  2),
             "Total USD": round(float(g["total_usd"]), 2)}
            for i, g in enumerate(gb)]
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_config={
            "#":          st.column_config.NumberColumn(width="small"),
            "CONCEPTO":   st.column_config.TextColumn(width="large"),
            "Total Bs.":  st.column_config.NumberColumn(format="%.2f"),
            "Total USD":  st.column_config.NumberColumn(format="$%.2f"),
        },
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Gastos Bs.",          f"Bs. {total_bs:,.2f}")
    c2.metric("Total Gastos USD",          f"${total_usd:,.2f}")
    c3.metric(f"Fondo Reserva 10% USD",    f"${fr_usd:,.2f}")
    st.markdown(
        f"**Total Gastos Relacionados:** Bs. {total_bs + fr_bs:,.2f} &nbsp;|&nbsp; "
        f"USD ${total_usd + fr_usd:,.2f}",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PASO 3A — BALANCE: VISTA PREVIA + GENERAR PDF
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📊 Paso 3A — Balance Mensual")

if not grupos_balance:
    st.warning("Ningún grupo está marcado para **Balance**. Activa la columna 📊 en el Paso 2.")
else:
    with st.expander(
        f"👁️ Vista previa Balance — {len(grupos_balance)} conceptos", expanded=False
    ):
        _render_preview_balance(grupos_balance)

    if st.button("📥 Generar Balance PDF", use_container_width=False, key="btn_bal_pdf"):
        from utils.balance_pdf import generar_balance_pdf
        with st.spinner("Generando PDF..."):
            try:
                pdf_bytes = generar_balance_pdf(
                    condominio_nombre=condominio.get("nombre") or "",
                    condominio_rif=condominio.get("numero_documento") or "",
                    mes_nombre=mes_nombre, anio=anio,
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

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# PASO 3B — RECIBOS: VISTA PREVIA POR UNIDAD + GENERAR PDF
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📄 Paso 3B — Recibos por Unidad")

if not grupos_recibo:
    st.warning("Ningún grupo está marcado para **Recibo**. Activa la columna 📄 en el Paso 2.")
elif not _unidades_validas:
    st.warning("No hay unidades con alícuota registradas.")
else:
    # ── Selector de unidad ──────────────────────────────────────────────────
    opts_uni = {}
    for u in _unidades_validas:
        codigo = (u.get("codigo") or u.get("numero") or "").strip()
        prop   = u.get("propietarios") or {}
        label  = f"{codigo} — {(prop.get('nombre') or '—')}"
        opts_uni[label] = u

    col_sel, col_prev = st.columns([3, 2])
    with col_sel:
        sel_uni = st.selectbox(
            "Seleccionar unidad para previsualizar",
            options=list(opts_uni.keys()),
            key="prev_uni_sel",
        )
    with col_prev:
        st.markdown("<br>", unsafe_allow_html=True)
        mostrar_prev = st.button("👁️ Ver vista previa", key="btn_prev_recibo")

    # ── Vista previa de la unidad seleccionada ──────────────────────────────
    unidad_sel = opts_uni.get(sel_uni)
    if mostrar_prev and unidad_sel:
        st.session_state["_prev_recibo_uid"] = unidad_sel.get("id")

    if st.session_state.get("_prev_recibo_uid"):
        uid_prev = st.session_state["_prev_recibo_uid"]
        u_prev   = next((u for u in _unidades_validas if u.get("id") == uid_prev), None)
        if u_prev:
            codigo_prev = (u_prev.get("codigo") or u_prev.get("numero") or "").strip()
            with st.expander(
                f"👁️ Vista previa — Inmueble {codigo_prev}", expanded=True
            ):
                try:
                    d_prev = _datos_recibo_unidad(u_prev)
                    _render_preview_recibo(d_prev)

                    # PDF solo para esta unidad
                    from utils.recibo_pdf import generar_recibos_pdf as _gen_pdf
                    if st.button(
                        f"📥 Generar PDF solo {codigo_prev}",
                        key=f"btn_pdf_uno_{uid_prev}",
                    ):
                        with st.spinner("Generando..."):
                            pdf_u = _gen_pdf([d_prev])
                            st.session_state["_pdf_uno_bytes"] = pdf_u
                            st.session_state["_pdf_uno_nombre"] = (
                                f"Recibo_{codigo_prev}_{mes_nombre}_{anio}.pdf"
                            )

                    if st.session_state.get("_pdf_uno_bytes"):
                        st.download_button(
                            label=f"⬇️ Descargar recibo {codigo_prev}",
                            data=st.session_state["_pdf_uno_bytes"],
                            file_name=st.session_state.get("_pdf_uno_nombre", "Recibo.pdf"),
                            mime="application/pdf",
                            key="dl_pdf_uno",
                        )
                except Exception as e:
                    st.error(f"❌ Error al generar vista previa: {e}")

    st.markdown("---")

    # ── Generar TODOS los recibos ───────────────────────────────────────────
    st.markdown(f"**Generar todos los recibos — {len(_unidades_validas)} unidades**")
    if st.button(
        f"📥 Generar PDF todos los recibos ({len(_unidades_validas)} unidades)",
        key="btn_pdf_todos",
    ):
        with st.spinner(f"Generando {len(_unidades_validas)} recibos..."):
            try:
                from utils.recibo_pdf import generar_recibos_pdf as _gen_pdfs
                todos_datos = [_datos_recibo_unidad(u) for u in _unidades_validas]
                pdf_todos   = _gen_pdfs(todos_datos)
                st.session_state["_recibos_pdf_bytes"] = pdf_todos
                st.session_state["_recibos_pdf_nombre"] = (
                    f"Recibos_{mes_nombre}_{anio}.pdf"
                )
            except Exception as e:
                st.error(f"❌ {e}")

    if st.session_state.get("_recibos_pdf_bytes"):
        st.download_button(
            label="⬇️ Descargar todos los recibos (PDF)",
            data=st.session_state["_recibos_pdf_bytes"],
            file_name=st.session_state.get("_recibos_pdf_nombre", "Recibos.pdf"),
            mime="application/pdf",
            key="dl_recibos",
        )
