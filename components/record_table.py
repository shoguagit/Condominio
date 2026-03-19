"""
Vista de registros en tabla estilo Tremor: HTML <table> 100% ancho, sin bordes,
header gris, filas con separador sutil, acciones por enlaces. Botón Nuevo outline.
"""
import html
from typing import Any, Callable

import streamlit as st

from components.crud_toolbar import get_current_index, set_current_index
from components.styles import render_empty_state


def _apply_search(data: list[dict], field: str, term: str) -> list[dict]:
    if not term or not field:
        return data
    term_lower = term.lower()
    return [row for row in data if term_lower in str(row.get(field, "")).lower()]


def _format_display(value: Any, fmt: str | None) -> str:
    if value is None:
        return "—"
    if fmt == "boolean":
        return "Sí" if value else "No"
    if fmt == "currency":
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            return str(value)
    return str(value).strip() or "—"


def render_record_table(
    data: list[dict],
    key: str,
    columns_config: dict[str, dict],
    search_field: str = "",
    caption: str = "",
    modo_key: str | None = None,
    on_incluir: Callable[[], None] | None = None,
    on_modificar: Callable[[], None] | None = None,
    on_eliminar: Callable[[], None] | None = None,
    empty_state_icon: str = "📋",
    empty_state_title: str = "No hay registros aún",
    empty_state_subtitle: str = "Use el botón Nuevo para agregar el primero.",
    page_size: int = 20,
    right_align_columns: list[str] | None = None,
) -> None:
    """
    Tabla estilo Tremor: <table> HTML 100% ancho, header gris sin fondo,
    separadores sutiles, botón Nuevo outline. Acciones por enlace (Ver, Editar, Eliminar).
    """
    modo_key = modo_key or f"{key.rstrip('s')}_modo" if key.endswith("s") else f"{key}_modo"
    right_align_columns = right_align_columns or []

    # Primera columna reservada para checkbox de selección múltiple
    visible_cols = {
        col: cfg
        for col, cfg in columns_config.items()
        if not cfg.get("hide", False)
    }
    col_keys = list(visible_cols.keys())

    search_key = f"rt_search_{key}"
    page_key = f"rt_page_{key}"
    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    filtered = _apply_search(data, search_field, st.session_state[search_key])
    total_filtered = len(filtered)

    # ── Barra: búsqueda + Nuevo (misma fila, estilo corporativo) + contador ───
    col_search, col_btn, col_count = st.columns([4, 1, 1])
    with col_search:
        search_term = st.text_input(
            "Buscar",
            value=st.session_state[search_key],
            key=f"rt_input_{key}",
            placeholder=f"Filtrar por {search_field}..." if search_field else "Buscar...",
            label_visibility="collapsed",
        )
        if search_term != st.session_state[search_key]:
            st.session_state[search_key] = search_term
            st.session_state[page_key] = 0
            st.rerun()

    with col_btn:
        st.markdown(
            '<div class="record-table-bar record-table-bar-nuevo">',
            unsafe_allow_html=True,
        )
        if st.button("+ Nuevo", key=f"rt_new_{key}", use_container_width=True, type="primary"):
            if on_incluir:
                on_incluir()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_count:
        st.markdown(
            f"<div style='text-align:right;padding-top:6px;font-size:13px;color:#717D7E;'>"
            f"{total_filtered} registro(s)</div>",
            unsafe_allow_html=True,
        )

    # ── Paginar ─────────────────────────────────────────────────────────────
    total = total_filtered
    current_page = st.session_state[page_key]
    total_pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(current_page, total_pages - 1)
    st.session_state[page_key] = current_page

    start = current_page * page_size
    page_data = filtered[start : start + page_size]

    if not filtered:
        has_search = bool(st.session_state.get(search_key, "").strip())
        render_empty_state(
            icon="🔍" if has_search else empty_state_icon,
            title="No se encontraron registros." if has_search else empty_state_title,
            subtitle="Pruebe otro término." if has_search else empty_state_subtitle,
        )
        return

    # ── Cabecera de tabla (HTML) ───────────────────────────────────────────────
    caption_text = html.escape(caption or f"{total} registro(s)")
    thead_cells = ['<th class="table-th table-th-checkbox"></th>']
    for col_key in col_keys:
        cfg = visible_cols[col_key]
        label = html.escape(cfg.get("label", col_key))
        align_cls = " text-right" if col_key in right_align_columns else ""
        thead_cells.append(f'<th class="table-th{align_cls}">{label}</th>')
    thead_cells.append('<th class="table-th table-th-actions">Acciones</th>')
    thead_row = '<tr class="table-header-row">' + "".join(thead_cells) + "</tr>"
    st.markdown(
        '<div class="table-root">'
        f'<div class="table-caption">{caption_text}</div>'
        '<table class="tremor-table">'
        f"<thead>{thead_row}</thead></table>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Filas con botones Ver / Editar / Eliminar (Streamlit, solo ícono 40px) ─
    # Pesos de columnas: checkbox pequeño + anchos de columns_config + 3 acciones fijas
    col_weights = [0.4]  # checkbox
    for col_key in col_keys:
        w = visible_cols[col_key].get("width", 100)
        col_weights.append(max(0.5, (w or 100) / 100.0))
    col_weights.extend([0.5, 0.5, 0.5])  # Ver, Editar, Eliminar
    n_cols = len(col_weights)

    st.markdown('<div class="record-table-actions-row">', unsafe_allow_html=True)
    sel_key = f"rt_selected_{key}"
    selected_indices: set[int] = set(st.session_state.get(sel_key, set()) or [])
    index_map: dict[int, dict] = {}

    for row_idx, rec in enumerate(page_data):
        try:
            original_idx = data.index(rec)
        except ValueError:
            original_idx = start + row_idx
        index_map[original_idx] = rec
        is_selected = original_idx in selected_indices
        row_style = "background:#EBF5FB;" if is_selected else ""
        st.markdown(
            '<div style="border-bottom:1px solid #F0F0F0; padding:6px 0;">',
            unsafe_allow_html=True,
        )
        cols = st.columns(col_weights)
        ci = 0
        # Checkbox (visual por ahora)
        with cols[ci]:
            st.markdown(
                f'<div style="font-size:12px;color:#6B7280;">{"☑" if is_selected else "☐"}</div>',
                unsafe_allow_html=True,
            )
        ci += 1
        # Celdas de datos
        for col_key in col_keys:
            cfg = visible_cols[col_key]
            raw = rec.get(col_key)
            text = _format_display(raw, cfg.get("format"))
            if col_key == "activo":
                if bool(raw):
                    cell_html = '<span class="badge badge-activo">● Activo</span>'
                else:
                    cell_html = '<span class="badge badge-inactivo">● Inactivo</span>'
            else:
                cell_html = html.escape(text)
            with cols[ci]:
                st.markdown(
                    f'<div style="font-size:13px;color:#374151;{row_style}">{cell_html}</div>',
                    unsafe_allow_html=True,
                )
            ci += 1
        # Botones de acción: solo ícono, 40px, con tooltip
        with cols[ci]:
            if st.button("👁", key=f"rt_ver_{key}_{original_idx}", use_container_width=True, help="Ver detalle"):
                set_current_index(key, original_idx)
                if modo_key:
                    st.session_state[modo_key] = None
                st.rerun()
        ci += 1
        with cols[ci]:
            if st.button("✏️", key=f"rt_edit_{key}_{original_idx}", use_container_width=True, help="Editar registro"):
                set_current_index(key, original_idx)
                if on_modificar:
                    on_modificar()
                st.rerun()
        ci += 1
        with cols[ci]:
            if st.button("🗑", key=f"rt_del_{key}_{original_idx}", use_container_width=True, help="Eliminar registro"):
                set_current_index(key, original_idx)
                if on_eliminar:
                    on_eliminar()
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if index_map:
        all_indices = sorted(index_map.keys())
        current = get_current_index(key)
        if current not in all_indices:
            set_current_index(key, all_indices[0])

    # ── Paginación simplificada ───────────────────────────────────────────────
    if total_pages > 1:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        c_prev, c_label, c_next = st.columns([1, 1, 1])
        with c_prev:
            if st.button("◀", key=f"rt_prev_{key}", disabled=current_page == 0, use_container_width=True):
                st.session_state[page_key] = max(0, current_page - 1)
                st.rerun()
        with c_label:
            st.markdown(
                f"<div style='text-align:center;padding-top:6px;font-size:12px;color:#5D6D7E;'>"
                f"{current_page + 1} de {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with c_next:
            if st.button("▶", key=f"rt_next_{key}", disabled=current_page >= total_pages - 1, use_container_width=True):
                st.session_state[page_key] = min(total_pages - 1, current_page + 1)
                st.rerun()

