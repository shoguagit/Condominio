"""
Vista de registros en cards (sin grid/tabla): búsqueda, cards con acciones Ver/Editar/Eliminar.
Sustituto moderno de data_table + crud_toolbar para CRUD por módulo.
"""
from typing import Any, Callable

import streamlit as st

from components.crud_toolbar import set_current_index
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


def render_record_cards(
    data: list[dict],
    key: str,
    title_field: str,
    subtitle_fields: list[str],
    columns_config: dict[str, dict],
    search_field: str = "",
    modo_key: str | None = None,
    on_incluir: Callable[[], None] | None = None,
    on_modificar: Callable[[], None] | None = None,
    on_eliminar: Callable[[], None] | None = None,
    empty_state_icon: str = "📋",
    empty_state_title: str = "No hay registros aún",
    empty_state_subtitle: str = "Use el botón Nuevo para agregar el primero.",
    cards_per_row: int = 3,
    page_size: int = 12,
) -> None:
    """
    Muestra los registros como cards (no como tabla). Cada card tiene título, subtítulos y
    botones Ver, Editar, Eliminar. Barra superior: búsqueda + botón Nuevo.

    - key: identificador del módulo (ej. "propietarios").
    - title_field: campo para el título de la card (ej. "nombre").
    - subtitle_fields: campos a mostrar debajo del título (ej. ["cedula", "telefono"]).
    - columns_config: dict con label y format por campo (para formato currency/boolean).
    - modo_key: clave en session_state del modo (ej. "prop_modo"). Si no se pasa, se infiere como f"{key}_modo" quitando la 's' final o usando key + "_modo".
    - on_incluir, on_modificar, on_eliminar: callbacks al pulsar Nuevo o los botones de la card.
    """
    modo_key = modo_key or f"{key.rstrip('s')}_modo" if key.endswith("s") else f"{key}_modo"

    search_key = f"rc_search_{key}"
    page_key = f"rc_page_{key}"
    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    # ── Barra: búsqueda + Nuevo ─────────────────────────────────────────────
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search_term = st.text_input(
            "Buscar",
            value=st.session_state[search_key],
            key=f"rc_input_{key}",
            placeholder=f"Filtrar por {search_field}..." if search_field else "Buscar...",
            label_visibility="collapsed",
        )
        if search_term != st.session_state[search_key]:
            st.session_state[search_key] = search_term
            st.session_state[page_key] = 0
            st.rerun()

    with col_btn:
        if st.button("Nuevo", key=f"rc_new_{key}", use_container_width=True, type="primary"):
            if on_incluir:
                on_incluir()
            st.rerun()

    # ── Filtrar y paginar ───────────────────────────────────────────────────
    filtered = _apply_search(data, search_field, st.session_state[search_key])
    total = len(filtered)
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

    # Contador y paginación compacta
    st.markdown(
        f"<p class='form-card-hint' style='margin:0 0 12px 0;'>{total} registro(s)</p>",
        unsafe_allow_html=True,
    )

    # ── Grid de cards ───────────────────────────────────────────────────────
    for row_start in range(0, len(page_data), cards_per_row):
        row_cards = page_data[row_start : row_start + cards_per_row]
        cols = st.columns(cards_per_row)
        for col_idx, rec in enumerate(row_cards):
            if col_idx >= len(cols):
                break
            with cols[col_idx]:
                _render_one_card(
                    rec,
                    key,
                    title_field,
                    subtitle_fields,
                    columns_config,
                    data,
                    page_data,
                    on_modificar,
                    on_eliminar,
                    set_current_index,
                )

    # ── Paginación ──────────────────────────────────────────────────────────
    if total_pages > 1:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
        with c1:
            if st.button("⏮", key=f"rc_first_{key}", disabled=current_page == 0, use_container_width=True):
                st.session_state[page_key] = 0
                st.rerun()
        with c2:
            if st.button("◀", key=f"rc_prev_{key}", disabled=current_page == 0, use_container_width=True):
                st.session_state[page_key] = max(0, current_page - 1)
                st.rerun()
        with c3:
            st.markdown(
                f"<div style='text-align:center;padding-top:6px;font-size:12px;color:#5D6D7E;'>"
                f"Página {current_page + 1} de {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with c4:
            if st.button("▶", key=f"rc_next_{key}", disabled=current_page >= total_pages - 1, use_container_width=True):
                st.session_state[page_key] = min(total_pages - 1, current_page + 1)
                st.rerun()
        with c5:
            if st.button("⏭", key=f"rc_last_{key}", disabled=current_page >= total_pages - 1, use_container_width=True):
                st.session_state[page_key] = total_pages - 1
                st.rerun()


def _render_one_card(
    rec: dict,
    key: str,
    title_field: str,
    subtitle_fields: list[str],
    columns_config: dict,
    full_data: list[dict],
    page_data: list[dict],
    on_modificar: Callable[[], None] | None,
    on_eliminar: Callable[[], None] | None,
    set_current_index_fn: Callable[[str, int], None],
) -> None:
    """Dibuja una card y maneja clics en Ver/Editar/Eliminar."""
    try:
        original_idx = full_data.index(rec)
    except ValueError:
        original_idx = 0

    title = str(rec.get(title_field) or "—")
    cfg = columns_config.get(title_field, {})
    title_label = cfg.get("label", title_field)

    lines = []
    for f in subtitle_fields:
        cfg_f = columns_config.get(f, {})
        label = cfg_f.get("label", f)
        raw = rec.get(f)
        fmt = cfg_f.get("format")
        lines.append(f"{label}: {_format_display(raw, fmt)}")

    subtitle_html = "<br>".join(f"<span style='font-size:12px;color:#5D6D7E;'>{line}</span>" for line in lines)

    st.markdown(
        f"""
        <div class="record-card">
            <div class="record-card-title">{title}</div>
            <div class="record-card-subtitle">{subtitle_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_v, col_e, col_d = st.columns(3)
    with col_v:
        if st.button("Ver", key=f"rc_ver_{key}_{original_idx}", use_container_width=True):
            set_current_index_fn(key, original_idx)
            st.rerun()
    with col_e:
        if st.button("Editar", key=f"rc_edit_{key}_{original_idx}", use_container_width=True):
            set_current_index_fn(key, original_idx)
            if on_modificar:
                on_modificar()
            st.rerun()
    with col_d:
        if st.button("Eliminar", key=f"rc_del_{key}_{original_idx}", use_container_width=True):
            set_current_index_fn(key, original_idx)
            if on_eliminar:
                on_eliminar()
            st.rerun()
