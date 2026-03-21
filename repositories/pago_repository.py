from supabase import Client

from utils.error_handler import safe_db_operation, DatabaseError


class PagoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "pagos"

    @safe_db_operation("pago.create")
    def create(self, data: dict) -> dict:
        metodo = (data.get("metodo") or "").lower()
        if metodo == "transferencia":
            ref = (data.get("referencia") or "").strip()
            if not ref:
                raise DatabaseError(
                    "El número de referencia es obligatorio para transferencias."
                )
        response = self.client.table(self.table).insert(data).execute()
        return response.data[0]

    @safe_db_operation("pago.get_by_periodo")
    def get_by_periodo(self, condominio_id: int, periodo: str) -> list[dict]:
        return (
            self.client.table(self.table)
            .select("*, unidades(codigo, numero), propietarios(nombre)")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .order("fecha_pago", desc=True)
            .execute()
        ).data

    @safe_db_operation("pago.get_by_unidad")
    def get_by_unidad(self, unidad_id: int, periodo: str) -> list[dict]:
        return (
            self.client.table(self.table)
            .select("*")
            .eq("unidad_id", unidad_id)
            .eq("periodo", periodo)
            .order("fecha_pago", desc=True)
            .execute()
        ).data

    @safe_db_operation("pago.get_total_pagado_unidad")
    def get_total_pagado_unidad(self, unidad_id: int, periodo: str) -> float:
        rows = (
            self.client.table(self.table)
            .select("monto_bs")
            .eq("unidad_id", unidad_id)
            .eq("periodo", periodo)
            .execute()
        ).data
        return float(sum(float(r.get("monto_bs") or 0) for r in rows))

    @safe_db_operation("pago.get_indicadores_mes")
    def get_indicadores_mes(
        self,
        condominio_id: int,
        periodo: str,
        presupuesto_mes: float,
        suma_indiviso_pct: float,
    ) -> dict:
        """
        Total cobrado, N pagos, unidades al día (estado_pago), pendiente por cobrar.
        Pendiente = max(0, esperado_mes - cobrado_mes) con esperado ≈ presupuesto * suma_indiviso/100.
        """
        rows = (
            self.client.table(self.table)
            .select("monto_bs,unidad_id")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .execute()
        ).data
        total_cobrado = float(sum(float(r.get("monto_bs") or 0) for r in rows))
        n_pagos = len(rows)

        unidades_rows = (
            self.client.table("unidades")
            .select("id,estado_pago")
            .eq("condominio_id", condominio_id)
            .eq("activo", True)
            .execute()
        ).data
        al_dia = sum(1 for u in unidades_rows if (u.get("estado_pago") or "") == "al_dia")

        esperado = float(presupuesto_mes) * (float(suma_indiviso_pct) / 100.0)
        pendiente = max(0.0, round(esperado - total_cobrado, 2))

        return {
            "total_cobrado_bs": round(total_cobrado, 2),
            "n_pagos": n_pagos,
            "unidades_al_dia": al_dia,
            "pendiente_cobrar_bs": pendiente,
        }
