from supabase import Client

from utils.error_handler import safe_db_operation


class GastoFijoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "gastos_fijos"

    @safe_db_operation("gasto_fijo.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, alicuotas(descripcion)")
            .eq("condominio_id", condominio_id)
            .order("descripcion")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("gasto_fijo.get_by_id")
    def get_by_id(self, gasto_id: int) -> dict | None:
        return (
            self.client.table(self.table)
            .select("*, alicuotas(descripcion)")
            .eq("id", gasto_id).single().execute()
        ).data

    @safe_db_operation("gasto_fijo.create")
    def create(self, data: dict) -> dict:
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("gasto_fijo.update")
    def update(self, gasto_id: int, data: dict) -> dict:
        return (
            self.client.table(self.table)
            .update(data).eq("id", gasto_id).execute()
        ).data[0]

    @safe_db_operation("gasto_fijo.delete")
    def delete(self, gasto_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", gasto_id).execute()
        return True

    @safe_db_operation("gasto_fijo.total_por_condominio")
    def total_mensual(self, condominio_id: int) -> float:
        """Suma de todos los gastos fijos activos del condominio."""
        records = self.get_all(condominio_id, solo_activos=True)
        return sum(float(r.get("monto") or 0) for r in records)
