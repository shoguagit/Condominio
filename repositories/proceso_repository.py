from supabase import Client

from utils.error_handler import safe_db_operation


class ProcesoMensualRepository:
    def __init__(self, client: Client):
        self.client = client

    @safe_db_operation("proceso.get_or_create")
    def get_or_create(self, condominio_id: int, periodo: str) -> dict:
        resp = (
            self.client.table("procesos_mensuales")
            .select("*")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        ins = (
            self.client.table("procesos_mensuales")
            .insert({"condominio_id": condominio_id, "periodo": periodo})
            .execute()
        )
        return ins.data[0]

    @safe_db_operation("proceso.update")
    def update(self, proceso_id: int, data: dict) -> dict:
        return (
            self.client.table("procesos_mensuales")
            .update(data)
            .eq("id", proceso_id)
            .execute()
        ).data[0]

    @safe_db_operation("proceso.get_cuotas")
    def get_cuotas(self, condominio_id: int, periodo: str) -> list[dict]:
        return (
            self.client.table("cuotas_unidad")
            .select("*, unidades(codigo, numero), propietarios(nombre)")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .order("id", desc=False)
            .execute()
        ).data

    @safe_db_operation("proceso.upsert_cuota")
    def upsert_cuota(self, data: dict) -> dict:
        proceso_id = data.get("proceso_id")
        unidad_id = data.get("unidad_id")
        if not proceso_id or not unidad_id:
            raise ValueError("proceso_id y unidad_id son obligatorios para upsert_cuota")

        existing = (
            self.client.table("cuotas_unidad")
            .select("id")
            .eq("proceso_id", proceso_id)
            .eq("unidad_id", unidad_id)
            .execute()
        ).data

        if existing:
            cuota_id = existing[0]["id"]
            return (
                self.client.table("cuotas_unidad")
                .update(data)
                .eq("id", cuota_id)
                .execute()
            ).data[0]

        return self.client.table("cuotas_unidad").insert(data).execute().data[0]

    @safe_db_operation("proceso.set_estado")
    def set_estado(self, proceso_id: int, estado: str) -> dict:
        return (
            self.client.table("procesos_mensuales")
            .update({"estado": estado})
            .eq("id", proceso_id)
            .execute()
        ).data[0]

