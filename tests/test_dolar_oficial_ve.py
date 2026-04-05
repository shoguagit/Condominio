"""Tests sin red para tasas BCV (parse + búsqueda por fecha)."""

from datetime import date

import pytest

from utils import dolar_oficial_ve as dov


def test_parse_filtra_paralelo_y_consolida_fechas() -> None:
    raw = [
        {"fuente": "oficial", "fecha": "2026-03-10", "promedio": 100.0},
        {"fuente": "paralelo", "fecha": "2026-03-10", "promedio": 999.0},
        {"fuente": "oficial", "fecha": "2026-03-12", "promedio": 110.0},
    ]
    s = dov.parse_historico_oficial_json(raw)
    assert s == [(date(2026, 3, 10), 100.0), (date(2026, 3, 12), 110.0)]


def test_tasa_ultimo_dia_menor_o_igual() -> None:
    series = [
        (date(2026, 3, 10), 400.0),
        (date(2026, 3, 14), 450.0),
    ]
    r, lbl = dov.tasa_bcv_bs_por_usd_para_fecha_con_serie(date(2026, 3, 12), series)
    assert r == 400.0
    assert "2026-03-10" in lbl

    r2, lbl2 = dov.tasa_bcv_bs_por_usd_para_fecha_con_serie(date(2026, 3, 14), series)
    assert r2 == 450.0
    assert lbl2 == "2026-03-14"


def test_tasa_antes_del_historico() -> None:
    series = [(date(2026, 1, 5), 300.0)]
    r, lbl = dov.tasa_bcv_bs_por_usd_para_fecha_con_serie(date(2020, 1, 1), series)
    assert r == 300.0
    assert "hist" in lbl.lower() or "antes" in lbl.lower()


def test_monto_usd() -> None:
    assert dov.monto_usd_desde_bs(1000.0, 400.0) == pytest.approx(2.5)
