"""Tests reportes PDF y lógica de datos (Fase 3).

Requiere ``reportlab`` instalado en el **mismo intérprete** que ejecuta pytest.
Si ``pytest`` usa Python 3.12 pero ``pip install`` instaló en el venv 3.14, fallará.
Use: ``python -m pytest tests/unit/test_reportes.py -v`` (con el ``python`` del venv).
"""

import pytest

pytest.importorskip("reportlab")

from repositories.reporte_repository import ReporteRepository
from utils.pdf_generator import formato_bs, formato_usd, monto_bs_a_usd
from utils.reportes_pdf import pdf_estado_cuenta_individual


def test_formato_bs():
    assert "Bs." in formato_bs(1234.5)
    assert "1,234.50" in formato_bs(1234.5)


def test_formato_usd():
    assert "$" in formato_usd(99.99)
    assert "99.99" in formato_usd(99.99)


def test_monto_bs_a_usd():
    assert monto_bs_a_usd(84000, 455.25) > 180
    assert monto_bs_a_usd(100, 0) == 0.0


def test_estado_cuenta_estructura_pdf_bytes():
    condo = {
        "nombre": "Condo Test",
        "direccion": "Calle 1",
        "numero_documento": "J-12345678-9",
        "tipos_documento": {"nombre": "RIF"},
    }
    estado = {
        "unidad": {"codigo": "A-1", "indiviso_pct": 25.5},
        "propietario": {"nombre": "Juan Pérez", "cedula": "V-12345678"},
        "saldo_anterior_bs": 100.0,
        "cuota_ordinaria_bs": 200.0,
        "mora_bs": 0.0,
        "pagos_recibidos_bs": 50.0,
        "saldo_cierre_bs": 250.0,
    }
    hist = [
        {"periodo": "2026-01-01", "cuota_bs": 200, "pagado_bs": 200, "saldo_bs": 0},
    ]
    pdf_bytes = pdf_estado_cuenta_individual(
        condo, "03/2026", "2026-03-01", 36.0, estado, hist
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 100
    assert pdf_bytes[:4] == b"%PDF"


def test_balance_desde_movimientos_reales_excepcion_devuelve_estructura():
    """Si falla la BD, get_balance devuelve dict con claves esperadas."""
    r = ReporteRepository.__new__(ReporteRepository)
    r.client = None  # type: ignore[assignment]
    bal = ReporteRepository.get_balance(r, 1, "2026-03-01")
    assert "total_ingresos_bs" in bal
    assert "total_gastos_bs" in bal
    assert "gastos_por_concepto" in bal
    assert "superavit_bs" in bal


def test_morosidad_solo_saldo_positivo_sin_cliente():
    r = ReporteRepository.__new__(ReporteRepository)
    r.client = None  # type: ignore[assignment]
    assert ReporteRepository.get_morosidad(r, 1, "2026-03-01", "todos") == []


def test_solventes_solo_al_dia_sin_cliente():
    r = ReporteRepository.__new__(ReporteRepository)
    r.client = None  # type: ignore[assignment]
    assert ReporteRepository.get_solventes(r, 1, "2026-03-01") == []
