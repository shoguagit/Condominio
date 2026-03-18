"""
Barra de herramientas CRUD con navegación de registros estilo Sisconin.

Uso típico en una página:
    from components.crud_toolbar import render_toolbar, init_toolbar_state

    init_toolbar_state("proveedores")
    action = render_toolbar(
        key="proveedores",
        total=len(records),
        on_incluir=lambda: st.session_state.update({"modo": "incluir"}),
        on_modificar=lambda: st.session_state.update({"modo": "modificar"}),
        on_eliminar=lambda: st.session_state.update({"modo": "eliminar"}),
    )
    current_index = st.session_state["toolbar_proveedores_idx"]
"""
from typing import Callable

import streamlit as st


def init_toolbar_state(key: str) -> None:
    """Inicializa el estado de navegación para una toolbar identificada por key.
    Índice -1 = ninguna fila seleccionada (el panel de detalle no se abre al entrar)."""
    if f"toolbar_{key}_idx" not in st.session_state:
        st.session_state[f"toolbar_{key}_idx"] = -1


def render_toolbar(
    key: str,
    total: int,
    on_incluir: Callable | None = None,
    on_modificar: Callable | None = None,
    on_eliminar: Callable | None = None,
    show_nav: bool = True,
) -> str | None:
    """
    Renderiza la barra de herramientas CRUD + navegación de registros.

    Parámetros:
        key         Identificador único de la toolbar (p.ej. "proveedores")
        total       Total de registros en la tabla actual
        on_incluir  Callback al pulsar [+ Incluir]
        on_modificar Callback al pulsar [✏ Modificar]
        on_eliminar  Callback al pulsar [🗑 Eliminar]
        show_nav    Mostrar controles de navegación de registros

    Retorna el nombre de la acción pulsada: "incluir" | "modificar" | "eliminar" | None
    """
    idx_key = f"toolbar_{key}_idx"
    init_toolbar_state(key)

    current = st.session_state[idx_key]
    if total == 0:
        current = -1
    elif current >= total:
        current = total - 1
    elif current < -1:
        current = -1
    st.session_state[idx_key] = current

    action = None

    # ── Estilos inline para la barra ─────────────────────────────────────────
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] button {
            border-radius: 5px !important;
            font-size: 13px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Columnas: acciones CRUD | separador | navegación ─────────────────────
    if show_nav:
        col_inc, col_mod, col_del, col_sep, col_first, col_prev, col_nav, col_next, col_last = \
            st.columns([1.2, 1.2, 1.2, 0.3, 0.6, 0.6, 1.4, 0.6, 0.6])
    else:
        col_inc, col_mod, col_del = st.columns([1.2, 1.2, 1.2])

    with col_inc:
        if st.button("➕ Incluir", key=f"btn_incluir_{key}", use_container_width=True, type="primary"):
            action = "incluir"
            if on_incluir:
                on_incluir()

    with col_mod:
        disabled_mod = total == 0 or current < 0
        if st.button("✏️ Modificar", key=f"btn_modificar_{key}",
                     use_container_width=True, disabled=disabled_mod):
            action = "modificar"
            if on_modificar:
                on_modificar()

    with col_del:
        disabled_del = total == 0 or current < 0
        if st.button("🗑️ Eliminar", key=f"btn_eliminar_{key}",
                     use_container_width=True, disabled=disabled_del):
            action = "eliminar"
            if on_eliminar:
                on_eliminar()

    if show_nav:
        with col_sep:
            st.markdown(
                "<div style='border-left:2px solid #D5D8DC; height:36px; margin-top:4px;'></div>",
                unsafe_allow_html=True,
            )

        with col_first:
            if st.button("⏮", key=f"btn_first_{key}", use_container_width=True,
                         disabled=total == 0 or current <= 0, help="Primer registro"):
                st.session_state[idx_key] = 0
                st.rerun()

        with col_prev:
            if st.button("◀", key=f"btn_prev_{key}", use_container_width=True,
                         disabled=total == 0 or current <= 0, help="Anterior"):
                st.session_state[idx_key] = max(0, current - 1)
                st.rerun()

        with col_nav:
            label = (f"{current + 1} de {total}" if current >= 0 else f"— de {total}") if total > 0 else "0 de 0"
            st.markdown(
                f"<div style='text-align:center; padding-top:6px; font-size:13px;"
                f"color:#2C3E50; font-weight:600;'>{label}</div>",
                unsafe_allow_html=True,
            )

        with col_next:
            if st.button("▶", key=f"btn_next_{key}", use_container_width=True,
                         disabled=total == 0 or current >= total - 1, help="Siguiente"):
                st.session_state[idx_key] = min(total - 1, current + 1)
                st.rerun()

        with col_last:
            if st.button("⏭", key=f"btn_last_{key}", use_container_width=True,
                         disabled=total == 0 or current >= total - 1, help="Último registro"):
                st.session_state[idx_key] = total - 1
                st.rerun()

    st.markdown("<hr style='margin:6px 0 12px 0; border-color:#D5D8DC;'>", unsafe_allow_html=True)
    return action


def get_current_index(key: str) -> int:
    """Retorna el índice del registro actualmente seleccionado en la toolbar (-1 = ninguno)."""
    return st.session_state.get(f"toolbar_{key}_idx", -1)


def set_current_index(key: str, idx: int) -> None:
    """Establece el índice del registro seleccionado (útil al seleccionar fila en tabla)."""
    st.session_state[f"toolbar_{key}_idx"] = idx
