"""
Agrupamiento de unidades por código (letra / bloque / decena) — lógica pura.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class GrupoUnidades:
    letra: str  # 'A', 'B', '100', 'SIN_GRUPO', etc.
    unidades: list[dict]
    total: int
    con_email: int


def detectar_numero(codigo_unidad: str) -> str:
    """
    Extrae la parte numérica principal del código para ordenar.
    Ej: 'A01' → '01', 'B12' → '12', '101' → '101'.
    """
    cod = (codigo_unidad or "").strip()
    nums = re.findall(r"\d+", cod)
    if not nums:
        return "0"
    return max(nums, key=lambda x: (len(x), x))


def detectar_grupo(codigo_unidad: str) -> str:
    """
    Detecta el grupo/letra de una unidad a partir de su código.

    - Letra(s) seguida de dígito → primera letra del prefijo alfabético
      (ej. 'A01' → 'A', 'AB12' → 'A', 'M04' → 'M').
    - Dígitos y al final letras → bloque alfabético final
      (ej. '01A' → 'A', '12B' → 'B').
    - Solo dígitos → bloque por centenas (ej. '101' → '100', '205' → '200').
    - Si no coincide → 'SIN_GRUPO'.
    """
    cod = (codigo_unidad or "").strip()
    if not cod:
        return "SIN_GRUPO"

    if re.fullmatch(r"\d+", cod):
        n = int(cod)
        if n >= 100:
            return str((n // 100) * 100)
        if n >= 10:
            return str((n // 10) * 10)
        return "0"

    m = re.match(r"^([A-Za-z]+)\d", cod)
    if m:
        return m.group(1)[0].upper()

    m = re.match(r"^\d+([A-Za-z]+)$", cod)
    if m:
        return m.group(1).upper()

    return "SIN_GRUPO"


def _tiene_correo(u: dict) -> bool:
    e = u.get("propietario_email")
    if e is None:
        return False
    if isinstance(e, list):
        return any(str(x or "").strip() for x in e)
    return bool(str(e).strip())


def agrupar_unidades(unidades: list[dict]) -> dict[str, GrupoUnidades]:
    """
    Agrupa unidades por grupo detectado.
    Cada unidad debe incluir al menos: unidad_id, unidad_codigo, propietario_nombre,
    propietario_email (str, lista de str o vacío).
    Retorna dict ordenado alfabéticamente por clave (SIN_GRUPO al final).
    """
    buckets: dict[str, list[dict]] = {}
    for u in unidades:
        cod = str(u.get("unidad_codigo") or "")
        g = detectar_grupo(cod)
        buckets.setdefault(g, []).append(u)

    def _sort_key(k: str) -> tuple[int, str]:
        return (1 if k == "SIN_GRUPO" else 0, k)

    result: dict[str, GrupoUnidades] = {}
    for k in sorted(buckets.keys(), key=_sort_key):
        lst = buckets[k]
        con_email = sum(1 for x in lst if _tiene_correo(x))
        result[k] = GrupoUnidades(
            letra=k,
            unidades=lst,
            total=len(lst),
            con_email=con_email,
        )
    return result
