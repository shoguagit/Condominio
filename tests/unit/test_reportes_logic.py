"""Tests de lógica de reportes sin dependencia de reportlab."""

from utils.reportes_logic import map_categoria_gasto


def test_map_categoria_gasto():
    assert map_categoria_gasto("Mantenimiento ascensor") == "Mantenimiento"
    assert map_categoria_gasto("Pago luz") == "Servicios"
    assert map_categoria_gasto("Nómina") == "Personal"
    assert map_categoria_gasto("Otro gasto") == "Otros"
