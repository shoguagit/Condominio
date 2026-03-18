from supabase import Client

from utils.error_handler import safe_db_operation, AuthError, DatabaseError
from config.supabase_client import get_admin_client


class UsuarioRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "usuarios"

    # ── Lectura ───────────────────────────────────────────────────────────────

    @safe_db_operation("usuario.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, condominios(nombre)")
            .eq("condominio_id", condominio_id)
            .order("nombre")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("usuario.get_by_id")
    def get_by_id(self, usuario_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*, condominios(nombre)")
            .eq("id", usuario_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("usuario.get_by_email")
    def get_by_email(self, email: str) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq("email", email)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("usuario.get_by_condominio")
    def get_by_condominio(self, condominio_id: int) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq("condominio_id", condominio_id)
            .eq("activo", True)
            .order("nombre")
            .execute()
        )
        return response.data

    # ── Escritura ─────────────────────────────────────────────────────────────

    @safe_db_operation("usuario.create")
    def create(self, data: dict, password: str) -> dict:
        """
        Registra el usuario en Supabase Auth y luego en la tabla usuarios.
        data debe incluir: nombre, email, rol, condominio_id.
        """
        email = (data.get("email") or "").strip()

        # 1. Crear en Supabase Auth (service_role puede crear usuarios directamente)
        try:
            admin_client = get_admin_client()
            auth_resp = admin_client.auth.admin.create_user({
                "email":            email,
                "password":         password,
                "email_confirm":    True,
            })
            if not auth_resp.user:
                raise AuthError("No se pudo crear el usuario en Supabase Auth.")
        except Exception as e:
            # Nos protegemos contra cualquier tipo raro de excepción
            try:
                err = str(e)
            except Exception:
                err = repr(e)
            err_l = err.lower() if isinstance(err, str) else ""

            if "service_key" in err_l or "service role" in err_l:
                raise DatabaseError(
                    "Falta configurar SUPABASE_SERVICE_KEY (service_role) en Secrets/.env "
                    "para poder crear usuarios en Supabase Auth."
                )
            if "already registered" in err_l or "already exists" in err_l:
                raise DatabaseError("Ya existe un usuario registrado con ese correo.")
            raise DatabaseError(f"Error al crear usuario en Auth: {err}")

        # 2. Insertar en tabla usuarios
        payload = {k: v for k, v in data.items() if k != "password"}
        response = self.client.table(self.table).insert(payload).execute()
        return response.data[0]

    @safe_db_operation("usuario.update")
    def update(self, usuario_id: int, data: dict) -> dict:
        """Actualiza datos del usuario (sin contraseña)."""
        payload = {k: v for k, v in data.items() if k != "password"}
        response = (
            self.client.table(self.table)
            .update(payload)
            .eq("id", usuario_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("usuario.toggle_activo")
    def toggle_activo(self, usuario_id: int, activo: bool) -> dict:
        """Activa o desactiva un usuario sin eliminarlo físicamente."""
        response = (
            self.client.table(self.table)
            .update({"activo": activo})
            .eq("id", usuario_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("usuario.change_password")
    def change_password(self, email: str, new_password: str) -> bool:
        """
        Cambia la contraseña del usuario en Supabase Auth.
        Usa siempre un cliente inicializado con service_role key.
        """
        try:
            # Obtener el user_id de Auth por email
            admin_client = get_admin_client()
            users_resp = admin_client.auth.admin.list_users()
            auth_user  = next(
                (u for u in users_resp if u.email == email), None
            )
            if not auth_user:
                raise AuthError("Usuario no encontrado en Supabase Auth.")

            admin_client.auth.admin.update_user_by_id(
                auth_user.id,
                {"password": new_password},
            )
            return True
        except Exception as e:
            raise AuthError(f"No se pudo cambiar la contraseña: {e}")

    @safe_db_operation("usuario.delete")
    def delete(self, usuario_id: int, email: str) -> bool:
        """
        Elimina el usuario de la tabla y de Supabase Auth.
        Se recomienda usar toggle_activo en lugar de delete en producción.
        """
        # Eliminar de la tabla
        self.client.table(self.table).delete().eq("id", usuario_id).execute()

        # Eliminar de Auth
        try:
            admin_client = get_admin_client()
            users_resp = admin_client.auth.admin.list_users()
            auth_user  = next((u for u in users_resp if u.email == email), None)
            if auth_user:
                admin_client.auth.admin.delete_user(auth_user.id)
        except Exception:
            pass  # Si falla Auth, el registro de BD ya fue eliminado

        return True

    @safe_db_operation("usuario.update_ultimo_acceso")
    def update_ultimo_acceso(self, email: str) -> None:
        """Registra la fecha/hora del último acceso al sistema."""
        self.client.table(self.table).update(
            {"ultimo_acceso": "now()"}
        ).eq("email", email).execute()
