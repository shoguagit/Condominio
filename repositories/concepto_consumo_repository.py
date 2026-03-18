from supabase import Client

from utils.error_handler import safe_db_operation


class ConceptoConsumoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "conceptos_consumo"

    @safe_db_operation("concepto_consumo.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*")
            .eq("condominio_id", condominio_id)
            .order("nombre")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("concepto_consumo.get_by_id")
    def get_by_id(self, concepto_id: int) -> dict | None:
        return (
            self.client.table(self.table)
            .select("*").eq("id", concepto_id).single().execute()
        ).data

    @safe_db_operation("concepto_consumo.create")
    def create(self, data: dict) -> dict:
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("concepto_consumo.update")
    def update(self, concepto_id: int, data: dict) -> dict:
        return (
            self.client.table(self.table)
            .update(data).eq("id", concepto_id).execute()
        ).data[0]

    @safe_db_operation("concepto_consumo.delete")
    def delete(self, concepto_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", concepto_id).execute()
        return True
