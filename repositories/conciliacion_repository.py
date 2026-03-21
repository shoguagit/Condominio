"""Conciliación bancaria: movimientos (ingresos) vs pagos registrados (Fase 4-C)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from supabase import Client

from utils.conciliacion import evaluar_estado_conciliacion
from utils.error_handler import DatabaseError, safe_db_operation


def _parse_date(d: Any) -> date | None:
    if d is None:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    s = str(d)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


class ConciliacionRepository:
    def __init__(self, client: Client):
        self.client = client
        self._mov = "movimientos"
        self._pag = "pagos"
        self._conc = "conciliaciones"

    @safe_db_operation("conciliacion.obtener_estado_periodo")
    def obtener_estado_periodo(self, condominio_id: int, periodo_db: str) -> dict:
        """periodo_db: fecha del mes en BD (ej. 2026-02-01) como en movimientos/pagos."""
        ingresos = (
            self.client.table(self._mov)
            .select(
                "id, monto_bs, conciliado, tipo_alerta, revisado, referencia, fecha, pago_id"
            )
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo_db)
            .eq("tipo", "ingreso")
            .execute()
        ).data or []

        total_mov = len(ingresos)
        conc = sum(1 for r in ingresos if r.get("conciliado"))
        sin_con = total_mov - conc
        saldo_banco = round(sum(float(r.get("monto_bs") or 0) for r in ingresos), 2)

        rows_p = (
            self.client.table(self._pag)
            .select("monto_bs")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo_db)
            .execute()
        ).data or []
        saldo_sistema = round(sum(float(r.get("monto_bs") or 0) for r in rows_p), 2)

        diferencia = round(saldo_banco - saldo_sistema, 2)
        balance_estado = evaluar_estado_conciliacion(saldo_banco, saldo_sistema)
        if balance_estado == "con_diferencias":
            estado = "con_diferencias"
        elif sin_con > 0 or any(
            r.get("tipo_alerta") and not r.get("revisado") for r in ingresos
        ):
            estado = "pendiente"
        else:
            estado = "conciliado"

        alertas = [r for r in ingresos if r.get("tipo_alerta")]

        return {
            "total_movimientos_banco": total_mov,
            "total_conciliados": conc,
            "total_sin_conciliar": sin_con,
            "saldo_banco": saldo_banco,
            "saldo_sistema": saldo_sistema,
            "diferencia": diferencia,
            "estado": estado,
            "alertas": alertas,
        }

    @safe_db_operation("conciliacion.sugerir_vinculacion")
    def sugerir_vinculacion(
        self, movimiento_id: int, condominio_id: int, periodo_db: str
    ) -> dict | None:
        mrows = (
            self.client.table(self._mov)
            .select("*")
            .eq("id", movimiento_id)
            .eq("condominio_id", condominio_id)
            .limit(1)
            .execute()
        ).data
        if not mrows:
            return None
        mov = mrows[0]
        if (mov.get("tipo") or "").lower() != "ingreso":
            return None

        pagos = (
            self.client.table(self._pag)
            .select("*, unidades(codigo, numero)")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo_db)
            .execute()
        ).data or []

        ref_m = (mov.get("referencia") or "").strip()
        mb = float(mov.get("monto_bs") or 0)
        f_mov = _parse_date(mov.get("fecha"))

        for p in pagos:
            ref_p = (p.get("referencia") or "").strip()
            if ref_m and ref_p and ref_m == ref_p:
                return {
                    "pago": p,
                    "confianza": "alta",
                    "razon": "referencia",
                }

        if f_mov:
            for p in pagos:
                fp = _parse_date(p.get("fecha_pago"))
                if not fp:
                    continue
                mp = float(p.get("monto_bs") or 0)
                same_wk = f_mov.isocalendar()[:2] == fp.isocalendar()[:2]
                if abs(mb - mp) <= 1.01 and same_wk:
                    return {
                        "pago": p,
                        "confianza": "media",
                        "razon": "monto_semana",
                    }

        if f_mov:
            for p in pagos:
                fp = _parse_date(p.get("fecha_pago"))
                if not fp:
                    continue
                mp = float(p.get("monto_bs") or 0)
                if (
                    f_mov.year == fp.year
                    and f_mov.month == fp.month
                    and round(mb, 2) == round(mp, 2)
                ):
                    return {
                        "pago": p,
                        "confianza": "baja",
                        "razon": "monto_mes",
                    }

        return None

    @safe_db_operation("conciliacion.confirmar_vinculacion")
    def confirmar_vinculacion(
        self, movimiento_id: int, pago_id: int, usuario: str
    ) -> dict:
        mrows = (
            self.client.table(self._mov)
            .select("*")
            .eq("id", movimiento_id)
            .limit(1)
            .execute()
        ).data
        if not mrows:
            raise DatabaseError("Movimiento no encontrado.")
        mov = mrows[0]
        prows = (
            self.client.table(self._pag)
            .select("*")
            .eq("id", pago_id)
            .limit(1)
            .execute()
        ).data
        if not prows:
            raise DatabaseError("Pago no encontrado.")
        pago = prows[0]
        mb = float(mov.get("monto_bs") or 0)
        mp = float(pago.get("monto_bs") or 0)
        tipo_alerta = None
        if round(mb, 2) != round(mp, 2):
            tipo_alerta = "monto_no_coincide"

        return (
            self.client.table(self._mov)
            .update(
                {
                    "conciliado": True,
                    "pago_id": pago_id,
                    "tipo_alerta": tipo_alerta,
                    "revisado": True,
                }
            )
            .eq("id", movimiento_id)
            .execute()
        ).data[0]

    @safe_db_operation("conciliacion.rechazar_vinculacion")
    def rechazar_vinculacion(
        self, movimiento_id: int, tipo_alerta: str, usuario: str
    ) -> dict:
        return (
            self.client.table(self._mov)
            .update(
                {
                    "revisado": True,
                    "tipo_alerta": tipo_alerta,
                    "conciliado": False,
                    "pago_id": None,
                }
            )
            .eq("id", movimiento_id)
            .execute()
        ).data[0]

    @safe_db_operation("conciliacion.detectar_pagos_sin_movimiento")
    def detectar_pagos_sin_movimiento(
        self, condominio_id: int, periodo_db: str
    ) -> list[dict]:
        pagos = (
            self.client.table(self._pag)
            .select("*, unidades(codigo, numero)")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo_db)
            .execute()
        ).data or []

        movs = (
            self.client.table(self._mov)
            .select("pago_id")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo_db)
            .execute()
        ).data or []
        linked = {
            int(m["pago_id"])
            for m in movs
            if m.get("pago_id") is not None
        }

        return [p for p in pagos if int(p["id"]) not in linked]

    @safe_db_operation("conciliacion.cerrar_conciliacion")
    def cerrar_conciliacion(
        self, condominio_id: int, periodo_db: str, usuario: str
    ) -> dict:
        ym = periodo_db[:7] if periodo_db else ""
        estado = self.obtener_estado_periodo(condominio_id, periodo_db)
        if round(float(estado["diferencia"]), 2) != 0.0:
            raise DatabaseError(
                "No se puede cerrar la conciliación: la diferencia debe ser Bs. 0,00."
            )

        sin_mov = self.detectar_pagos_sin_movimiento(condominio_id, periodo_db)

        row = (
            self.client.table(self._conc)
            .insert(
                {
                    "condominio_id": condominio_id,
                    "periodo": ym,
                    "saldo_banco": float(estado["saldo_banco"]),
                    "saldo_sistema": float(estado["saldo_sistema"]),
                    "estado": "conciliado",
                    "movimientos_banco": int(estado["total_movimientos_banco"]),
                    "movimientos_conciliados": int(estado["total_conciliados"]),
                    "pagos_sin_movimiento": len(sin_mov),
                    "created_by": (usuario or "")[:255],
                }
            )
            .execute()
        ).data[0]
        return row
