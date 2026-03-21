import logging

from supabase import Client

from utils.error_handler import safe_db_operation, DatabaseError
from utils.indiviso_cuota import cuota_bs_desde_presupuesto

logger = logging.getLogger(__name__)

_TAB_UNI = "unidades"


def suma_indivisos_si_disponible(
    client: Client, condominio_id: int, exclude_id: int | None = None
) -> float:
    """
    Suma indiviso_pct sin decorador: no tumba la app si PostgREST/RLS/red fallan
    (p. ej. Streamlit Cloud).
    """
    try:
        rows = (
            client.table(_TAB_UNI)
            .select("*")
            .eq("condominio_id", condominio_id)
            .execute()
        ).data
        total = 0.0
        for r in rows or []:
            if exclude_id is not None and r.get("id") == exclude_id:
                continue
            total += float(r.get("indiviso_pct") or 0)
        return round(total, 4)
    except Exception as e:
        logger.warning("suma_indivisos_si_disponible: %s", e)
        return 0.0


def indicadores_unidades_si_disponible(
    client: Client, condominio_id: int, solo_activos: bool = False
) -> dict:
    """Métricas de unidades; dict vacío en error."""
    try:
        q = client.table(_TAB_UNI).select("*").eq("condominio_id", condominio_id)
        if solo_activos:
            q = q.eq("activo", True)
        rows = q.execute().data
        rows = rows or []
        total = len(rows)
        al_dia = sum(1 for r in rows if (r.get("estado_pago") or "al_dia") == "al_dia")
        morosos = sum(1 for r in rows if (r.get("estado_pago") or "") == "moroso")
        pct_asignado = round(sum(float(r.get("indiviso_pct") or 0) for r in rows), 4)
        return {
            "total": total,
            "al_dia": al_dia,
            "morosos": morosos,
            "pct_asignado": pct_asignado,
        }
    except Exception as e:
        logger.warning("indicadores_unidades_si_disponible: %s", e)
        return {"total": 0, "al_dia": 0, "morosos": 0, "pct_asignado": 0.0}


class UnidadRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table  = "unidades"

    @safe_db_operation("unidad.get_all")
    def get_all(self, condominio_id: int, solo_activos: bool = False) -> list[dict]:
        query = (
            self.client.table(self.table)
            .select("*, propietarios(id, nombre, cedula, correo)")
            .eq("condominio_id", condominio_id)
            .order("numero")
        )
        if solo_activos:
            query = query.eq("activo", True)
        return query.execute().data

    @safe_db_operation("unidad.get_by_id")
    def get_by_id(self, unidad_id: int) -> dict | None:
        response = (
            self.client.table(self.table)
            .select("*, propietarios(id, nombre, cedula, correo)")
            .eq("id", unidad_id)
            .single()
            .execute()
        )
        return response.data

    @safe_db_operation("unidad.get_by_propietario")
    def get_by_propietario(self, propietario_id: int) -> list[dict]:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq("propietario_id", propietario_id)
            .eq("activo", True)
            .execute()
        )
        return response.data

    @safe_db_operation("unidad.create")
    def create(self, data: dict) -> dict:
        codigo = (data.get("codigo") or "").strip()
        if not codigo:
            raise DatabaseError("El código de la unidad es obligatorio.")
        if data.get("saldo") is None:
            data["saldo"] = 0.00
        # propietario_id y alicuota_id son opcionales (se asignan después)
        response = self.client.table(self.table).insert(data).execute()
        return response.data[0]

    @safe_db_operation("unidad.update")
    def update(self, unidad_id: int, data: dict) -> dict:
        codigo = (data.get("codigo") or "").strip()
        if not codigo:
            raise DatabaseError("El código de la unidad es obligatorio.")
        if data.get("saldo") is None:
            data["saldo"] = 0.00
        # propietario_id y alicuota_id pueden ser null (sin asignar)
        payload = dict(data)
        response = (
            self.client.table(self.table)
            .update(payload)
            .eq("id", unidad_id)
            .execute()
        )
        return response.data[0]

    @safe_db_operation("unidad.delete")
    def delete(self, unidad_id: int) -> bool:
        self.client.table(self.table).delete().eq("id", unidad_id).execute()
        return True

    @safe_db_operation("unidad.search")
    def search(self, condominio_id: int, term: str) -> list[dict]:
        """Busca por número de unidad."""
        response = (
            self.client.table(self.table)
            .select("*, propietarios(id, nombre)")
            .eq("condominio_id", condominio_id)
            .ilike("numero", f"%{term}%")
            .order("numero")
            .execute()
        )
        return response.data

    @safe_db_operation("unidad.toggle_activo")
    def toggle_activo(self, unidad_id: int, activo: bool) -> dict:
        response = (
            self.client.table(self.table)
            .update({"activo": activo})
            .eq("id", unidad_id)
            .execute()
        )
        return response.data[0]

    def get_suma_indivisos(self, condominio_id: int, exclude_id: int | None = None) -> float:
        """Delega en suma_indivisos_si_disponible (sin @safe_db_operation)."""
        return suma_indivisos_si_disponible(self.client, condominio_id, exclude_id)

    def get_disponible_indiviso(self, condominio_id: int, exclude_id: int | None = None) -> float:
        """100% − suma actual de indivisos (sin la unidad excluida)."""
        return round(100.0 - self.get_suma_indivisos(condominio_id, exclude_id), 4)

    def get_indicadores(self, condominio_id: int) -> dict:
        """Delega en indicadores_unidades_si_disponible (sin @safe_db_operation)."""
        return indicadores_unidades_si_disponible(self.client, condominio_id)

    def get_with_cuota(self, condominio_id: int, presupuesto_mes: float) -> list[dict]:
        """Unidades con _cuota_bs calculada (presupuesto × indiviso/100)."""
        rows = self.get_all(condominio_id)
        pres = float(presupuesto_mes or 0)
        for r in rows:
            pct = float(r.get("indiviso_pct") or 0)
            if pres > 0:
                r["_cuota_bs"] = cuota_bs_desde_presupuesto(pres, pct)
            else:
                r["_cuota_bs"] = None
        return rows
