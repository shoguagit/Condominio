import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL y SUPABASE_KEY son obligatorios. "
        "Copia .env.example a .env y completa los valores."
    )
