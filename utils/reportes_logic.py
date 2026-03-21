"""Lógica pura compartida por reportes (categorías, etc.)."""


def map_categoria_gasto(nombre_concepto: str) -> str:
    n = (nombre_concepto or "").lower()
    if any(x in n for x in ("manten", "repar", "ascensor", "limpieza")):
        return "Mantenimiento"
    if any(x in n for x in ("servicio", "luz", "agua", "gas", "internet", "electric")):
        return "Servicios"
    if any(x in n for x in ("personal", "nómina", "nomina", "empleado", "salario")):
        return "Personal"
    return "Otros"
