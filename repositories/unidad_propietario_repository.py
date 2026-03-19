from supabase import Client

from utils.error_handler import safe_db_operation


class UnidadPropietarioRepository:
    """Relación unidad – propietarios (1 unidad : N propietarios, activos/inactivos, es_principal)."""
    TABLE = "unidad_propietarios"

    def __init__(self, client: Client):
        self.client = client

    @safe_db_operation("unidad_propietario.get_by_unidad")
    def get_by_unidad(self, unidad_id: int) -> list[dict]:
        response = (
            self.client.table(self.TABLE)
            .select("*, propietarios(id, nombre, cedula, correo, activo)")
            .eq("unidad_id", unidad_id)
            .order("es_principal", desc=True)
            .order("id")
            .execute()
        )
        return response.data

    @safe_db_operation("unidad_propietario.add")
    def add(self, unidad_id: int, propietario_id: int, activo: bool = True, es_principal: bool = False) -> dict:
        data = {
            "unidad_id": unidad_id,
            "propietario_id": propietario_id,
            "activo": activo,
            "es_principal": es_principal,
        }
        response = self.client.table(self.TABLE).insert(data).execute()
        return response.data[0]

    @safe_db_operation("unidad_propietario.remove")
    def remove(self, unidad_propietario_id: int) -> bool:
        self.client.table(self.TABLE).delete().eq("id", unidad_propietario_id).execute()
        return True

    @safe_db_operation("unidad_propietario.set_principal")
    def set_principal(self, unidad_id: int, unidad_propietario_id: int) -> None:
        # Quitar principal de todos los de esta unidad
        self.client.table(self.TABLE).update({"es_principal": False}).eq("unidad_id", unidad_id).execute()
        # Marcar este como principal
        self.client.table(self.TABLE).update({"es_principal": True}).eq("id", unidad_propietario_id).execute()

    @safe_db_operation("unidad_propietario.toggle_activo")
    def toggle_activo(self, unidad_propietario_id: int, activo: bool) -> dict:
        response = (
            self.client.table(self.TABLE)
            .update({"activo": activo})
            .eq("id", unidad_propietario_id)
            .execute()
        )
        return response.data[0]
