from supabase import Client

from utils.error_handler import safe_db_operation


class FondoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "fondos"

    @safe_db_operation("fondo.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, alicuotas(descripcion)")
            .eq("condominio_id", condominio_id)
            .order("nombre")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("fondo.get_by_id")
    def get_by_id(self, fondo_id: int) -> dict | None:
        return (
            self.client.table(self.table)
            .select("*, alicuotas(descripcion)")
            .eq("id", fondo_id).single().execute()
        ).data

    @safe_db_operation("fondo.create")
    def create(self, data: dict) -> dict:
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("fondo.update")
    def update(self, fondo_id: int, data: dict) -> dict:
        return (
            self.client.table(self.table)
            .update(data).eq("id", fondo_id).execute()
        ).data[0]

    @safe_db_operation("fondo.delete")
    def delete(self, fondo_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", fondo_id).execute()
        return True

    @safe_db_operation("fondo.actualizar_saldo")
    def actualizar_saldo(self, fondo_id: int, nuevo_saldo: float) -> dict:
        return (
            self.client.table(self.table)
            .update({"saldo": nuevo_saldo})
            .eq("id", fondo_id).execute()
        ).data[0]
