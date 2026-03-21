"""Tests — lógica pura de conciliación (Fase 4-C)."""

from datetime import date

from utils.conciliacion import clasificar_alerta, evaluar_estado_conciliacion


def test_clasificar_alerta_pago_parcial():
    assert (
        clasificar_alerta(200.0, 252.0, date(2026, 2, 10), "2026-02") == "pago_parcial"
    )


def test_clasificar_alerta_pago_superior():
    assert (
        clasificar_alerta(300.0, 252.0, date(2026, 2, 10), "2026-02")
        == "pago_superior"
    )


def test_clasificar_alerta_monto_coincide():
    assert (
        clasificar_alerta(252.0, 252.0, date(2026, 2, 1), "2026-02") is None
    )


def test_clasificar_alerta_fecha_fuera_periodo():
    assert (
        clasificar_alerta(252.0, 252.0, date(2026, 1, 15), "2026-02")
        == "fecha_fuera_periodo"
    )


def test_diferencia_cero_permite_cierre():
    assert evaluar_estado_conciliacion(1000.0, 1000.0) == "conciliado"


def test_diferencia_no_cero_bloquea_cierre():
    assert evaluar_estado_conciliacion(1000.0, 999.0) == "con_diferencias"
