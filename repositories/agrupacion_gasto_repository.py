"""Repositorio para agrupaciones_gasto (una fila por condominio+periodo)."""

from __future__ import annotations

import json
from typing import Any

from supabase import Client

from utils.error_handler import safe_db_operation

TABLE = "agrupaciones_gasto"


class AgrupacionGastoRepository:
    def __init__(self, client: Client) -> None:
        self.client = client

    @safe_db_operation("agrupacion.get")
    def get(self, condominio_id: int, periodo: str) -> list[dict] | None:
        """Devuelve la lista de grupos guardados o None si no existe registro."""
        resp = (
            self.client.table(TABLE)
            .select("grupos")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .execute()
        )
        if resp.data:
            raw = resp.data[0]["grupos"]
            # Supabase puede devolver str o list
            if isinstance(raw, str):
                return json.loads(raw)
            return raw or []
        return None

    @safe_db_operation("agrupacion.upsert")
    def upsert(
        self, condominio_id: int, periodo: str, grupos: list[dict[str, Any]]
    ) -> None:
        """Inserta o actualiza la agrupación del período."""
        self.client.table(TABLE).upsert(
            {
                "condominio_id": condominio_id,
                "periodo": periodo,
                "grupos": json.dumps(grupos, ensure_ascii=False),
                "updated_at": "now()",
            },
            on_conflict="condominio_id,periodo",
        ).execute()
