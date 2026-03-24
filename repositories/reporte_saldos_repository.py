"""
Datos para el reporte PDF de saldos iniciales acumulados (Fase 6).
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from utils.error_handler import safe_db_operation
from utils.pdf_generator import monto_bs_a_usd, rif_condominio_texto


def _propietario_nombre_fila(row: dict) -> str:
    p = row.get("propietarios")
    if isinstance(p, dict) and (p.get("nombre") or "").strip():
        return str(p["nombre"]).strip()
    return "—"


def _codigo_unidad(row: dict) -> str:
    return (row.get("codigo") or row.get("numero") or "").strip() or str(row.get("id", ""))


class ReporteSaldosRepository:
    def __init__(self, client: Client):
        self.client = client
        self._tab_u = "unidades"
        self._tab_c = "condominios"

    def _fetch_unidades_saldo_raw(self, condominio_id: int) -> list[dict]:
        return (
            self.client.table(self._tab_u)
            .select(
                "id, codigo, numero, indiviso_pct, saldo_inicial_bs, saldo, "
                "requiere_revision, nota_revision, propietarios(nombre)"
            )
            .eq("condominio_id", int(condominio_id))
            .eq("activo", True)
            .gt("saldo_inicial_bs", 0)
            .execute()
        ).data or []

    @safe_db_operation("reporte_saldos.obtener_config_condominio")
    def obtener_config_condominio(self, condominio_id: int) -> dict[str, Any]:
        rows = (
            self.client.table(self._tab_c)
            .select("id, nombre, numero_documento, logo_url, tipos_documento(nombre)")
            .eq("id", int(condominio_id))
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            return {
                "nombre": "—",
                "numero_documento": "",
                "logo_url": None,
                "rif": "—",
            }
        r = rows[0]
        return {
            "nombre": (r.get("nombre") or "").strip() or "—",
            "numero_documento": (r.get("numero_documento") or "").strip(),
            "logo_url": r.get("logo_url"),
            "rif": rif_condominio_texto(r),
        }

    @safe_db_operation("reporte_saldos.obtener_unidades_con_saldo")
    def obtener_unidades_con_saldo(
        self, condominio_id: int, tasa_cambio: float
    ) -> list[dict[str, Any]]:
        tasa = float(tasa_cambio or 0)
        rows = self._fetch_unidades_saldo_raw(condominio_id)

        out: list[dict[str, Any]] = []
        for r in rows:
            s_ini = float(r.get("saldo_inicial_bs") or 0)
            saldo_usd = monto_bs_a_usd(s_ini, tasa) if tasa > 0 else 0.0
            cod = _codigo_unidad(r)
            out.append(
                {
                    "id": int(r["id"]),
                    "numero_unidad": cod,
                    "propietario_nombre": _propietario_nombre_fila(r),
                    "indiviso_pct": float(r.get("indiviso_pct") or 0),
                    "saldo_inicial_bs": s_ini,
                    "saldo": float(r.get("saldo") or 0),
                    "requiere_revision": bool(r.get("requiere_revision")),
                    "nota_revision": r.get("nota_revision"),
                    "meses_sin_pagar": 0,
                    "primer_periodo": None,
                    "saldo_usd": saldo_usd,
                }
            )

        import re

        def _nk(s: str) -> list:
            s = s or ""
            return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", s)]

        out.sort(key=lambda x: _nk(str(x.get("numero_unidad") or "")))
        return out

    @safe_db_operation("reporte_saldos.obtener_resumen_saldos_reporte")
    def obtener_resumen_saldos_reporte(
        self, condominio_id: int, tasa_cambio: float
    ) -> dict[str, Any]:
        tasa = float(tasa_cambio or 0)
        rows = self._fetch_unidades_saldo_raw(condominio_id)
        total_u = len(rows)
        req = sum(1 for r in rows if r.get("requiere_revision"))
        suma_bs = sum(float(r.get("saldo_inicial_bs") or 0) for r in rows)
        suma_usd = monto_bs_a_usd(suma_bs, tasa) if tasa > 0 else 0.0
        return {
            "total_unidades": total_u,
            "requieren_revision": req,
            "suma_total_bs": round(suma_bs, 2),
            "suma_total_usd": round(float(suma_usd), 2),
        }
