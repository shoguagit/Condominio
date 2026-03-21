"""
Lógica pura de conciliación bancaria (Fase 4-C). Sin I/O.
"""

from __future__ import annotations

from datetime import date


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
