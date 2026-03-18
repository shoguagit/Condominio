from supabase import Client

from utils.error_handler import safe_db_operation


class ProveedorRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "proveedores"

    @safe_db_operation("proveedor.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, tipos_documento(nombre)")
            .eq("condominio_id", condominio_id)
            .order("nombre")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("proveedor.get_by_id")
    def get_by_id(self, proveedor_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*, tipos_documento(nombre)")
            .eq("id", proveedor_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("proveedor.create")
    def create(self, data: dict) -> dict:
        response = self.client.table(self.table).insert(data).execute()
        return response.data[0]

    @safe_db_operation("proveedor.update")
    def update(self, proveedor_id: int, data: dict) -> dict:
        response = (
            self.client.table(self.table)
            .update(data)
            .eq("id", proveedor_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("proveedor.delete")
    def delete(self, proveedor_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", proveedor_id).execute()
        return True

    @safe_db_operation("proveedor.search")
    def search(self, condominio_id: int, term: str) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*, tipos_documento(nombre)")
            .eq("condominio_id", condominio_id)
            .ilike("nombre", f"%{term}%")
            .order("nombre")
            .execute()
        )
        return response.data

    @safe_db_operation("proveedor.toggle_activo")
    def toggle_activo(self, proveedor_id: int, activo: bool) -> dict:
        response = (
            self.client.table(self.table)
            .update({"activo": activo})
            .eq("id", proveedor_id)
            .execute()
        )
        return response.data[0]
