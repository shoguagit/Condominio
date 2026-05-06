"""Selección de unidad cuando una cédula tiene varias (por proximidad al monto vs cuota)."""


def test_ordena_por_menor_abs_monto_menos_cuota():
    unidades = [
        {"codigo_unidad": "A02", "unidad_id": 2},
        {"codigo_unidad": "A01", "unidad_id": 1},
    ]
    crefs = [13800.0, 10106.95]
    monto = 10106.95
    scored = []
    for cref, u in zip(crefs, unidades):
        diff = abs(float(monto) - cref) if cref > 0 else float("inf")
        scored.append((diff, cref, u))
    scored.sort(key=lambda x: (x[0], (x[2].get("codigo_unidad") or "").upper()))
    assert scored[0][2]["codigo_unidad"] == "A01"


def test_empate_codigo_cuando_sin_cuota():
    unidades = [
        {"codigo_unidad": "B02", "unidad_id": 2},
        {"codigo_unidad": "B01", "unidad_id": 1},
    ]
    scored = [(float("inf"), 0.0, u) for u in unidades]
    scored.sort(key=lambda x: (x[0], (x[2].get("codigo_unidad") or "").upper()))
    assert scored[0][2]["codigo_unidad"] == "B01"
