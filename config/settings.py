import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
# Clave service_role para operaciones de administración (crear/cambiar usuarios)
SUPABASE_SERVICE_KEY: str | None = os.getenv("SUPABASE_SERVICE_KEY") or None
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL y SUPABASE_KEY son obligatorios. "
        "Copia .env.example a .env y completa los valores."
    )
