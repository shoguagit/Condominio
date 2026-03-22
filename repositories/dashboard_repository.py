"""
Métricas del dashboard principal (período en proceso, datos reales Supabase).
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from dateutil.relativedelta import relativedelta
from supabase import Client

from repositories.presupuesto_repository import fetch_presupuesto_si_existe
from utils.error_handler import safe_db_operation
from utils.validators import date_periodo_to_mm_yyyy


def _as_int_condo(condominio_id: int | str) -> int:
    return int(condominio_id)


def _norm_periodo_key(p: Any) -> str:
    if p is None:
        return ""
    s = str(p)[:10]
    return s


def _meses_deuda_consecutivos(
    por_periodo: dict[str, float],
    periodo_db: str,
    max_meses: int = 36,
) -> int:
    """Cuenta meses consecutivos con total_a_pagar_bs > 0 hasta periodo_db inclusive."""
    try:
        cur = date.fromisoformat(str(periodo_db)[:10])
    except ValueError:
        return 0
    cnt = 0
    for _ in range(max_meses):
        key = cur.isoformat()
        val = por_periodo.get(key)
        if val is None:
            break
        if float(val or 0) <= 0:
            break
        cnt += 1
        cur = cur - relativedelta(months=1)
    return cnt


class DashboardRepository:
    def __init__(self, client: Client):
        self.client = client

    @safe_db_operation("dashboard.obtener_metricas_cobranza")
    def obtener_metricas_cobranza(self, condominio_id: int | str, periodo: str) -> dict:
        cid = _as_int_condo(condominio_id)
        rows = (
            self.client.table("cuotas_unidad")
            .select("cuota_calculada_bs, cobros_extraordinarios")
            .eq("condominio_id", cid)
            .eq("periodo", periodo)
            .execute()
        ).data or []

        cuotas_esperadas_bs = sum(float(r.get("cuota_calculada_bs") or 0) for r in rows)
        cobros_extraordinarios_bs = sum(float(r.get("cobros_extraordinarios") or 0) for r in rows)
        total_esperado_bs = sum(
            float(r.get("cuota_calculada_bs") or 0) + float(r.get("cobros_extraordinarios") or 0)
            for r in rows
        )

        prow = (
            self.client.table("pagos")
            .select("monto_bs")
            .eq("condominio_id", cid)
            .eq("periodo", periodo)
            .execute()
        ).data or []
        total_cobrado_bs = sum(float(r.get("monto_bs") or 0) for r in prow)

        if total_esperado_bs > 0:
            pct_cobranza = round((total_cobrado_bs / total_esperado_bs) * 100, 2)
        else:
            pct_cobranza = 0.0

        urows = (
            self.client.table("unidades")
            .select("estado_pago")
            .eq("condominio_id", cid)
            .execute()
        ).data or []

        def _count(estado: str) -> int:
            e = estado.lower()
            return sum(1 for r in urows if str(r.get("estado_pago") or "").lower() == e)

        unidades_al_dia = _count("al_dia")
        unidades_morosas = _count("moroso")
        unidades_parcial = _count("parcial")

        return {
            "cuotas_esperadas_bs": round(cuotas_esperadas_bs, 2),
            "cobros_extraordinarios_bs": round(cobros_extraordinarios_bs, 2),
            "total_esperado_bs": round(total_esperado_bs, 2),
            "total_cobrado_bs": round(total_cobrado_bs, 2),
            "pct_cobranza": pct_cobranza,
            "unidades_al_dia": unidades_al_dia,
            "unidades_morosas": unidades_morosas,
            "unidades_parcial": unidades_parcial,
        }

    @safe_db_operation("dashboard.obtener_morosos")
    def obtener_morosos(self, condominio_id: int | str, periodo: str) -> dict:
        """
        Morosos con más de 1 mes de atraso: saldo anterior > 0 y saldo pendiente actual > 0.
        """
        cid = _as_int_condo(condominio_id)
        rows = (
            self.client.table("cuotas_unidad")
            .select(
                "unidad_id, saldo_anterior_bs, total_a_pagar_bs, cuota_calculada_bs, "
                "unidades(codigo, numero), propietarios(nombre, correo)"
            )
            .eq("condominio_id", cid)
            .eq("periodo", periodo)
            .execute()
        ).data or []

        criticos: list[dict] = []
        uids: list[int] = []
        for r in rows:
            saldo_ant = float(r.get("saldo_anterior_bs") or 0)
            total_pagar = float(r.get("total_a_pagar_bs") or 0)
            if saldo_ant > 0 and total_pagar > 0:
                uid = r.get("unidad_id")
                if uid is not None:
                    uids.append(int(uid))
                u = r.get("unidades") or {}
                codigo = (u.get("codigo") or u.get("numero") or "—")
                prop = (r.get("propietarios") or {}) if isinstance(r.get("propietarios"), dict) else {}
                criticos.append(
                    {
                        "unidad_id": int(uid) if uid is not None else None,
                        "unidad": str(codigo).strip() or "—",
                        "propietario": (prop.get("nombre") or "—") if prop else "—",
                        "email": (
                            (prop.get("correo") or prop.get("email") or "").strip()
                            if prop
                            else ""
                        ),
                        "saldo_bs": round(total_pagar, 2),
                        "meses_atraso": 0,
                    }
                )

        hist_by_unit: dict[int, dict[str, float]] = {}
        if uids:
            hist = (
                self.client.table("cuotas_unidad")
                .select("unidad_id, periodo, total_a_pagar_bs")
                .eq("condominio_id", cid)
                .in_("unidad_id", list(set(uids)))
                .lte("periodo", periodo)
                .execute()
            ).data or []
            for h in hist:
                uid = h.get("unidad_id")
                if uid is None:
                    continue
                k = int(uid)
                pk = _norm_periodo_key(h.get("periodo"))
                if not pk:
                    continue
                hist_by_unit.setdefault(k, {})[pk] = float(h.get("total_a_pagar_bs") or 0)

        monto_total = 0.0
        for item in criticos:
            uid = item.get("unidad_id")
            if uid is not None:
                streak = _meses_deuda_consecutivos(hist_by_unit.get(uid, {}), periodo)
                item["meses_atraso"] = max(streak, 2) if streak > 0 else 2
            else:
                item["meses_atraso"] = 2
            monto_total += float(item["saldo_bs"])

        return {
            "total_morosos": len(criticos),
            "monto_total_adeudado_bs": round(monto_total, 2),
            "lista": criticos,
        }

    @safe_db_operation("dashboard.obtener_flujo_mes")
    def obtener_flujo_mes(self, condominio_id: int | str, periodo: str) -> dict:
        rows = (
            self.client.table("movimientos")
            .select("monto_bs, tipo")
            .eq("condominio_id", _as_int_condo(condominio_id))
            .eq("periodo", periodo)
            .execute()
        ).data or []

        total_ingresos_bs = 0.0
        total_egresos_bs = 0.0
        for r in rows:
            m = float(r.get("monto_bs") or 0)
            t = str(r.get("tipo") or "").lower()
            if t == "ingreso":
                total_ingresos_bs += m
            elif t == "egreso":
                total_egresos_bs += m

        superavit_bs = round(total_ingresos_bs - total_egresos_bs, 2)
        return {
            "total_ingresos_bs": round(total_ingresos_bs, 2),
            "total_egresos_bs": round(total_egresos_bs, 2),
            "superavit_bs": superavit_bs,
            "es_superavit": superavit_bs >= 0,
        }

    @safe_db_operation("dashboard.obtener_saldo_banco")
    def obtener_saldo_banco(self, condominio_id: int | str, periodo: str) -> dict:
        cid = _as_int_condo(condominio_id)
        rows = (
            self.client.table("movimientos")
            .select("monto_bs, tipo, conciliado")
            .eq("condominio_id", cid)
            .eq("periodo", periodo)
            .execute()
        ).data or []

        ing = eg = 0.0
        conc = pend = 0
        for r in rows:
            m = float(r.get("monto_bs") or 0)
            t = str(r.get("tipo") or "").lower()
            if t == "ingreso":
                ing += m
            elif t == "egreso":
                eg += m
            if r.get("conciliado") is True:
                conc += 1
            else:
                pend += 1

        saldo_bs = round(ing - eg, 2)
        ym = str(periodo)[:7] if periodo else ""
        crows = (
            self.client.table("conciliaciones")
            .select("id")
            .eq("condominio_id", cid)
            .eq("periodo", ym)
            .limit(1)
            .execute()
        ).data or []
        tiene_conciliacion = len(crows) > 0

        return {
            "saldo_bs": saldo_bs,
            "movimientos_conciliados": conc,
            "movimientos_pendientes": pend,
            "tiene_conciliacion": tiene_conciliacion,
        }

    @safe_db_operation("dashboard.obtener_info_cierre")
    def obtener_info_cierre(self, condominio_id: int | str, periodo: str) -> dict:
        cid = _as_int_condo(condominio_id)
        proc_row = (
            self.client.table("procesos_mensuales")
            .select("*")
            .eq("condominio_id", cid)
            .eq("periodo", periodo)
            .limit(1)
            .execute()
        ).data
        proceso = proc_row[0] if proc_row else None

        raw_estado = (proceso.get("estado") if proceso else None) or "borrador"
        raw_estado_l = str(raw_estado).lower()
        if raw_estado_l == "procesado":
            estado_proceso = "en_proceso"
        elif raw_estado_l == "cerrado":
            estado_proceso = "cerrado"
        else:
            estado_proceso = "borrador"

        pres = fetch_presupuesto_si_existe(self.client, cid, periodo)
        presupuesto_definido = bool(pres and float(pres.get("monto_bs") or 0) > 0)

        cuotas = (
            self.client.table("cuotas_unidad")
            .select("id")
            .eq("condominio_id", cid)
            .eq("periodo", periodo)
            .limit(1)
            .execute()
        ).data or []
        cuotas_generadas = len(cuotas) > 0

        pagos_sum = (
            self.client.table("pagos")
            .select("monto_bs")
            .eq("condominio_id", cid)
            .eq("periodo", periodo)
            .execute()
        ).data or []
        hay_pagos = sum(float(r.get("monto_bs") or 0) for r in pagos_sum) > 0

        cerrado = raw_estado_l == "cerrado"
        ok1 = presupuesto_definido
        ok2 = cuotas_generadas
        ok3 = hay_pagos
        ok4 = cerrado

        if not ok1:
            pasos_completados = 0
        elif not ok2:
            pasos_completados = 1
        elif not ok3:
            pasos_completados = 2
        elif not ok4:
            pasos_completados = 3
        else:
            pasos_completados = 4

        periodo_actual = date_periodo_to_mm_yyyy(periodo)
        try:
            d0 = date.fromisoformat(str(periodo)[:10])
            d1 = d0 + relativedelta(months=1)
            proximo_periodo = f"{d1.month:02d}/{d1.year}"
        except ValueError:
            proximo_periodo = "—"

        try:
            y, m = int(str(periodo)[0:4]), int(str(periodo)[5:7])
            ultimo = calendar.monthrange(y, m)[1]
            fin = date(y, m, ultimo)
            dias_para_fin_mes = max(0, (fin - date.today()).days)
        except (ValueError, IndexError):
            dias_para_fin_mes = 0

        return {
            "periodo_actual": periodo_actual,
            "estado_proceso": estado_proceso,
            "pasos_completados": pasos_completados,
            "proximo_periodo": proximo_periodo,
            "dias_para_fin_mes": dias_para_fin_mes,
            "presupuesto_definido": presupuesto_definido,
            "cuotas_generadas": cuotas_generadas,
            "presupuesto_ok": ok1,
            "cuotas_ok": ok2,
            "pagos_ok": ok3,
            "cierre_ok": ok4,
        }
