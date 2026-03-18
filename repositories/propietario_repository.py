from supabase import Client

from utils.error_handler import safe_db_operation


class PropietarioRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "propietarios"

    @safe_db_operation("propietario.get_all")
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

    @safe_db_operation("propietario.get_by_id")
    def get_by_id(self, propietario_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq("id", propietario_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("propietario.create")
    def create(self, data: dict) -> dict:
        response = self.client.table(self.table).insert(data).execute()
        return response.data[0]

    @safe_db_operation("propietario.update")
    def update(self, propietario_id: int, data: dict) -> dict:
        response = (
            self.client.table(self.table)
            .update(data)
            .eq("id", propietario_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("propietario.delete")
    def delete(self, propietario_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", propietario_id).execute()
        return True

    @safe_db_operation("propietario.search")
    def search(self, condominio_id: int, term: str) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq("condominio_id", condominio_id)
            .ilike("nombre", f"%{term}%")
            .order("nombre")
            .execute()
        )
        return response.data

    @safe_db_operation("propietario.toggle_activo")
    def toggle_activo(self, propietario_id: int, activo: bool) -> dict:
        response = (
            self.client.table(self.table)
            .update({"activo": activo})
            .eq("id", propietario_id)
            .execute()
        )
        return response.data[0]
