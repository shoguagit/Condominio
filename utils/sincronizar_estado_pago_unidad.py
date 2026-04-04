"""
Recalcula `unidades.estado_pago` tras registrar un pago (misma lógica que Pagos y Cobros).
"""

from __future__ import annotations

import logging

from supabase import Client

from repositories.cobro_extraordinario_repository import CobroExtraordinarioRepository
from repositories.mora_repository import MoraRepository
from repositories.pago_repository import PagoRepository
from repositories.presupuesto_repository import fetch_presupuesto_si_existe
from repositories.unidad_repository import UnidadRepository
from utils.cierre_mensual import estado_pago_db
from utils.error_handler import DatabaseError
from utils.indiviso_cuota import cuota_bs_desde_presupuesto

logger = logging.getLogger(__name__)


def sincronizar_estado_pago_unidad(
    client: Client,
    condominio_id: int,
    unidad_id: int,
    periodo_db: str,
) -> None:
    """Actualiza solo `estado_pago`; ignora errores para no tumbar la importación."""
    try:
        repo_uni = UnidadRepository(client)
        repo_pago = PagoRepository(client)
        repo_mora = MoraRepository(client)
        repo_cobro_ext = CobroExtraordinarioRepository(client)

        u_row = repo_uni.get_by_id(unidad_id)
        if not u_row:
            return
        pres_row = fetch_presupuesto_si_existe(client, condominio_id, periodo_db)
        presupuesto_mes = float(pres_row["monto_bs"]) if pres_row else 0.0

        saldo_ux = float(u_row.get("saldo") or 0)
        pct_x = float(u_row.get("indiviso_pct") or 0)
        cuota_x = (
            cuota_bs_desde_presupuesto(presupuesto_mes, pct_x) if presupuesto_mes else 0.0
        )
        try:
            mora_cfg_x = repo_mora.obtener_config(condominio_id)
        except DatabaseError:
            mora_cfg_x = {"activa": False, "pct_mora": 0.0}
        anio_x = int(periodo_db[:4])
        mes_x = int(periodo_db[5:7])
        try:
            mora_aplica_x = repo_mora.mora_aplica_hoy(condominio_id, anio_x, mes_x)
        except Exception:
            mora_aplica_x = False
        mora_m_x = 0.0
        if mora_aplica_x and mora_cfg_x.get("activa") and saldo_ux > 0:
            mora_m_x = MoraRepository.calcular_mora_unidad(
                saldo_ux, cuota_x, float(mora_cfg_x.get("pct_mora") or 0)
            )
        try:
            ya_x = repo_pago.get_total_pagado_unidad(unidad_id, periodo_db)
        except DatabaseError:
            ya_x = 0.0
        p_ym = periodo_db[:7] if periodo_db else ""
        try:
            cob_x = repo_cobro_ext.total_por_unidad(unidad_id, p_ym)
        except DatabaseError:
            cob_x = 0.0
        total_x = round(saldo_ux + cuota_x + cob_x + mora_m_x - ya_x, 2)
        ya_eff = max(0.0, float(ya_x))
        ep = estado_pago_db(total_x, ya_eff)
        repo_uni.update(unidad_id, {"estado_pago": ep})
    except Exception as e:
        logger.warning("sincronizar_estado_pago_unidad: %s", e)
