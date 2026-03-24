"""
Parseo de Excel histórico de saldos por unidad (lógica pura, sin excepciones hacia arriba).
"""

from __future__ import annotations

import datetime
import io
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

UMBRAL_DIFERENCIA = 0.5  # Bs.

COL_CODIGO = 0
COL_PROPIETARIO = 1
COL_INDIVISO = 2
COL_SALDO_FEB = 30
COL_DIFERENCIA = 37

# Morosos acumulados (Hoja2)
MOR_COL_NRO = 0
MOR_COL_NOMBRE = 1
MOR_COL_INDIVISO = 2
MOR_COL_CUOTA_INI = 3
MOR_COL_CUOTA_FIN = 29  # inclusive
MOR_COL_MESES = 30

# Columna Excel (índice 0-based) → primer mes con cuota > 0 (YYYY-MM)
MAPA_PERIODOS = {
    3: "2023-12",
    4: "2024-01",
    5: "2024-02",
    6: "2024-03",
    7: "2024-04",
    8: "2024-05",
    9: "2024-06",
    10: "2024-07",
    11: "2024-08",
    12: "2024-09",
    13: "2024-10",
    14: "2024-11",
    15: "2024-12",
    16: "2025-01",
    17: "2025-02",
    18: "2025-03",
    19: "2025-04",
    20: "2025-05",
    21: "2025-06",
    22: "2025-07",
    23: "2025-08",
    24: "2025-09",
    25: "2025-10",
    26: "2025-11",
    27: "2025-12",
    28: "2026-01",
    29: "2026-02",
}


@dataclass
class UnidadHistorico:
    codigo: str
    propietario: str
    indiviso_pct: float
    saldo_bs: float
    diferencia: float
    requiere_revision: bool
    nota: str
    meses: int = 0
    primer_periodo: str | None = None


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


def _es_datetime_o_timestamp(val: Any) -> bool:
    if val is None:
        return False
    try:
        import pandas as pd

        if isinstance(val, pd.Timestamp):
            return not pd.isna(val)
    except Exception:
        pass
    return isinstance(val, datetime.datetime)


def _nro_unidad_a_codigo(val: Any) -> str:
    """Normaliza NRO de Excel (str, int, float) a código de unidad."""
    if val is None:
        return ""
    try:
        import math

        import pandas as pd

        if pd.isna(val):
            return ""
    except Exception:
        pass
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        try:
            import math

            x = float(val)
            if math.isnan(x):
                return ""
            if x == int(x):
                return str(int(x))
        except (TypeError, ValueError, OverflowError):
            pass
    return _fila_a_str(val)


def _codigo_unidad_valido(codigo: str) -> bool:
    c = (codigo or "").strip()
    if not c:
        return False
    if c.upper() in ("NRO", "NRO.", "UNIDAD", "COD", "CODIGO", "CÓDIGO", "#", "TOTAL"):
        return False
    return bool(re.search(r"[A-Za-z0-9]", c))


def _entero_desde_celda(val: Any) -> int | None:
    if val is None:
        return None
    try:
        import math

        import pandas as pd

        if pd.isna(val):
            return None
    except Exception:
        pass
    if _es_datetime_o_timestamp(val):
        return None
    try:
        x = float(val)
        if math.isnan(x):
            return None
        if abs(x - round(x)) > 1e-6:
            return None
        return int(round(x))
    except (TypeError, ValueError, OverflowError):
        return None


def detectar_formato_excel(contenido_bytes: bytes) -> str:
    """
    Detecta el formato del archivo subido.

    Retorna: ``'solventes'`` | ``'morosos'`` | ``'desconocido'``.
    Nunca propaga excepciones.
    """
    if not contenido_bytes or len(contenido_bytes) < 10:
        return "desconocido"
    try:
        import pandas as pd
    except ImportError:
        return "desconocido"

    try:
        xl = pd.ExcelFile(io.BytesIO(contenido_bytes), engine="openpyxl")
        hojas = {str(s).strip() for s in xl.sheet_names}
    except Exception as e:
        logger.warning("detectar_formato_excel: %s", e)
        return "desconocido"

    # 1) Solventes: Hoja1 y encabezado en col 37 con "Diferencias"
    if "Hoja1" in hojas:
        try:
            df1 = pd.read_excel(
                xl, sheet_name="Hoja1", header=None, engine="openpyxl"
            )
            if df1.shape[1] > COL_DIFERENCIA:
                h37 = _fila_a_str(df1.iloc[0, COL_DIFERENCIA])
                if h37 and "diferencia" in h37.lower():
                    return "solventes"
        except Exception as e:
            logger.warning("detectar_formato_excel Hoja1: %s", e)

    # 2) Morosos: Hoja2, al menos 31 columnas y filas de datos con col 30 entera
    if "Hoja2" in hojas:
        try:
            df2 = pd.read_excel(
                xl, sheet_name="Hoja2", header=None, engine="openpyxl"
            )
            if df2.shape[1] > MOR_COL_MESES:
                for idx in range(min(len(df2), 25)):
                    row = df2.iloc[idx]
                    if len(row) <= MOR_COL_MESES:
                        continue
                    if _es_datetime_o_timestamp(row.iloc[MOR_COL_MESES]):
                        continue
                    cod = _nro_unidad_a_codigo(row.iloc[MOR_COL_NRO])
                    if not _codigo_unidad_valido(cod):
                        continue
                    if _entero_desde_celda(row.iloc[MOR_COL_MESES]) is not None:
                        return "morosos"
        except Exception as e:
            logger.warning("detectar_formato_excel Hoja2: %s", e)

    return "desconocido"


def parsear_morosos_excel(contenido_bytes: bytes) -> dict[str, Any]:
    """
    Parsea el archivo de morosos (Hoja2) con deuda acumulada.

    Saldo = suma de cuotas en columnas 3 a 29 donde valor > 0 y no es NaN.

    Retorna claves: ok, revisar (vacío), errores, total, formato.
    Nunca propaga excepciones.
    """
    vacio: dict[str, Any] = {
        "ok": [],
        "revisar": [],
        "errores": [],
        "total": 0,
        "formato": "morosos_acumulados",
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
            sheet_name="Hoja2",
            header=None,
            engine="openpyxl",
        )
    except Exception as e:
        logger.warning("parsear_morosos_excel: %s", e)
        vacio["errores"].append(f"No se pudo leer el Excel (¿hoja 'Hoja2' y formato .xlsx?): {e}")
        return vacio

    if df.shape[1] <= MOR_COL_MESES:
        vacio["errores"].append(
            f"El archivo no tiene suficientes columnas (se esperan al menos {MOR_COL_MESES + 1}, "
            f"hay {df.shape[1]})."
        )
        return vacio

    ok: list[UnidadHistorico] = []
    errores: list[str] = []

    for idx in range(len(df)):
        row = df.iloc[idx]
        try:
            if len(row) <= MOR_COL_MESES:
                continue

            col_meses = row.iloc[MOR_COL_MESES]
            if _es_datetime_o_timestamp(col_meses):
                continue

            codigo = _nro_unidad_a_codigo(row.iloc[MOR_COL_NRO])
            if not _codigo_unidad_valido(codigo):
                continue

            propietario = _fila_a_str(row.iloc[MOR_COL_NOMBRE] if len(row) > MOR_COL_NOMBRE else "")
            indiv_raw = row.iloc[MOR_COL_INDIVISO] if len(row) > MOR_COL_INDIVISO else None
            indiv = _fila_a_float(indiv_raw)
            if indiv is None:
                indiv = 0.0

            meses_int = _entero_desde_celda(col_meses)
            if meses_int is None:
                meses_int = 0

            suma = 0.0
            for c in range(MOR_COL_CUOTA_INI, MOR_COL_CUOTA_FIN + 1):
                if len(row) <= c:
                    break
                v = _fila_a_float(row.iloc[c])
                if v is not None and v > 0:
                    suma += v

            u = UnidadHistorico(
                codigo=codigo,
                propietario=propietario,
                indiviso_pct=float(indiv),
                saldo_bs=round(suma, 2),
                diferencia=0.0,
                requiere_revision=False,
                nota="",
                meses=int(meses_int),
            )
            ok.append(u)
        except Exception as e:
            logger.warning("parsear_morosos_excel fila %s: %s", idx + 1, e)
            errores.append(f"Fila {idx + 1}: error al interpretar ({e}).")

    vacio["ok"] = ok
    vacio["errores"] = errores
    vacio["total"] = len(ok)
    return vacio


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
                meses=0,
                primer_periodo="2026-02",
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
