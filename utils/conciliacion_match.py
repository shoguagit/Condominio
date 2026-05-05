"""
Coincidencia movimiento ↔ pagos (solo reglas, sin I/O).
Separado de utils.conciliacion para imports seguros en páginas Streamlit / PDF.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _parse_mov_fecha(d: Any) -> date | None:
    if d is None:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    s = str(d)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def sugerir_vinculacion_desde_filas(mov: dict, pagos: list[dict]) -> dict | None:
    """
    Misma regla que ConciliacionRepository.sugerir_vinculacion, sin consultas.
    Espera mov tipo ingreso con referencia/fecha/monto_bs; pagos con unidades embed.
    """
    if (mov.get("tipo") or "").lower() != "ingreso":
        return None

    ref_m = (mov.get("referencia") or "").strip()
    mb = float(mov.get("monto_bs") or 0)
    f_mov = _parse_mov_fecha(mov.get("fecha"))

    for p in pagos:
        ref_p = (p.get("referencia") or "").strip()
        if ref_m and ref_p and ref_m == ref_p:
            return {"pago": p, "confianza": "alta", "razon": "referencia"}

    if f_mov:
        for p in pagos:
            fp = _parse_mov_fecha(p.get("fecha_pago"))
            if not fp:
                continue
            mp = float(p.get("monto_bs") or 0)
            same_wk = f_mov.isocalendar()[:2] == fp.isocalendar()[:2]
            if abs(mb - mp) <= 1.01 and same_wk:
                return {"pago": p, "confianza": "media", "razon": "monto_semana"}

    if f_mov:
        for p in pagos:
            fp = _parse_mov_fecha(p.get("fecha_pago"))
            if not fp:
                continue
            mp = float(p.get("monto_bs") or 0)
            if (
                f_mov.year == fp.year
                and f_mov.month == fp.month
                and round(mb, 2) == round(mp, 2)
            ):
                return {"pago": p, "confianza": "baja", "razon": "monto_mes"}

    return None
