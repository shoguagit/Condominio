from datetime import date, datetime
from decimal import Decimal


def format_currency(amount: float | Decimal | None, symbol: str = "$", decimals: int = 2) -> str:
    """Formatea un monto como moneda. Ej: $1,234.56"""
    if amount is None:
        return f"{symbol} 0.00"
    return f"{symbol} {amount:,.{decimals}f}"


def format_bolivares(amount: float | Decimal | None) -> str:
    """Formatea en bolívares venezolanos. Ej: Bs. 1.234,56"""
    if amount is None:
        return "Bs. 0,00"
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs. {formatted}"


def format_date(value: date | datetime | str | None, fmt: str = "%d/%m/%Y") -> str:
    """Formatea una fecha al formato dd/mm/YYYY."""
    if value is None:
        return ""
    if isinstance(value, str):
        for pattern in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f%z"):
            try:
                value = datetime.strptime(value[:len(pattern)], pattern)
                break
            except ValueError:
                continue
        else:
            return value
    return value.strftime(fmt)


def format_mes_proceso(value: date | str | None) -> str:
    """Formatea el mes de proceso como MM/AAAA. Ej: 03/2026"""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return value
    return value.strftime("%m/%Y")


def format_document(tipo: str, numero: str) -> str:
    """Combina tipo y número de documento. Ej: RIF: J-12345678-9"""
    if not numero:
        return ""
    return f"{tipo}: {numero}" if tipo else numero


def truncate_text(text: str | None, max_length: int = 50) -> str:
    """Trunca un texto largo añadiendo '...' al final."""
    if not text:
        return ""
    return text if len(text) <= max_length else text[:max_length] + "..."
