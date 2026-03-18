from supabase import Client

from utils.error_handler import safe_db_operation


class FacturaRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "facturas_proveedor"

    @safe_db_operation("factura.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, proveedores(id, nombre)")
            .eq("condominio_id", condominio_id)
            .order("fecha", desc=True)
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("factura.get_by_mes_proceso")
    def get_by_mes_proceso(self, condominio_id: int, mes_proceso: str) -> list[dict]:
        """Retorna facturas del mes en proceso (formato 'YYYY-MM-01')."""
        response = (
            self.client.table(self.table)
            .select("*, proveedores(id, nombre)")
            .eq("condominio_id", condominio_id)
            .eq("mes_proceso", mes_proceso)
            .eq("activo", True)
            .order("fecha", desc=True)
            .execute()
        )
        return response.data

    @safe_db_operation("factura.get_by_proveedor")
    def get_by_proveedor(self, proveedor_id: int) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq("proveedor_id", proveedor_id)
            .eq("activo", True)
            .order("fecha", desc=True)
            .execute()
        )
        return response.data

    @safe_db_operation("factura.get_by_id")
    def get_by_id(self, factura_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*, proveedores(id, nombre)")
            .eq("id", factura_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("factura.create")
    def create(self, data: dict) -> dict:
        response = self.client.table(self.table).insert(data).execute()
        return response.data[0]

    @safe_db_operation("factura.update")
    def update(self, factura_id: int, data: dict) -> dict:
        response = (
            self.client.table(self.table)
            .update(data)
            .eq("id", factura_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("factura.delete")
    def delete(self, factura_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", factura_id).execute()
        return True

    @safe_db_operation("factura.registrar_pago")
    def registrar_pago(self, factura_id: int, monto_pago: float) -> dict:
        """Suma monto_pago al campo pagado; el saldo se recalcula en BD (columna generada)."""
        factura = self.get_by_id(factura_id)
        nuevo_pagado = float(factura.get("pagado") or 0) + monto_pago
        response = (
            self.client.table(self.table)
            .update({"pagado": nuevo_pagado})
            .eq("id", factura_id)
            .execute()
        )
        return response.data[0]
