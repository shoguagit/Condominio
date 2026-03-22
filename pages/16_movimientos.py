from collections import Counter

import pandas as pd
import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.movimiento_repository import MovimientoRepository
from repositories.concepto_repository import ConceptoRepository
from repositories.unidad_repository import UnidadRepository
from repositories.propietario_repository import PropietarioRepository
from repositories.conciliacion_repository import ConciliacionRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from utils.auth import check_authentication, require_condominio
from utils.bank_parser import MovimientoParsed, parsear_bytes
from utils.conciliacion import clasificar_alerta
from utils.error_handler import DatabaseError
from utils.supabase_compat import json_safe_date, json_safe_periodo
from utils.validators import validate_periodo, periodo_to_date_str


st.set_page_config(page_title="Movimientos Bancarios", page_icon="🏦", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Movimientos Bancarios")

condominio_id = require_condominio()


@st.cache_resource
def get_repos():
    client = get_supabase_client()
    return (
        MovimientoRepository(client),
        ConceptoRepository(client),
        UnidadRepository(client),
        PropietarioRepository(client),
        ConciliacionRepository(client),
    )


repo_mov, repo_concepto, repo_uni, repo_prop, repo_conciliacion = get_repos()

st.markdown("## 🏦 Movimientos Bancarios")

col_f, col_a = st.columns([2, 1])
with col_f:
    periodo = st.text_input(
        "Período (YYYY-MM-01) *",
        value=str(st.session_state.get("mes_proceso") or "").strip(),
    )
with col_a:
    st.caption("Formato sugerido: primer día del mes (ej: 2026-03-01).")

ok_p, msg_p = validate_periodo(periodo)
if not ok_p:
    st.error(f"❌ {msg_p}")
    st.stop()
ok_db, msg_db, periodo_db = periodo_to_date_str(periodo)
if not ok_db or not periodo_db:
    st.error(f"❌ {msg_db}")
    st.stop()

periodo_ym = periodo_db[:7]

st.divider()

tab_carga, tab_conciliacion = st.tabs(
    ["📥 Carga de movimientos", "🔍 Conciliación"]
)

with tab_carga:
    tab_list, tab_class, tab_upload = st.tabs(
        ["📄 Listado", "🏷️ Clasificar", "📥 Cargar Excel"]
    )

    with tab_list:
        tab_eg, tab_in = st.tabs(["⬇️ Egresos", "⬆️ Ingresos"])

        def _render_table(rows: list[dict]):
            if not rows:
                st.info("No hay movimientos.")
                return
            for r in rows:
                r["_concepto"] = (r.get("conceptos") or {}).get("nombre")
                u = r.get("unidades") or {}
                r["_unidad"] = (u.get("codigo") or u.get("numero") or "")
                r["_propietario"] = (r.get("propietarios") or {}).get("nombre")
            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("Id", width="small"),
                    "fecha": st.column_config.DateColumn("Fecha", width="small"),
                    "descripcion": st.column_config.TextColumn(
                        "Descripción", width="large"
                    ),
                    "referencia": st.column_config.TextColumn("Ref", width="small"),
                    "monto_bs": st.column_config.NumberColumn("Bs", format="%.2f"),
                    "_concepto": st.column_config.TextColumn("Concepto"),
                    "_unidad": st.column_config.TextColumn("Unidad"),
                    "_propietario": st.column_config.TextColumn("Propietario"),
                    "estado": st.column_config.TextColumn("Estado", width="small"),
                    "fuente": st.column_config.TextColumn("Fuente", width="small"),
                },
            )

        with tab_eg:
            try:
                egresos = repo_mov.get_by_tipo(condominio_id, periodo_db, "egreso")
            except DatabaseError as e:
                st.error(f"❌ {e}")
                egresos = []
            _render_table(egresos)
        with tab_in:
            try:
                ingresos = repo_mov.get_by_tipo(
                    condominio_id, periodo_db, "ingreso"
                )
            except DatabaseError as e:
                st.error(f"❌ {e}")
                ingresos = []
            _render_table(ingresos)

    with tab_class:
        st.markdown("### 🏷️ Clasificación")
        st.caption(
            "Asignar concepto/unidad/propietario y cambiar estado del movimiento."
        )

        conceptos = repo_concepto.get_all(condominio_id, solo_activos=True)
        unidades = repo_uni.get_all(condominio_id)
        propietarios = repo_prop.get_all(condominio_id, solo_activos=True)

        conc_labels = [c["nombre"] for c in conceptos]
        conc_ids = [c["id"] for c in conceptos]

        uni_labels = []
        uni_ids = []
        for u in unidades:
            codigo = (u.get("codigo") or u.get("numero") or "").strip()
            prop = u.get("propietarios") or {}
            uni_labels.append(f"{codigo} — {prop.get('nombre', '—')}")
            uni_ids.append(u["id"])

        prop_labels = [p["nombre"] for p in propietarios]
        prop_ids = [p["id"] for p in propietarios]

        st.divider()
        filtro_estado = st.selectbox(
            "Filtrar por estado",
            options=["pendiente", "clasificado", "procesado"],
            index=0,
        )
        tipo_tab = st.tabs(["⬇️ Egresos", "⬆️ Ingresos"])
        tipo_sel = ["egreso", "ingreso"]
        selected_row = None

        for i, t in enumerate(tipo_tab):
            with t:
                rows = repo_mov.get_by_tipo(
                    condominio_id, periodo_db, tipo_sel[i], estado=filtro_estado
                )
                if not rows:
                    st.info("No hay movimientos.")
                    continue
                options = []
                by_id = {}
                for r in rows:
                    label = (
                        f"#{r.get('id')} | {r.get('fecha')} | "
                        f"{float(r.get('monto_bs') or 0):,.2f} | "
                        f"{(r.get('descripcion') or '')[:60]}"
                    )
                    options.append(label)
                    by_id[label] = r
                pick = st.selectbox(
                    "Movimiento",
                    options=options,
                    key=f"mov_pick_{tipo_sel[i]}_{filtro_estado}",
                )
                selected_row = by_id.get(pick)

                if not selected_row:
                    continue

                if selected_row.get("estado") == "procesado":
                    st.warning(
                        "Este movimiento está PROCESADO (mes cerrado). Solo lectura."
                    )

                def _idx(ids, value):
                    try:
                        return ids.index(value) if value in ids else 0
                    except Exception:
                        return 0

                conc_default = _idx(conc_ids, selected_row.get("concepto_id"))
                uni_default = _idx(uni_ids, selected_row.get("unidad_id"))
                prop_default = _idx(prop_ids, selected_row.get("propietario_id"))

                col1, col2 = st.columns(2)
                with col1:
                    concepto_sel = st.selectbox(
                        "Concepto *",
                        options=conc_labels,
                        index=conc_default,
                        key=f"conc_{selected_row['id']}",
                    )
                    unidad_sel = st.selectbox(
                        "Unidad (opcional)",
                        options=["—"] + uni_labels,
                        index=uni_default + 1,
                        key=f"uni_{selected_row['id']}",
                    )
                with col2:
                    propietario_sel = st.selectbox(
                        "Propietario (opcional)",
                        options=["—"] + prop_labels,
                        index=prop_default + 1,
                        key=f"prop_{selected_row['id']}",
                    )
                    estado_sel = st.selectbox(
                        "Estado",
                        options=["pendiente", "clasificado"],
                        index=0
                        if selected_row.get("estado") == "pendiente"
                        else 1,
                        key=f"estado_{selected_row['id']}",
                        disabled=(selected_row.get("estado") == "procesado"),
                    )

                if st.button(
                    "Guardar clasificación",
                    type="primary",
                    use_container_width=True,
                    key=f"save_{selected_row['id']}",
                    disabled=(selected_row.get("estado") == "procesado"),
                ):
                    try:
                        concepto_id = (
                            conc_ids[conc_labels.index(concepto_sel)]
                            if concepto_sel
                            else None
                        )
                        if not concepto_id:
                            st.error("❌ Concepto es obligatorio para clasificar.")
                            st.stop()
                        unidad_id = (
                            None
                            if unidad_sel == "—"
                            else uni_ids[uni_labels.index(unidad_sel)]
                        )
                        propietario_id = (
                            None
                            if propietario_sel == "—"
                            else prop_ids[prop_labels.index(propietario_sel)]
                        )
                        payload = {
                            "concepto_id": concepto_id,
                            "unidad_id": unidad_id,
                            "propietario_id": propietario_id,
                            "estado": estado_sel,
                        }
                        repo_mov.update(int(selected_row["id"]), payload)
                        st.success("✅ Movimiento actualizado.")
                        st.rerun()
                    except DatabaseError as e:
                        st.error(f"❌ {e}")

    with tab_upload:
        st.markdown("### 📥 Cargar Excel (parser por banco)")
        st.caption(
            "Detectamos automáticamente BDV, Banesco, Bancamiga o Mercantil. "
            "Previsualiza y confirma antes de guardar en la base de datos."
        )

        if "upload_step" not in st.session_state:
            st.session_state.upload_step = 1
        if "parse_result" not in st.session_state:
            st.session_state.parse_result = None
        if "archivo_nombre" not in st.session_state:
            st.session_state.archivo_nombre = ""
        if "bank_uploader_nonce" not in st.session_state:
            st.session_state.bank_uploader_nonce = 0

        def _importar_movimientos_parsed(movs: list[MovimientoParsed]) -> int:
            inserted = 0
            periodo_json = json_safe_periodo(periodo_db)
            for m in movs:
                payload = {
                    "condominio_id": int(condominio_id),
                    "periodo": periodo_json,
                    "fecha": json_safe_date(m.fecha),
                    "descripcion": (m.concepto or "").strip() or None,
                    "referencia": (m.referencia or "").strip() or None,
                    "tipo": "ingreso" if m.es_ingreso else "egreso",
                    "monto_bs": float(m.monto),
                    "monto_usd": 0.0,
                    "tasa_cambio": 0.0,
                    "estado": "pendiente",
                    "fuente": "excel",
                }
                created = repo_mov.create(payload)
                inserted += 1
                if m.es_ingreso:
                    try:
                        sug = repo_conciliacion.sugerir_vinculacion(
                            int(created["id"]),
                            condominio_id,
                            periodo_db,
                        )
                        ms = (
                            float(sug["pago"]["monto_bs"])
                            if sug and sug.get("pago")
                            else 0.0
                        )
                        tipo_a = clasificar_alerta(
                            float(created.get("monto_bs") or 0),
                            ms,
                            m.fecha,
                            periodo_ym,
                        )
                        repo_mov.update(
                            int(created["id"]),
                            {"tipo_alerta": tipo_a},
                        )
                    except DatabaseError:
                        pass
            return inserted

        step = st.session_state.upload_step

        if step == 1:
            st.markdown("##### Paso 1/3 — Subir archivo")
            file = st.file_uploader(
                "Archivo Excel del banco",
                type=["xlsx"],
                key=f"bank_xlsx_{st.session_state.bank_uploader_nonce}",
            )
            if file is not None:
                if st.session_state.get("_bank_file_stem") != file.name:
                    st.session_state._bank_file_stem = file.name
                    st.session_state.archivo_nombre = file.name
                    st.session_state.parse_result = None
                    st.session_state.upload_step = 1

                st.caption(f"Archivo: **{file.name}**")
                if st.button(
                    "Analizar y previsualizar",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        st.session_state.parse_result = parsear_bytes(file.getvalue())
                        st.session_state.archivo_nombre = file.name
                        st.session_state.upload_step = 2
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error inesperado al analizar: {e}")

        elif step == 2:
            st.markdown("##### Paso 2/3 — Previsualización")
            pr = st.session_state.parse_result
            nombre = st.session_state.archivo_nombre or "—"
            st.caption(f"Archivo: **{nombre}**")

            if pr is None:
                st.warning("No hay resultado de análisis. Vuelve al paso 1.")
                if st.button("← Volver al paso 1"):
                    st.session_state.upload_step = 1
                    st.rerun()
            else:
                err_imp = st.session_state.get("_import_last_error")
                if err_imp:
                    st.error(
                        f"❌ **La importación falló** (no se guardó nada nuevo en este intento):\n\n"
                        f"{err_imp}"
                    )
                    if st.button("Ocultar aviso", key="dismiss_import_err"):
                        del st.session_state["_import_last_error"]
                        st.rerun()

                if pr.banco:
                    st.success(f"🏦 Banco detectado: **{pr.banco}**")
                else:
                    st.error("No se detectó banco.")

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Total ingresos Bs.", f"{pr.total_ingresos:,.2f}")
                with c2:
                    st.metric("Total egresos Bs.", f"{pr.total_egresos:,.2f}")
                with c3:
                    st.metric("Movimientos", len(pr.movimientos))

                if pr.advertencias:
                    with st.expander("⚠️ Advertencias", expanded=False):
                        for a in pr.advertencias:
                            st.caption(a)

                if pr.errores:
                    with st.expander("❌ Errores por fila", expanded=bool(pr.errores)):
                        for e in pr.errores[:200]:
                            st.text(e)
                        if len(pr.errores) > 200:
                            st.caption(f"… y {len(pr.errores) - 200} más.")

                if pr.movimientos:
                    preview_rows = [
                        {
                            "fecha": m.fecha,
                            "referencia": m.referencia,
                            "concepto": m.concepto[:80] + "…"
                            if len(m.concepto) > 80
                            else m.concepto,
                            "monto_bs": m.monto,
                            "tipo": "ingreso" if m.es_ingreso else "egreso",
                        }
                        for m in pr.movimientos
                    ]
                    st.dataframe(
                        preview_rows,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "fecha": st.column_config.DateColumn("Fecha"),
                            "referencia": st.column_config.TextColumn("Referencia"),
                            "concepto": st.column_config.TextColumn("Concepto"),
                            "monto_bs": st.column_config.NumberColumn(
                                "Monto Bs.", format="%.2f"
                            ),
                            "tipo": st.column_config.TextColumn("Tipo"),
                        },
                    )
                else:
                    st.info("No hay movimientos válidos para importar.")

                b1, b2 = st.columns(2)
                with b1:
                    if st.button("← Cambiar archivo", use_container_width=True):
                        st.session_state.upload_step = 1
                        st.session_state.parse_result = None
                        st.session_state.archivo_nombre = ""
                        st.session_state.bank_uploader_nonce = (
                            int(st.session_state.bank_uploader_nonce) + 1
                        )
                        st.rerun()
                with b2:
                    disabled = not pr.movimientos
                    if st.button(
                        "Importar a la base de datos",
                        type="primary",
                        use_container_width=True,
                        disabled=disabled,
                    ):
                        try:
                            with st.spinner(
                                "Importando movimientos en la base de datos… "
                                "No cierres esta pestaña."
                            ):
                                n = _importar_movimientos_parsed(pr.movimientos)
                            st.session_state.pop("_import_last_error", None)
                            st.session_state._import_ok_msg = (
                                f"✅ Se guardaron **{n}** movimientos "
                                f"({pr.banco}) en el período seleccionado."
                            )
                            st.session_state._import_ok_count = n
                            st.session_state._import_ok_banco = pr.banco or ""
                            st.session_state._import_ok_file = nombre
                            st.session_state._import_fire_toast = True
                            st.session_state.upload_step = 3
                            st.rerun()
                        except DatabaseError as err:
                            st.session_state["_import_last_error"] = str(err)
                            st.error(f"❌ {err}")
                            st.rerun()
                        except Exception as err:
                            st.session_state["_import_last_error"] = str(err)
                            st.error(f"❌ Error al importar: {err}")
                            st.rerun()

        elif step == 3:
            st.markdown("##### Paso 3/3 — Importación completada")
            msg = st.session_state.pop(
                "_import_ok_msg", "✅ Importación finalizada correctamente."
            )
            n_ok = st.session_state.pop("_import_ok_count", None)
            banco_ok = st.session_state.pop("_import_ok_banco", "")
            archivo_ok = st.session_state.pop("_import_ok_file", "")

            st.success(msg)
            if n_ok is not None:
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Movimientos guardados", n_ok)
                with m2:
                    st.metric("Banco", banco_ok or "—")
                with m3:
                    st.caption("Archivo")
                    st.write(archivo_ok or "—")
            st.info(
                "Los movimientos ya están en el listado del período. "
                "Puedes revisarlos en la pestaña **📄 Listado** o conciliar en **🔍 Conciliación**."
            )
            if st.session_state.pop("_import_fire_toast", False):
                st.toast("Importación completada", icon="✅")
            if st.button("Cargar otro archivo", type="primary", use_container_width=True):
                st.session_state.upload_step = 1
                st.session_state.parse_result = None
                st.session_state.archivo_nombre = ""
                st.session_state._bank_file_stem = None
                st.session_state.bank_uploader_nonce = (
                    int(st.session_state.bank_uploader_nonce) + 1
                )
                st.rerun()


def _fmt_sugerencia(sug: dict | None) -> tuple[str, str]:
    if not sug or not sug.get("pago"):
        return (
            '<span style="color:#c0392b">❌ Sin coincidencia</span>',
            "red",
        )
    p = sug["pago"]
    ref = p.get("referencia") or p.get("id")
    mb = float(p.get("monto_bs") or 0)
    u = p.get("unidades") or {}
    apt = u.get("codigo") or u.get("numero") or "—"
    conf = sug.get("confianza") or ""
    if conf == "alta":
        return (
            f'<span style="color:#1e8449">✅ Pago #{ref} — Bs. {mb:,.2f} (Apto {apt})</span>',
            "green",
        )
    if conf in ("media", "baja"):
        return (
            f'<span style="color:#b7950b">⚠️ Posible: Pago #{ref} — Bs. {mb:,.2f}</span>',
            "orange",
        )
    return (
        '<span style="color:#c0392b">❌ Sin coincidencia</span>',
        "red",
    )


ALERTA_ETIQUETAS = {
    "sin_pago_sistema": ("🔴", "Sin pago en sistema"),
    "monto_no_coincide": ("🟡", "Monto no coincide"),
    "pago_parcial": ("🟠", "Pago parcial"),
    "pago_superior": ("🟠", "Pago superior a la cuota"),
    "fecha_fuera_periodo": ("🔵", "Fecha fuera de período"),
}


with tab_conciliacion:
    usuario = (st.session_state.get("user_email") or "").strip() or "sistema"

    st.subheader("Resumen del período")
    try:
        estado = repo_conciliacion.obtener_estado_periodo(condominio_id, periodo_db)
    except DatabaseError as e:
        st.error(f"❌ {e}")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Movimientos banco", estado["total_movimientos_banco"])
    with c2:
        st.metric("Conciliados ✅", estado["total_conciliados"])
    with c3:
        st.metric("Sin conciliar ⚠️", estado["total_sin_conciliar"])
    with c4:
        d = float(estado["diferencia"])
        color = "#1e8449" if d == 0 else "#c0392b"
        st.markdown(
            f'<p style="font-size:0.85rem;color:#666">Diferencia Bs.</p>'
            f'<p style="font-size:1.6rem;font-weight:600;color:{color}">'
            f"Bs. {d:,.2f}</p>",
            unsafe_allow_html=True,
        )

    tot = max(estado["total_movimientos_banco"], 1)
    prog = estado["total_conciliados"] / tot
    st.progress(prog, text=f"Progreso: {estado['total_conciliados']} / {tot}")

    st.divider()
    st.subheader("Alertas activas")
    alertas = estado.get("alertas") or []
    if alertas:
        cnt = Counter(
            (a.get("tipo_alerta") or "sin_clasificar") for a in alertas
        )
        lines = []
        for tipo, n in sorted(cnt.items(), key=lambda x: -x[1]):
            if tipo == "sin_clasificar" or not tipo:
                continue
            icon, lab = ALERTA_ETIQUETAS.get(
                tipo, ("⚪", tipo.replace("_", " "))
            )
            lines.append(f"- {icon} **{lab}**: {n} movimiento(s)")
        if lines:
            st.warning("Resumen de alertas en movimientos del período:\n\n" + "\n".join(lines))
        else:
            st.success("✅ Sin alertas pendientes")
    else:
        st.success("✅ Sin alertas pendientes")

    st.divider()
    st.subheader("Movimientos por conciliar")

    try:
        ing_all = repo_mov.get_by_tipo(condominio_id, periodo_db, "ingreso")
    except DatabaseError as e:
        st.error(f"❌ {e}")
        ing_all = []

    pendientes = [r for r in ing_all if not r.get("conciliado")]
    if not pendientes:
        st.info("No hay ingresos pendientes de conciliar.")
    else:
        for r in pendientes:
            mid = int(r["id"])
            try:
                sug = repo_conciliacion.sugerir_vinculacion(
                    mid, condominio_id, periodo_db
                )
            except DatabaseError:
                sug = None

            html_sug, _ = _fmt_sugerencia(sug)
            ta = r.get("tipo_alerta") or "—"
            fecha = r.get("fecha")
            ref = r.get("referencia") or "—"
            monto = float(r.get("monto_bs") or 0)

            st.markdown("---")
            c_a, c_b, c_c, c_d = st.columns([1.2, 1, 1.2, 2.2])
            with c_a:
                st.caption("Fecha")
                st.write(str(fecha)[:10])
            with c_b:
                st.caption("Referencia")
                st.write(ref)
            with c_c:
                st.caption("Monto Bs.")
                st.write(f"Bs. {monto:,.2f}")
            with c_d:
                st.caption("Alerta / sugerencia")
                st.markdown(f"**{ta}**  \n{html_sug}", unsafe_allow_html=True)

            bc1, bc2 = st.columns(2)
            pago_id = None
            if sug and sug.get("pago"):
                pago_id = int(sug["pago"]["id"])
            with bc1:
                if st.button(
                    "✔ Confirmar",
                    key=f"conf_mov_{mid}",
                    disabled=(pago_id is None),
                ):
                    try:
                        repo_conciliacion.confirmar_vinculacion(
                            mid, pago_id, usuario
                        )
                        st.success("✅ Vinculación confirmada.")
                        st.rerun()
                    except DatabaseError as err:
                        st.error(f"❌ {err}")
            with bc2:
                if st.button("✘ Marcar sin pago", key=f"rej_mov_{mid}"):
                    try:
                        repo_conciliacion.rechazar_vinculacion(
                            mid, "sin_pago_sistema", usuario
                        )
                        st.success("Movimiento marcado como sin pago en sistema.")
                        st.rerun()
                    except DatabaseError as err:
                        st.error(f"❌ {err}")

    st.divider()
    st.subheader("⚠️ Pagos registrados sin movimiento bancario")
    try:
        sin_mov = repo_conciliacion.detectar_pagos_sin_movimiento(
            condominio_id, periodo_db
        )
    except DatabaseError as e:
        st.error(f"❌ {e}")
        sin_mov = []

    if not sin_mov:
        st.success("✅ Todos los pagos tienen movimiento bancario")
    else:
        rows_sm = []
        for p in sin_mov:
            u = p.get("unidades") or {}
            unidad = u.get("codigo") or u.get("numero") or "—"
            rows_sm.append(
                {
                    "fecha": p.get("fecha_pago"),
                    "unidad": unidad,
                    "monto_bs": float(p.get("monto_bs") or 0),
                    "metodo": p.get("metodo") or "—",
                    "referencia": p.get("referencia") or "—",
                }
            )
        st.dataframe(
            rows_sm,
            use_container_width=True,
            hide_index=True,
            column_config={
                "fecha": st.column_config.DateColumn("Fecha"),
                "unidad": st.column_config.TextColumn("Unidad"),
                "monto_bs": st.column_config.NumberColumn(
                    "Monto Bs.", format="%.2f"
                ),
                "metodo": st.column_config.TextColumn("Método"),
                "referencia": st.column_config.TextColumn("Referencia"),
            },
        )

    st.divider()
    st.subheader("Cierre de conciliación")
    dif = float(estado["diferencia"])
    if dif == 0:
        st.success("✅ Saldo cuadrado — listo para cerrar conciliación")
        if st.button("🔒 Cerrar conciliación del período", type="primary"):
            try:
                rec = repo_conciliacion.cerrar_conciliacion(
                    condominio_id, periodo_db, usuario
                )
                st.success(
                    f"✅ Conciliación cerrada. Registro id={rec.get('id')} | "
                    f"Período {rec.get('periodo')} | "
                    f"Mov. banco {rec.get('movimientos_banco')} | "
                    f"Conciliados {rec.get('movimientos_conciliados')} | "
                    f"Pagos sin mov. {rec.get('pagos_sin_movimiento')}"
                )
                st.rerun()
            except DatabaseError as e:
                st.error(f"❌ {e}")
    else:
        st.error(
            f"❌ Diferencia de Bs. {dif:,.2f} — no se puede cerrar hasta cuadrar"
        )
