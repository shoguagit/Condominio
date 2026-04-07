"""
Parser flexible para importar gastos del mes desde Excel o CSV.

Detecta automáticamente las columnas: fecha, referencia, monto, beneficiario y concepto.
La descripción final se construye con una plantilla configurable y el mes se puede
agregar automáticamente si no está ya presente en el texto.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Helpers básicos
# ---------------------------------------------------------------------------

MES_NOMBRES = {
    1: "Enero",    2: "Febrero",  3: "Marzo",     4: "Abril",
    5: "Mayo",     6: "Junio",    7: "Julio",      8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _norm_cell(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _parse_fecha(val: Any) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, date) and not isinstance(val, pd.Timestamp):
        return val
    try:
        ts = pd.to_datetime(val, dayfirst=True, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


def _parse_monto(val: Any) -> float | None:
    """
    Parsea montos en formato europeo (12.575,40) o estándar (12575.40).
    Devuelve None si no se puede convertir.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        v = float(val)
        return v if v > 0 else None
    s = str(val).strip().replace(" ", "").replace("\u00a0", "")
    if not s or s in ("-", "—", ""):
        return None
    s = s.lstrip("-+")
    # European: 12.575,40  →  12575.40
    if "," in s and "." in s:
        if s.index(".") < s.index(","):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # 12575,40  →  12575.40   (solo un separador → decimal con coma)
        if re.fullmatch(r"\d+,\d{1,2}", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        v = float(s)
        return v if v > 0 else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Carga del archivo
# ---------------------------------------------------------------------------

def cargar_df(file_obj: Any, nombre: str) -> pd.DataFrame:
    """
    Lee un Excel (.xls, .xlsx) o CSV desde un file-like object.
    Devuelve un DataFrame sin encabezados (todo string).
    Prueba saltar hasta 5 filas vacías al inicio en Excel.
    """
    nom_lower = nombre.lower()
    if nom_lower.endswith(".csv"):
        for sep in [";", ",", "\t", "|"]:
            for enc in ["utf-8-sig", "latin-1", "utf-8"]:
                try:
                    file_obj.seek(0)
                    df = pd.read_csv(
                        file_obj, sep=sep, encoding=enc,
                        header=None, dtype=str, skip_blank_lines=True,
                    )
                    if df.shape[1] >= 3 and df.shape[0] >= 2:
                        return df
                except Exception:
                    pass
        raise ValueError(
            "No se pudo leer el CSV. Verifique separador (coma, punto y coma, tabulador) "
            "y codificación (UTF-8 / Latin-1)."
        )

    # Excel
    for skip in range(6):
        try:
            file_obj.seek(0)
            df = pd.read_excel(
                file_obj, header=None, skiprows=skip, dtype=str, engine="openpyxl"
            )
            if df.shape[1] >= 3 and df.shape[0] >= 2:
                return df
        except Exception:
            pass
    # Fallback: xlrd for .xls
    try:
        file_obj.seek(0)
        df = pd.read_excel(file_obj, header=None, dtype=str)
        if df.shape[1] >= 3:
            return df
    except Exception:
        pass
    raise ValueError("No se pudo leer el archivo Excel. Asegúrese de que sea .xlsx o .xls válido.")


# ---------------------------------------------------------------------------
# Detección automática de columnas
# ---------------------------------------------------------------------------

def _pct_date(series: pd.Series) -> float:
    vals = [v for v in series if _norm_cell(v)]
    if not vals:
        return 0.0
    return sum(1 for v in vals if _parse_fecha(v) is not None) / len(vals)


def _pct_num(series: pd.Series) -> float:
    vals = [v for v in series if _norm_cell(v)]
    if not vals:
        return 0.0
    return sum(1 for v in vals if _parse_monto(v) is not None) / len(vals)


def _pct_ref(series: pd.Series) -> float:
    vals = [_norm_cell(v) for v in series if _norm_cell(v)]
    if not vals:
        return 0.0
    return sum(1 for v in vals if re.fullmatch(r"\d{6,20}", v)) / len(vals)


def _pct_text(series: pd.Series) -> float:
    vals = [_norm_cell(v) for v in series if _norm_cell(v)]
    if not vals:
        return 0.0
    return sum(1 for v in vals if re.search(r"[A-Za-záéíóúÁÉÍÓÚñÑüÜ]", v)) / len(vals)


def detectar_columnas(df: pd.DataFrame) -> dict[str, int | None]:
    """
    Devuelve mapeo sugerido: {'fecha': col_idx, 'referencia': col_idx, 'monto': col_idx,
                               'beneficiario': col_idx, 'concepto': col_idx}.
    Un valor None indica que la columna no pudo detectarse.
    Solo usa las primeras 40 filas para el análisis.
    """
    sample = df.head(40)
    n = sample.shape[1]

    date_s  = [_pct_date(sample.iloc[:, i]) for i in range(n)]
    num_s   = [_pct_num(sample.iloc[:, i])  for i in range(n)]
    ref_s   = [_pct_ref(sample.iloc[:, i])  for i in range(n)]
    text_s  = [_pct_text(sample.iloc[:, i]) for i in range(n)]

    used: set[int] = set()

    def best(scores: list[float], min_score: float = 0.5) -> int | None:
        cands = [(s, i) for i, s in enumerate(scores) if s >= min_score and i not in used]
        if not cands:
            return None
        idx = max(cands, key=lambda x: x[0])[1]
        used.add(idx)
        return idx

    fecha_idx = best(date_s, 0.5)
    ref_idx   = best(ref_s,  0.5)
    monto_idx = best(num_s,  0.5)

    # Columnas de texto restantes (izquierda a derecha)
    text_remaining = sorted(
        [(i, text_s[i]) for i in range(n) if i not in used and text_s[i] >= 0.3],
        key=lambda x: x[0],
    )
    benef_idx   = text_remaining[0][0] if len(text_remaining) >= 1 else None
    if benef_idx is not None:
        used.add(benef_idx)
    concepto_idx = text_remaining[1][0] if len(text_remaining) >= 2 else None

    return {
        "fecha":        fecha_idx,
        "referencia":   ref_idx,
        "monto":        monto_idx,
        "beneficiario": benef_idx,
        "concepto":     concepto_idx,
    }


# ---------------------------------------------------------------------------
# Procesado de filas
# ---------------------------------------------------------------------------

def procesar_filas(
    df: pd.DataFrame,
    col_map: dict[str, int | None],
    desc_template: str = "{beneficiario} {concepto}",
    agregar_mes: bool = True,
) -> tuple[list[dict], list[str]]:
    """
    Transforma las filas del DataFrame en dicts listos para insertar como movimientos.

    desc_template: usa {beneficiario} y/o {concepto} como marcadores.
    agregar_mes:   añade "MesNombre Año" al final si el mes no aparece ya en la descripción.

    Retorna:
        filas:  lista de dicts  {fecha, referencia, monto_bs, descripcion}
        errores: líneas problemáticas (fila ignorada)
    """
    filas: list[dict] = []
    errores: list[str] = []

    def _get(row: pd.Series, field: str) -> str:
        idx = col_map.get(field)
        if idx is None or idx >= len(row):
            return ""
        return _norm_cell(row.iloc[idx])

    for i, row in df.iterrows():
        fecha_raw = _get(row, "fecha")
        monto_raw = _get(row, "monto")

        # Fila vacía → saltar silenciosamente
        if not fecha_raw and not monto_raw:
            continue

        # Fecha
        fecha_val = _parse_fecha(fecha_raw)
        if fecha_val is None:
            if fecha_raw:
                errores.append(f"Fila {int(i)+1}: fecha no reconocida → '{fecha_raw}'")
            continue

        # Monto
        monto_val = _parse_monto(monto_raw)
        if monto_val is None:
            errores.append(
                f"Fila {int(i)+1} ({fecha_val}): monto no reconocido → '{monto_raw}'"
            )
            continue

        ref_str   = _get(row, "referencia")
        benef_str = _get(row, "beneficiario")
        conc_str  = _get(row, "concepto")

        # Construir descripción
        desc = desc_template.format(
            beneficiario=benef_str, concepto=conc_str
        ).strip()
        # Eliminar espacios dobles
        desc = re.sub(r"\s{2,}", " ", desc)
        if not desc:
            desc = benef_str or conc_str or "Sin descripción"

        # Agregar mes si no aparece ya
        if agregar_mes:
            mes_name = MES_NOMBRES.get(fecha_val.month, "")
            if mes_name and mes_name.lower() not in desc.lower():
                desc = f"{desc} {mes_name} {fecha_val.year}"

        filas.append(
            {
                "fecha": fecha_val,
                "referencia": ref_str,
                "monto_bs": round(monto_val, 2),
                "descripcion": desc,
            }
        )

    return filas, errores


# ---------------------------------------------------------------------------
# Helper: etiqueta de columna para el selector
# ---------------------------------------------------------------------------

def etiqueta_col(df: pd.DataFrame, idx: int) -> str:
    """Columna letra (A, B, …) + primeras 2 celdas de muestra."""
    letter = chr(ord("A") + idx) if idx < 26 else f"col{idx}"
    samples = [
        _norm_cell(df.iloc[r, idx]) for r in range(min(3, df.shape[0]))
        if _norm_cell(df.iloc[r, idx])
    ]
    sample_str = " | ".join(samples[:2])
    return f"Col {letter}: {sample_str[:40]}" if sample_str else f"Col {letter}"
