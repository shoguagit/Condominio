import re

PATRON_CEDULA = re.compile(r"\b([VvEeJjGg][-]?\d{6,9})\b")


def extraer_cedulas(texto: str) -> list[str]:
    """
    Extrae todas las cédulas venezolanas del texto.
    Formatos soportados:
    - V6919271, V-6919271
    - J051151689, J-051151689
    - E12345678 (extranjero)
    - G12345678 (gubernamental)
    Retorna lista de cédulas normalizadas sin guión
    en mayúsculas. Ej: ['V6919271', 'J051151689']
    NUNCA propaga excepciones.
    """
    if not texto:
        return []
    try:
        matches = PATRON_CEDULA.findall(str(texto).upper())
        return [m.replace("-", "") for m in matches]
    except Exception:
        return []


def clasificar_pago(monto_bs: float, cuota_ordinaria_bs: float) -> str:
    """
    Clasifica el tipo de pago.
    Retorna: 'total' | 'parcial' | 'extraordinario'

    - monto >= cuota_ordinaria → 'total'
    - 0 < monto < cuota_ordinaria → 'parcial'
    - monto > cuota_ordinaria (con diferencia > 1%) → 'extraordinario'

    Tolerancia: ±1% para cubrir redondeos
    """
    if cuota_ordinaria_bs <= 0:
        return "total"
    ratio = float(monto_bs) / float(cuota_ordinaria_bs)
    if ratio >= 0.99:
        if ratio > 1.01:
            return "extraordinario"
        return "total"
    return "parcial"
