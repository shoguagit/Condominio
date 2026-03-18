"""
Detalle de registro en tarjeta fija bajo la tabla (sin panel lateral).
"""
import html
import streamlit as st

from components.crud_toolbar import set_current_index


def check_close_detail(module_key: str) -> None:
    """
    Llamar al inicio de la página: si la URL tiene close_detail=1,
    limpia la selección del módulo y hace rerun sin el param.
    (Mantener por compatibilidad; el cierre normal es vía botón.)
    """
    raw_q = dict(st.query_params)
    q = {k: (v[0] if isinstance(v, list) and v else "") for k, v in raw_q.items()}
    if q.get("close_detail") == "1":
        set_current_index(module_key, -1)
        q.pop("close_detail", None)
        st.query_params = q
        st.rerun()


def _escape(s: str) -> str:
    """Escapa HTML para evitar que valores con < o > rompan el panel o muestren etiquetas."""
    text = str(s)
    # Proteger valores que provienen con tags sueltas (p.ej. "</div>" en datos)
    if text.strip() in {"</div>", "<div>", "<div/>", "</div/>"}:
        text = "—"
    return html.escape(text)


def render_detail_panel(
    fields: list[tuple[str, str]],
    module_key: str,
    title: str = "Detalle del registro",
) -> None:
    """
    Renderiza el detalle como una tarjeta fija debajo de la tabla,
    reutilizable para todos los módulos que antes usaban el panel lateral.
    """
    if not fields:
        return

    st.markdown(f"#### {title}")
    with st.container(border=True):
        # Distribuir campos en dos columnas para mejor lectura.
        col1, col2 = st.columns(2)
        for idx, (label, value) in enumerate(fields):
            if value is None:
                value = "—"
            elif isinstance(value, bool):
                value = "Sí" if value else "No"
            text = f"**{_escape(label)}**: {_escape(value)}"
            if idx % 2 == 0:
                with col1:
                    st.markdown(text, unsafe_allow_html=True)
            else:
                with col2:
                    st.markdown(text, unsafe_allow_html=True)
