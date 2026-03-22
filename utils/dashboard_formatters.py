"""
Formato y utilidades puras para el dashboard (sin I/O).
"""

from __future__ import annotations

from utils.validators import date_periodo_to_mm_yyyy


def periodo_a_mmyyyy(periodo_db: str) -> str:
    """'2026-04-01' → '04/2026'."""
    if not periodo_db or not str(periodo_db).strip():
        return "—"
    return date_periodo_to_mm_yyyy(str(periodo_db).strip())


def color_cobranza(pct: float) -> str:
    """Retorna color hex según % cobranza."""
    p = float(pct or 0)
    if p >= 90:
        return "#2ECC71"
    if p >= 70:
        return "#F39C12"
    return "#E74C3C"


def formato_bs_usd(monto_bs: float, tasa: float) -> str:
    """'Bs. 1,251,334.05 ≈ USD 2,748.65' (o USD N/D si tasa ≤ 0)."""
    bs = float(monto_bs or 0)
    t = float(tasa or 0)
    if t > 0:
        usd = bs / t
        return f"Bs. {bs:,.2f} ≈ USD {usd:,.2f}"
    return f"Bs. {bs:,.2f} — USD N/D"


def pasos_proceso(proceso: dict) -> list[dict]:
    """
    Retorna lista de 4 pasos con estado.
    proceso espera claves: presupuesto_ok, cuotas_ok, pagos_ok, cierre_ok (bool).
    """
    pairs = [
        ("Presupuesto", "presupuesto_ok"),
        ("Cuotas", "cuotas_ok"),
        ("Pagos", "pagos_ok"),
        ("Cierre", "cierre_ok"),
    ]
    return [{"nombre": n, "completado": bool(proceso.get(k))} for n, k in pairs]
