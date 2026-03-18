"""
Header corporativo global.
render_header() inyecta el CSS global, renderiza el sidebar y la barra de encabezado.
Es el punto de entrada de UI para todas las páginas internas.
Solo los admin ven el botón "Cambiar" para cambiar de condominio sin cerrar sesión.
"""
import streamlit as st

from utils.formatters import format_mes_proceso


def render_header() -> None:
    from components.sidebar import GLOBAL_CSS, render_sidebar
    from components.styles import inject_global_styles

    # Mantener inyección de estilos + sidebar del sistema
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    inject_global_styles()
    render_sidebar()

    condominio = st.session_state.get("condominio_nombre", "Sin condominio")
    mes = format_mes_proceso(st.session_state.get("mes_proceso")) or st.session_state.get("mes_proceso", "")
    tasa = st.session_state.get("tasa_cambio", "0.00")
    email = st.session_state.get("user_email", "")
    rol = st.session_state.get("user_role", "")

    # Header en una fila: [nombre + métricas] | [Cambiar] con mismo fondo azul
    st.markdown('<div class="header-bar-marker"></div>', unsafe_allow_html=True)
    col_content, col_btn = st.columns([7, 1])
    with col_content:
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:24px;">🏢</span>
                    <span style="color:#fff; font-size:18px; font-weight:700;">{condominio}</span>
                </div>
                <div style="display:flex; gap:28px; align-items:center;">
                    <div style="text-align:center; border-left:1px solid #2E86C1; padding-left:24px;">
                        <div style="color:#AED6F1; font-size:10px; text-transform:uppercase;">Mes en Proceso</div>
                        <div style="color:#fff; font-weight:600;">{mes}</div>
                    </div>
                    <div style="text-align:center; border-left:1px solid #2E86C1; padding-left:24px;">
                        <div style="color:#AED6F1; font-size:10px; text-transform:uppercase;">Tasa BCV</div>
                        <div style="color:#fff; font-weight:600;">Bs. {tasa}</div>
                    </div>
                    <div style="text-align:center; border-left:1px solid #2E86C1; padding-left:24px;">
                        <div style="color:#AED6F1; font-size:10px; text-transform:uppercase;">Usuario</div>
                        <div style="color:#fff; font-weight:600;">
                            {email} <span style="background:#28B463; color:#fff; padding:2px 8px; border-radius:12px; font-size:11px; margin-left:6px;">{rol}</span>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.session_state.get("user_role") == "admin":
            if st.button("🔄 Cambiar", key="btn_cambiar"):
                st.session_state.show_condominio_switcher = True
                st.rerun()
        else:
            st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

    # 4 — Selector de condominio (admin: tras "Cambiar" o tras login)
    if st.session_state.get("user_role") == "admin" and st.session_state.get("show_condominio_switcher", False):
        from config.supabase_client import get_supabase_client
        from repositories.condominio_repository import CondominioRepository
        from utils.auth import apply_condominio_to_session
        condominios = CondominioRepository(get_supabase_client()).get_all(solo_activos=False)
        if condominios:
            options = [c.get("nombre") or f"Condominio #{c.get('id')}" for c in condominios]
            current_name = st.session_state.get("condominio_nombre") or "—"
            idx = options.index(current_name) if current_name in options else 0
            sel = st.selectbox(
                "Seleccione el condominio",
                options,
                index=idx,
                key="header_condo_switcher_select",
            )
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Listo", key="header_condo_switcher_ok", type="primary"):
                    i = options.index(sel)
                    apply_condominio_to_session(condominios[i]["id"])
                    st.session_state.show_condominio_switcher = False
                    st.rerun()
            with col_b:
                if st.button("Cancelar", key="header_condo_switcher_cancel"):
                    st.session_state.show_condominio_switcher = False
                    st.rerun()
        else:
            st.caption("No hay condominios registrados.")
            if st.button("Cerrar", key="header_condo_switcher_close"):
                st.session_state.show_condominio_switcher = False
                st.rerun()
