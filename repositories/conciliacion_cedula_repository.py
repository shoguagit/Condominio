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


def _cedula_comparable_key(raw: str | None) -> str:
    """
    Clave estable para comparar cédula banco vs BD (puntos, guiones, ceros a la izquierda).
    Ej.: V05220576 y V5220576 normalizados al mismo prefijo+numérico sin ceros iniciales.
    """
    n = _normalize_ced(raw or "")
    if not n:
        return ""
    if len(n) > 1 and n[0].isalpha():
        num = n[1:].lstrip("0") or "0"
        return n[0] + num
    return n.lstrip("0") or "0"


def _cedula_coincide_lista(cedulas_banco: list[str], cedula_db: str | None) -> bool:
    if not cedulas_banco:
        return False
    kdb = _cedula_comparable_key(cedula_db)
    if not kdb:
        return False
    for c in cedulas_banco:
        if _cedula_comparable_key(c) == kdb:
            return True
    return False


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
        Unidades vinculadas a propietarios cuya cédula coincide con las extraídas del banco.

        1) Intenta coincidencia exacta en SQL (.in_ con variantes).
        2) Si no hay filas: recorre propietarios activos del condominio y compara con
           clave comparable (formato distinto, ceros a la izquierda).
        3) Une unidades por `propietario_id` principal y por `unidad_propietarios`
           (titular y copropietario).

        Retorna: unidad_id, codigo_unidad, propietario_nombre, cedula_encontrada,
        cuota_bs, saldo_bs, propietario_id
        """
        if not cedulas:
            return []

        cedulas_buscar = _cedulas_valores_para_in(cedulas)
        props: list[dict] = []
        if cedulas_buscar:
            props = (
                self.client.table("propietarios")
                .select("id, nombre, cedula")
                .eq("condominio_id", int(condominio_id))
                .eq("activo", True)
                .in_("cedula", cedulas_buscar)
                .execute()
            ).data or []

        if not props:
            all_p = (
                self.client.table("propietarios")
                .select("id, nombre, cedula")
                .eq("condominio_id", int(condominio_id))
                .eq("activo", True)
                .execute()
            ).data or []
            props = [
                p for p in all_p if _cedula_coincide_lista(cedulas, p.get("cedula"))
            ]

        if not props:
            return []

        prop_map = {int(p["id"]): p for p in props}
        prop_ids = list(prop_map.keys())

        unidad_ids: set[int] = set()
        prop_por_unidad: dict[int, int] = {}

        for pid in prop_ids:
            u_direct = (
                self.client.table("unidades")
                .select("id")
                .eq("condominio_id", int(condominio_id))
                .eq("activo", True)
                .eq("propietario_id", pid)
                .execute()
            ).data or []
            for u in u_direct:
                uid = int(u["id"])
                unidad_ids.add(uid)
                prop_por_unidad.setdefault(uid, pid)

            up_rows = (
                self.client.table("unidad_propietarios")
                .select("unidad_id")
                .eq("propietario_id", pid)
                .execute()
            ).data or []
            for row in up_rows:
                uid = row.get("unidad_id")
                if uid is None:
                    continue
                uid = int(uid)
                ucheck = (
                    self.client.table("unidades")
                    .select("id, condominio_id, activo")
                    .eq("id", uid)
                    .limit(1)
                    .execute()
                ).data or []
                if not ucheck:
                    continue
                if int(ucheck[0].get("condominio_id") or 0) != int(condominio_id):
                    continue
                if ucheck[0].get("activo") is False:
                    continue
                unidad_ids.add(uid)
                prop_por_unidad.setdefault(uid, pid)

        if not unidad_ids:
            return []

        ulist = sorted(unidad_ids)
        chunk = 80
        urows_full: list[dict] = []
        for i in range(0, len(ulist), chunk):
            part = ulist[i : i + chunk]
            batch = (
                self.client.table("unidades")
                .select("id, codigo, saldo")
                .in_("id", part)
                .execute()
            ).data or []

            urows_full.extend(batch or [])

        resultado: list[dict] = []
        for u in urows_full:
            uid = int(u["id"])
            pid = prop_por_unidad.get(uid)
            if pid is None:
                continue
            prop = prop_map.get(pid) or {}
            cod = (u.get("codigo") or "").strip() or str(uid)
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
        resultado.sort(key=lambda r: (r["codigo_unidad"] or "").upper())
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
