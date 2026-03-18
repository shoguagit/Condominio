"""
Breadcrumb de navegación: 🏠 Inicio > [Nombre del Módulo].
Inicio es clickeable (st.page_link a app.py). Estilo: texto #6B7280, Inicio azul #2E86C1.
"""
import streamlit as st


def render_breadcrumb(modulo_label: str) -> None:
    """
    Muestra breadcrumb arriba del contenido del módulo.
    Estilo: texto pequeño #6B7280, separador ">", Inicio clickeable azul #2E86C1.
    """
    st.markdown(
        '<div class="breadcrumb-wrap" style="margin-bottom:8px;">',
        unsafe_allow_html=True,
    )
    bc1, bc2 = st.columns([1, 12])
    with bc1:
        st.page_link("app.py", label="🏠 Inicio", icon=None)
    with bc2:
        st.markdown(
            f'<span style="font-size:12px;color:#6B7280;"> &gt; {modulo_label}</span>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
