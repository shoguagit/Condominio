"""
Carga y revisión de saldo inicial histórico por unidad (Fase 6-A).
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from utils.error_handler import safe_db_operation
from utils.pdf_generator import monto_bs_a_usd


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
    ) -> dict[str, Any]:
        """
        Busca la unidad por código en el condominio y actualiza saldo inicial y saldo actual.
        """
        cod = str(codigo_unidad or "").strip()
        if not cod:
            return {"encontrada": False, "unidad_id": None}

        rows = (
            self.client.table(self._tab)
            .select("id")
            .eq("condominio_id", int(condominio_id))
            .eq("codigo", cod)
            .limit(1)
            .execute()
        ).data or []

        if not rows:
            return {"encontrada": False, "unidad_id": None}

        uid = int(rows[0]["id"])
        nota_val = (nota or "").strip() if requiere_revision else None

        payload: dict[str, Any] = {
            "saldo_inicial_bs": round(float(saldo_bs), 2),
            "saldo": round(float(saldo_bs), 2),
            "requiere_revision": bool(requiere_revision),
            "nota_revision": nota_val,
        }

        self.client.table(self._tab).update(payload).eq("id", uid).execute()
        return {"encontrada": True, "unidad_id": uid}

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
