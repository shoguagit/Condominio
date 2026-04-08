"""Tasa oficial Bs/USD desde DolarAPI (histórico BCV)."""

from __future__ import annotations

import bisect
import logging
from datetime import date
from typing import Any

import requests

logger = logging.getLogger(__name__)

DOLARAPI_HISTORICO_URL = "https://ve.dolarapi.com/v1/historicos/dolares"
REQUEST_TIMEOUT_S = 25


def parse_historico_oficial_json(data: list[dict[str, Any]]) -> list[tuple[date, float]]:
    """Filtra fuente oficial; una fila por fecha (última en JSON gana)."""
    by_day: dict[date, float] = {}
    for row in data or []:
        if str(row.get("fuente") or "").lower() != "oficial":
            continue
        fe = row.get("fecha")
        pr = row.get("promedio")
        if fe is None or pr is None:
            continue
        try:
            d = date.fromisoformat(str(fe)[:10])
            by_day[d] = float(pr)
        except (ValueError, TypeError):
            continue
    return sorted(by_day.items(), key=lambda x: x[0])


def _fetch_historico_oficial() -> list[tuple[date, float]]:
    try:
        r = requests.get(DOLARAPI_HISTORICO_URL, timeout=REQUEST_TIMEOUT_S)
        r.raise_for_status()
        raw = r.json()
        if not isinstance(raw, list):
            return []
        return parse_historico_oficial_json(raw)
    except Exception as e:
        logger.warning("dolar_oficial_ve: fallo al cargar histórico: %s", e)
        return []


def cargar_historico_bcv_oficial() -> list[tuple[date, float]]:
    """Una descarga fresca del histórico (p. ej. scripts de mantenimiento sin caché Streamlit)."""
    return _fetch_historico_oficial()


_cached_historico_loader: object | None = None


def _get_cached_historico() -> list[tuple[date, float]]:
    """Carga con caché Streamlit solo cuando la app llama a tasas_oficiales_ordenadas (evita importar st en CLI)."""
    global _cached_historico_loader
    if _cached_historico_loader is None:
        try:
            import streamlit as st

            _cached_historico_loader = st.cache_data(
                ttl=3600, show_spinner=False
            )(_fetch_historico_oficial)
        except Exception:
            _cached_historico_loader = _fetch_historico_oficial
    fn = _cached_historico_loader  # type: ignore[assignment]
    return fn()  # type: ignore[misc]


def tasas_oficiales_ordenadas() -> list[tuple[date, float]]:
    return _get_cached_historico()


def _to_date(fecha_pago: date | str) -> date:
    if isinstance(fecha_pago, date):
        return fecha_pago
    s = str(fecha_pago).strip()[:10]
    return date.fromisoformat(s)


def tasa_bcv_bs_por_usd_para_fecha_con_serie(
    fecha_pago: date | str,
    series: list[tuple[date, float]],
) -> tuple[float | None, str]:
    """
    Igual que tasa_bcv_bs_por_usd_para_fecha pero con la serie ya cargada
    (p. ej. scripts de una sola ejecución que consultan la API una vez).
    """
    try:
        fp = _to_date(fecha_pago)
    except ValueError:
        return None, "fecha_invalida"

    if not series:
        return None, "sin_datos"

    dates = [x[0] for x in series]
    i = bisect.bisect_right(dates, fp) - 1
    if i >= 0:
        used, rate = series[i][0], float(series[i][1])
        if rate <= 0:
            return None, "tasa_no_positiva"
        if used == fp:
            return rate, fp.isoformat()
        return rate, f"{fp.isoformat()}→{used.isoformat()}"

    rate0 = float(series[0][1])
    if rate0 <= 0:
        return None, "tasa_no_positiva"
    return rate0, f"antes_histórico→{series[0][0].isoformat()}"


def tasa_bcv_bs_por_usd_para_fecha(fecha_pago: date | str) -> tuple[float | None, str]:
    """
    Devuelve (tasa Bs por 1 USD, etiqueta) consultando solo la API (con caché Streamlit).

    En la aplicación use `resolver_tasa_para_fecha(client, fecha)` para leer primero
    la tabla `tasas_bcv_dia` y persistir el histórico en BD.
    """
    return tasa_bcv_bs_por_usd_para_fecha_con_serie(fecha_pago, tasas_oficiales_ordenadas())


def monto_usd_desde_bs(monto_bs: float, tasa_bs_por_usd: float) -> float:
    if tasa_bs_por_usd and tasa_bs_por_usd > 0:
        return round(float(monto_bs) / float(tasa_bs_por_usd), 2)
    return 0.0
