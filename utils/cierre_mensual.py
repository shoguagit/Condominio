"""
Lógica pura de cierre mensual (Fase 2). Sin I/O ni Streamlit.
"""

from __future__ import annotations


def saldo_nuevo_tras_cierre(saldo_anterior: float, cuota: float, pagado: float) -> float:
    """Saldo que arrastra la unidad tras aplicar cuota del mes y pagos del período."""
    return round(float(saldo_anterior) + float(cuota) - float(pagado), 2)


def etiqueta_estado_cierre_ui(saldo_nuevo: float, pagado: float) -> str:
    """Etiqueta para tablas en UI (español)."""
    sn = round(float(saldo_nuevo), 2)
    pg = round(float(pagado), 2)
    if sn == 0:
        return "Al día"
    if sn > 0 and pg > 0:
        return "Parcial"
    return "Moroso"


def estado_pago_db(saldo_nuevo: float, pagado: float) -> str:
    """Valores para columna unidades.estado_pago."""
    sn = round(float(saldo_nuevo), 2)
    pg = round(float(pagado), 2)
    if sn == 0:
        return "al_dia"
    if sn > 0 and pg > 0:
        return "parcial"
    return "moroso"


def eficiencia_cobro(total_cuotas: float, total_cobrado: float) -> float:
    """Porcentaje 0–100; si no hay cuotas emitidas, 0."""
    tc = float(total_cuotas)
    cob = float(total_cobrado)
    if tc <= 0:
        return 0.0
    return round((cob / tc) * 100, 2)


def puede_generar_cuotas(estado_proceso: str) -> bool:
    """No generar si el período ya está cerrado."""
    return (estado_proceso or "").lower() != "cerrado"


def puede_cerrar_mes(estado_proceso: str) -> bool:
    return (estado_proceso or "").lower() == "procesado"


def periodo_permite_pagos(estado_proceso: str | None) -> bool:
    """
    False si existe proceso explícitamente cerrado para ese período.
    estado_proceso None = sin fila de proceso → se permiten pagos.
    """
    if estado_proceso is None:
        return True
    return (estado_proceso or "").lower() != "cerrado"


def texto_pasos_cierre(
    tiene_presupuesto: bool,
    cuotas_generadas: bool,
    hay_pagos_periodo: bool,
    proceso_cerrado: bool,
) -> tuple[list[str], int]:
    """
    Devuelve líneas de pasos (solo texto) y el índice 1-based del paso actual
    (primer paso incompleto, o 4 si todo completado hasta cierre).
    """
    lines = [
        "Paso 1: Presupuesto definido",
        "Paso 2: Cuotas generadas",
        "Paso 3: Pagos registrados",
        "Paso 4: Cierre y arrastre",
    ]
    ok1 = tiene_presupuesto
    ok2 = cuotas_generadas
    ok3 = hay_pagos_periodo
    ok4 = proceso_cerrado

    if not ok1:
        return lines, 1
    if not ok2:
        return lines, 2
    if not ok3:
        return lines, 3
    if not ok4:
        return lines, 4
    return lines, 4
