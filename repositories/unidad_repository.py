from supabase import Client

from utils.error_handler import safe_db_operation, DatabaseError


class UnidadRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "unidades"

    @safe_db_operation("unidad.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, propietarios(id, nombre, cedula, correo)")
            .eq("condominio_id", condominio_id)
            .order("numero")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("unidad.get_by_id")
    def get_by_id(self, unidad_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*, propietarios(id, nombre, cedula, correo)")
            .eq("id", unidad_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("unidad.get_by_propietario")
    def get_by_propietario(self, propietario_id: int) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq("propietario_id", propietario_id)
            .eq("activo", True)
            .execute()
        )
        return response.data

    @safe_db_operation("unidad.create")
    def create(self, data: dict) -> dict:
        codigo = (data.get("codigo") or "").strip()
        if not codigo:
            raise DatabaseError("El código de la unidad es obligatorio.")
        if data.get("saldo") is None:
            data["saldo"] = 0.00
        # propietario_id y alicuota_id son opcionales (se asignan después)
        response = self.client.table(self.table).insert(data).execute()
        return response.data[0]

    @safe_db_operation("unidad.update")
    def update(self, unidad_id: int, data: dict) -> dict:
        codigo = (data.get("codigo") or "").strip()
        if not codigo:
            raise DatabaseError("El código de la unidad es obligatorio.")
        if data.get("saldo") is None:
            data["saldo"] = 0.00
        # propietario_id y alicuota_id pueden ser null (sin asignar)
        payload = dict(data)
        response = (
            self.client.table(self.table)
            .update(payload)
            .eq("id", unidad_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("unidad.delete")
    def delete(self, unidad_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", unidad_id).execute()
        return True

    @safe_db_operation("unidad.search")
    def search(self, condominio_id: int, term: str) -> list[dict]:
        """Busca por número de unidad."""
        response = (
            self.client.table(self.table)
            .select("*, propietarios(id, nombre)")
            .eq("condominio_id", condominio_id)
            .ilike("numero", f"%{term}%")
            .order("numero")
            .execute()
        )
        return response.data

    @safe_db_operation("unidad.toggle_activo")
    def toggle_activo(self, unidad_id: int, activo: bool) -> dict:
        response = (
            self.client.table(self.table)
            .update({"activo": activo})
            .eq("id", unidad_id)
            .execute()
        )
        return response.data[0]
