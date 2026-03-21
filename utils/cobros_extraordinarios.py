"""
Lógica pura: distribución de cobros extraordinarios por indiviso (Fase 4-B).
"""

from __future__ import annotations


def calcular_monto_unidad(monto_total: float, indiviso_pct: float) -> float:
    """Monto de la unidad = monto_total × (indiviso_pct / 100), redondeado a 2 decimales."""
    return round(float(monto_total) * (float(indiviso_pct) / 100.0), 2)


def validar_cobro_extraordinario(concepto: str, monto_total: float) -> None:
    if not (concepto or "").strip():
        raise ValueError("El concepto es obligatorio.")
    if float(monto_total) <= 0:
        raise ValueError("El monto total debe ser mayor a cero.")


def distribuir_monto_entre_unidades(
    monto_total: float, unidades: list[dict]
) -> list[tuple[int, float]]:
    """
    Lista (unidad_id, monto) por indiviso; ajusta el primer renglón para que
    la suma coincida con monto_total (± redondeo).
    """
    if float(monto_total) <= 0:
        raise ValueError("El monto total debe ser mayor a cero.")
    mt = float(monto_total)
    parts: list[tuple[int, float]] = []
    for u in unidades:
        uid = int(u["id"])
        pct = float(u.get("indiviso_pct") or 0)
        parts.append((uid, calcular_monto_unidad(mt, pct)))
    if not parts:
        return []
    s = round(sum(m for _, m in parts), 2)
    diff = round(mt - s, 2)
    if abs(diff) >= 0.005:
        uid0, m0 = parts[0]
        parts[0] = (uid0, round(m0 + diff, 2))
    return parts
