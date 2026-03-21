import logging

from supabase import Client

from utils.error_handler import DatabaseError

logger = logging.getLogger(__name__)


def fetch_presupuesto_si_existe(
    client: Client, condominio_id: int, periodo: str
) -> dict | None:
    """
    Lectura directa sin decorador ni instancia de repositorio.
    Evita DatabaseError en Streamlit Cloud si la tabla no existe o falla PostgREST.
    """
    try:
        resp = (
            client.table("presupuestos")
            .select("*")
            .eq("condominio_id", condominio_id)
            .eq("periodo", periodo)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return None
    except Exception as e:
        logger.warning("fetch_presupuesto_si_existe: %s", e)
        return None


class PresupuestoRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "presupuestos"

    def get_by_periodo(self, condominio_id: int, periodo: str) -> dict | None:
        """Delega en fetch_presupuesto_si_existe (sin decorador)."""
        return fetch_presupuesto_si_existe(self.client, condominio_id, periodo)

    def upsert(self, condominio_id: int, periodo: str, monto_bs: float, descripcion: str | None = None) -> dict:
        """
        Sin @safe_db_operation: errores claros y sin asumir que resp.data tiene filas
        (PostgREST a veces devuelve lista vacía con Prefer: return=minimal).
        """
        payload: dict = {
            "condominio_id": condominio_id,
            "periodo": periodo,
            "monto_bs": float(monto_bs),
            "estado": "activo",
        }
        if descripcion is not None:
            payload["descripcion"] = descripcion

        try:
            existing = self.get_by_periodo(condominio_id, periodo)
            if existing:
                resp = (
                    self.client.table(self.table)
                    .update(payload)
                    .eq("id", existing["id"])
                    .execute()
                )
            else:
                resp = self.client.table(self.table).insert(payload).execute()

            data = getattr(resp, "data", None) or []
            if isinstance(data, list) and len(data) > 0:
                return data[0]

            again = fetch_presupuesto_si_existe(self.client, condominio_id, periodo)
            if again:
                return again

            raise RuntimeError(
                "La operación no devolvió filas; revise RLS o permisos de la tabla presupuestos."
            )
        except DatabaseError:
            raise
        except Exception as e:
            err = str(e).lower()
            logger.warning("presupuesto.upsert falló: %s", e)
            if (
                "does not exist" in err
                or "42p01" in err
                or ("relation" in err and "presupuestos" in err)
            ):
                raise DatabaseError(
                    "No existe la tabla presupuestos. Ejecute scripts/fase1_migration.sql "
                    "en el SQL Editor de Supabase y vuelva a intentar."
                ) from e
            if "permission denied" in err or "rls" in err or "policy" in err:
                raise DatabaseError(
                    "Sin permiso para escribir en presupuestos. Compruebe la clave "
                    "(service_role) y las políticas RLS en Supabase."
                ) from e
            raise DatabaseError(f"No se pudo guardar el presupuesto: {e}") from e
