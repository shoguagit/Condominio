"""Suma de indivisos % y límite 100%."""
import pytest

from utils.indiviso_cuota import (
    suma_indivisos_pct,
    valida_no_supera_100_pct,
    valida_suma_exacta_100_pct,
    TOLERANCIA_INDIVISO_PCT,
)


def test_suma_indivisos():
    assert suma_indivisos_pct([4.2, 5.0, 90.8]) == pytest.approx(100.0)


def test_no_supera_100_rechaza():
    ok, msg = valida_no_supera_100_pct(100.5)
    assert ok is False
    assert "100" in msg


def test_no_supera_100_acepta():
    assert valida_no_supera_100_pct(100.0)[0] is True
    assert valida_no_supera_100_pct(99.99)[0] is True


def test_exacta_100_tolerancia():
    assert valida_suma_exacta_100_pct(100.0)[0] is True
    assert valida_suma_exacta_100_pct(100.005)[0] is True
    assert valida_suma_exacta_100_pct(99.995)[0] is True


def test_exacta_100_fuera_tolerancia():
    ok, _ = valida_suma_exacta_100_pct(100.02)
    assert ok is False
    ok2, _ = valida_suma_exacta_100_pct(99.97)
    assert ok2 is False


def test_tolerancia_valor():
    assert TOLERANCIA_INDIVISO_PCT == 0.01
