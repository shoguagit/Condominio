from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY

_client: Client | None = None


def get_supabase_client() -> Client:
    """Retorna el cliente Supabase (anon) como singleton para operaciones normales."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def get_admin_client() -> Client:
    """
    Retorna un cliente Supabase inicializado con la service_role key.
    Usado solo para operaciones de administración de usuarios (Auth admin).
    """
    if not SUPABASE_SERVICE_KEY:
        raise ValueError(
            "SUPABASE_SERVICE_KEY es obligatoria para operaciones de administración "
            "de usuarios (crear/cambiar/eliminar). Defínela en .env / Secrets."
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
