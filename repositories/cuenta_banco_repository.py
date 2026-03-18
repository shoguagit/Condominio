from supabase import Client

from utils.error_handler import safe_db_operation


class CuentaBancoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "cuentas_bancos"

    @safe_db_operation("cuenta_banco.get_all")
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

    @safe_db_operation("cuenta_banco.get_by_id")
    def get_by_id(self, cuenta_id: int) -> dict | None:
        return (
            self.client.table(self.table)
            .select("*").eq("id", cuenta_id).single().execute()
        ).data

    @safe_db_operation("cuenta_banco.create")
    def create(self, data: dict) -> dict:
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("cuenta_banco.update")
    def update(self, cuenta_id: int, data: dict) -> dict:
        return (
            self.client.table(self.table)
            .update(data).eq("id", cuenta_id).execute()
        ).data[0]

    @safe_db_operation("cuenta_banco.delete")
    def delete(self, cuenta_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", cuenta_id).execute()
        return True

    @safe_db_operation("cuenta_banco.actualizar_saldo")
    def actualizar_saldo(self, cuenta_id: int, nuevo_saldo: float) -> dict:
        return (
            self.client.table(self.table)
            .update({"saldo": nuevo_saldo})
            .eq("id", cuenta_id).execute()
        ).data[0]

    @safe_db_operation("cuenta_banco.saldo_total")
    def saldo_total(self, condominio_id: int) -> dict[str, float]:
        """Retorna saldo total agrupado por moneda."""
        records = self.get_all(condominio_id, solo_activos=True)
        totales: dict[str, float] = {}
        for r in records:
            moneda = r.get("moneda", "USD") or "USD"
            totales[moneda] = totales.get(moneda, 0.0) + float(r.get("saldo") or 0)
        return totales
