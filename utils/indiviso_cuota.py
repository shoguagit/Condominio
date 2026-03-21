"""
Reglas de indiviso (%) y cuota mensual por presupuesto.
Sin dependencias de Streamlit ni Supabase (aptas para tests unitarios).
"""

TOLERANCIA_INDIVISO_PCT = 0.01  # ±0,01 puntos porcentuales respecto a 100,00%


def suma_indivisos_pct(valores: list[float]) -> float:
    """Suma de porcentajes de indiviso (ej. 4.2 + 5.0 = 9.2)."""
    return float(sum(float(v or 0) for v in valores))


def valida_no_supera_100_pct(nueva_suma_pct: float) -> tuple[bool, str]:
    """Bloquea si la suma de indivisos supera 100% (tolerancia 0,01 pp)."""
    if nueva_suma_pct > 100.0 + TOLERANCIA_INDIVISO_PCT:
        return False, (
            f"La suma de indivisos sería {nueva_suma_pct:.2f}%. "
            "No puede superar 100%"
        )
    return True, ""


def valida_suma_exacta_100_pct(total_pct: float) -> tuple[bool, str]:
    """La suma de todos los indivisos del condominio debe ser 100,00% ± 0,01%."""
    if abs(total_pct - 100.0) > TOLERANCIA_INDIVISO_PCT:
        return False, (
            f"La suma de indivisos es {total_pct:.2f}%. "
            "Debe ser exactamente 100,00% (tolerancia ±0,01%)."
        )
    return True, ""


def cuota_bs_desde_presupuesto(presupuesto_mes: float, indiviso_pct: float) -> float:
    """cuota = presupuesto_mes × (indiviso_pct / 100)"""
    return round(float(presupuesto_mes) * (float(indiviso_pct) / 100.0), 2)
