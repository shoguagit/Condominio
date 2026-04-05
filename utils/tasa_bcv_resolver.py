"""
Resuelve tasa BCV oficial para una fecha de pago: primero BD (tasas_bcv_dia),
si no alcanza sincroniza desde la API y vuelve a consultar.
"""

from __future__ import annotations

import logging
from datetime import date

from supabase import Client

from repositories.tasa_bcv_repository import TasaBcvRepository
from utils.dolar_oficial_ve import tasa_bcv_bs_por_usd_para_fecha_con_serie

logger = logging.getLogger(__name__)


def _to_date(fecha_pago: date | str) -> date:
    if isinstance(fecha_pago, date):
        return fecha_pago
    return date.fromisoformat(str(fecha_pago).strip()[:10])


def resolver_tasa_para_fecha(client: Client, fecha_pago: date | str) -> tuple[float | None, str]:
    """
    Devuelve (tasa Bs por 1 USD, etiqueta).
    Usa la tabla tasas_bcv_dia; si está vacía o no cubre la fecha, llama a la API y hace upsert.
    """
    try:
        fp = _to_date(fecha_pago)
    except ValueError:
        return None, "fecha_invalida"

    repo = TasaBcvRepository(client)

    def _lookup_from_db() -> tuple[float | None, str]:
        row = repo.get_last_on_or_before(fp)
        if row is None:
            return None, "sin_datos_bd"
        used_d, rate = row
        if rate <= 0:
            return None, "tasa_no_positiva"
        if used_d == fp:
            return float(rate), fp.isoformat()
        return float(rate), f"{fp.isoformat()}→{used_d.isoformat()}"

    tasa, meta = _lookup_from_db()
    if tasa is not None:
        return tasa, meta

    merged = repo.merge_from_api()
    if merged <= 0:
        logger.warning("tasa_bcv_resolver: API no devolvió datos al sincronizar")
        return None, "sin_datos_api"

    tasa2, meta2 = _lookup_from_db()
    if tasa2 is not None:
        return tasa2, meta2

    earliest = repo.get_earliest()
    if earliest is None:
        return None, "sin_datos"
    ed, er = earliest
    if er <= 0:
        return None, "tasa_no_positiva"
    if fp < ed:
        return float(er), f"antes_histórico→{ed.isoformat()}"

    series = repo.list_sorted_pairs()
    if not series:
        return None, "sin_datos"
    return tasa_bcv_bs_por_usd_para_fecha_con_serie(fp, series)
