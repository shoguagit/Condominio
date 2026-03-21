"""Lógica pura compartida por reportes (categorías, etc.)."""

import re


def map_categoria_gasto(nombre_concepto: str) -> str:
    n = (nombre_concepto or "").lower().strip()
    if not n:
        return "Otros"
    if any(x in n for x in ("manten", "repar", "ascensor", "limpieza")):
        return "Mantenimiento"
    # Palabras cortas (p. ej. "gas") no deben coincidir dentro de "gasto".
    if re.search(r"\bservicio", n):
        return "Servicios"
    for pat in (
        r"\bluz\b",
        r"\bagua\b",
        r"\bgas\b",
        r"\binternet\b",
        r"\belectric",
    ):
        if re.search(pat, n):
            return "Servicios"
    if any(x in n for x in ("personal", "nómina", "nomina", "empleado", "salario")):
        return "Personal"
    return "Otros"
