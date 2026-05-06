from utils.asignacion_movimientos_cuotas import mejor_asignacion_montos_a_cuotas


def test_cuatro_montos_cuatro_cuotas_biyeccion():
    montos = [10106.95, 13800.0, 12879.0, 12880.0]
    cuotas = [10107.0, 13800.0, 12879.0, 12880.0]
    idx = mejor_asignacion_montos_a_cuotas(montos, cuotas)
    assert len(idx) == 4
    assert sorted(idx) == [0, 1, 2, 3]


def test_dos_montos_tres_cuotas_elige_mejor_par():
    montos = [100.0, 300.0]
    cuotas = [99.0, 500.0, 301.0]
    idx = mejor_asignacion_montos_a_cuotas(montos, cuotas)
    assert idx[0] in (0, 2)
    assert idx[1] in (0, 2)
    assert idx[0] != idx[1]
