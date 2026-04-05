"""Caché en BD de tasas BCV oficiales por fecha."""

from __future__ import annotations

import logging
from datetime import date

from supabase import Client

from utils.dolar_oficial_ve import cargar_historico_bcv_oficial
from utils.error_handler import DatabaseError, safe_db_operation
from utils.supabase_compat import json_safe_date

logger = logging.getLogger(__name__)

TABLE = "tasas_bcv_dia"
UPSERT_CHUNK = 250


class TasaBcvRepository:
    def __init__(self, client: Client):
        self.client = client

    @safe_db_operation("tasa_bcv.get_last_on_or_before")
    def get_last_on_or_before(self, fecha: date) -> tuple[date, float] | None:
        fp = json_safe_date(fecha)
        if len(fp) < 10:
            return None
        rows = (
            self.client.table(TABLE)
            .select("fecha, tasa_bs_por_usd")
            .lte("fecha", fp)
            .order("fecha", desc=True)
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            return None
        r = rows[0]
        d = date.fromisoformat(str(r["fecha"])[:10])
        return d, float(r["tasa_bs_por_usd"])

    @safe_db_operation("tasa_bcv.get_earliest")
    def get_earliest(self) -> tuple[date, float] | None:
        rows = (
            self.client.table(TABLE)
            .select("fecha, tasa_bs_por_usd")
            .order("fecha", desc=False)
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            return None
        r = rows[0]
        d = date.fromisoformat(str(r["fecha"])[:10])
        return d, float(r["tasa_bs_por_usd"])

    def upsert_series(self, series: list[tuple[date, float]]) -> int:
        """Inserta/actualiza filas; no usa decorador para no envolver errores de chunk."""
        if not series:
            return 0
        n = 0
        for i in range(0, len(series), UPSERT_CHUNK):
            chunk = series[i : i + UPSERT_CHUNK]
            payload = [
                {
                    "fecha": d.isoformat(),
                    "tasa_bs_por_usd": float(rate),
                    "fuente": "oficial",
                }
                for d, rate in chunk
            ]
            try:
                self.client.table(TABLE).upsert(payload, on_conflict="fecha").execute()
                n += len(payload)
            except Exception as e:
                logger.error("tasa_bcv.upsert_series chunk falló: %s", e)
                raise DatabaseError(f"No se pudo guardar tasas BCV en caché: {e}") from e
        return n

    def merge_from_api(self) -> int:
        """Descarga histórico oficial y lo vuelca en tasas_bcv_dia."""
        serie = cargar_historico_bcv_oficial()
        if not serie:
            return 0
        return self.upsert_series(serie)

    def list_sorted_pairs(self) -> list[tuple[date, float]]:
        """Todas las filas ordenadas por fecha (paginado)."""
        out: list[tuple[date, float]] = []
        start = 0
        page = 1000
        while True:
            rows = (
                self.client.table(TABLE)
                .select("fecha, tasa_bs_por_usd")
                .order("fecha", desc=False)
                .range(start, start + page - 1)
                .execute()
            ).data or []
            if not rows:
                break
            for r in rows:
                out.append(
                    (
                        date.fromisoformat(str(r["fecha"])[:10]),
                        float(r["tasa_bs_por_usd"]),
                    )
                )
            if len(rows) < page:
                break
            start += page
        return out
