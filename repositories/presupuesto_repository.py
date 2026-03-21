import logging

from supabase import Client

from utils.error_handler import safe_db_operation

logger = logging.getLogger(__name__)


class PresupuestoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "presupuestos"

    def get_by_periodo(self, condominio_id: int, periodo: str) -> dict | None:
        """
        Sin safe_db_operation: si la tabla `presupuestos` no existe (migración no aplicada),
        devuelve None en lugar de tumbar la página (p. ej. Streamlit Cloud).
        """
        try:
            resp = (
                self.client.table(self.table)
                .select("*")
                .eq("condominio_id", condominio_id)
                .eq("periodo", periodo)
                .execute()
            )
            if resp.data:
                return resp.data[0]
            return None
        except Exception as e:
            logger.warning("presupuesto.get_by_periodo omitido: %s", e)
            return None

    @safe_db_operation("presupuesto.upsert")
    def upsert(self, condominio_id: int, periodo: str, monto_bs: float, descripcion: str | None = None) -> dict:
        existing = self.get_by_periodo(condominio_id, periodo)
        payload = {
            "condominio_id": condominio_id,
            "periodo": periodo,
            "monto_bs": float(monto_bs),
            "descripcion": descripcion,
            "estado": "activo",
        }
        if existing:
            return (
                self.client.table(self.table)
                .update(payload)
                .eq("id", existing["id"])
                .execute()
            ).data[0]
        return self.client.table(self.table).insert(payload).execute().data[0]
