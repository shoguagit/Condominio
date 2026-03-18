import streamlit as st
from utils.auth import check_authentication, require_condominio
from components.header import render_header
from components.breadcrumb import render_breadcrumb

check_authentication()
render_header()
render_breadcrumb("Reportes")
st.info("🚧 Módulo en construcción.")
