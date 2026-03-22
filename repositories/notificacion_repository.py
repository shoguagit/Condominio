"""
Notificaciones por correo: configuración SMTP en condominios y auditoría de envíos.
"""

from __future__ import annotations

from datetime import datetime, timezone

from supabase import Client

from utils.error_handler import safe_db_operation


class NotificacionRepository:
    def __init__(self, client: Client):
        self.client = client
        self._condo = "condominios"
        self._notif = "notificaciones_enviadas"

    @safe_db_operation("notificacion.registrar_envio")
    def registrar_envio(
        self,
        condominio_id: int,
        periodo: str,
        unidad_id: int | None,
        email: str,
        nombre: str,
        asunto: str,
        cuerpo: str,
        enviado: bool,
        error: str | None,
        tipo: str = "mora",
    ) -> dict:
        row: dict = {
            "condominio_id": int(condominio_id),
            "periodo": (periodo or "")[:7],
            "unidad_id": int(unidad_id) if unidad_id is not None else None,
            "propietario_email": (email or "")[:255] or None,
            "propietario_nombre": (nombre or "")[:255] or None,
            "asunto": (asunto or "")[:255] or None,
            "cuerpo": cuerpo,
            "enviado": bool(enviado),
            "error_mensaje": error if error else None,
            "tipo": tipo,
        }
        if enviado:
            row["enviado_at"] = datetime.now(timezone.utc).isoformat()
        ins = self.client.table(self._notif).insert(row).execute()
        return (ins.data or [{}])[0]

    @safe_db_operation("notificacion.obtener_historial")
    def obtener_historial(self, condominio_id: int, periodo: str) -> list[dict]:
        per = (periodo or "")[:7]
        return (
            self.client.table(self._notif)
            .select("*")
            .eq("condominio_id", int(condominio_id))
            .eq("periodo", per)
            .order("created_at", desc=True)
            .execute()
        ).data or []

    @safe_db_operation("notificacion.obtener_config_smtp")
    def obtener_config_smtp(self, condominio_id: int) -> dict | None:
        rows = (
            self.client.table(self._condo)
            .select("smtp_email, smtp_app_password, smtp_nombre_remitente")
            .eq("id", int(condominio_id))
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            return None
        r = rows[0]
        em = (r.get("smtp_email") or "").strip()
        if not em:
            return None
        return {
            "smtp_email": em,
            "smtp_app_password": r.get("smtp_app_password") or "",
            "smtp_nombre_remitente": (r.get("smtp_nombre_remitente") or "").strip()
            or "Administración del Condominio",
        }

    @safe_db_operation("notificacion.actualizar_config_smtp")
    def actualizar_config_smtp(
        self,
        condominio_id: int,
        smtp_email: str,
        app_password: str | None,
        nombre_remitente: str,
    ) -> dict:
        data: dict = {
            "smtp_email": (smtp_email or "").strip() or None,
            "smtp_nombre_remitente": (nombre_remitente or "").strip()
            or "Administración del Condominio",
        }
        pwd = (app_password or "").replace(" ", "").strip()
        if pwd:
            data["smtp_app_password"] = pwd
        resp = (
            self.client.table(self._condo)
            .update(data)
            .eq("id", int(condominio_id))
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else {}
