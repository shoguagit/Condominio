from supabase import Client

from utils.error_handler import safe_db_operation


class PaisRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "paises"

    @safe_db_operation("pais.get_all")
    def get_all(self) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*")
            .order("nombre")
            .execute()
        )
        return response.data

    @safe_db_operation("pais.get_by_id")
    def get_by_id(self, pais_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq("id", pais_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("tipos_documento.get_by_pais")
    def get_tipos_documento_by_pais(self, pais_id: int) -> list[dict]:
        response = (
            self.client.table("tipos_documento")
            .select("*")
            .eq("pais_id", pais_id)
            .order("nombre")
            .execute()
        )
        return response.data

    @safe_db_operation("tipos_documento.get_all")
    def get_all_tipos_documento(self) -> list[dict]:
        response = (
            self.client.table("tipos_documento")
            .select("*, paises(nombre)")
            .order("nombre")
            .execute()
        )
        return response.data
