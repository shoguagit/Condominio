"""
Categorías de Gastos — configuración por condominio.

Sección 1: Subcategorías activas (agrupadas por categoría padre)
Sección 2: Palabras clave por subcategoría (edición con pills)
Sección 3: Probar clasificación automática en tiempo real
"""
import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.categoria_gasto_repository import CategoriaGastoRepository
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from components.header import render_header
from components.breadcrumb import render_breadcrumb

st.set_page_config(page_title="Categorías de Gastos", page_icon="🏷️", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Categorías de Gastos")

condominio_id = require_condominio()


@st.cache_resource
def get_repo() -> CategoriaGastoRepository:
    return CategoriaGastoRepository(get_supabase_client())


repo = get_repo()

# ── Inicialización idempotente del seed ────────────────────────────────────────
if not st.session_state.get(f"_cats_init_{condominio_id}"):
    with st.spinner("Inicializando categorías base…"):
        repo.inicializar_subcategorias_condominio(condominio_id)
    st.session_state[f"_cats_init_{condominio_id}"] = True

st.markdown("## 🏷️ Categorías de Gastos")
st.caption(
    "Configura las subcategorías y palabras clave que el sistema usa para "
    "clasificar automáticamente cada gasto en Redistribución de Gastos."
)
st.info(
    "**Tres secciones en esta página (desplázate hacia arriba si solo ves 2 y 3):** "
    "**Sección 1** — lista de subcategorías por categoría padre · "
    "**Sección 2** — palabras clave · "
    "**Sección 3** — prueba de clasificación (el resultado aparece al escribir en el campo).",
    icon="ℹ️",
)

# ── Cargar datos ───────────────────────────────────────────────────────────────
try:
    categorias  = repo.listar_categorias()
    subcats     = repo.listar_subcategorias(condominio_id)
    palabras    = repo.listar_palabras_clave(condominio_id)
except DatabaseError as e:
    st.error(f"❌ {e}")
    st.stop()

cat_by_id   = {c["id"]: c for c in categorias}
subcat_by_id = {s["id"]: s for s in subcats}

# Agrupar subcategorías por categoría padre
subcats_por_cat: dict[str, list[dict]] = {}
for s in subcats:
    cat_info = s.get("categorias_gasto") or {}
    key = cat_info.get("codigo", "OTROS")
    subcats_por_cat.setdefault(key, []).append(s)

# Agrupar palabras clave por subcategoría
palabras_por_sub: dict[int, list[dict]] = {}
for p in palabras:
    palabras_por_sub.setdefault(p["subcategoria_id"], []).append(p)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — Subcategorías activas
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 📂 Sección 1 — Subcategorías activas")
st.caption("Subcategorías agrupadas por categoría padre. Agrega las propias del condominio.")

for cat in categorias:
    ccodigo = cat["codigo"]
    cnombre = cat["nombre"]
    subs_cat = subcats_por_cat.get(ccodigo, [])

    with st.expander(f"**{cnombre}** — {len(subs_cat)} subcategorías", expanded=True):
        if subs_cat:
            # Tabla de subcategorías
            cols = st.columns([3, 1, 1, 1])
            cols[0].markdown("**Subcategoría**")
            cols[1].markdown("**Palabras clave**")
            cols[2].markdown("**Sistema**")
            cols[3].markdown("**Acciones**")
            st.markdown(
                "<hr style='margin:4px 0 8px;border-color:#D6EAF8'>",
                unsafe_allow_html=True,
            )
            for s in sorted(subs_cat, key=lambda x: x.get("orden", 99)):
                c0, c1, c2, c3 = st.columns([3, 1, 1, 1])
                n_palabras = len(palabras_por_sub.get(s["id"], []))
                c0.markdown(f"**{s['nombre']}**  \n`{s['codigo']}`")
                c1.markdown(f"🔑 {n_palabras}")
                c2.markdown("🔒 Sistema" if s.get("es_sistema") else "✏️ Custom")
                if not s.get("es_sistema"):
                    if c3.button("🗑", key=f"del_sub_{s['id']}", help="Eliminar subcategoría"):
                        try:
                            repo.eliminar_subcategoria(s["id"])
                            st.success(f"✅ '{s['nombre']}' eliminada.")
                            st.rerun()
                        except DatabaseError as e:
                            st.error(f"❌ {e}")
        else:
            st.caption("Sin subcategorías para esta categoría.")

        # Formulario inline para crear nueva subcategoría
        with st.form(f"nueva_subcat_{ccodigo}", clear_on_submit=True):
            st.markdown(f"**＋ Nueva subcategoría bajo {cnombre}**")
            col_n, col_o = st.columns([3, 1])
            nombre_new  = col_n.text_input("Nombre *", key=f"ns_nombre_{ccodigo}", placeholder="Ej: Gastos legales")
            orden_new   = col_o.number_input("Orden", min_value=1, max_value=99, value=99, key=f"ns_orden_{ccodigo}")
            if st.form_submit_button("Guardar subcategoría", type="primary"):
                if not nombre_new.strip():
                    st.error("❌ El nombre es obligatorio.")
                else:
                    try:
                        repo.crear_subcategoria(
                            condominio_id=condominio_id,
                            categoria_id=cat["id"],
                            nombre=nombre_new.strip(),
                            orden=int(orden_new),
                        )
                        st.success(f"✅ Subcategoría '{nombre_new.strip()}' creada.")
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — Palabras clave por subcategoría
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🔑 Sección 2 — Palabras clave por subcategoría")
st.caption(
    "Cada palabra clave ayuda al sistema a identificar a qué subcategoría pertenece un gasto. "
    "Puedes agregar o eliminar palabras para ajustar la clasificación automática."
)

if not subcats:
    st.warning("No hay subcategorías. Créalas en la Sección 1.")
else:
    # Selector de subcategoría
    opts_sub = {
        f"{(s.get('categorias_gasto') or {}).get('nombre', '—')} › {s['nombre']}": s
        for s in sorted(subcats, key=lambda x: (
            (x.get("categorias_gasto") or {}).get("orden", 99),
            x.get("orden", 99),
        ))
    }
    sel_label = st.selectbox("Seleccionar subcategoría", options=list(opts_sub.keys()), key="pk_sel_sub")
    sub_sel   = opts_sub.get(sel_label)

    if sub_sel:
        pks = palabras_por_sub.get(sub_sel["id"], [])

        st.markdown(f"**Palabras clave para: {sub_sel['nombre']}**")

        # Pills / chips de palabras existentes
        if pks:
            cols_per_row = 6
            rows = [pks[i:i + cols_per_row] for i in range(0, len(pks), cols_per_row)]
            for row in rows:
                pill_cols = st.columns(len(row) + (cols_per_row - len(row)))
                for idx, pk in enumerate(row):
                    with pill_cols[idx]:
                        st.markdown(
                            f"<span style='background:#EBF5FB;color:#1B4F72;"
                            f"padding:3px 10px;border-radius:12px;font-size:12px;"
                            f"font-weight:600;display:inline-block;margin:2px 0'>"
                            f"{pk['palabra']}</span>",
                            unsafe_allow_html=True,
                        )
                        if st.button("×", key=f"del_pk_{pk['id']}", help=f"Eliminar '{pk['palabra']}'"):
                            try:
                                repo.eliminar_palabra_clave(pk["id"])
                                st.success(f"✅ '{pk['palabra']}' eliminada.")
                                st.rerun()
                            except DatabaseError as e:
                                st.error(f"❌ {e}")
        else:
            st.caption("Sin palabras clave. Agrega la primera.")

        # Formulario agregar palabra
        with st.form(f"agregar_pk_{sub_sel['id']}", clear_on_submit=True):
            col_inp, col_btn = st.columns([4, 1])
            nueva_palabra = col_inp.text_input(
                "Nueva palabra clave",
                placeholder="Ej: corpoelec, limpieza, gerente…",
                key=f"pk_new_{sub_sel['id']}",
            )
            if col_btn.form_submit_button("Agregar", type="primary"):
                if not nueva_palabra.strip():
                    st.error("❌ Escribe una palabra.")
                else:
                    try:
                        repo.agregar_palabra_clave(condominio_id, sub_sel["id"], nueva_palabra.strip())
                        st.success(f"✅ '{nueva_palabra.strip().lower()}' agregada.")
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — Probar clasificación
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### 🧪 Sección 3 — Probar clasificación automática")
st.caption("Escribe una descripción de gasto para ver qué subcategoría sugeriría el sistema.")

texto_prueba = st.text_input(
    "Descripción de gasto",
    placeholder='Ej: "Ferretería Abraham Saba Arena y Cemento" o "Nómina Gerente Marzo 2026"',
    key="prueba_clasif",
)

if not texto_prueba.strip():
    st.caption(
        "👆 Escribe arriba una descripción de gasto; aquí aparecerá la **subcategoría sugerida**, "
        "el **código** y la **confianza** del clasificador."
    )
else:
    with st.spinner("Clasificando…"):
        sugerencia = repo.sugerir_subcategoria(
            condominio_id, texto_prueba, subcats=subcats, palabras=palabras
        )

    if sugerencia:
        confianza = sugerencia["confianza"]
        color = "#28B463" if confianza >= 0.5 else "#E67E22" if confianza > 0 else "#7F8C8D"
        st.markdown(
            f"<div style='background:#F4F9FD;border-left:4px solid {color};"
            f"padding:12px 16px;border-radius:6px;margin-top:8px'>"
            f"<span style='font-size:13px;font-weight:700;color:#1C2833'>"
            f"Sugerencia: {sugerencia['categoria_nombre']} › {sugerencia['subcategoria_nombre']}"
            f"</span><br>"
            f"<span style='font-size:12px;color:#5D6D7E'>"
            f"Código: <code>{sugerencia['subcategoria_codigo']}</code> &nbsp;·&nbsp; "
            f"Confianza: <b style='color:{color}'>{confianza:.0%}</b>"
            f"</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("ℹ️ No se encontró ninguna coincidencia. Se asignaría 'Sin clasificar'.")
