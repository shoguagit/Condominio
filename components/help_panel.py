"""
Panel de ayuda lateral derecho estilo Sisconin.

Uso en una página (columna derecha):
    from components.help_panel import render_help_panel

    col_main, col_help = st.columns([3, 1])
    with col_main:
        ...  # contenido principal
    with col_help:
        render_help_panel(
            icono="📄",
            titulo="Proveedores",
            descripcion_corta="Gestión de proveedores del condominio.",
            descripcion_larga=(
                "Registre las empresas y personas que prestan servicios "
                "al condominio. Puede incluir datos de contacto, tipo de "
                "documento y controlar el saldo pendiente."
            ),
        )
"""
import streamlit as st


def render_help_panel(
    icono: str = "",
    titulo: str = "",
    descripcion_corta: str = "",
    descripcion_larga: str = "",
    tips: list[str] | None = None,
) -> None:
    """
    Renderiza el panel de ayuda lateral con fondo blanco y borde.

    Parámetros:
        icono              Emoji representativo del módulo
        titulo             Nombre del módulo
        descripcion_corta  Una línea que resume el módulo
        descripcion_larga  Párrafo explicativo más detallado
        tips               Lista de tips/notas adicionales (opcional)
    """
    return  # Panel de ayuda desactivado — libera espacio horizontal

    tips = tips or []

    tips_html = ""
    if tips:
        items = "".join(f"<li style='margin-bottom:4px;'>{t}</li>" for t in tips)
        tips_html = f"""
        <div style='margin-top:12px;'>
            <p style='font-size:11px; font-weight:600; color:#2C3E50;
                      text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;'>
                Notas
            </p>
            <ul style='padding-left:16px; font-size:12px; color:#5D6D7E; margin:0;'>
                {items}
            </ul>
        </div>
        """

    desc_larga_html = ""
    if descripcion_larga:
        desc_larga_html = f"""
        <p style='font-size:12px; color:#5D6D7E; line-height:1.6; margin:8px 0 0 0;'>
            {descripcion_larga}
        </p>
        """

    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #D5D8DC;
            border-left: 4px solid #1B4F72;
            border-radius: 8px;
            padding: 16px;
            font-family: sans-serif;
        ">
            <div style='text-align:center; font-size:2.2rem; margin-bottom:8px;'>
                {icono}
            </div>
            <p style='
                font-size:14px;
                font-weight:700;
                color:#1B4F72;
                text-align:center;
                margin:0 0 8px 0;
            '>
                {titulo}
            </p>
            <hr style='border:none; border-top:1px solid #D5D8DC; margin:8px 0;'>
            <p style='font-size:12px; color:#2C3E50; font-weight:500; margin:0;'>
                {descripcion_corta}
            </p>
            {desc_larga_html}
            {tips_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_help_shortcuts(shortcuts: dict[str, str]) -> None:  # noqa: ARG001
    return  # Panel de atajos desactivado

    # pylint: disable=unreachable
    shortcuts = shortcuts  # dead code kept for reference
    """
    Renderiza un mini panel de atajos de teclado o acciones rápidas.

    Parámetro:
        shortcuts  Dict {"acción": "descripción"}. Ej: {"➕ Incluir": "Agrega un nuevo registro"}
    """
    rows = "".join(
        f"""
        <tr>
            <td style='padding:3px 8px 3px 0; font-weight:600;
                       color:#1B4F72; font-size:12px; white-space:nowrap;'>{accion}</td>
            <td style='padding:3px 0; font-size:12px; color:#5D6D7E;'>{desc}</td>
        </tr>
        """
        for accion, desc in shortcuts.items()
    )

    st.markdown(
        f"""
        <div style='
            background:#F4F6F7;
            border:1px solid #D5D8DC;
            border-radius:6px;
            padding:10px 12px;
            margin-top:10px;
        '>
            <p style='font-size:11px; font-weight:600; color:#2C3E50;
                      text-transform:uppercase; letter-spacing:0.5px; margin:0 0 6px 0;'>
                Acciones disponibles
            </p>
            <table style='width:100%; border-collapse:collapse;'>
                {rows}
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
