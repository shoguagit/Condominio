"""Tests mora (Fase 4-A): cálculo puro y fecha límite."""

from unittest.mock import MagicMock, patch

import datetime

import pytest

from repositories.mora_repository import MoraRepository

calcular_mora_unidad = MoraRepository.calcular_mora_unidad


def test_mora_base_correcta():
    # saldo_anterior=500, cuota=250, pct=5%
    # base=750, mora=750*0.05=37.50
    assert calcular_mora_unidad(500, 250, 5.0) == 37.50


def test_mora_sin_saldo():
    assert calcular_mora_unidad(0, 0, 5.0) == 0.0


def test_mora_saldo_anterior_negativo():
    assert calcular_mora_unidad(-100, 250, 5.0) == 0.0


def test_mora_saldo_anterior_cero():
    assert calcular_mora_unidad(0, 250, 5.0) == 0.0


def test_mora_pct_cero():
    assert calcular_mora_unidad(500, 250, 0.0) == 0.0


@pytest.fixture
def mora_repo():
    return MoraRepository(MagicMock())


def test_mora_no_aplica_antes_vencimiento(mora_repo):
    condominio_id = 1
    with patch.object(mora_repo._condo_repo, "obtener_dia_limite", return_value=15):
        mock_date = MagicMock()
        mock_date.today.return_value = datetime.date(2026, 3, 10)
        mock_date.side_effect = lambda *args: datetime.date(*args)
        with patch("repositories.mora_repository.date", mock_date):
            assert mora_repo.mora_aplica_hoy(condominio_id, 2026, 3) is False


def test_mora_aplica_despues_vencimiento(mora_repo):
    condominio_id = 1
    with patch.object(mora_repo._condo_repo, "obtener_dia_limite", return_value=15):
        mock_date = MagicMock()
        mock_date.today.return_value = datetime.date(2026, 3, 20)
        mock_date.side_effect = lambda *args: datetime.date(*args)
        with patch("repositories.mora_repository.date", mock_date):
            assert mora_repo.mora_aplica_hoy(condominio_id, 2026, 3) is True
