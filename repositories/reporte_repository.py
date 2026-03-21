"""
Datos agregados para reportes PDF (Fase 3).
"""

from __future__ import annotations

import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from supabase import Client

from utils.reportes_logic import map_categoria_gasto

logger = logging.getLogger(__name__)


def _lista_periodos_hacia_atras(periodo_db: str, n: int) -> list[str]:
    """n períodos desde periodo_db hacia atrás, orden cronológico ascendente."""
    d0 = datetime.strptime(periodo_db[:10], "%Y-%m-%d").date().replace(day=1)
    raw = [(d0 - relativedelta(months=i)).isoformat() for i in range(n)]
    return list(reversed(raw))


class ReporteRepository:
    def __init__(self, client: Client):
        self.client = client

    def get_cuota_unidad_periodo(
        self, condominio_id: int, unidad_id: int, periodo: str
    ) -> dict | None:
        try:
            r = (
                self.client.table("cuotas_unidad")
                .select("*")
                .eq("condominio_id", condominio_id)
                .eq("unidad_id", unidad_id)
                .eq("periodo", periodo)
                .limit(1)
                .execute()
            )
            rows = r.data or []
            return rows[0] if rows else None
        except Exception as e:
            logger.warning("get_cuota_unidad_periodo: %s", e)
            return None

    def get_estado_cuenta(
        self, unidad_id: int, periodo: str, condominio_id: int
    ) -> dict:
        """Datos para estado de cuenta individual."""
        out: dict = {
            "unidad": None,
            "propietario": None,
            "cuota_row": None,
            "saldo_anterior_bs": 0.0,
            "cuota_ordinaria_bs": 0.0,
            "mora_bs": 0.0,
            "total_a_pagar_bs": 0.0,
            "pagos_recibidos_bs": 0.0,
            "saldo_cierre_bs": 0.0,
        }
        try:
            u = (
                self.client.table("unidades")
                .select("*, propietarios(id, nombre, cedula, correo)")
                .eq("id", unidad_id)
                .eq("condominio_id", condominio_id)
                .single()
                .execute()
            ).data
            out["unidad"] = u
            out["propietario"] = u.get("propietarios") if u else None

            cuota = self.get_cuota_unidad_periodo(condominio_id, unidad_id, periodo)
            out["cuota_row"] = cuota
            if cuota:
                out["saldo_anterior_bs"] = float(cuota.get("saldo_anterior_bs") or 0)
                out["cuota_ordinaria_bs"] = float(cuota.get("cuota_calculada_bs") or 0)
                out["mora_bs"] = float(cuota.get("mora_bs") or 0)
                out["total_a_pagar_bs"] = float(cuota.get("total_a_pagar_bs") or 0)
            else:
                out["saldo_anterior_bs"] = float(u.get("saldo") or 0) if u else 0.0

            pag_rows = (
                self.client.table("pagos")
                .select("monto_bs")
                .eq("unidad_id", unidad_id)
                .eq("periodo", periodo)
                .execute()
            ).data
            out["pagos_recibidos_bs"] = float(
                sum(float(x.get("monto_bs") or 0) for x in (pag_rows or []))
            )

            if cuota:
                base = out["saldo_anterior_bs"] + out["cuota_ordinaria_bs"] + out["mora_bs"]
                out["saldo_cierre_bs"] = round(base - out["pagos_recibidos_bs"], 2)
            else:
                out["total_a_pagar_bs"] = round(
                    out["saldo_anterior_bs"] + out["cuota_ordinaria_bs"], 2
                )
                out["saldo_cierre_bs"] = round(
                    out["saldo_anterior_bs"] + out["cuota_ordinaria_bs"] - out["pagos_recibidos_bs"],
                    2,
                )
        except Exception as e:
            logger.warning("get_estado_cuenta: %s", e)
        return out

    def get_historico_unidad(self, unidad_id: int, periodo_actual: str, periodos: int = 3) -> list[dict]:
        try:
            u = (
                self.client.table("unidades")
                .select("condominio_id")
                .eq("id", unidad_id)
                .single()
                .execute()
            ).data
            condo_id = int(u["condominio_id"])
        except Exception:
            return []
        hist: list[dict] = []
        for p in _lista_periodos_hacia_atras(periodo_actual, periodos):
            cuota = self.get_cuota_unidad_periodo(condo_id, unidad_id, p)
            pag = (
                self.client.table("pagos")
                .select("monto_bs")
                .eq("unidad_id", unidad_id)
                .eq("periodo", p)
                .execute()
            ).data
            pagado = float(sum(float(x.get("monto_bs") or 0) for x in (pag or [])))
            cuota_bs = float(cuota.get("cuota_calculada_bs") or 0) if cuota else 0.0
            saldo_bs = float(cuota.get("total_a_pagar_bs") or 0) if cuota else 0.0
            hist.append(
                {
                    "periodo": p,
                    "cuota_bs": cuota_bs,
                    "pagado_bs": pagado,
                    "saldo_bs": saldo_bs,
                }
            )
        return hist

    def _meses_atraso_unidad(
        self, condominio_id: int, unidad_id: int, periodo_db: str
    ) -> int:
        try:
            rows = (
                self.client.table("cuotas_unidad")
                .select("periodo, total_a_pagar_bs")
                .eq("condominio_id", condominio_id)
                .eq("unidad_id", unidad_id)
                .order("periodo", desc=True)
                .execute()
            ).data
        except Exception:
            return 0
        if not rows:
            return 1  # deuda sin cuotas formalizadas
        count = 0
        started = False
        target = periodo_db[:10]
        for r in rows or []:
            per = str(r.get("periodo"))[:10]
            if per > target:
                continue
            if per == target:
                started = True
            if not started:
                continue
            if float(r.get("total_a_pagar_bs") or 0) > 0:
                count += 1
            else:
                break
        if not started and float(rows[0].get("total_a_pagar_bs") or 0) > 0:
            return len([x for x in rows if float(x.get("total_a_pagar_bs") or 0) > 0])
        return count

    def get_morosidad(self, condominio_id: int, periodo: str, filtro: str) -> list[dict]:
        """
        filtro: 'todos' | 'morosos' | 'parciales'
        todos = saldo > 0; morosos = moroso; parciales = parcial
        """
        filtro = (filtro or "todos").lower()
        try:
            q = (
                self.client.table("unidades")
                .select("*, propietarios(nombre, cedula)")
                .eq("condominio_id", condominio_id)
                .eq("activo", True)
            )
            rows = q.execute().data or []
        except Exception as e:
            logger.warning("get_morosidad: %s", e)
            return []

        out: list[dict] = []
        for u in rows:
            saldo = float(u.get("saldo") or 0)
            if saldo <= 0:
                continue
            ep = (u.get("estado_pago") or "").lower()
            if filtro == "morosos" and ep != "moroso":
                continue
            if filtro == "parciales" and ep != "parcial":
                continue
            uid = int(u["id"])
            meses = self._meses_atraso_unidad(condominio_id, uid, periodo)
            mora_bs = 0.0
            out.append(
                {
                    "unidad_id": uid,
                    "codigo": u.get("codigo") or u.get("numero") or "—",
                    "propietario": (u.get("propietarios") or {}).get("nombre", "—"),
                    "meses_atraso": max(meses, 1),
                    "deuda_bs": saldo,
                    "mora_bs": mora_bs,
                    "total_bs": saldo + mora_bs,
                    "estado_pago": ep,
                }
            )
        return out

    def get_balance(self, condominio_id: int, periodo: str) -> dict:
        """Ingresos reales (pagos) y gastos reales (egresos)."""
        try:
            pag_rows = (
                self.client.table("pagos")
                .select("monto_bs, monto_usd")
                .eq("condominio_id", condominio_id)
                .eq("periodo", periodo)
                .execute()
            ).data
            total_cuotas_cobradas_bs = float(
                sum(float(x.get("monto_bs") or 0) for x in (pag_rows or []))
            )
            total_cuotas_cobradas_usd = float(
                sum(float(x.get("monto_usd") or 0) for x in (pag_rows or []))
            )

            extra_rows = (
                self.client.table("movimientos")
                .select("monto_bs, monto_usd, descripcion, unidad_id")
                .eq("condominio_id", condominio_id)
                .eq("periodo", periodo)
                .eq("tipo", "ingreso")
                .execute()
            ).data
            cobros_extra_bs = float(
                sum(float(x.get("monto_bs") or 0) for x in (extra_rows or []))
            )
            cobros_extra_usd = float(
                sum(float(x.get("monto_usd") or 0) for x in (extra_rows or []))
            )

            egr_rows = (
                self.client.table("movimientos")
                .select("monto_bs, monto_usd, descripcion, conceptos(nombre)")
                .eq("condominio_id", condominio_id)
                .eq("periodo", periodo)
                .eq("tipo", "egreso")
                .execute()
            ).data
            gastos_por_concepto: dict[str, tuple[float, float]] = {}
            for x in egr_rows or []:
                c = x.get("conceptos") or {}
                nom = (c.get("nombre") or "Sin concepto").strip()
                bs = float(x.get("monto_bs") or 0)
                usd = float(x.get("monto_usd") or 0)
                prev_bs, prev_usd = gastos_por_concepto.get(nom, (0.0, 0.0))
                gastos_por_concepto[nom] = (prev_bs + bs, prev_usd + usd)
            total_gastos_bs = sum(t[0] for t in gastos_por_concepto.values())
            total_gastos_usd = sum(t[1] for t in gastos_por_concepto.values())

            total_ing_bs = total_cuotas_cobradas_bs + cobros_extra_bs
            total_ing_usd = total_cuotas_cobradas_usd + cobros_extra_usd
            superavit_bs = total_ing_bs - total_gastos_bs
            superavit_usd = total_ing_usd - total_gastos_usd

            return {
                "cuotas_cobradas_bs": total_cuotas_cobradas_bs,
                "cuotas_cobradas_usd": total_cuotas_cobradas_usd,
                "cobros_extraordinarios_bs": cobros_extra_bs,
                "cobros_extraordinarios_usd": cobros_extra_usd,
                "intereses_mora_bs": 0.0,
                "intereses_mora_usd": 0.0,
                "total_ingresos_bs": total_ing_bs,
                "total_ingresos_usd": total_ing_usd,
                "gastos_por_concepto": gastos_por_concepto,
                "total_gastos_bs": total_gastos_bs,
                "total_gastos_usd": total_gastos_usd,
                "superavit_bs": superavit_bs,
                "superavit_usd": superavit_usd,
            }
        except Exception as e:
            logger.warning("get_balance: %s", e)
            return {
                "cuotas_cobradas_bs": 0.0,
                "cuotas_cobradas_usd": 0.0,
                "cobros_extraordinarios_bs": 0.0,
                "cobros_extraordinarios_usd": 0.0,
                "intereses_mora_bs": 0.0,
                "intereses_mora_usd": 0.0,
                "total_ingresos_bs": 0.0,
                "total_ingresos_usd": 0.0,
                "gastos_por_concepto": {},
                "total_gastos_bs": 0.0,
                "total_gastos_usd": 0.0,
                "superavit_bs": 0.0,
                "superavit_usd": 0.0,
            }

    def get_libro_cobros(self, condominio_id: int, periodo: str) -> list[dict]:
        try:
            rows = (
                self.client.table("pagos")
                .select("*, unidades(codigo, numero), propietarios(nombre)")
                .eq("condominio_id", condominio_id)
                .eq("periodo", periodo)
                .order("fecha_pago", desc=False)
                .execute()
            ).data
        except Exception as e:
            logger.warning("get_libro_cobros: %s", e)
            return []
        return list(rows or [])

    def get_libro_gastos(self, condominio_id: int, periodo: str) -> list[dict]:
        try:
            rows = (
                self.client.table("movimientos")
                .select("*, conceptos(nombre)")
                .eq("condominio_id", condominio_id)
                .eq("periodo", periodo)
                .eq("tipo", "egreso")
                .order("fecha", desc=False)
                .execute()
            ).data
        except Exception as e:
            logger.warning("get_libro_gastos: %s", e)
            rows = []
        return list(rows or [])

    def subtotales_gastos_por_categoria(self, movimientos_egreso: list[dict]) -> dict[str, float]:
        buckets: dict[str, float] = {
            "Mantenimiento": 0.0,
            "Servicios": 0.0,
            "Personal": 0.0,
            "Otros": 0.0,
        }
        for m in movimientos_egreso:
            c = m.get("conceptos") or {}
            cat = map_categoria_gasto(c.get("nombre") or "")
            buckets[cat] = buckets.get(cat, 0.0) + float(m.get("monto_bs") or 0)
        return buckets

    def get_origen_aplicacion(self, condominio_id: int, periodo: str) -> dict:
        bal = self.get_balance(condominio_id, periodo)
        libro_g = self.get_libro_gastos(condominio_id, periodo)
        sub = self.subtotales_gastos_por_categoria(libro_g)

        origen_bs = bal["cuotas_cobradas_bs"] + bal["cobros_extraordinarios_bs"]
        origen_usd = bal["cuotas_cobradas_usd"] + bal["cobros_extraordinarios_usd"]
        saldo_ant_disp_bs = 0.0
        saldo_ant_disp_usd = 0.0
        total_origen_bs = origen_bs + saldo_ant_disp_bs
        total_origen_usd = origen_usd + saldo_ant_disp_usd

        aplic_bs = sum(sub.values())
        aplic_items = [(k, v) for k, v in sub.items() if v > 0]
        rem = total_origen_bs - aplic_bs
        return {
            "origen": {
                "cuotas": (bal["cuotas_cobradas_bs"], bal["cuotas_cobradas_usd"]),
                "extraordinarios": (
                    bal["cobros_extraordinarios_bs"],
                    bal["cobros_extraordinarios_usd"],
                ),
                "saldo_anterior": (saldo_ant_disp_bs, saldo_ant_disp_usd),
                "total": (total_origen_bs, total_origen_usd),
            },
            "aplicacion": aplic_items,
            "total_aplicacion_bs": aplic_bs,
            "fondos_disponibles_bs": total_origen_bs,
            "fondos_aplicados_bs": aplic_bs,
            "remanente_bs": rem,
        }

    def get_solventes(self, condominio_id: int, periodo: str) -> list[dict]:
        """Unidades al día según estado_pago (instantáneo; alineado a período vía cuota si existe)."""
        try:
            rows = (
                self.client.table("unidades")
                .select("*, propietarios(nombre, cedula)")
                .eq("condominio_id", condominio_id)
                .eq("activo", True)
                .eq("estado_pago", "al_dia")
                .execute()
            ).data
        except Exception as e:
            logger.warning("get_solventes: %s", e)
            return []
        out: list[dict] = []
        for u in rows or []:
            uid = int(u["id"])
            cuota = self.get_cuota_unidad_periodo(condominio_id, uid, periodo)
            cuota_bs = float(cuota.get("cuota_calculada_bs") or 0) if cuota else 0.0
            pag_rows = (
                self.client.table("pagos")
                .select("monto_bs")
                .eq("unidad_id", uid)
                .eq("periodo", periodo)
                .execute()
            ).data
            pagado = float(sum(float(x.get("monto_bs") or 0) for x in (pag_rows or [])))
            prop = u.get("propietarios") or {}
            out.append(
                {
                    "unidad_id": uid,
                    "codigo": u.get("codigo") or u.get("numero") or "—",
                    "propietario": prop.get("nombre", "—"),
                    "cedula": prop.get("cedula") or "—",
                    "cuota_bs": cuota_bs,
                    "pagado_bs": pagado,
                    "estado": "Al día",
                }
            )
        return out

    def registrar_reporte_generado(
        self,
        condominio_id: int,
        tipo_reporte: str,
        periodo: str,
        unidad_id: int | None = None,
        generado_por: str | None = None,
    ) -> None:
        try:
            payload = {
                "condominio_id": condominio_id,
                "tipo_reporte": tipo_reporte,
                "periodo": periodo,
                "unidad_id": unidad_id,
                "generado_por": generado_por,
            }
            self.client.table("reportes_generados").insert(payload).execute()
        except Exception as e:
            logger.debug("registrar_reporte_generado (opcional): %s", e)
