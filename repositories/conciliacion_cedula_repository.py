"""Conciliación automática: cédula en descripción del movimiento → pago(s)."""

from __future__ import annotations

import logging
import re

from supabase import Client

from utils.error_handler import DatabaseError, safe_db_operation
from utils.supabase_compat import json_safe_date

logger = logging.getLogger(__name__)


def _normalize_ced(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", (s or "").upper())


def _cedulas_valores_para_in(cedulas: list[str]) -> list[str]:
    """Variantes exactas para PostgREST .in_('cedula', ...) según formatos típicos en BD."""
    seen: set[str] = set()
    out: list[str] = []
    for c in cedulas:
        n = _normalize_ced(c)
        if not n:
            continue
        candidatos = [n]
        if len(n) > 1 and n[0].isalpha():
            candidatos.append(n[1:])
            candidatos.append(f"{n[0]}-{n[1:]}")
        for cand in candidatos:
            if cand and cand not in seen:
                seen.add(cand)
                out.append(cand)
    return out


class ConciliacionCedulaRepository:
    def __init__(self, client: Client):
        self.client = client

    @safe_db_operation("conciliacion_cedula.obtener_tasa_condominio")
    def obtener_tasa_condominio(self, condominio_id: int) -> dict:
        """Lee tasa_cambio del condominio (vacío si no existe fila)."""
        rows = (
            self.client.table("condominios")
            .select("tasa_cambio")
            .eq("id", int(condominio_id))
            .limit(1)
            .execute()
        ).data or []
        return dict(rows[0]) if rows else {}

    @safe_db_operation("conciliacion_cedula.buscar_unidades_por_cedula")
    def buscar_unidades_por_cedula(
        self, cedulas: list[str], condominio_id: int
    ) -> list[dict]:
        """
        Unidades cuyo propietario principal (`unidades.propietario_id`) tiene
        `propietarios.cedula` igual a alguna variante buscada (coincidencia exacta en BD).

        Retorna: unidad_id, codigo_unidad, propietario_nombre, cedula_encontrada,
        cuota_bs, saldo_bs, propietario_id
        """
        if not cedulas:
            return []

        cedulas_buscar = _cedulas_valores_para_in(cedulas)
        if not cedulas_buscar:
            return []

        props = (
            self.client.table("propietarios")
            .select("id, nombre, cedula")
            .eq("condominio_id", int(condominio_id))
            .eq("activo", True)
            .in_("cedula", cedulas_buscar)
            .execute()
        ).data or []

        if not props:
            return []

        prop_map = {int(p["id"]): p for p in props}
        prop_ids = list(prop_map.keys())

        unidades_rows = (
            self.client.table("unidades")
            .select("id, codigo, numero, saldo, propietario_id")
            .eq("condominio_id", int(condominio_id))
            .eq("activo", True)
            .in_("propietario_id", prop_ids)
            .execute()
        ).data or []

        resultado: list[dict] = []
        for u in unidades_rows:
            pid = u.get("propietario_id")
            if pid is None:
                continue
            pid = int(pid)
            prop = prop_map.get(pid) or {}
            uid = int(u["id"])
            cod = (u.get("codigo") or u.get("numero") or "").strip() or str(uid)
            resultado.append(
                {
                    "unidad_id": uid,
                    "codigo_unidad": cod,
                    "propietario_nombre": str(prop.get("nombre") or ""),
                    "cedula_encontrada": str(prop.get("cedula") or ""),
                    "cuota_bs": 0.0,
                    "saldo_bs": float(u.get("saldo") or 0),
                    "propietario_id": pid,
                }
            )
        return resultado

    @safe_db_operation("conciliacion_cedula.obtener_cuota_unidad")
    def obtener_cuota_unidad(self, unidad_id: int, periodo: str) -> float:
        """
        cuota_calculada_bs de cuotas_unidad para la unidad y período (YYYY-MM-01).
        Retorna 0.0 si no existe.
        """
        p = json_safe_date(periodo)[:10]
        if len(p) < 10:
            return 0.0
        rows = (
            self.client.table("cuotas_unidad")
            .select("cuota_calculada_bs")
            .eq("unidad_id", int(unidad_id))
            .eq("periodo", p)
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            return 0.0
        return float(rows[0].get("cuota_calculada_bs") or 0)

    @safe_db_operation("conciliacion_cedula.registrar_pago_automatico")
    def registrar_pago_automatico(
        self,
        condominio_id: int,
        unidad_id: int,
        periodo: str,
        monto_bs: float,
        fecha_pago: str,
        referencia: str,
        movimiento_id: int,
        tipo_pago: str,
        tasa_cambio: float,
        propietario_id: int | None = None,
    ) -> dict:
        """
        Inserta fila en pagos con origen conciliacion_automatica.
        Evita duplicado (mismo movimiento_id + unidad_id).
        """
        periodo_d = json_safe_date(periodo)[:10]
        if len(periodo_d) < 10:
            raise DatabaseError("Período inválido para el pago automático.")

        dup = (
            self.client.table("pagos")
            .select("id")
            .eq("movimiento_id", int(movimiento_id))
            .eq("unidad_id", int(unidad_id))
            .limit(1)
            .execute()
        ).data or []
        if dup:
            return {**dup[0], "_es_reutilizado": True}

        ref = (referencia or "").strip() or f"AUTO-{movimiento_id}"
        tc = float(tasa_cambio or 0)
        m_usd = round(float(monto_bs) / tc, 4) if tc > 0 else 0.0

        payload = {
            "condominio_id": int(condominio_id),
            "unidad_id": int(unidad_id),
            "propietario_id": int(propietario_id) if propietario_id else None,
            "periodo": periodo_d,
            "fecha_pago": json_safe_date(fecha_pago)[:10],
            "monto_bs": round(float(monto_bs), 2),
            "monto_usd": m_usd,
            "tasa_cambio": tc,
            "metodo": "transferencia",
            "referencia": ref[:100],
            "estado": "confirmado",
            "tipo_pago": tipo_pago,
            "origen": "conciliacion_automatica",
            "movimiento_id": int(movimiento_id),
        }
        ins = self.client.table("pagos").insert(payload).execute().data or []
        if not ins:
            raise DatabaseError("No se pudo registrar el pago automático.")
        return {**ins[0], "_es_reutilizado": False}

    @safe_db_operation("conciliacion_cedula.marcar_movimiento_conciliado")
    def marcar_movimiento_conciliado(
        self, movimiento_id: int, pago_id: int
    ) -> dict:
        resp = (
            self.client.table("movimientos")
            .update(
                {
                    "conciliado": True,
                    "pago_id": int(pago_id),
                    "tipo_alerta": None,
                    "revisado": True,
                }
            )
            .eq("id", int(movimiento_id))
            .execute()
        ).data or []
        if not resp:
            raise DatabaseError("No se pudo actualizar el movimiento.")
        return resp[0]

    @safe_db_operation("conciliacion_cedula.movimiento_ya_conciliado")
    def movimiento_ya_conciliado(self, movimiento_id: int) -> bool:
        rows = (
            self.client.table("movimientos")
            .select("conciliado")
            .eq("id", int(movimiento_id))
            .limit(1)
            .execute()
        ).data or []
        return bool(rows and rows[0].get("conciliado"))

    def listar_pagos_automaticos_periodo(
        self,
        condominio_id: int,
        periodo_db: str,
        tipo_filtro: str | None = None,
    ) -> list[dict]:
        """
        Pagos automáticos por cédula en el período.

        Sin embeds; filtro `origen` en Python. Si Supabase/RLS falla, devuelve []
        y registra el error (no usa @safe_db_operation para no tumbar la página).
        """
        try:
            p = json_safe_date(periodo_db)[:10]
            rows = (
                self.client.table("pagos")
                .select("*")
                .eq("condominio_id", int(condominio_id))
                .eq("periodo", p)
                .execute()
            ).data or []

            rows = [
                r
                for r in rows
                if (r.get("origen") or "") == "conciliacion_automatica"
                and r.get("movimiento_id")
            ]

            def _fp_key(rec: dict) -> str:
                fp = rec.get("fecha_pago")
                return str(fp or "")[:10]

            rows.sort(key=_fp_key, reverse=True)

            out = list(rows)
            if tipo_filtro and tipo_filtro != "Todos":
                out = [r for r in out if (r.get("tipo_pago") or "") == tipo_filtro]

            chunk = 80
            mids = sorted(
                {int(r["movimiento_id"]) for r in out if r.get("movimiento_id")}
            )
            mov_by_id: dict[int, dict] = {}
            if mids:
                for i in range(0, len(mids), chunk):
                    part = mids[i : i + chunk]
                    mrows = (
                        self.client.table("movimientos")
                        .select("id, fecha, referencia, descripcion, conciliado")
                        .in_("id", part)
                        .execute()
                    ).data or []
                    for m in mrows:
                        if m.get("id") is not None:
                            mov_by_id[int(m["id"])] = m

            uids = sorted({int(r["unidad_id"]) for r in out if r.get("unidad_id")})
            uni_by_id: dict[int, dict] = {}
            if uids:
                for i in range(0, len(uids), chunk):
                    part = uids[i : i + chunk]
                    urows = (
                        self.client.table("unidades")
                        .select("id, codigo")
                        .in_("id", part)
                        .execute()
                    ).data or []
                    for u in urows:
                        if u.get("id") is not None:
                            uni_by_id[int(u["id"])] = u

            for r in out:
                mid = r.get("movimiento_id")
                r["movimientos"] = mov_by_id.get(int(mid)) if mid is not None else {}
                uid = r.get("unidad_id")
                r["unidades"] = uni_by_id.get(int(uid)) if uid is not None else {}

            return out
        except Exception as e:
            logger.warning(
                "conciliacion_cedula.listar_pagos_automaticos_periodo: %s",
                e,
                exc_info=True,
            )
            return []
