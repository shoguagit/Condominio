"""
Parseo de Excel histórico de saldos por unidad (lógica pura, sin excepciones hacia arriba).
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

UMBRAL_DIFERENCIA = 0.5  # Bs.

COL_CODIGO = 0
COL_PROPIETARIO = 1
COL_INDIVISO = 2
COL_SALDO_FEB = 30
COL_DIFERENCIA = 37


@dataclass
class UnidadHistorico:
    codigo: str
    propietario: str
    indiviso_pct: float
    saldo_bs: float
    diferencia: float
    requiere_revision: bool
    nota: str


def _fila_a_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        import math

        x = float(val)
        if math.isnan(x):
            return None
        return x
    except (TypeError, ValueError):
        return None


def _fila_a_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", ""):
        return ""
    return s


def parsear_historico_excel(contenido_bytes: bytes) -> dict[str, Any]:
    """
    Parsea el archivo Excel histórico de saldos.

    Retorna siempre un dict con:
        ok, revisar, errores, total
    Nunca propaga excepciones.
    """
    vacio: dict[str, Any] = {
        "ok": [],
        "revisar": [],
        "errores": [],
        "total": 0,
    }
    if not contenido_bytes or len(contenido_bytes) < 10:
        vacio["errores"].append("Archivo vacío o demasiado pequeño.")
        return vacio

    try:
        import pandas as pd
    except ImportError:
        vacio["errores"].append("pandas no está disponible en el entorno.")
        return vacio

    try:
        df = pd.read_excel(
            io.BytesIO(contenido_bytes),
            sheet_name="Hoja1",
            header=None,
            engine="openpyxl",
        )
    except Exception as e:
        logger.warning("parsear_historico_excel: %s", e)
        vacio["errores"].append(f"No se pudo leer el Excel (¿hoja 'Hoja1' y formato .xlsx?): {e}")
        return vacio

    if df.shape[1] < COL_DIFERENCIA + 1:
        vacio["errores"].append(
            f"El archivo no tiene suficientes columnas (se esperan al menos {COL_DIFERENCIA + 1}, "
            f"hay {df.shape[1]})."
        )
        return vacio

    ok: list[UnidadHistorico] = []
    revisar: list[UnidadHistorico] = []
    errores: list[str] = []

    # Fila 0 = encabezados; datos desde fila 1
    for idx in range(1, len(df)):
        row = df.iloc[idx]
        try:
            codigo = _fila_a_str(row.iloc[COL_CODIGO] if len(row) > COL_CODIGO else "")
            propietario = _fila_a_str(row.iloc[COL_PROPIETARIO] if len(row) > COL_PROPIETARIO else "")
            indiv_raw = row.iloc[COL_INDIVISO] if len(row) > COL_INDIVISO else None
            saldo_bs = _fila_a_float(row.iloc[COL_SALDO_FEB] if len(row) > COL_SALDO_FEB else None)
            dif = _fila_a_float(row.iloc[COL_DIFERENCIA] if len(row) > COL_DIFERENCIA else None)

            if saldo_bs is None:
                continue

            if not codigo:
                errores.append(f"Fila {idx + 1}: sin código de unidad, se omite.")
                continue

            indiv = _fila_a_float(indiv_raw)
            if indiv is None:
                indiv = 0.0

            dif_val = float(dif) if dif is not None else 0.0
            req = abs(dif_val) > UMBRAL_DIFERENCIA
            nota = ""
            if req:
                nota = f"Diferencia de Bs. {dif_val:+,.2f} vs cálculo automático"

            u = UnidadHistorico(
                codigo=codigo,
                propietario=propietario,
                indiviso_pct=float(indiv),
                saldo_bs=float(saldo_bs),
                diferencia=float(dif_val),
                requiere_revision=req,
                nota=nota,
            )
            if req:
                revisar.append(u)
            else:
                ok.append(u)
        except Exception as e:
            logger.warning("parsear_historico_excel fila %s: %s", idx + 1, e)
            errores.append(f"Fila {idx + 1}: error al interpretar ({e}).")

    total = len(ok) + len(revisar)
    return {
        "ok": ok,
        "revisar": revisar,
        "errores": errores,
        "total": total,
    }
