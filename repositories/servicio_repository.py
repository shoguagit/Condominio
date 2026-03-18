from supabase import Client

from utils.error_handler import safe_db_operation


class ServicioRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "servicios"

    @safe_db_operation("servicio.get_all")
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

    @safe_db_operation("servicio.get_by_id")
    def get_by_id(self, servicio_id: int) -> dict | None:
        return (
            self.client.table(self.table)
            .select("*").eq("id", servicio_id).single().execute()
        ).data

    @safe_db_operation("servicio.create")
    def create(self, data: dict) -> dict:
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("servicio.update")
    def update(self, servicio_id: int, data: dict) -> dict:
        return (
            self.client.table(self.table)
            .update(data).eq("id", servicio_id).execute()
        ).data[0]

    @safe_db_operation("servicio.delete")
    def delete(self, servicio_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", servicio_id).execute()
        return True
