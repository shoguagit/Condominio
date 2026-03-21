"""Tests cobros extraordinarios por indiviso (Fase 4-B)."""

from unittest.mock import MagicMock

import pytest

from repositories.cobro_extraordinario_repository import CobroExtraordinarioRepository
from utils.cobros_extraordinarios import (
    calcular_monto_unidad,
    distribuir_monto_entre_unidades,
    validar_cobro_extraordinario,
)


def test_distribucion_proporcional():
    assert calcular_monto_unidad(1000, 10.0) == 100.0


def test_distribucion_suma_correcta():
    unidades = [
        {"id": 1, "indiviso_pct": 25.0},
        {"id": 2, "indiviso_pct": 25.0},
        {"id": 3, "indiviso_pct": 25.0},
        {"id": 4, "indiviso_pct": 25.0},
    ]
    parts = distribuir_monto_entre_unidades(1000.0, unidades)
    s = sum(m for _, m in parts)
    assert abs(s - 1000.0) <= 0.01


def test_cobro_monto_cero_rechazado():
    with pytest.raises(ValueError, match="monto"):
        validar_cobro_extraordinario("Reparación", 0.0)


def test_cobro_concepto_vacio_rechazado():
    with pytest.raises(ValueError, match="concepto"):
        validar_cobro_extraordinario("", 100.0)
    with pytest.raises(ValueError, match="concepto"):
        validar_cobro_extraordinario("   ", 50.0)


def test_total_por_unidad_sin_cobros():
    client = MagicMock()
    chain = MagicMock()
    client.table.return_value = chain
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    repo = CobroExtraordinarioRepository(client)
    assert repo.total_por_unidad(42, "2026-04") == 0.0
