"""Cobros extraordinarios distribuidos por indiviso (Fase 4-B)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from supabase import Client

from utils.cobros_extraordinarios import (
    distribuir_monto_entre_unidades,
    validar_cobro_extraordinario,
)
from utils.error_handler import safe_db_operation


class CobroExtraordinarioRepository:
    def __init__(self, client: Client):
        self.client = client
        self._t_cobros = "cobros_extraordinarios"
        self._t_det = "cobros_extraordinarios_unidad"

    @safe_db_operation("cobro_ext.listar_por_periodo")
    def listar_por_periodo(self, condominio_id: int, periodo: str) -> list[dict]:
        """Cobros activos del condominio para período YYYY-MM (incluye n_unidades)."""
        ym = periodo[:7] if periodo else ""
        cobros = (
            self.client.table(self._t_cobros)
            .select("*")
            .eq("condominio_id", condominio_id)
            .eq("periodo", ym)
            .eq("activo", True)
            .order("created_at", desc=False)
            .execute()
        ).data or []
        if not cobros:
            return []
        det = (
            self.client.table(self._t_det)
            .select("cobro_extraordinario_id")
            .eq("condominio_id", condominio_id)
            .eq("periodo", ym)
            .execute()
        ).data or []
        cnt = Counter(int(r["cobro_extraordinario_id"]) for r in det)
        for row in cobros:
            row["n_unidades"] = int(cnt.get(int(row["id"]), 0))
        return cobros

    def crear(
        self,
        condominio_id: int,
        periodo: str,
        concepto: str,
        monto_total: float,
    ) -> dict:
        """
        Valida concepto y monto; crea cabecera y detalle por unidad activa.
        periodo: YYYY-MM (o YYYY-MM-01, se normaliza a YYYY-MM).
        """
        validar_cobro_extraordinario(concepto, monto_total)
        return self._crear_distribuir(condominio_id, periodo, concepto, monto_total)

    @safe_db_operation("cobro_ext.crear")
    def _crear_distribuir(
        self,
        condominio_id: int,
        periodo: str,
        concepto: str,
        monto_total: float,
    ) -> dict:
        ym = periodo[:7] if periodo else ""
        unidades = (
            self.client.table("unidades")
            .select("id, indiviso_pct")
            .eq("condominio_id", condominio_id)
            .eq("activo", True)
            .execute()
        ).data or []
        distrib = distribuir_monto_entre_unidades(float(monto_total), unidades)
        cobro_row = (
            self.client.table(self._t_cobros)
            .insert(
                {
                    "condominio_id": condominio_id,
                    "periodo": ym,
                    "concepto": (concepto or "").strip(),
                    "monto_total": round(float(monto_total), 2),
                    "activo": True,
                }
            )
            .execute()
        ).data[0]
        cid = int(cobro_row["id"])
        for uid, monto in distrib:
            self.client.table(self._t_det).insert(
                {
                    "cobro_extraordinario_id": cid,
                    "unidad_id": uid,
                    "condominio_id": condominio_id,
                    "periodo": ym,
                    "monto": monto,
                    "pagado": False,
                }
            ).execute()
        return {
            "cobro": cobro_row,
            "unidades_afectadas": len(distrib),
        }

    @safe_db_operation("cobro_ext.eliminar")
    def eliminar(self, cobro_id: int) -> bool:
        """Soft delete si el período del cobro no está cerrado."""
        rows = (
            self.client.table(self._t_cobros)
            .select("id, condominio_id, periodo, activo")
            .eq("id", cobro_id)
            .limit(1)
            .execute()
        ).data
        if not rows:
            return False
        row = rows[0]
        if not row.get("activo", True):
            return False
        ym = str(row.get("periodo") or "")[:7]
        periodo_db = f"{ym}-01" if len(ym) == 7 else ym
        proc = (
            self.client.table("procesos_mensuales")
            .select("estado")
            .eq("condominio_id", int(row["condominio_id"]))
            .eq("periodo", periodo_db)
            .limit(1)
            .execute()
        ).data
        if proc and str(proc[0].get("estado") or "").lower() == "cerrado":
            return False
        now = datetime.now(timezone.utc).isoformat()
        self.client.table(self._t_cobros).update(
            {"activo": False, "updated_at": now}
        ).eq("id", cobro_id).execute()
        return True

    @safe_db_operation("cobro_ext.total_por_unidad")
    def total_por_unidad(self, unidad_id: int, periodo: str) -> float:
        """Suma montos de detalle cuyo cobro padre está activo."""
        ym = periodo[:7] if periodo else ""
        det = (
            self.client.table(self._t_det)
            .select("monto, cobro_extraordinario_id")
            .eq("unidad_id", unidad_id)
            .eq("periodo", ym)
            .execute()
        ).data or []
        if not det:
            return 0.0
        ids = list({int(r["cobro_extraordinario_id"]) for r in det})
        parents = (
            self.client.table(self._t_cobros)
            .select("id, activo")
            .in_("id", ids)
            .execute()
        ).data or []
        active = {int(p["id"]) for p in parents if p.get("activo", True)}
        total = sum(
            float(r.get("monto") or 0)
            for r in det
            if int(r["cobro_extraordinario_id"]) in active
        )
        return round(total, 2)

    @safe_db_operation("cobro_ext.listar_detalle_unidad")
    def listar_detalle_unidad(self, unidad_id: int, periodo: str) -> list[dict]:
        """Filas con concepto y monto para estado de cuenta."""
        ym = periodo[:7] if periodo else ""
        det = (
            self.client.table(self._t_det)
            .select("monto, cobro_extraordinario_id")
            .eq("unidad_id", unidad_id)
            .eq("periodo", ym)
            .execute()
        ).data or []
        if not det:
            return []
        ids = list({int(r["cobro_extraordinario_id"]) for r in det})
        parents = (
            self.client.table(self._t_cobros)
            .select("id, concepto, activo")
            .in_("id", ids)
            .execute()
        ).data or []
        pmap = {int(p["id"]): p for p in parents}
        out: list[dict] = []
        for r in det:
            pid = int(r["cobro_extraordinario_id"])
            p = pmap.get(pid)
            if not p or not p.get("activo", True):
                continue
            out.append(
                {
                    "concepto": p.get("concepto") or "—",
                    "monto": round(float(r.get("monto") or 0), 2),
                    "cobro_extraordinario_id": pid,
                }
            )
        return out
