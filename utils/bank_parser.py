"""
Parser inteligente para extractos Excel de bancos venezolanos (Movimientos Bancarios).
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pandas as pd


@dataclass
class MovimientoParsed:
    fecha: date
    referencia: str
    concepto: str
    monto: float
    es_ingreso: bool
    banco_detectado: str


@dataclass
class ParseResult:
    banco: str
    movimientos: list[MovimientoParsed]
    total_ingresos: float
    total_egresos: float
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)


def _norm_cell(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _norm_col_name(s: Any) -> str:
    t = _norm_cell(s).lower()
    t = "".join(
        c
        for c in unicodedata.normalize("NFD", t)
        if unicodedata.category(c) != "Mn"
    )
    t = re.sub(r"\s+", "", t)
    return t


def limpiar_monto(valor: str | float | int | None, formato: str) -> float:
    """
    formato: 'europeo' (punto=miles, coma=decimal)
             'estandar' (coma=miles opcional, punto=decimal)
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        raise ValueError("Monto vacío")
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return float(valor)

    s = str(valor).strip().replace(" ", "").replace("\u00a0", "")
    if not s or s in ("-", "—"):
        raise ValueError("Monto vacío")

    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    elif s.startswith("-"):
        neg = True
        s = s[1:]

    if formato == "europeo":
        if "," in s:
            entero, decimal = s.rsplit(",", 1)
            entero = entero.replace(".", "")
            s = f"{entero}.{decimal}"
        else:
            s = s.replace(".", "")
    else:
        # estándar: quitar comas de miles
        s = s.replace(",", "")

    out = float(s)
    return -out if neg else out


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


def _df_desde_fila_header(df_raw: pd.DataFrame, header_row: int) -> pd.DataFrame:
    if df_raw.shape[0] <= header_row:
        return pd.DataFrame()
    headers = df_raw.iloc[header_row].tolist()
    body = df_raw.iloc[header_row + 1 :].copy()
    names: list[str] = []
    used: dict[str, int] = {}
    for i, h in enumerate(headers):
        base = _norm_cell(h) if pd.notna(h) else f"_col{i}"
        if not base:
            base = f"_col{i}"
        cnt = used.get(base, 0)
        used[base] = cnt + 1
        names.append(base if cnt == 0 else f"{base}_{cnt}")
    body.columns = names
    return body.reset_index(drop=True)


def _resolver_columna(df: pd.DataFrame, *candidatos: str) -> str | None:
    """candidatos en forma normalizada sin espacios."""
    cmap = {_norm_col_name(c): c for c in df.columns}
    for cand in candidatos:
        n = _norm_col_name(cand)
        if n in cmap:
            return cmap[n]
    return None


def detectar_banco(df_raw: pd.DataFrame) -> str:
    """
    Analiza las primeras filas del DataFrame sin procesar
    y retorna el nombre del banco detectado.
    Lanza ValueError si no puede identificar el banco.
    """
    if df_raw is None or df_raw.empty:
        raise ValueError("El archivo no tiene filas.")

    # Mercantil: fila 1, columna C — "Monto total:"
    if df_raw.shape[0] > 1 and df_raw.shape[1] > 2:
        c1 = _norm_cell(df_raw.iloc[1, 2])
        if "monto total" in c1.lower():
            return "Mercantil"

    # Bancamiga: fila 1, celda A contiene 'Bancamiga'
    if df_raw.shape[0] > 1:
        a1 = _norm_cell(df_raw.iloc[1, 0])
        if "bancamiga" in a1.lower():
            return "Bancamiga"

    # Banesco / BDV: encabezado en fila 0
    row0 = df_raw.iloc[0].tolist()
    cols_banesco = {
        "Fecha",
        "Referencia",
        "Descripción",
        "Monto",
        "Balance",
    }
    fila0_set = {
        str(v).strip()
        for v in row0
        if v is not None and not (isinstance(v, float) and pd.isna(v)) and str(v).strip()
    }
    if cols_banesco.issubset(fila0_set):
        return "Banesco"

    for v in row0:
        if _norm_col_name(v) == "tipomovimiento":
            return "BDV"

    raise ValueError(
        "No se reconoce el formato del banco. "
        "Bancos soportados: BDV, Banesco, Bancamiga, Mercantil."
    )


def _fecha_normalizada_para_duplicado(val: Any) -> str:
    """Compara fechas como YYYY-MM-DD (date, ISO str, timestamps)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    s = str(val).strip()
    if "T" in s:
        return s.split("T", 1)[0][:10]
    return s[:10] if len(s) >= 10 else s


def _montos_iguales_duplicado(a: float, b: Any) -> bool:
    try:
        return round(float(a), 2) == round(float(b), 2)
    except (TypeError, ValueError):
        return False


def es_duplicado(
    movimiento: MovimientoParsed,
    existentes: list[dict],
    condominio_id: int | None = None,
) -> bool:
    """
    Verifica si el movimiento ya existe en la lista de existentes.

    existentes: dicts con keys referencia, monto, fecha, concepto;
    opcional condominio_id para alinear con la regla de negocio (mismo condominio).

    Si referencia es None, '', '0', 'None' o 'nan' (como texto):
        duplicado = mismo condominio (si aplica) + fecha + monto + concepto
    Si referencia tiene valor real:
        duplicado = mismo condominio (si aplica) + referencia + monto
    """
    ref_raw = movimiento.referencia
    ref = str(ref_raw).strip() if ref_raw is not None else ""
    ref_vacia = ref in ("", "0", "None", "nan") or ref.lower() == "nan"

    fecha_mov = _fecha_normalizada_para_duplicado(movimiento.fecha)
    concepto_mov = str(movimiento.concepto or "").strip()

    for e in existentes:
        if condominio_id is not None and "condominio_id" in e:
            try:
                if int(e["condominio_id"]) != int(condominio_id):
                    continue
            except (TypeError, ValueError):
                continue

        if ref_vacia:
            fe = _fecha_normalizada_para_duplicado(e.get("fecha"))
            conc_e = str(e.get("concepto", "") or "").strip()
            if (
                fe == fecha_mov
                and _montos_iguales_duplicado(movimiento.monto, e.get("monto", 0))
                and conc_e == concepto_mov
            ):
                return True
        else:
            er = str(e.get("referencia", "") or "").strip()
            if er == ref and _montos_iguales_duplicado(
                movimiento.monto, e.get("monto", 0)
            ):
                return True
    return False


def _totales(movs: list[MovimientoParsed]) -> tuple[float, float]:
    ti = sum(m.monto for m in movs if m.es_ingreso)
    te = sum(m.monto for m in movs if not m.es_ingreso)
    return round(ti, 2), round(te, 2)


def parsear_bdv(df_raw: pd.DataFrame) -> ParseResult:
    errores: list[str] = []
    advertencias: list[str] = []
    movs: list[MovimientoParsed] = []

    df = _df_desde_fila_header(df_raw, 0)
    if df.empty:
        return ParseResult("BDV", [], 0, 0, ["Sin filas de datos."], [])

    c_fecha = _resolver_columna(df, "fecha")
    c_ref = _resolver_columna(df, "referencia")
    c_conc = _resolver_columna(df, "concepto")
    c_monto = _resolver_columna(df, "monto")
    c_tipo = _resolver_columna(df, "tipomovimiento")

    if not all([c_fecha, c_ref, c_conc, c_monto, c_tipo]):
        return ParseResult(
            "BDV",
            [],
            0,
            0,
            ["Faltan columnas esperadas (fecha, referencia, concepto, monto, tipoMovimiento)."],
            [],
        )

    for idx, row in df.iterrows():
        n = int(idx) + 2
        try:
            fd = _parse_fecha(row.get(c_fecha))
            if fd is None:
                errores.append(f"Fila {n}: fecha inválida o vacía.")
                continue
            ref = _norm_cell(row.get(c_ref))
            conc = _norm_cell(row.get(c_conc))
            try:
                monto_raw = limpiar_monto(row.get(c_monto), "europeo")
            except ValueError as e:
                errores.append(f"Fila {n}: monto inválido ({e}).")
                continue
            tipo_mv = _norm_cell(row.get(c_tipo))
            tml = tipo_mv.lower().replace("é", "e")
            es_credito = tml == "nota de credito" and monto_raw > 0
            if es_credito:
                movs.append(
                    MovimientoParsed(
                        fecha=fd,
                        referencia=ref,
                        concepto=conc,
                        monto=abs(monto_raw),
                        es_ingreso=True,
                        banco_detectado="BDV",
                    )
                )
            elif monto_raw != 0:
                movs.append(
                    MovimientoParsed(
                        fecha=fd,
                        referencia=ref,
                        concepto=conc,
                        monto=abs(monto_raw),
                        es_ingreso=False,
                        banco_detectado="BDV",
                    )
                )
        except Exception as e:
            errores.append(f"Fila {n}: {e}")

    ti, te = _totales(movs)
    return ParseResult("BDV", movs, ti, te, errores, advertencias)


def parsear_banesco(df_raw: pd.DataFrame) -> ParseResult:
    errores: list[str] = []
    advertencias: list[str] = []
    movs: list[MovimientoParsed] = []

    df = _df_desde_fila_header(df_raw, 0)
    if df.empty:
        return ParseResult("Banesco", [], 0, 0, ["Sin filas de datos."], [])

    c_fecha = _resolver_columna(df, "fecha")
    c_ref = _resolver_columna(df, "referencia")
    c_desc = _resolver_columna(df, "descripción", "descripcion")
    c_monto = _resolver_columna(df, "monto")

    if not all([c_fecha, c_ref, c_monto]):
        return ParseResult(
            "Banesco",
            [],
            0,
            0,
            ["Faltan columnas esperadas (Fecha, Referencia, Monto)."],
            [],
        )

    for idx, row in df.iterrows():
        n = int(idx) + 2
        try:
            fd = _parse_fecha(row.get(c_fecha))
            if fd is None:
                if all(
                    pd.isna(row.get(c)) or str(row.get(c)).strip() == ""
                    for c in df.columns
                ):
                    continue
                errores.append(f"Fila {n}: fecha inválida o vacía.")
                continue
            ref = _norm_cell(row.get(c_ref))
            desc = _norm_cell(row.get(c_desc)) if c_desc else ""

            try:
                monto_raw = limpiar_monto(row.get(c_monto), "estandar")
            except ValueError as e:
                errores.append(f"Fila {n}: monto inválido ({e}).")
                continue

            if monto_raw == 0:
                continue

            es_ingreso = monto_raw > 0
            monto = abs(monto_raw)

            movs.append(
                MovimientoParsed(
                    fecha=fd,
                    referencia=ref,
                    concepto=desc,
                    monto=monto,
                    es_ingreso=es_ingreso,
                    banco_detectado="Banesco",
                )
            )
        except Exception as e:
            errores.append(f"Fila {n}: {e}")

    ti, te = _totales(movs)
    return ParseResult("Banesco", movs, ti, te, errores, advertencias)


def _limpiar_referencia_bancamiga(ref: str) -> str:
    r = ref.strip()
    if r.startswith("'"):
        r = r[1:].strip()
    return r


def parsear_bancamiga(df_raw: pd.DataFrame) -> ParseResult:
    errores: list[str] = []
    advertencias: list[str] = []
    movs: list[MovimientoParsed] = []

    df = _df_desde_fila_header(df_raw, 5)
    if df.empty:
        return ParseResult("Bancamiga", [], 0, 0, ["Sin filas de datos."], [])

    c_fecha = _resolver_columna(df, "fecha")
    c_ref = _resolver_columna(df, "referencia")
    c_conc = _resolver_columna(df, "concepto")
    c_deb = _resolver_columna(df, "débito", "debito")
    c_cred = _resolver_columna(df, "crédito", "credito")

    if not all([c_fecha, c_ref, c_cred]):
        return ParseResult(
            "Bancamiga",
            [],
            0,
            0,
            ["Faltan columnas esperadas (Fecha, Referencia, Crédito)."],
            [],
        )

    for idx, row in df.iterrows():
        n = int(idx) + 7
        try:
            fd = _parse_fecha(row.get(c_fecha))
            if fd is None:
                if all(
                    pd.isna(row.get(c)) or str(row.get(c)).strip() == ""
                    for c in df.columns
                ):
                    continue
                errores.append(f"Fila {n}: fecha inválida o vacía.")
                continue
            ref = _limpiar_referencia_bancamiga(_norm_cell(row.get(c_ref)))
            conc = _norm_cell(row.get(c_conc)) if c_conc else ""
            try:
                credito = limpiar_monto(row.get(c_cred), "estandar")
            except ValueError:
                credito = 0.0
            debito = 0.0
            if c_deb:
                try:
                    debito = limpiar_monto(row.get(c_deb), "estandar")
                except ValueError:
                    debito = 0.0

            if credito > 0:
                movs.append(
                    MovimientoParsed(
                        fecha=fd,
                        referencia=ref,
                        concepto=conc,
                        monto=abs(credito),
                        es_ingreso=True,
                        banco_detectado="Bancamiga",
                    )
                )
            elif debito > 0:
                movs.append(
                    MovimientoParsed(
                        fecha=fd,
                        referencia=ref,
                        concepto=conc,
                        monto=abs(debito),
                        es_ingreso=False,
                        banco_detectado="Bancamiga",
                    )
                )
        except Exception as e:
            errores.append(f"Fila {n}: {e}")

    ti, te = _totales(movs)
    return ParseResult("Bancamiga", movs, ti, te, errores, advertencias)


def parsear_mercantil(df_raw: pd.DataFrame) -> ParseResult:
    errores: list[str] = []
    advertencias: list[str] = []
    movs: list[MovimientoParsed] = []

    df = _df_desde_fila_header(df_raw, 5)
    if df.empty:
        return ParseResult("Mercantil", [], 0, 0, ["Sin filas de datos."], [])

    c_fecha = _resolver_columna(df, "fecha")
    c_ref = _resolver_columna(df, "referencia")
    c_desc = _resolver_columna(df, "descripción", "descripcion")
    c_monto = _resolver_columna(df, "monto")

    if not all([c_fecha, c_ref, c_monto]):
        return ParseResult(
            "Mercantil",
            [],
            0,
            0,
            ["Faltan columnas esperadas (Fecha, Referencia, Monto)."],
            [],
        )

    skip_ref = "000000000000000"

    for idx, row in df.iterrows():
        n = int(idx) + 7
        try:
            ref = _norm_cell(row.get(c_ref))
            if ref.replace(" ", "") == skip_ref:
                continue

            fd = _parse_fecha(row.get(c_fecha))
            if fd is None:
                if all(
                    pd.isna(row.get(c)) or str(row.get(c)).strip() == ""
                    for c in df.columns
                ):
                    continue
                errores.append(f"Fila {n}: fecha inválida o vacía.")
                continue

            desc = _norm_cell(row.get(c_desc)) if c_desc else ""
            try:
                monto_raw = limpiar_monto(row.get(c_monto), "europeo")
            except ValueError as e:
                errores.append(f"Fila {n}: monto inválido ({e}).")
                continue

            if monto_raw == 0:
                continue

            movs.append(
                MovimientoParsed(
                    fecha=fd,
                    referencia=ref,
                    concepto=desc,
                    monto=abs(monto_raw),
                    es_ingreso=monto_raw > 0,
                    banco_detectado="Mercantil",
                )
            )
        except Exception as e:
            errores.append(f"Fila {n}: {e}")

    ti, te = _totales(movs)
    return ParseResult("Mercantil", movs, ti, te, errores, advertencias)


def _parse_df_raw(df_raw: pd.DataFrame) -> ParseResult:
    advertencias: list[str] = []
    try:
        banco = detectar_banco(df_raw)
    except ValueError as e:
        return ParseResult("", [], 0, 0, [str(e)], [])

    try:
        if banco == "BDV":
            return parsear_bdv(df_raw)
        if banco == "Banesco":
            return parsear_banesco(df_raw)
        if banco == "Bancamiga":
            return parsear_bancamiga(df_raw)
        if banco == "Mercantil":
            return parsear_mercantil(df_raw)
    except Exception as e:
        return ParseResult(banco, [], 0, 0, [f"Error al parsear: {e}"], advertencias)

    return ParseResult(banco, [], 0, 0, [f"Banco no implementado: {banco}"], [])


def parsear_archivo(filepath: str) -> ParseResult:
    """
    Detecta banco y parsea desde ruta de archivo.
    No lanza excepciones: errores en ParseResult.errores.
    """
    try:
        df_raw = pd.read_excel(filepath, header=None, engine="openpyxl")
    except Exception as e:
        return ParseResult(
            "",
            [],
            0,
            0,
            [f"No se pudo leer el archivo: {e}"],
            [],
        )
    return _parse_df_raw(df_raw)


def parsear_bytes(contenido: bytes) -> ParseResult:
    """Igual que parsear_archivo pero desde bytes (p. ej. st.file_uploader)."""
    try:
        df_raw = pd.read_excel(io.BytesIO(contenido), header=None, engine="openpyxl")
    except Exception as e:
        return ParseResult(
            "",
            [],
            0,
            0,
            [f"No se pudo leer el Excel: {e}"],
            [],
        )
    return _parse_df_raw(df_raw)
