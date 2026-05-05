"""
Lógica pura de conciliación bancaria (Fase 4-C). Sin I/O.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _fecha_en_periodo(fecha_mov: date, periodo_ym: str) -> bool:
    if not periodo_ym or len(periodo_ym) < 7:
        return True
    try:
        y = int(periodo_ym[0:4])
        m = int(periodo_ym[5:7])
    except (ValueError, TypeError):
        return True
    return fecha_mov.year == y and fecha_mov.month == m


def clasificar_alerta(
    monto_banco: float,
    monto_sistema: float,
    fecha_mov: date,
    periodo: str,
) -> str | None:
    """
    Clasifica alerta según montos y período.
    Orden: fecha fuera de período → sin pago en sistema → parcial/superior → monto distinto → OK.
    """
    if not _fecha_en_periodo(fecha_mov, periodo):
        return "fecha_fuera_periodo"

    ms = float(monto_sistema)
    mb = float(monto_banco)
    if ms <= 0:
        return "sin_pago_sistema"

    if mb < ms * 0.99:
        return "pago_parcial"
    if mb > ms * 1.01:
        return "pago_superior"
    if round(mb, 2) != round(ms, 2):
        return "monto_no_coincide"
    return None


def evaluar_estado_conciliacion(saldo_banco: float, saldo_sistema: float) -> str:
    """'conciliado' si saldos cuadran a 2 decimales; si no, 'con_diferencias'."""
    if round(float(saldo_banco), 2) == round(float(saldo_sistema), 2):
        return "conciliado"
    return "con_diferencias"


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
