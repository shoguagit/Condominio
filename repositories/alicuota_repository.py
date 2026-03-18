from supabase import Client

from utils.error_handler import safe_db_operation


class AlicuotaRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "alicuotas"

    @safe_db_operation("alicuota.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*")
            .eq("condominio_id", condominio_id)
            .order("descripcion")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("alicuota.get_by_id")
    def get_by_id(self, alicuota_id: int) -> dict | None:
        return (
            self.client.table(self.table)
            .select("*").eq("id", alicuota_id).single().execute()
        ).data

    @safe_db_operation("alicuota.create")
    def create(self, data: dict) -> dict:
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("alicuota.update")
    def update(self, alicuota_id: int, data: dict) -> dict:
        return (
            self.client.table(self.table)
            .update(data).eq("id", alicuota_id).execute()
        ).data[0]

    @safe_db_operation("alicuota.delete")
    def delete(self, alicuota_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", alicuota_id).execute()
        return True

    @safe_db_operation("alicuota.recalcular")
    def recalcular_desde_unidades(self, alicuota_id: int, total_unidades: int) -> dict:
        """Actualiza cantidad_unidades y recalcula total_alicuota (1 / total_unidades)."""
        total = round(1 / total_unidades, 6) if total_unidades > 0 else 0
        return (
            self.client.table(self.table)
            .update({"cantidad_unidades": total_unidades, "total_alicuota": total})
            .eq("id", alicuota_id).execute()
        ).data[0]
