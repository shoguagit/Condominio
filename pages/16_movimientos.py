from collections import Counter
import re

import pandas as pd
import streamlit as st

from config.supabase_client import get_supabase_client
from repositories.movimiento_repository import MovimientoRepository
from repositories.concepto_repository import ConceptoRepository
from repositories.unidad_repository import UnidadRepository
from repositories.propietario_repository import PropietarioRepository
from repositories.conciliacion_repository import ConciliacionRepository
from repositories.conciliacion_cedula_repository import ConciliacionCedulaRepository
from components.header import render_header
from components.breadcrumb import render_breadcrumb
from utils.auth import check_authentication, require_condominio
from utils.bank_parser import MovimientoParsed, es_duplicado, parsear_bytes
from utils.conciliacion import clasificar_alerta
from utils.conciliacion_automatica import procesar_conciliacion_automatica
from utils.cedula_extractor import extraer_cedulas
from utils.error_handler import DatabaseError
from utils.supabase_compat import json_safe_date, json_safe_periodo
from utils.validators import validate_periodo, periodo_to_date_str


def convertir_periodo(periodo_mmyyyy: str) -> str:
    """'01/2026' → '2026-01' (YYYY-MM). Vacío si formato inválido."""
    try:
        s = str(periodo_mmyyyy or "").strip()
        partes = s.split("/")
        if len(partes) != 2:
            return ""
        mm, yyyy = partes[0].strip().zfill(2), partes[1].strip()
        if not mm.isdigit() or not yyyy.isdigit() or len(yyyy) != 4:
            return ""
        im = int(mm)
        if im < 1 or im > 12:
            return ""
        return f"{yyyy}-{mm}"
    except Exception:
        return ""


def mes_proceso_a_mmyyyy_default(raw: str) -> str:
    """Valor inicial del selector: mes_proceso suele ser YYYY-MM-01 → MM/YYYY."""
    s = str(raw or "").strip()
    if len(s) >= 10 and re.match(r"^\d{4}-\d{2}-\d{2}", s):
        y, m, _ = s[:10].split("-")
        return f"{m}/{y}"
    if re.match(r"^\d{1,2}/\d{4}$", s):
        return s
    return ""


def detectar_periodo_archivo(
    movimientos: list[MovimientoParsed],
    fallback_periodo_db: str,
) -> str:
    """
    Período YYYY-MM-01 más frecuente según las fechas del archivo.
    Si no hay fechas, intenta mes_proceso y luego fallback_periodo_db.
    """
    periodos = [
        f"{m.fecha.year}-{str(m.fecha.month).zfill(2)}-01"
        for m in movimientos
        if getattr(m, "fecha", None) is not None
    ]
    if periodos:
        return Counter(periodos).most_common(1)[0][0]
    raw = str(st.session_state.get("mes_proceso") or "").strip()
    if raw:
        ok, _, pdb = periodo_to_date_str(raw)
        if ok and pdb:
            return pdb[:10]
    return (fallback_periodo_db or "")[:10]


st.set_page_config(page_title="Movimientos Bancarios", page_icon="🏦", layout="wide")
check_authentication()
render_header()
render_breadcrumb("Movimientos Bancarios")

condominio_id = require_condominio()

# Bump cuando cambie la firma/lógica de los repos; si no, Streamlit puede seguir
# usando instancias cacheadas viejas (p. ej. métodos con @safe_db_operation obsoleto).
_REPOS_CACHE_KEY = 4


@st.cache_resource
def get_repos(_snap: int = _REPOS_CACHE_KEY):
    _ = _snap  # forma parte de la clave de caché; subir _REPOS_CACHE_KEY al cambiar repos
    client = get_supabase_client()
    return (
        MovimientoRepository(client),
        ConceptoRepository(client),
        UnidadRepository(client),
        PropietarioRepository(client),
        ConciliacionRepository(client),
        ConciliacionCedulaRepository(client),
    )


repo_mov, repo_concepto, repo_uni, repo_prop, repo_conciliacion, repo_conc_ced = (
    get_repos()
)

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

        def _existentes_para_duplicados(rows: list[dict]) -> list[dict]:
            out: list[dict] = []
            for r in rows or []:
                out.append(
                    {
                        "condominio_id": r.get("condominio_id"),
                        "referencia": str(r.get("referencia") or "").strip(),
                        "monto": float(r.get("monto_bs") or 0),
                        "fecha": r.get("fecha"),
                        "concepto": str(r.get("descripcion") or "").strip(),
                    }
                )
            return out

        def _importar_movimientos_parsed(
            movs: list[MovimientoParsed],
            periodo_import_db: str,
        ) -> tuple[int, int, int]:
            """Retorna (insertados, omitidos_por_duplicado, pagos_auto_cedula)."""
            inserted = 0
            skipped = 0
            conciliados_auto = 0
            cid = int(condominio_id)
            periodo_ym_imp = periodo_import_db[:7]
            try:
                raw_ex = repo_mov.get_all(condominio_id, periodo_import_db)
            except DatabaseError:
                raw_ex = []
            existentes = _existentes_para_duplicados(raw_ex)
            periodo_json = json_safe_periodo(periodo_import_db)

            for m in movs:
                if es_duplicado(m, existentes, cid):
                    skipped += 1
                    continue
                payload = {
                    "condominio_id": cid,
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
                existentes.append(
                    {
                        "condominio_id": cid,
                        "referencia": str(m.referencia or "").strip(),
                        "monto": float(m.monto),
                        "fecha": json_safe_date(m.fecha),
                        "concepto": (m.concepto or "").strip(),
                    }
                )
                if m.es_ingreso:
                    movimiento_dict = {
                        "id": int(created["id"]),
                        "descripcion": m.concepto,
                        "monto_bs": float(m.monto),
                        "tipo": "ingreso",
                        "referencia": m.referencia,
                        "fecha": str(m.fecha),
                    }
                    resultado_conc = procesar_conciliacion_automatica(
                        movimiento=movimiento_dict,
                        condominio_id=cid,
                        periodo=periodo_import_db[:7],
                    )
                    if resultado_conc.get("pagos_registrados", 0) > 0:
                        conciliados_auto += resultado_conc["pagos_registrados"]
                    if not resultado_conc.get("procesado"):
                        try:
                            sug = repo_conciliacion.sugerir_vinculacion(
                                int(created["id"]),
                                condominio_id,
                                periodo_import_db,
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
                                periodo_ym_imp,
                            )
                            repo_mov.update(
                                int(created["id"]),
                                {"tipo_alerta": tipo_a},
                            )
                        except DatabaseError:
                            pass
            return inserted, skipped, conciliados_auto

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
                        pr_new = parsear_bytes(file.getvalue())
                        st.session_state.parse_result = pr_new
                        st.session_state.archivo_nombre = file.name
                        st.session_state.pop("periodo_import_override", None)
                        pdet = detectar_periodo_archivo(
                            pr_new.movimientos, periodo_db
                        )
                        if len(pdet) >= 10:
                            st.session_state["_periodo_import_default_mm"] = (
                                f"{pdet[5:7]}/{pdet[:4]}"
                            )
                        else:
                            st.session_state["_periodo_import_default_mm"] = (
                                mes_proceso_a_mmyyyy_default(
                                    str(st.session_state.get("mes_proceso") or "")
                                )
                                or mes_proceso_a_mmyyyy_default(periodo_db)
                            )
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

                _def_mm = st.session_state.get("_periodo_import_default_mm") or ""
                if not _def_mm:
                    _pd = detectar_periodo_archivo(pr.movimientos, periodo_db)
                    _def_mm = (
                        f"{_pd[5:7]}/{_pd[:4]}" if len(_pd) >= 10 else ""
                    ) or mes_proceso_a_mmyyyy_default(periodo_db)

                st.divider()
                st.markdown("##### Período contable del archivo")
                st.info(
                    f"Período detectado (mes más frecuente en las fechas del archivo): "
                    f"**{_def_mm}**. Ajusta solo si el extracto mezcla varios meses."
                )
                periodo_override = st.text_input(
                    "📅 Período del archivo (MM/YYYY)",
                    value=_def_mm,
                    key="periodo_import_override",
                    help="Detectado automáticamente. Corrígelo si el archivo "
                    "tiene fechas de varios meses.",
                )
                _ym_imp = convertir_periodo(periodo_override)
                periodo_import = f"{_ym_imp}-01" if _ym_imp else ""
                if periodo_override.strip() and not _ym_imp:
                    st.warning(
                        "⚠️ Formato de período no reconocido. Use **MM/YYYY** (ej: 01/2026)."
                    )

                b1, b2 = st.columns(2)
                with b1:
                    if st.button("← Cambiar archivo", use_container_width=True):
                        st.session_state.upload_step = 1
                        st.session_state.parse_result = None
                        st.session_state.archivo_nombre = ""
                        st.session_state.pop("periodo_import_override", None)
                        st.session_state.bank_uploader_nonce = (
                            int(st.session_state.bank_uploader_nonce) + 1
                        )
                        st.rerun()
                with b2:
                    disabled = not pr.movimientos or not periodo_import
                    if st.button(
                        "Importar a la base de datos",
                        type="primary",
                        use_container_width=True,
                        disabled=disabled,
                    ):
                        try:
                            if not periodo_import or len(periodo_import) < 10:
                                raise DatabaseError(
                                    "Período inválido. Indique MM/YYYY correcto."
                                )
                            with st.spinner(
                                "Importando movimientos en la base de datos… "
                                "No cierres esta pestaña."
                            ):
                                n, n_skip, n_auto = _importar_movimientos_parsed(
                                    pr.movimientos,
                                    periodo_import,
                                )
                            st.session_state.pop("_import_last_error", None)
                            st.session_state._import_ok_msg = (
                                f"✅ Se guardaron **{n}** movimientos "
                                f"({pr.banco}) en período **{periodo_import}**. "
                                f"Omitidos por duplicado: **{n_skip}**."
                            )
                            st.session_state._import_ok_auto = int(n_auto or 0)
                            st.session_state._import_ok_count = n
                            st.session_state._import_ok_skipped = n_skip
                            st.session_state._import_ok_banco = pr.banco or ""
                            st.session_state._import_ok_file = nombre
                            st.session_state._import_ok_periodo = periodo_import
                            st.session_state._import_fire_toast = True
                            st.session_state.upload_step = 3
                            st.rerun()
                        except DatabaseError as err:
                            err_s = str(err)
                            if (
                                "row-level security" in err_s.lower()
                                or "42501" in err_s
                            ):
                                err_s = (
                                    f"{err_s}\n\n**Qué hacer:** En Supabase → **SQL Editor**, "
                                    "ejecute el script **`scripts/fase4d_movimientos_rls_migration.sql`** "
                                    "del repositorio (políticas RLS para `movimientos`). "
                                    "Después, si aplica: **Settings → API → Reload schema**."
                                )
                            st.session_state["_import_last_error"] = err_s
                            st.error(f"❌ {err_s}")
                            st.rerun()
                        except Exception as err:
                            err_s = str(err)
                            if (
                                "row-level security" in err_s.lower()
                                or "42501" in err_s
                            ):
                                err_s = (
                                    f"{err_s}\n\n**Qué hacer:** En Supabase → **SQL Editor**, "
                                    "ejecute **`scripts/fase4d_movimientos_rls_migration.sql`**."
                                )
                            st.session_state["_import_last_error"] = err_s
                            st.error(f"❌ Error al importar: {err_s}")
                            st.rerun()

        elif step == 3:
            st.markdown("##### Paso 3/3 — Importación completada")
            msg = st.session_state.pop(
                "_import_ok_msg", "✅ Importación finalizada correctamente."
            )
            n_ok = st.session_state.pop("_import_ok_count", None)
            n_skip = st.session_state.pop("_import_ok_skipped", None)
            banco_ok = st.session_state.pop("_import_ok_banco", "")
            archivo_ok = st.session_state.pop("_import_ok_file", "")
            periodo_ok = st.session_state.pop("_import_ok_periodo", None)

            st.success(msg)
            n_auto = int(st.session_state.pop("_import_ok_auto", 0) or 0)
            if n_auto > 0:
                st.success(
                    f"✅ {n_auto} pagos registrados automáticamente por cédula detectada"
                )
            if n_ok is not None:
                m1, m2, m3, m4, m5 = st.columns(5)
                with m1:
                    st.metric("Movimientos guardados", n_ok)
                with m2:
                    st.metric("Omitidos (duplicado)", n_skip if n_skip is not None else 0)
                with m3:
                    st.metric("Período (BD)", periodo_ok or "—")
                with m4:
                    st.metric("Banco", banco_ok or "—")
                with m5:
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

    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        _default_conc = mes_proceso_a_mmyyyy_default(
            str(st.session_state.get("mes_proceso") or "")
        )
        periodo_conc = st.text_input(
            "Período a conciliar (MM/YYYY)",
            value=_default_conc,
            key="periodo_conciliacion",
            help="Puede conciliar cualquier período, no solo el mes activo de carga.",
        )
    with col_p2:
        st.caption(
            "Este período solo aplica a **Conciliación**. "
            "La carga y el listado siguen usando el período superior (YYYY-MM-01)."
        )

    periodo_ym_conc = convertir_periodo(periodo_conc)
    if not periodo_ym_conc:
        st.error("❌ Período inválido. Use formato **MM/YYYY** (ej: 01/2026).")
    else:
        periodo_db_conc = f"{periodo_ym_conc}-01"

        st.subheader("Resumen del período")
        estado = None
        try:
            estado = repo_conciliacion.obtener_estado_periodo(
                condominio_id, periodo_db_conc
            )
        except DatabaseError as e:
            st.error(f"❌ {e}")

        if estado is not None:
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
                ing_all = repo_mov.get_by_tipo(condominio_id, periodo_db_conc, "ingreso")
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
                            mid, condominio_id, periodo_db_conc
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
                    condominio_id, periodo_db_conc
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
            st.subheader("📋 Pagos registrados automáticamente")
            st.caption(
                "Movimientos conciliados al importar por cédula detectada en la descripción."
            )
            filtro_tipo_auto = st.selectbox(
                "Filtrar por tipo de pago",
                options=["Todos", "total", "parcial", "extraordinario"],
                key="filtro_pago_auto_cedula",
            )
            try:
                pagos_auto = repo_conc_ced.listar_pagos_automaticos_periodo(
                    condominio_id,
                    periodo_db_conc,
                    None if filtro_tipo_auto == "Todos" else filtro_tipo_auto,
                )
            except DatabaseError as e:
                st.error(f"❌ {e}")
                pagos_auto = []
            except Exception:
                st.warning(
                    "No se pudo cargar la tabla de pagos automáticos por cédula. "
                    "Recarga la página. Si el error continúa, revise permisos RLS en Supabase "
                    "para `pagos` / `movimientos` / `unidades`."
                )
                pagos_auto = []

            if not pagos_auto:
                st.info("No hay pagos automáticos por cédula en este período.")
            else:
                rows_pa: list[dict] = []
                for p in pagos_auto:
                    mov = p.get("movimientos") or {}
                    desc = str(mov.get("descripcion") or "")
                    ceds = extraer_cedulas(desc)
                    ced_str = ", ".join(ceds) if ceds else "—"
                    u = p.get("unidades") or {}
                    unidad = (u.get("codigo") or u.get("numero") or "—")
                    conc = mov.get("conciliado")
                    estado_lab = "Conciliado" if conc else "Pendiente"
                    rows_pa.append(
                        {
                            "fecha": mov.get("fecha"),
                            "referencia": mov.get("referencia") or p.get("referencia"),
                            "descripcion": desc[:120] + ("…" if len(desc) > 120 else ""),
                            "cedula_detectada": ced_str,
                            "unidad": unidad,
                            "monto_bs": float(p.get("monto_bs") or 0),
                            "tipo_pago": p.get("tipo_pago") or "—",
                            "estado": estado_lab,
                        }
                    )
                st.dataframe(
                    rows_pa,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "fecha": st.column_config.DateColumn("Fecha"),
                        "referencia": st.column_config.TextColumn("Referencia"),
                        "descripcion": st.column_config.TextColumn("Descripción"),
                        "cedula_detectada": st.column_config.TextColumn(
                            "Cédula detectada"
                        ),
                        "unidad": st.column_config.TextColumn("Unidad"),
                        "monto_bs": st.column_config.NumberColumn(
                            "Monto Bs.", format="%.2f"
                        ),
                        "tipo_pago": st.column_config.TextColumn("Tipo pago"),
                        "estado": st.column_config.TextColumn("Estado"),
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
                            condominio_id, periodo_db_conc, usuario
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
