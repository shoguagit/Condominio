from supabase import Client

from utils.error_handler import safe_db_operation


class MovimientoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "movimientos"

    @safe_db_operation("movimiento.get_all")
    def get_all(self, condominio_id: int, periodo: str | None = None) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, conceptos(nombre), unidades(codigo, numero), propietarios(nombre)")
            .eq("condominio_id", condominio_id)
            .order("fecha", desc=True)
        )
        if periodo:
            query = query.eq("periodo", periodo)
        return query.execute().data

    @safe_db_operation("movimiento.get_by_tipo")
    def get_by_tipo(
        self,
        condominio_id: int,
        periodo: str,
        tipo: str,
        estado: str | None = None,
    ) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, conceptos(nombre), unidades(id, codigo, numero), propietarios(id, nombre)")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .eq("tipo", tipo)
            .order("fecha", desc=True)
        )
        if estado:
            query = query.eq("estado", estado)
        return query.execute().data

    @safe_db_operation("movimiento.sum_egresos_periodo")
    def sum_egresos_periodo(self, condominio_id: int, periodo: str) -> float:
        rows = (
            self.client.table(self.table)
            .select("monto_bs")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .eq("tipo", "egreso")
            .execute()
        ).data
        return float(sum(float(r.get("monto_bs") or 0) for r in (rows or [])))

    @safe_db_operation("movimiento.sum_ingresos_por_unidad")
    def sum_ingresos_por_unidad(self, condominio_id: int, periodo: str) -> dict[int, float]:
        rows = (
            self.client.table(self.table)
            .select("unidad_id, monto_bs")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .eq("tipo", "ingreso")
            .execute()
        ).data
        out: dict[int, float] = {}
        for r in rows:
            uid = r.get("unidad_id")
            if not uid:
                continue
            out[int(uid)] = out.get(int(uid), 0.0) + float(r.get("monto_bs") or 0)
        return out

    @safe_db_operation("movimiento.mark_periodo_procesado")
    def mark_periodo_procesado(self, condominio_id: int, periodo: str) -> int:
        resp = (
            self.client.table(self.table)
            .update({"estado": "procesado"})
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .execute()
        )
        return len(resp.data or [])

    @safe_db_operation("movimiento.create")
    def create(self, data: dict) -> dict:
        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("movimiento.update")
    def update(self, id: int, data: dict) -> dict:
        return (
            self.client.table(self.table)
            .update(data)
            .eq("id", id)
            .execute()
        ).data[0]

    @safe_db_operation("movimiento.delete")
    def delete(self, id: int) -> bool:
        self.client.table(self.table).delete().eq("id", id).execute()
        return True

    @safe_db_operation("movimiento.delete_egresos_periodo")
    def delete_egresos_periodo(self, condominio_id: int, periodo: str) -> int:
        """Elimina todos los egresos de un período. Devuelve cantidad eliminada."""
        resp = (
            self.client.table(self.table)
            .delete()
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .eq("tipo", "egreso")
            .execute()
        )
        return len(resp.data or [])

