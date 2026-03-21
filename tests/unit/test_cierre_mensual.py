"""Tests lógica cierre mensual (Fase 2)."""

from utils.cierre_mensual import (
    saldo_nuevo_tras_cierre,
    etiqueta_estado_cierre_ui,
    eficiencia_cobro,
    puede_generar_cuotas,
    puede_cerrar_mes,
    periodo_permite_pagos,
)


def test_saldo_nuevo_al_dia():
    assert saldo_nuevo_tras_cierre(0, 252_000, 252_000) == 0.0


def test_saldo_nuevo_moroso():
    assert saldo_nuevo_tras_cierre(0, 252_000, 0) == 252_000.0


def test_saldo_nuevo_parcial():
    assert saldo_nuevo_tras_cierre(0, 252_000, 126_000) == 126_000.0


def test_arrastre_saldo_anterior():
    """Saldo anterior + cuota - pagado = saldo que arrastra."""
    assert saldo_nuevo_tras_cierre(252_000, 252_000, 252_000) == 252_000.0


def test_eficiencia_cobro():
    assert eficiencia_cobro(1_000_000, 720_000) == 72.0
    assert eficiencia_cobro(0, 100) == 0.0


def test_etiquetas_ui():
    assert etiqueta_estado_cierre_ui(0, 100) == "Al día"
    assert etiqueta_estado_cierre_ui(50, 50) == "Parcial"
    assert etiqueta_estado_cierre_ui(100, 0) == "Moroso"


def test_bloqueo_periodo_cerrado():
    assert puede_generar_cuotas("cerrado") is False
    assert puede_generar_cuotas("procesado") is True
    assert puede_cerrar_mes("cerrado") is False
    assert puede_cerrar_mes("procesado") is True
    assert periodo_permite_pagos("cerrado") is False
    assert periodo_permite_pagos("procesado") is True
    assert periodo_permite_pagos(None) is True
