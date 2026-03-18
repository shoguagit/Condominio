from supabase import Client

from utils.error_handler import safe_db_operation, DatabaseError


class ConceptoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "conceptos"

    @safe_db_operation("concepto.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False,
                tipo: str | None = None) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*")
            .eq("condominio_id", condominio_id)
            .order("nombre")
        )
        if solo_activos:
            query = query.eq("activo", True)
        if tipo:
            query = query.eq("tipo", tipo)
        return query.execute().data

    @safe_db_operation("concepto.get_by_id")
    def get_by_id(self, concepto_id: int) -> dict | None:
        return (
            self.client.table(self.table)
            .select("*").eq("id", concepto_id).single().execute()
        ).data

    @safe_db_operation("concepto.create")
    def create(self, data: dict) -> dict:
        tipo = (data.get("tipo") or "").strip()
        if tipo not in {"gasto", "ajuste"}:
            raise DatabaseError("Tipo de concepto inválido. Use 'Gasto' o 'Ajuste'.")
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("concepto.update")
    def update(self, concepto_id: int, data: dict) -> dict:
        if "tipo" in data:
            tipo = (data.get("tipo") or "").strip()
            if tipo not in {"gasto", "ajuste"}:
                raise DatabaseError("Tipo de concepto inválido. Use 'Gasto' o 'Ajuste'.")
        return (
            self.client.table(self.table)
            .update(data).eq("id", concepto_id).execute()
        ).data[0]

    @safe_db_operation("concepto.delete")
    def delete(self, concepto_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", concepto_id).execute()
        return True

    def can_delete(self, id: int, condominio_id: int) -> bool:
        """
        No se permite eliminar si el concepto ya fue usado en movimientos
        del condominio en el período activo (condominios.mes_proceso).
        """
        condo = (
            self.client.table("condominios")
            .select("mes_proceso")
            .eq("id", condominio_id)
            .single()
            .execute()
        ).data or {}

        periodo_activo = condo.get("mes_proceso")
        if not periodo_activo:
            # Si no hay mes_proceso configurado, permitir borrar (no hay "período activo" definido)
            return True

        result = (
            self.client.table("movimientos")
            .select("id")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo_activo)
            .eq("concepto_id", id)
            .execute()
        )
        return len(result.data or []) == 0
