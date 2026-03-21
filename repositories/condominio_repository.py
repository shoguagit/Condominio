from supabase import Client

from utils.error_handler import DatabaseError, safe_db_operation


class CondominioRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "condominios"

    @safe_db_operation("condominio.get_all")
    def get_all(self, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, paises(nombre, simbolo_moneda), tipos_documento(nombre)")
            .order("nombre")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("condominio.get_by_id")
    def get_by_id(self, condominio_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*, paises(nombre, simbolo_moneda), tipos_documento(nombre)")
            .eq("id", condominio_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("condominio.create")
    def create(self, data: dict) -> dict:
        response = (
            self.client.table(self.table)
            .insert(data)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("condominio.update")
    def update(self, condominio_id: int, data: dict) -> dict:
        response = (
            self.client.table(self.table)
            .update(data)
            .eq("id", condominio_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("condominio.delete")
    def delete(self, condominio_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", condominio_id).execute()
        return True

    @safe_db_operation("condominio.search")
    def search(self, term: str) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*, paises(nombre, simbolo_moneda), tipos_documento(nombre)")
            .ilike("nombre", f"%{term}%")
            .order("nombre")
            .execute()
        )
        return response.data

    @safe_db_operation("condominio.toggle_activo")
    def toggle_activo(self, condominio_id: int, activo: bool) -> dict:
        response = (
            self.client.table(self.table)
            .update({"activo": activo})
            .eq("id", condominio_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("condominio.actualizar_dia_limite")
    def actualizar_dia_limite(self, condominio_id: int, dia: int) -> dict:
        """Actualiza el día límite de pago del condominio (1–28)."""
        if not isinstance(dia, int) or not (1 <= dia <= 28):
            raise DatabaseError("El día límite de pago debe estar entre 1 y 28.")
        return (
            self.client.table(self.table)
            .update({"dia_limite_pago": dia})
            .eq("id", condominio_id)
            .execute()
        ).data[0]

    @safe_db_operation("condominio.obtener_dia_limite")
    def obtener_dia_limite(self, condominio_id: int) -> int:
        """Día límite de pago; por defecto 15 si no está configurado."""
        # Sin .single(): PostgREST devuelve error (PGRST116) si no hay exactamente 1 fila.
        resp = (
            self.client.table(self.table)
            .select("dia_limite_pago")
            .eq("id", condominio_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return 15
        row = rows[0]
        d = row.get("dia_limite_pago")
        if d is None:
            return 15
        try:
            di = int(d)
            return di if 1 <= di <= 28 else 15
        except (TypeError, ValueError):
            return 15


def obtener_dia_limite_safe(repo: CondominioRepository, condominio_id: int) -> int:
    """
    Devuelve día límite (1–28) o 15 por defecto.
    Evita AttributeError si el despliegue tiene una versión antigua del repositorio
    sin `obtener_dia_limite`, o si falla la consulta (columna aún no migrada, etc.).
    """
    obt = getattr(repo, "obtener_dia_limite", None)
    if not callable(obt):
        return 15
    try:
        return int(obt(condominio_id))
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:
        return 15
