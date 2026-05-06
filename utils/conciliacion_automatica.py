"""Orquestación: movimiento bancario → pago(s) por cédula en descripción."""

from __future__ import annotations

import logging
from datetime import date

from config.supabase_client import get_supabase_client
from repositories.conciliacion_cedula_repository import ConciliacionCedulaRepository
from repositories.presupuesto_repository import fetch_presupuesto_si_existe
from utils.cedula_extractor import clasificar_pago, extraer_cedulas
from utils.indiviso_cuota import cuota_bs_desde_presupuesto
from utils.tasa_bcv_resolver import resolver_tasa_para_fecha
from utils.sincronizar_estado_pago_unidad import sincronizar_estado_pago_unidad
from utils.supabase_compat import json_safe_periodo
from utils.asignacion_movimientos_cuotas import mejor_asignacion_montos_a_cuotas

logger = logging.getLogger(__name__)


def _cuota_referencia_unidad(
    repo: ConciliacionCedulaRepository,
    u: dict,
    periodo_db: str,
    presupuesto_bs: float,
) -> float:
    """
    Cuota esperada del período: cuotas_unidad.cuota_calculada_bs si existe;
    si no, presupuesto del mes × indiviso % de la unidad.
    """
    uid = int(u["unidad_id"])
    c = repo.obtener_cuota_unidad(uid, periodo_db)
    if c > 0:
        return float(c)
    pct = float(u.get("indiviso_pct") or 0)
    if presupuesto_bs > 0 and pct > 0:
        return float(cuota_bs_desde_presupuesto(presupuesto_bs, pct))
    return 0.0


def _elegir_unidad_por_proximidad_cuota(
    repo: ConciliacionCedulaRepository,
    unidades: list[dict],
    monto_bs: float,
    periodo_db: str,
    presupuesto_bs: float,
) -> list[dict]:
    """
    Si hay varias unidades para la misma cédula, elige la que minimiza
    |monto_banco − cuota_esperada| (cuota del período o derivada por indiviso).
    Empata por código de unidad.
    """
    if len(unidades) <= 1:
        return unidades
    scored: list[tuple[float, float, dict]] = []
    for u in unidades:
        cref = _cuota_referencia_unidad(repo, u, periodo_db, presupuesto_bs)
        diff = abs(float(monto_bs) - cref) if cref > 0 else float("inf")
        scored.append((diff, cref, u))
    scored.sort(key=lambda x: (x[0], (x[2].get("codigo_unidad") or "").upper()))
    best_diff, best_cref, best_u = scored[0]
    if best_diff < float("inf"):
        logger.warning(
            "CONC_AUTO: %s unidades para la misma cédula; se asigna %s "
            "(cuota_ref≈%.2f Bs., |monto−cuota|=%.2f)",
            len(unidades),
            best_u.get("codigo_unidad"),
            float(best_cref),
            float(best_diff),
        )
    else:
        logger.warning(
            "CONC_AUTO: %s unidades sin cuota de referencia; se asigna %s (orden por código)",
            len(unidades),
            best_u.get("codigo_unidad"),
        )
    return [best_u]


def _periodo_fecha_db(periodo: str) -> str:
    s = (periodo or "").strip()
    if len(s) == 7 and s[4] == "-":
        return f"{s}-01"
    return json_safe_periodo(s)[:10]


def procesar_conciliacion_automatica(
    movimiento: dict,
    condominio_id: int,
    periodo: str,
    *,
    unidades_precargadas: list[dict] | None = None,
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

        if unidades_precargadas is not None:
            unidades = list(unidades_precargadas)
            logger.warning(
                "CONC_AUTO: usando %s unidad(es) precargada(s) (asignación por lote)",
                len(unidades),
            )
        else:
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
        obs_mov = str(movimiento.get("descripcion") or "").strip()
        if len(obs_mov) > 8000:
            obs_mov = obs_mov[:8000]

        try:
            fp_d = date.fromisoformat(fecha_pago) if len(fecha_pago) >= 10 else date.today()
        except ValueError:
            fp_d = date.today()

        t_bcv = None
        try:
            t_bcv, _ = resolver_tasa_para_fecha(client, fp_d)
        except Exception:
            logger.warning("CONC_AUTO: resolver tasa BCV falló; uso tasa sesión", exc_info=True)
        tasa_pago = float(t_bcv) if t_bcv and t_bcv > 0 else float(tasa)
        if tasa_pago <= 0:
            tasa_pago = 1.0

        pres_row = fetch_presupuesto_si_existe(client, int(condominio_id), periodo_db)
        pres_bs = float((pres_row or {}).get("monto_bs") or 0)

        if unidades_precargadas is None:
            unidades = _elegir_unidad_por_proximidad_cuota(
                repo, unidades, monto_bs, periodo_db, pres_bs
            )

        pagos_nuevos = 0
        first_pago_id: int | None = None
        last_tipo = "total"
        unidades_limpias: list[dict] = []

        for u in unidades:
            uid = int(u["unidad_id"])
            cuota = _cuota_referencia_unidad(repo, u, periodo_db, pres_bs)
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
                tasa_cambio=float(tasa_pago),
                propietario_id=u.get("propietario_id"),
                observaciones=obs_mov or None,
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


def procesar_grupo_movimientos_misma_cedula(
    movimientos: list[dict],
    condominio_id: int,
    periodo: str,
) -> dict:
    """
    Varios ingresos del mismo período con la misma cédula en la descripción:
    asigna cada movimiento a **una unidad distinta** cuando hay varias unidades,
    minimizando en conjunto sum |monto − cuota| (no cada movimiento por separado).
    """
    vacio_agg = {
        "procesado": False,
        "cedulas_encontradas": [],
        "unidades_vinculadas": [],
        "pagos_registrados": 0,
        "movimientos_con_pago": 0,
        "tipo_pago": "",
        "motivo_omision": None,
    }
    try:
        if not movimientos:
            return {**vacio_agg, "motivo_omision": "sin_movimientos"}

        client = get_supabase_client()
        repo = ConciliacionCedulaRepository(client)

        pend: list[dict] = []
        for m in movimientos:
            mid = m.get("id")
            if mid is None:
                continue
            if repo.movimiento_ya_conciliado(int(mid)):
                continue
            pend.append(m)

        if not pend:
            return {**vacio_agg, "motivo_omision": "ya_conciliados"}

        if len(pend) == 1:
            m0 = pend[0]
            movimiento_dict = {
                "id": int(m0["id"]),
                "descripcion": m0.get("descripcion") or "",
                "monto_bs": float(m0.get("monto_bs") or 0),
                "tipo": "ingreso",
                "referencia": m0.get("referencia") or "",
                "fecha": str(m0.get("fecha") or "")[:10],
            }
            return procesar_conciliacion_automatica(
                movimiento_dict, condominio_id, periodo
            )

        texto0 = str(pend[0].get("descripcion") or "")
        cedulas = extraer_cedulas(texto0)
        if not cedulas:
            return {**vacio_agg, "motivo_omision": "sin_cedula"}

        unidades = repo.buscar_unidades_por_cedula(cedulas, int(condominio_id))
        if not unidades:
            return {
                **vacio_agg,
                "cedulas_encontradas": cedulas,
                "motivo_omision": "sin_coincidencia",
            }

        periodo_db = _periodo_fecha_db(periodo)
        pres_row = fetch_presupuesto_si_existe(client, int(condominio_id), periodo_db)
        pres_bs = float((pres_row or {}).get("monto_bs") or 0)

        cuotas = [
            _cuota_referencia_unidad(repo, u, periodo_db, pres_bs) for u in unidades
        ]
        montos = [float(m.get("monto_bs") or 0) for m in pend]

        assign_j = mejor_asignacion_montos_a_cuotas(montos, cuotas)
        logger.warning(
            "CONC_AUTO lote: %s mov., %s und.; índices unidad asignados %s cuotas=%s montos=%s",
            len(pend),
            len(unidades),
            assign_j,
            [round(c, 2) for c in cuotas],
            [round(x, 2) for x in montos],
        )

        total_pagos = 0
        movs_ok = 0
        last_tipo = ""
        all_uv: list[dict] = []

        for i, m in enumerate(pend):
            u_pick = unidades[int(assign_j[i]) % len(unidades)]
            movimiento_dict = {
                "id": int(m["id"]),
                "descripcion": m.get("descripcion") or "",
                "monto_bs": float(m.get("monto_bs") or 0),
                "tipo": "ingreso",
                "referencia": m.get("referencia") or "",
                "fecha": str(m.get("fecha") or "")[:10],
            }
            res = procesar_conciliacion_automatica(
                movimiento_dict,
                condominio_id,
                periodo,
                unidades_precargadas=[u_pick],
            )
            pr = int(res.get("pagos_registrados") or 0)
            total_pagos += pr
            if pr > 0:
                movs_ok += 1
            if res.get("tipo_pago"):
                last_tipo = str(res.get("tipo_pago"))
            all_uv.extend(res.get("unidades_vinculadas") or [])

        return {
            "procesado": total_pagos > 0,
            "cedulas_encontradas": cedulas,
            "unidades_vinculadas": all_uv,
            "pagos_registrados": total_pagos,
            "movimientos_con_pago": movs_ok,
            "tipo_pago": last_tipo,
            "motivo_omision": None if total_pagos > 0 else "sin_pago_nuevo",
        }
    except Exception:
        logger.warning("CONC_AUTO lote: error_interno", exc_info=True)
        return {
            **vacio_agg,
            "motivo_omision": "error_interno",
        }
