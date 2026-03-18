from supabase import Client

from utils.error_handler import safe_db_operation, DatabaseError
from utils.validators import validate_alicuota_valor, validate_suma_alicuotas


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
        condominio_id = data.get("condominio_id")
        if not condominio_id:
            raise DatabaseError("Falta condominio_id para crear alícuota.")

        ok_val, msg_val = validate_alicuota_valor(data.get("total_alicuota"))
        if not ok_val:
            raise DatabaseError(msg_val)

        # Validar suma aproximada a 1.00 incluyendo la nueva alícuota
        current = self.get_all(condominio_id)
        valores = [float(r.get("total_alicuota") or 0) for r in current] + [float(data.get("total_alicuota") or 0)]
        ok_sum, msg_sum = validate_suma_alicuotas(valores)
        if not ok_sum:
            raise DatabaseError(msg_sum)

        return self.client.table(self.table).insert(data).execute().data[0]

    @safe_db_operation("alicuota.update")
    def update(self, alicuota_id: int, data: dict) -> dict:
        if self.is_assigned(alicuota_id):
            raise DatabaseError("Esta alícuota ya está asignada a una unidad y no puede modificarse.")

        condominio_id = data.get("condominio_id")
        if not condominio_id:
            # Intentar cargar condominio desde el registro actual
            current = self.get_by_id(alicuota_id) or {}
            condominio_id = current.get("condominio_id")
        if not condominio_id:
            raise DatabaseError("Falta condominio_id para actualizar alícuota.")

        ok_val, msg_val = validate_alicuota_valor(data.get("total_alicuota"))
        if not ok_val:
            raise DatabaseError(msg_val)

        # Validar suma excluyendo el registro anterior (reemplazado por el nuevo total)
        current = self.get_all(condominio_id)
        valores = []
        for r in current:
            rid = r.get("id")
            if rid == alicuota_id:
                continue
            valores.append(float(r.get("total_alicuota") or 0))
        valores.append(float(data.get("total_alicuota") or 0))

        ok_sum, msg_sum = validate_suma_alicuotas(valores)
        if not ok_sum:
            raise DatabaseError(msg_sum)

        return (
            self.client.table(self.table)
            .update(data).eq("id", alicuota_id).execute()
        ).data[0]

    @safe_db_operation("alicuota.delete")
    def delete(self, alicuota_id: int) -> bool:
        # Regla de negocio: nunca se eliminan alícuotas
        raise DatabaseError("Las alícuotas no pueden eliminarse una vez creadas. Contacte al administrador.")

    def can_delete(self, id) -> bool:
        """Las alícuotas nunca se eliminan."""
        return False

    def is_assigned(self, id) -> bool:
        """
        Verifica si la alícuota está asignada en tabla unidades.
        Requiere columna unidades.alicuota_id.
        """
        try:
            result = self.client.table("unidades").select("id").eq("alicuota_id", id).execute()
            return bool(result.data) and len(result.data) > 0
        except Exception:
            # Si la migración aún no fue aplicada, no bloquear operaciones.
            return False

    @safe_db_operation("alicuota.recalcular")
    def recalcular_desde_unidades(self, alicuota_id: int, total_unidades: int) -> dict:
        """Actualiza cantidad_unidades y recalcula total_alicuota (1 / total_unidades)."""
        total = round(1 / total_unidades, 6) if total_unidades > 0 else 0
        return (
            self.client.table(self.table)
            .update({"cantidad_unidades": total_unidades, "total_alicuota": total})
            .eq("id", alicuota_id).execute()
        ).data[0]
