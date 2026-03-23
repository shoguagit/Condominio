"""
Alertas de coherencia: saldo acumulado vs cuota del mes (primer mes acumulado).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def calcular_alertas_coherencia(
    unidades: list[dict],
    condominio_id: int,
    periodo_db: str,
    obtener_datos: Callable[[int, int, str], dict[str, Any] | None],
    *,
    tolerancia_usd: float = 0.02,
) -> list[dict]:
    """
    Para cada unidad seleccionada: si hay datos de cuota y meses_acumulados == 1,
    verifica que acumulado_usd ≈ cuota_usd.

    ``obtener_datos(unidad_id, condominio_id, periodo_db)`` debe devolver el dict
    de ``obtener_datos_unidad_periodo`` o None.
    """
    periodo = str(periodo_db or "").strip()[:10]
    if len(periodo) == 7:
        periodo = f"{periodo}-01"

    alertas: list[dict] = []
    for u in unidades:
        uid = u.get("unidad_id")
        if uid is None:
            continue
        try:
            datos = obtener_datos(int(uid), int(condominio_id), periodo)
        except Exception as e:
            # No bloquear la página por fallos al consultar cuota (auxiliar)
            logger.warning(
                "calcular_alertas_coherencia: unidad_id=%s periodo=%r omitida: %s",
                uid,
                periodo,
                e,
            )
            continue
        if not datos:
            continue
        if int(datos.get("meses_acumulados") or 0) != 1:
            continue
        acu = float(datos.get("acumulado_usd") or 0)
        cuo = float(datos.get("cuota_usd") or 0)
        if abs(acu - cuo) <= tolerancia_usd:
            continue
        diff = acu - cuo
        cod = str(u.get("unidad_codigo") or "—")
        nom = str(u.get("propietario_nombre") or "—")
        alertas.append(
            {
                "Inmueble": cod,
                "Propietario": nom,
                "Cuota Mes (USD)": f"${cuo:,.2f}",
                "Acumulado US$": f"${acu:,.2f}",
                "Diferencia (USD)": f"${diff:+,.2f}",
            }
        )
    return alertas
