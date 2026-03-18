from supabase import Client

from utils.error_handler import safe_db_operation


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
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("concepto.update")
    def update(self, concepto_id: int, data: dict) -> dict:
        return (
            self.client.table(self.table)
            .update(data).eq("id", concepto_id).execute()
        ).data[0]

    @safe_db_operation("concepto.delete")
    def delete(self, concepto_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", concepto_id).execute()
        return True
