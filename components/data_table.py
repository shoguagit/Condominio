"""
Tabla de datos con búsqueda, paginación y selección de fila.
Estilos modernos (borderless, hover, skeleton, estado vacío) vía components.styles.
"""
from typing import Any

import pandas as pd
import streamlit as st

from components.styles import render_empty_state, render_table_skeleton

PAGE_SIZE = 20


def _apply_search(data: list[dict], field: str, term: str) -> list[dict]:
    """Filtra la lista por el campo indicado (case-insensitive)."""
    if not term or not field:
        return data
    term_lower = term.lower()
    return [row for row in data if term_lower in str(row.get(field, "")).lower()]


def _format_value(value: Any, fmt: str | None) -> Any:
    """Aplica formato de presentación a un valor."""
    if value is None:
        return ""
    if fmt == "currency":
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return value
    if fmt == "boolean":
        return "✅" if value else "❌"
    if fmt == "date":
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y")
        return str(value)[:10] if value else ""
    return value


def render_data_table(
    data: list[dict],
    columns_config: dict[str, dict],
    search_field: str = "",
    key: str = "table",
    page_size: int = PAGE_SIZE,
    height: int = 400,
    loading: bool = False,
    skeleton_columns: int | None = None,
    empty_state_icon: str = "📋",
    empty_state_title: str = "No hay registros aún",
    empty_state_subtitle: str = "Haz click en + Incluir para agregar el primero.",
) -> int | None:
    """
    Renderiza una tabla de datos (estilo borderless, hover, fade-in).
    Si loading=True muestra skeleton y retorna None (sin búsqueda ni paginación).
    Si no hay datos tras filtrar muestra estado vacío elegante.

    Parámetros adicionales:
        loading              Si True, solo muestra skeleton y retorna None.
        skeleton_columns     Columnas del skeleton (por defecto desde columns_config).
        empty_state_*        Textos e ícono del estado vacío.
    """
    visible_cols = {
        col: cfg
        for col, cfg in columns_config.items()
        if not cfg.get("hide", False)
    }
    ncols = skeleton_columns if skeleton_columns is not None else len(visible_cols)

    if loading:
        render_table_skeleton(column_count=ncols, row_count=5)
        return None

    search_key = f"search_{key}"
    page_key   = f"page_{key}"

    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    # ── Barra de búsqueda + contador ────────────────────────────────────────
    col_search, col_total = st.columns([4, 1])
    with col_search:
        search_term = st.text_input(
            "🔍 Buscar por:",
            value=st.session_state[search_key],
            key=f"input_{search_key}",
            placeholder=f"Escriba para filtrar por {search_field}...",
            label_visibility="collapsed",
        )
        if search_term != st.session_state[search_key]:
            st.session_state[search_key] = search_term
            st.session_state[page_key] = 0
            st.rerun()

    # ── Filtrar y paginar ────────────────────────────────────────────────────
    filtered = _apply_search(data, search_field, st.session_state[search_key])
    total_filtered = len(filtered)
    current_page   = st.session_state[page_key]
    total_pages    = max(1, (total_filtered + page_size - 1) // page_size)
    current_page   = min(current_page, total_pages - 1)
    st.session_state[page_key] = current_page

    start = current_page * page_size
    end   = start + page_size
    page_data = filtered[start:end]

    with col_total:
        st.markdown(
            f"<div style='text-align:right; padding-top:6px; font-size:13px;"
            f"color:#717D7E;'>{total_filtered} registro(s)</div>",
            unsafe_allow_html=True,
        )

    # ── Estado vacío (sin datos o búsqueda sin resultados) ────────────────────
    if not filtered:
        has_search = bool(st.session_state.get(search_key, "").strip())
        render_empty_state(
            icon="🔍" if has_search else empty_state_icon,
            title="No se encontraron registros." if has_search else empty_state_title,
            subtitle="Pruebe otro término de búsqueda." if has_search else empty_state_subtitle,
        )
        return None

    # ── Construir DataFrame de visualización + índice global en `data` ───────
    rows = []
    row_global_indices: list[int] = []
    for offset, row in enumerate(page_data):
        gi = start + offset
        display_row = {}
        for col, cfg in visible_cols.items():
            raw = row.get(col)
            display_row[cfg.get("label", col)] = _format_value(raw, cfg.get("format"))
        rows.append(display_row)
        row_global_indices.append(gi)

    df = pd.DataFrame(rows)

    # ── Configuración de columnas para st.dataframe ───────────────────────────
    col_cfg = {}
    for col, cfg in visible_cols.items():
        label = cfg.get("label", col)
        if "width" in cfg:
            col_cfg[label] = st.column_config.TextColumn(label, width=cfg["width"])

    # ── Tabla con selección de fila (índice respecto a la lista `data` pasada) ─
    df_widget_key = f"df_sel_{key}"
    selected_original_idx: int | None = None
    df_event = None
    try:
        df_event = st.dataframe(
            df,
            column_config=col_cfg if col_cfg else None,
            use_container_width=True,
            height=height,
            hide_index=True,
            key=df_widget_key,
            on_select="rerun",
            selection_mode="single-row",
        )
    except (TypeError, ValueError):
        st.dataframe(
            df,
            column_config=col_cfg if col_cfg else None,
            use_container_width=True,
            height=height,
            hide_index=True,
            key=f"df_legacy_{key}",
        )
        if row_global_indices:
            pick = st.radio(
                "Fila activa (página actual)",
                options=list(range(len(row_global_indices))),
                format_func=lambda i: " | ".join(
                    str(x) for x in df.iloc[i].tolist()[:4]
                )[:120],
                key=f"dt_fallback_pick_{key}_p{current_page}",
            )
            gix_fb = row_global_indices[int(pick)]
            if 0 <= gix_fb < len(data):
                selected_original_idx = gix_fb

    if df_event is not None:
        sel = getattr(df_event, "selection", None)
        row_tuple: tuple = ()
        if sel is not None:
            row_tuple = tuple(getattr(sel, "rows", ()) or ())
        if row_tuple and row_global_indices:
            li = int(row_tuple[0])
            if 0 <= li < len(row_global_indices):
                gix = row_global_indices[li]
                if 0 <= gix < len(data):
                    selected_original_idx = gix

    st.caption(
        "💡 **Seleccione la fila** con la casilla a la izquierda; "
        "ese registro será el activo para Modificar / Eliminar (y la barra ◀ ▶)."
    )

    # ── Paginación simplificada ──────────────────────────────────────────────
    if total_pages > 1:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Mostrar Primero/Último solo si hay más de 50 registros
        show_extremes = total_filtered > 50
        if show_extremes:
            c_first, c_prev, c_label, c_next, c_last = st.columns([1, 1, 1, 1, 1])
        else:
            c_prev, c_label, c_next = st.columns([1, 1, 1])
            c_first = c_last = None  # type: ignore[assignment]

        if show_extremes and c_first is not None:
            with c_first:
                if st.button("⏮", key=f"pg_first_{key}", disabled=current_page == 0, use_container_width=True):
                    st.session_state[page_key] = 0
                    st.rerun()

        with c_prev:
            if st.button("◀", key=f"pg_prev_{key}", disabled=current_page == 0, use_container_width=True):
                st.session_state[page_key] = max(0, current_page - 1)
                st.rerun()

        with c_label:
            st.markdown(
                f"<div style='text-align:center; padding-top:6px; font-size:13px;"
                f"color:#2C3E50;'>{current_page + 1} de {total_pages}</div>",
                unsafe_allow_html=True,
            )

        with c_next:
            if st.button("▶", key=f"pg_next_{key}",
                         disabled=current_page >= total_pages - 1,
                         use_container_width=True):
                st.session_state[page_key] = min(total_pages - 1, current_page + 1)
                st.rerun()

        if show_extremes and c_last is not None:
            with c_last:
                if st.button("⏭", key=f"pg_last_{key}",
                             disabled=current_page >= total_pages - 1,
                             use_container_width=True):
                    st.session_state[page_key] = total_pages - 1
                    st.rerun()

    return selected_original_idx
