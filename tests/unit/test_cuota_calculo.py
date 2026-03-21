"""Cuota mensual = presupuesto × (indiviso % / 100)."""
import pytest

from utils.indiviso_cuota import cuota_bs_desde_presupuesto


def test_cuota_basica():
    assert cuota_bs_desde_presupuesto(6_000_000, 4.2) == pytest.approx(252_000.0)


def test_cuota_cero_presupuesto():
    assert cuota_bs_desde_presupuesto(0, 50) == 0.0


def test_cuota_redondeo():
    assert cuota_bs_desde_presupuesto(100, 33.33) == pytest.approx(33.33)
