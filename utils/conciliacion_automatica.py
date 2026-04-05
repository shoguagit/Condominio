"""Orquestación: movimiento bancario → pago(s) por cédula en descripción."""

from __future__ import annotations

import logging

from config.supabase_client import get_supabase_client
from repositories.conciliacion_cedula_repository import ConciliacionCedulaRepository
from utils.cedula_extractor import clasificar_pago, extraer_cedulas
from utils.sincronizar_estado_pago_unidad import sincronizar_estado_pago_unidad
from utils.supabase_compat import json_safe_periodo

logger = logging.getLogger(__name__)


def _periodo_fecha_db(periodo: str) -> str:
    s = (periodo or "").strip()
    if len(s) == 7 and s[4] == "-":
        return f"{s}-01"
    return json_safe_periodo(s)[:10]


def procesar_conciliacion_automatica(
    movimiento: dict,
    condominio_id: int,
    periodo: str,
) -> dict:
    """
    Proceso completo para un movimiento bancario.
    NUNCA propaga excepciones.
    """
    vacio = {
        "procesado": False,
        "cedulas_encontradas": [],
        "unidades_vinculadas": [],
        "pagos_registrados": 0,
        "tipo_pago": "",
        "motivo_omision": None,
    }
    try:
        _desc = str(movimiento.get("descripcion") or "")[:50]
        logger.warning(
            "CONC_AUTO: procesando movimiento %s tipo=%s desc=%s",
            movimiento.get("id"),
            movimiento.get("tipo"),
            _desc,
        )

        if (movimiento.get("tipo") or "").lower() != "ingreso":
            logger.warning("CONC_AUTO: omitido por: no_ingreso")
            return {
                **vacio,
                "motivo_omision": "no_ingreso",
            }

        mid = movimiento.get("id")
        if mid is None:
            logger.warning("CONC_AUTO: omitido por: sin_id_movimiento")
            return {**vacio, "motivo_omision": "sin_id_movimiento"}

        client = get_supabase_client()
        repo = ConciliacionCedulaRepository(client)

        tasa = 0.0
        try:
            import streamlit as st

            tasa = float(st.session_state.get("tasa_cambio", 0) or 0)
        except Exception:
            pass

        if tasa <= 0:
            config = repo.obtener_tasa_condominio(int(condominio_id))
            tasa = float(config.get("tasa_cambio", 0) or 0)

        if tasa <= 0:
            tasa = 1.0

        if repo.movimiento_ya_conciliado(int(mid)):
            logger.warning("CONC_AUTO: omitido por: ya_conciliado")
            return {
                **vacio,
                "motivo_omision": "ya_conciliado",
                "procesado": False,
            }

        texto = movimiento.get("descripcion") or ""
        cedulas = extraer_cedulas(str(texto))
        logger.warning("CONC_AUTO: cédulas encontradas: %s", cedulas)
        if not cedulas:
            logger.warning("CONC_AUTO: omitido por: sin_cedula")
            return {
                **vacio,
                "cedulas_encontradas": [],
                "motivo_omision": "sin_cedula",
            }

        unidades = repo.buscar_unidades_por_cedula(cedulas, int(condominio_id))
        logger.warning("CONC_AUTO: unidades encontradas: %s", unidades)
        if not unidades:
            logger.warning("CONC_AUTO: omitido por: sin_coincidencia")
            return {
                **vacio,
                "cedulas_encontradas": cedulas,
                "motivo_omision": "sin_coincidencia",
            }

        periodo_db = _periodo_fecha_db(periodo)
        monto_bs = float(movimiento.get("monto_bs") or 0)
        fecha_pago = str(movimiento.get("fecha") or "")[:10]
        referencia = str(movimiento.get("referencia") or "").strip()

        pagos_nuevos = 0
        first_pago_id: int | None = None
        last_tipo = "total"
        unidades_limpias: list[dict] = []

        for u in unidades:
            uid = int(u["unidad_id"])
            cuota = repo.obtener_cuota_unidad(uid, periodo_db)
            tipo = clasificar_pago(monto_bs, cuota)
            last_tipo = tipo
            u_out = {k: v for k, v in u.items() if not str(k).startswith("_")}
            u_out["cuota_bs"] = cuota
            unidades_limpias.append(u_out)

            p = repo.registrar_pago_automatico(
                condominio_id=int(condominio_id),
                unidad_id=uid,
                periodo=periodo_db,
                monto_bs=monto_bs,
                fecha_pago=fecha_pago,
                referencia=referencia,
                movimiento_id=int(mid),
                tipo_pago=tipo,
                tasa_cambio=float(tasa),
                propietario_id=u.get("propietario_id"),
            )
            es_dup = bool(p.pop("_es_reutilizado", False))
            if not es_dup:
                pagos_nuevos += 1
                sincronizar_estado_pago_unidad(
                    client, int(condominio_id), uid, periodo_db
                )
            pid = int(p.get("id") or 0)
            if pid and first_pago_id is None:
                first_pago_id = pid

        if first_pago_id is not None and pagos_nuevos > 0:
            repo.marcar_movimiento_conciliado(int(mid), first_pago_id)

        if pagos_nuevos <= 0:
            logger.warning("CONC_AUTO: omitido por: sin_pago_nuevo")

        return {
            "procesado": pagos_nuevos > 0,
            "cedulas_encontradas": cedulas,
            "unidades_vinculadas": unidades_limpias,
            "pagos_registrados": pagos_nuevos,
            "tipo_pago": last_tipo,
            "motivo_omision": None if pagos_nuevos > 0 else "sin_pago_nuevo",
        }
    except Exception:
        logger.warning("CONC_AUTO: omitido por: error_interno", exc_info=True)
        return {
            **vacio,
            "motivo_omision": "error_interno",
        }
