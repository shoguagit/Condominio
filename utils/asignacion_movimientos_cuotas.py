"""
Asignación de movimientos bancarios a unidades cuando hay varios montos y varias cuotas.

Objetivo: minimizar sum_i |monto_i − cuota_j| con cada unidad usada como mucho una vez
(asignación inyectiva). Para tamaños pequeños (típico ≤ 8) se usa fuerza bruta exacta.
"""

from __future__ import annotations

from itertools import combinations, permutations

# Límite práctico para explosión combinatoria
_MAX_N_MOV = 10
_MAX_M_UNI = 14


def _costo_par(monto: float, cuota_ref: float) -> float:
    if cuota_ref <= 0:
        return 1e12
    return abs(float(monto) - float(cuota_ref))


def mejor_asignacion_montos_a_cuotas(
    montos: list[float],
    cuotas: list[float],
) -> list[int]:
    """
    Para cada índice de movimiento i devuelve el índice de unidad j asignado.

    Minimiza sum_i |montos[i] - cuotas[j]| con j distintos cuando len(montos) <= len(cuotas).

    Si hay más movimientos que unidades, asigna primero los montos más altos a las
    mejores parejas libres y reutiliza unidades solo al final (heurística).
    """
    n = len(montos)
    m = len(cuotas)
    if n == 0:
        return []
    if m == 0:
        return [0] * n
    if n > _MAX_N_MOV or m > _MAX_M_UNI:
        return _asignacion_greedy(montos, cuotas)

    if n <= m:
        best_cost = float("inf")
        best_assign: list[int] | None = None
        for chosen in combinations(range(m), n):
            for orden_unidades in permutations(chosen):
                # movimiento i -> unidad orden_unidades[i]
                ctot = sum(
                    _costo_par(montos[i], cuotas[orden_unidades[i]])
                    for i in range(n)
                )
                if ctot < best_cost:
                    best_cost = ctot
                    best_assign = list(orden_unidades)
        assert best_assign is not None
        return best_assign

    # n > m : no hay inyección completa
    return _asignacion_greedy(montos, cuotas)


def _asignacion_greedy(montos: list[float], cuotas: list[float]) -> list[int]:
    """Empareja primero montos grandes con la mejor cuota libre; si faltan cupos, repite."""
    n = len(montos)
    m = len(cuotas)
    orden_mov = sorted(range(n), key=lambda i: montos[i], reverse=True)
    usadas_por_j = [0] * m
    assign = [0] * n
    for ii in orden_mov:
        mejor_j = None
        mejor_c = float("inf")
        for j in range(m):
            if usadas_por_j[j] > 0:
                continue
            c = _costo_par(montos[ii], cuotas[j])
            if c < mejor_c:
                mejor_c = c
                mejor_j = j
        if mejor_j is None:
            for j in range(m):
                c = _costo_par(montos[ii], cuotas[j])
                if c < mejor_c:
                    mejor_c = c
                    mejor_j = j
        assert mejor_j is not None
        usadas_por_j[mejor_j] += 1
        assign[ii] = mejor_j
    return assign
