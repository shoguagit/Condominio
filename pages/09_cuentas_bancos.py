import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.cuenta_banco_repository import CuentaBancoRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from components.crud_toolbar import render_toolbar, init_toolbar_state, get_current_index, set_current_index
from components.help_panel import render_help_panel, render_help_shortcuts
from components.data_table import render_data_table
from components.detail_panel import check_close_detail, render_detail_panel
from utils.auth import check_authentication, require_condominio
from utils.error_handler import DatabaseError
from utils.validators import validate_form
from utils.formatters import format_currency

st.set_page_config(page_title="Cuentas / Bancos", page_icon="🏦", layout="wide")
check_authentication()

render_header()
render_breadcrumb("Cuentas / Bancos")
condominio_id = require_condominio()
if st.session_state.get("_last_condominio_id") != condominio_id:
    st.session_state._last_condominio_id = condominio_id
    st.session_state.cb_records = None
@st.cache_resource
def get_repo():
    return CuentaBancoRepository(get_supabase_client())

repo = get_repo()

for k, v in {"cb_modo": None, "cb_records": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

init_toolbar_state("cuentas_bancos")

if st.session_state.cb_records is None:
    with st.spinner("Cargando cuentas..."):
        st.session_state.cb_records = repo.get_all(condominio_id)

records = st.session_state.cb_records

MONEDAS = ["USD", "VES", "EUR", "COP", "ARS", "PEN"]

st.markdown("## 🏦 Cuentas / Bancos")

col_main, col_help = st.columns([4, 1])

with col_help:
    render_help_panel(
        icono="🏦",
        titulo="Cuentas / Bancos",
        descripcion_corta="Cuentas de caja y bancarias del condominio.",
        descripcion_larga=(
            "Registre todas las cuentas donde se manejan los fondos del condominio: "
            "caja chica, cuentas bancarias, billeteras digitales, etc. "
            "El saldo se actualiza según los movimientos registrados."
        ),
        tips=[
            "Siempre debe existir una 'Cuenta Principal'.",
            "El saldo inicial solo se define al crear la cuenta.",
            "Puede manejar cuentas en múltiples monedas.",
        ],
    )
    if records:
        totales = repo.saldo_total(condominio_id)
        st.markdown("<div style='margin-top:8px;'>", unsafe_allow_html=True)
        for moneda, total in totales.items():
            color = "#28B463" if total >= 0 else "#E74C3C"
            st.markdown(
                f"<div style='background:#EBF5FB;border-radius:8px;padding:10px 12px;"
                f"font-size:12px;color:#2C3E50;margin-bottom:6px;'>"
                f"<b>Saldo {moneda}:</b><br>"
                f"<span style='font-size:16px;font-weight:700;color:{color};'>"
                f"{format_currency(total, moneda)}</span></div>",
                unsafe_allow_html=True,
            )

with col_main:
    check_close_detail("cuentas_bancos")
    render_toolbar(
        key="cuentas_bancos",
        total=len(records),
        on_incluir  = lambda: st.session_state.update({"cb_modo": "incluir"}),
        on_modificar= lambda: st.session_state.update({"cb_modo": "modificar"}),
        on_eliminar = lambda: st.session_state.update({"cb_modo": "eliminar"}),
    )

    sel_idx = render_data_table(
        data=records,
        columns_config={
            "id":            {"label": "Id",            "width": 55},
            "descripcion":   {"label": "Descripción",   "width": 220},
            "numero_cuenta": {"label": "N° Cuenta",     "width": 150},
            "moneda":        {"label": "Moneda",        "width": 75},
            "saldo_inicial": {"label": "Saldo Inicial", "width": 110, "format": "currency"},
            "saldo":         {"label": "Saldo Actual",  "width": 110, "format": "currency"},
            "activo":        {"label": "Activo",        "width": 65,  "format": "boolean"},
        },
        search_field="descripcion",
        key="cuentas_bancos",
        empty_state_title="Este condominio no tiene cuentas/bancos registrados aún",
        empty_state_subtitle="Haz click en + Nuevo para agregar el primero.",
    )
    if sel_idx is not None:
        set_current_index("cuentas_bancos", sel_idx)

    current_idx = get_current_index("cuentas_bancos")
    current_rec = records[current_idx] if records and 0 <= current_idx < len(records) else None
    modo        = st.session_state.cb_modo

    if modo in ("incluir", "modificar"):
        is_edit = modo == "modificar"
        st.markdown(f"### {'✏️ Modificar' if is_edit else '➕ Nueva'} Cuenta")
        st.markdown("<hr style='margin:4px 0 12px 0;'>", unsafe_allow_html=True)
        cr = current_rec if is_edit and current_rec else {}

        moneda_default = MONEDAS.index(cr["moneda"]) if cr.get("moneda") in MONEDAS else 0

        with st.form("form_cuenta_banco"):
            col1, col2 = st.columns(2)
            with col1:
                descripcion  = st.text_input("Descripción *", value=cr.get("descripcion", ""), max_chars=150,
                                              placeholder="Ej: Cuenta Principal, Caja Chica")
                numero_cuenta = st.text_input("Número de cuenta", value=cr.get("numero_cuenta", ""),
                                              max_chars=30, placeholder="Ej: 0102-1234-56-7890123456")
                activo        = st.checkbox("Activo", value=cr.get("activo", True))
            with col2:
                moneda = st.selectbox("Moneda *", options=MONEDAS, index=moneda_default)
                saldo_inicial = st.number_input(
                    "Saldo inicial",
                    value=float(cr.get("saldo_inicial") or 0),
                    min_value=0.0, step=0.01, format="%.2f",
                    disabled=is_edit,
                    help="Solo se define al crear la cuenta.",
                )
                if is_edit:
                    saldo_actual = st.number_input(
                        "Saldo actual",
                        value=float(cr.get("saldo") or 0),
                        min_value=0.0, step=0.01, format="%.2f",
                    )

            col_s, col_c = st.columns(2)
            with col_s:
                guardar  = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("✖ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.cb_modo = None
            st.rerun()

        if guardar:
            errors = validate_form({"descripcion": descripcion}, {"descripcion": {"required": True, "max_length": 150}})
            if errors:
                for e in errors:
                    st.error(f"❌ {e}")
            else:
                payload = {
                    "condominio_id": condominio_id,
                    "descripcion":   (descripcion or "").strip(),
                    "numero_cuenta": (numero_cuenta or "").strip() or None,
                    "moneda":        moneda,
                    "activo":        activo,
                }
                if is_edit and current_rec:
                    payload["saldo"] = saldo_actual
                else:
                    payload["saldo_inicial"] = saldo_inicial
                    payload["saldo"]         = saldo_inicial

                try:
                    if is_edit and current_rec:
                        repo.update(current_rec["id"], payload)
                        st.success("✅ Cuenta actualizada.")
                    else:
                        repo.create(payload)
                        st.success("✅ Cuenta creada.")
                    st.session_state.cb_modo    = None
                    st.session_state.cb_records = None
                    st.rerun()
                except DatabaseError as e:
                    st.error(f"❌ {e}")

    elif modo == "eliminar":
        if not current_rec:
            st.warning("⚠️ Seleccione una cuenta.")
            st.session_state.cb_modo = None
        else:
            st.warning(f"⚠️ ¿Eliminar la cuenta **{current_rec.get('descripcion')}**? Saldo actual: {format_currency(float(current_rec.get('saldo') or 0))}")
            col_y, col_n = st.columns(2)
            with col_y:
                if st.button("✅ Sí, eliminar", type="primary", use_container_width=True, key="cb_del_y"):
                    try:
                        repo.delete(current_rec["id"])
                        st.success("✅ Cuenta eliminada.")
                        st.session_state.cb_modo    = None
                        st.session_state.cb_records = None
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")
            with col_n:
                if st.button("✖ Cancelar", use_container_width=True, key="cb_del_n"):
                    st.session_state.cb_modo = None
                    st.rerun()

    elif current_rec and modo is None:
        saldo = float(current_rec.get("saldo") or 0)
        detail_fields = [
            ("Descripción", current_rec.get("descripcion") or "—"),
            ("N° Cuenta", current_rec.get("numero_cuenta") or "—"),
            ("Moneda", current_rec.get("moneda") or "—"),
            ("Saldo inicial", format_currency(float(current_rec.get("saldo_inicial") or 0))),
            ("Saldo actual", format_currency(saldo)),
            ("Estado", "Activo" if current_rec.get("activo") else "Inactivo"),
        ]
        render_detail_panel(detail_fields, "cuentas_bancos", "Detalle de la cuenta")
