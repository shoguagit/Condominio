from supabase import Client

from utils.error_handler import safe_db_operation


class CondominioRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "condominios"

    @safe_db_operation("condominio.get_all")
    def get_all(self, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, paises(nombre, simbolo_moneda), tipos_documento(nombre)")
            .order("nombre")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("condominio.get_by_id")
    def get_by_id(self, condominio_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*, paises(nombre, simbolo_moneda), tipos_documento(nombre)")
            .eq("id", condominio_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("condominio.create")
    def create(self, data: dict) -> dict:
        response = (
            self.client.table(self.table)
            .insert(data)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("condominio.update")
    def update(self, condominio_id: int, data: dict) -> dict:
        response = (
            self.client.table(self.table)
            .update(data)
            .eq("id", condominio_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("condominio.delete")
    def delete(self, condominio_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", condominio_id).execute()
        return True

    @safe_db_operation("condominio.search")
    def search(self, term: str) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*, paises(nombre, simbolo_moneda), tipos_documento(nombre)")
            .ilike("nombre", f"%{term}%")
            .order("nombre")
            .execute()
        )
        return response.data

    @safe_db_operation("condominio.toggle_activo")
    def toggle_activo(self, condominio_id: int, activo: bool) -> dict:
        response = (
            self.client.table(self.table)
            .update({"activo": activo})
            .eq("id", condominio_id)
            .execute()
        )
        return response.data[0]
