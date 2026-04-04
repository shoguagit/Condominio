"""Conciliación automática: cédula en descripción del movimiento → pago(s)."""

from __future__ import annotations

import re

from supabase import Client

from utils.error_handler import DatabaseError, safe_db_operation
from utils.supabase_compat import json_safe_date


def _normalize_ced(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", (s or "").upper())


def _variantes_busqueda(cedulas: list[str]) -> set[str]:
    v: set[str] = set()
    for c in cedulas:
        n = _normalize_ced(c)
        if n:
            v.add(n)
            if len(n) > 1 and n[0].isalpha():
                v.add(n[1:])
    return v


def _cedula_propietario_coincide(db_ced: str | None, variantes: set[str]) -> bool:
    n = _normalize_ced(db_ced or "")
    if not n:
        return False
    if n in variantes:
        return True
    if len(n) > 1 and n[0].isalpha() and n[1:] in variantes:
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
        Busca unidades cuyo propietario tenga alguna de las cédulas indicadas.
        Retorna lista de dicts con:
        unidad_id, codigo_unidad, propietario_nombre, cedula_encontrada,
        cuota_bs, saldo_bs, propietario_id
        """
        if not cedulas:
            return []
        variantes = _variantes_busqueda(cedulas)
        props = (
            self.client.table("propietarios")
            .select("id, nombre, cedula")
            .eq("condominio_id", int(condominio_id))
            .eq("activo", True)
            .execute()
        ).data or []

        matched: list[tuple[int, str, str]] = []
        for p in props:
            ced_db = p.get("cedula")
            if not _cedula_propietario_coincide(ced_db, variantes):
                continue
            dbn = _normalize_ced(str(ced_db))
            cedula_encontrada = dbn
            for c in cedulas:
                cn = _normalize_ced(c)
                if cn == dbn or (len(cn) > 1 and cn[1:] == dbn) or (
                    len(dbn) > 1 and dbn[1:] == cn
                ):
                    cedula_encontrada = c.replace("-", "").upper()
                    break
            matched.append(
                (int(p["id"]), str(p.get("nombre") or ""), cedula_encontrada)
            )

        if not matched:
            return []

        unidad_ids: set[int] = set()
        prop_by_unidad: dict[int, tuple[int, str, str]] = {}

        for pid, nombre, ced_enc in matched:
            u_direct = (
                self.client.table("unidades")
                .select("id, codigo, numero, saldo, propietario_id")
                .eq("condominio_id", int(condominio_id))
                .eq("activo", True)
                .eq("propietario_id", pid)
                .execute()
            ).data or []
            for u in u_direct:
                uid = int(u["id"])
                unidad_ids.add(uid)
                prop_by_unidad[uid] = (pid, nombre, ced_enc)

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
                prop_by_unidad[uid] = (pid, nombre, ced_enc)

        out: list[dict] = []
        for uid in sorted(unidad_ids):
            urow = (
                self.client.table("unidades")
                .select("id, codigo, numero, saldo")
                .eq("id", uid)
                .limit(1)
                .execute()
            ).data or []
            if not urow:
                continue
            u = urow[0]
            pid, nom, ced_e = prop_by_unidad[uid]
            cod = (u.get("codigo") or u.get("numero") or "").strip() or str(uid)
            out.append(
                {
                    "unidad_id": uid,
                    "codigo_unidad": cod,
                    "propietario_nombre": nom,
                    "cedula_encontrada": ced_e,
                    "cuota_bs": 0.0,
                    "saldo_bs": float(u.get("saldo") or 0),
                    "propietario_id": pid,
                }
            )
        return out

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

    @safe_db_operation("conciliacion_cedula.listar_pagos_automaticos_periodo")
    def listar_pagos_automaticos_periodo(
        self,
        condominio_id: int,
        periodo_db: str,
        tipo_filtro: str | None = None,
    ) -> list[dict]:
        """
        Pagos con origen conciliacion_automatica y movimiento vinculado.
        No usa embed `movimientos(...)` (PostgREST a veces no expone la FK hasta
        recargar esquema); carga movimientos en un segundo SELECT por ids.
        """
        p = json_safe_date(periodo_db)[:10]
        rows = (
            self.client.table("pagos")
            .select(
                "id, fecha_pago, monto_bs, tipo_pago, estado, referencia, movimiento_id, "
                "unidades(codigo, numero)"
            )
            .eq("condominio_id", int(condominio_id))
            .eq("periodo", p)
            .eq("origen", "conciliacion_automatica")
            .order("fecha_pago", desc=True)
            .execute()
        ).data or []

        out = [r for r in rows if r.get("movimiento_id")]
        if tipo_filtro and tipo_filtro != "Todos":
            out = [r for r in out if (r.get("tipo_pago") or "") == tipo_filtro]

        mids = sorted({int(r["movimiento_id"]) for r in out if r.get("movimiento_id")})
        mov_by_id: dict[int, dict] = {}
        if mids:
            chunk = 80
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

        for r in out:
            mid = r.get("movimiento_id")
            r["movimientos"] = mov_by_id.get(int(mid)) if mid is not None else {}

        return out
