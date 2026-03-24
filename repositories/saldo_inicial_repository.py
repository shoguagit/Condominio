"""
Carga y revisión de saldo inicial histórico por unidad (Fase 6-A).
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from utils.error_handler import DatabaseError, safe_db_operation
from utils.pdf_generator import monto_bs_a_usd

_MSG_MIGRACION_6B = (
    "Ejecute en Supabase (SQL Editor) el script **scripts/fase6a_saldo_inicial_migration.sql** "
    "completo (incluye columnas `meses_sin_pagar` y `primer_periodo`) "
    "o **scripts/fase6b_meses_sin_pagar_migration.sql**. "
    "Luego, en Supabase: **Settings → API → Reload schema** si el error menciona el caché de esquema."
)


def _es_error_columnas_meses_periodo(exc: Exception) -> bool:
    s = str(exc).lower()
    return (
        "meses_sin_pagar" in s
        or "primer_periodo" in s
        or "pgrst204" in s
        or "42703" in s
        or ("could not find" in s and "column" in s)
        or ("schema cache" in s and "column" in s)
    )


def _ejecutar_update_unidad(
    client: Client, tabla: str, unidad_id: int, payload: dict[str, Any]
) -> None:
    try:
        client.table(tabla).update(payload).eq("id", int(unidad_id)).execute()
    except Exception as e:
        if _es_error_columnas_meses_periodo(e):
            raise DatabaseError(
                f"Faltan columnas en la tabla `unidades` para guardar meses/primer período. {_MSG_MIGRACION_6B}"
            ) from e
        raise


def _normalizar_primer_periodo(val: str | None) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s[:7]
    if len(s) == 7 and s[4] == "-" and s[:4].isdigit() and s[5:].isdigit():
        return s
    return None


class SaldoInicialRepository:
    def __init__(self, client: Client):
        self.client = client
        self._tab = "unidades"
        self._condo = "condominios"

    @safe_db_operation("saldo_inicial.registrar_saldo_inicial")
    def registrar_saldo_inicial(
        self,
        condominio_id: int,
        codigo_unidad: str,
        saldo_bs: float,
        requiere_revision: bool,
        nota: str | None = None,
        meses_sin_pagar: int = 0,
        primer_periodo: str | None = None,
        forzar_update: bool = False,
    ) -> dict[str, Any]:
        """
        Busca la unidad por código y actualiza saldo inicial (o solo metadatos si ``forzar_update``).
        """
        cod = str(codigo_unidad or "").strip()
        if not cod:
            return {"encontrada": False, "unidad_id": None, "omitida": False, "solo_metadatos": False}

        rows = (
            self.client.table(self._tab)
            .select("id, saldo_inicial_bs")
            .eq("condominio_id", int(condominio_id))
            .eq("codigo", cod)
            .limit(1)
            .execute()
        ).data or []

        if not rows:
            return {"encontrada": False, "unidad_id": None, "omitida": False, "solo_metadatos": False}

        row0 = rows[0]
        uid = int(row0["id"])
        saldo_actual = float(row0.get("saldo_inicial_bs") or 0)
        pp_norm = _normalizar_primer_periodo(primer_periodo)
        meses_i = int(meses_sin_pagar or 0)

        if saldo_actual > 0 and forzar_update:
            payload_meta: dict[str, Any] = {
                "meses_sin_pagar": meses_i,
                "primer_periodo": pp_norm,
            }
            _ejecutar_update_unidad(self.client, self._tab, uid, payload_meta)
            return {
                "encontrada": True,
                "unidad_id": uid,
                "omitida": False,
                "solo_metadatos": True,
                "mensaje": "Actualizados solo meses y primer período (saldo sin cambios).",
            }

        if saldo_actual > 0:
            return {
                "encontrada": True,
                "unidad_id": uid,
                "omitida": True,
                "solo_metadatos": False,
                "mensaje": f"Ya tiene saldo Bs. {saldo_actual:,.2f}",
            }

        nota_val = (nota or "").strip() if requiere_revision else None

        payload: dict[str, Any] = {
            "saldo_inicial_bs": round(float(saldo_bs), 2),
            "saldo": round(float(saldo_bs), 2),
            "requiere_revision": bool(requiere_revision),
            "nota_revision": nota_val,
            "meses_sin_pagar": meses_i,
            "primer_periodo": pp_norm,
        }

        _ejecutar_update_unidad(self.client, self._tab, uid, payload)
        return {"encontrada": True, "unidad_id": uid, "omitida": False, "solo_metadatos": False}

    @safe_db_operation("saldo_inicial.obtener_resumen_saldos")
    def obtener_resumen_saldos(
        self,
        condominio_id: int,
        tasa_cambio: float = 0.0,
    ) -> dict[str, Any]:
        """
        Resumen de saldos en el condominio.
        ``tasa_cambio``: para ``suma_total_usd`` (sesión o BD).
        """
        cid = int(condominio_id)
        all_u = (
            self.client.table(self._tab)
            .select("id, saldo_inicial_bs, saldo, requiere_revision")
            .eq("condominio_id", cid)
            .execute()
        ).data or []

        total_unidades = len(all_u)
        con_si = 0
        req_rev = 0
        suma_bs = 0.0

        for r in all_u:
            s_ini = float(r.get("saldo_inicial_bs") or 0)
            if bool(r.get("requiere_revision")):
                req_rev += 1
            if s_ini != 0 or bool(r.get("requiere_revision")):
                con_si += 1
            suma_bs += s_ini

        tasa = float(tasa_cambio or 0)
        if tasa <= 0:
            crow = (
                self.client.table(self._condo)
                .select("tasa_cambio")
                .eq("id", cid)
                .limit(1)
                .execute()
            ).data or [{}]
            tasa = float((crow[0] or {}).get("tasa_cambio") or 0)

        suma_usd = monto_bs_a_usd(suma_bs, tasa) if tasa > 0 else 0.0

        return {
            "total_unidades": total_unidades,
            "con_saldo_inicial": con_si,
            "requieren_revision": req_rev,
            "suma_total_bs": round(suma_bs, 2),
            "suma_total_usd": round(float(suma_usd), 2),
        }

    @safe_db_operation("saldo_inicial.listar_requieren_revision")
    def listar_requieren_revision(self, condominio_id: int) -> list[dict]:
        rows = (
            self.client.table(self._tab)
            .select("id, codigo, numero, saldo, saldo_inicial_bs, nota_revision, propietarios(nombre)")
            .eq("condominio_id", int(condominio_id))
            .eq("requiere_revision", True)
            .order("codigo")
            .execute()
        ).data or []
        out: list[dict] = []
        for r in rows:
            p = r.get("propietarios") or {}
            nom = (p.get("nombre") if isinstance(p, dict) else None) or "—"
            cod = (r.get("codigo") or r.get("numero") or "").strip() or str(r.get("id"))
            out.append(
                {
                    "id": int(r["id"]),
                    "codigo": cod,
                    "numero_unidad": cod,
                    "propietario_nombre": nom,
                    "saldo": float(r.get("saldo") or 0),
                    "saldo_inicial_bs": float(r.get("saldo_inicial_bs") or 0),
                    "nota_revision": r.get("nota_revision") or "",
                }
            )
        return out

    @safe_db_operation("saldo_inicial.actualizar_saldo_manual")
    def actualizar_saldo_manual(
        self,
        unidad_id: int,
        saldo_bs: float,
        nota: str,
    ) -> dict:
        payload = {
            "saldo": round(float(saldo_bs), 2),
            "saldo_inicial_bs": round(float(saldo_bs), 2),
            "requiere_revision": False,
            "nota_revision": (nota or "").strip() or None,
        }
        resp = (
            self.client.table(self._tab)
            .update(payload)
            .eq("id", int(unidad_id))
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else {}
