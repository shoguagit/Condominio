"""Configuración y cálculo de mora por condominio (Fase 4-A)."""

from __future__ import annotations

from datetime import date

from supabase import Client

from repositories.condominio_repository import CondominioRepository, obtener_dia_limite_safe
from utils.error_handler import safe_db_operation


class MoraRepository:
    """Acceso a config_mora y reglas de mora (columna BD: activo → dict['activa'])."""

    def __init__(self, client: Client):
        self.client = client
        self._condo_repo = CondominioRepository(client)

    @staticmethod
    def _row_to_config(row: dict) -> dict:
        return {
            "id": row.get("id"),
            "condominio_id": row.get("condominio_id"),
            "pct_mora": float(row.get("pct_mora") or 0),
            "activa": bool(row.get("activo", False)),
            "dias_gracia": row.get("dias_gracia"),
            "updated_at": row.get("updated_at"),
        }

    @safe_db_operation("mora.obtener_config")
    def obtener_config(self, condominio_id: int) -> dict:
        """
        Retorna config_mora del condominio.
        Si no existe fila, inserta pct_mora=0 y activo=False y la devuelve.
        """
        resp = (
            self.client.table("config_mora")
            .select("*")
            .eq("condominio_id", condominio_id)
            .execute()
        )
        if resp.data:
            return self._row_to_config(resp.data[0])
        ins = (
            self.client.table("config_mora")
            .insert(
                {
                    "condominio_id": condominio_id,
                    "pct_mora": 0.0,
                    "activo": False,
                }
            )
            .execute()
        )
        return self._row_to_config(ins.data[0])

    @safe_db_operation("mora.actualizar_config")
    def actualizar_config(self, condominio_id: int, pct_mora: float, activa: bool) -> dict:
        """Upsert de configuración de mora. pct_mora en [0, 100]."""
        pct = float(pct_mora)
        if not (0 <= pct <= 100):
            raise ValueError("pct_mora debe estar entre 0 y 100.")
        payload = {
            "condominio_id": condominio_id,
            "pct_mora": pct,
            "activo": bool(activa),
        }
        ex = (
            self.client.table("config_mora")
            .select("id")
            .eq("condominio_id", condominio_id)
            .execute()
        )
        if ex.data:
            row = (
                self.client.table("config_mora")
                .update(payload)
                .eq("condominio_id", condominio_id)
                .execute()
            ).data[0]
        else:
            row = self.client.table("config_mora").insert(payload).execute().data[0]
        return self._row_to_config(row)

    @staticmethod
    def calcular_mora_unidad(saldo_anterior: float, cuota_mes: float, pct_mora: float) -> float:
        """
        Cálculo puro de mora. Si saldo_anterior <= 0 → 0 siempre.
        Si saldo_anterior > 0: base = saldo_anterior + cuota_mes; mora = base * (pct/100).
        """
        if float(saldo_anterior) <= 0:
            return 0.0
        base_mora = float(saldo_anterior) + float(cuota_mes)
        return round(base_mora * (float(pct_mora) / 100.0), 2)

    @safe_db_operation("mora.mora_aplica_hoy")
    def mora_aplica_hoy(self, condominio_id: int, anio: int, mes: int) -> bool:
        """
        True si hoy es estrictamente posterior al día límite del período (año/mes).
        """
        dia_limite = obtener_dia_limite_safe(self._condo_repo, condominio_id)
        fecha_limite = date(int(anio), int(mes), int(dia_limite))
        return date.today() > fecha_limite
