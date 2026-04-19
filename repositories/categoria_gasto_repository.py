"""Repositorio para el sistema de categorías y subcategorías de gastos."""
from __future__ import annotations

import re

from supabase import Client

from utils.error_handler import safe_db_operation, DatabaseError

# Palabras ruido ignoradas al clasificar (igual que redistribucion_gastos.py)
_NOISE = {
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    "2023", "2024", "2025", "2026", "2027",
    "usd", "bsf", "bs", "de", "la", "el", "y", "en", "para", "los", "las",
    "del", "al", "con", "por", "mas", "menos", "pago", "pag", "fact",
    "factura", "nd", "ref", "nro", "no", "num",
}

# Orden para reportes PDF
ORDEN_CATEGORIAS: dict[str | None, int] = {
    "NOMINA":        1,
    "SERVICIOS":     2,
    "MANTENIMIENTO": 3,
    "OTROS":         4,
    None:            5,
}

# Seed de subcategorías base (código → (nombre, orden, palabras_clave))
_SEED_SUBCATS: list[dict] = [
    # NOMINA
    {"cat": "NOMINA", "codigo": "NOMINA_PERSONAL",   "nombre": "Personal",
     "orden": 1, "palabras": ["gerente", "subgerente", "vigilancia", "empleado", "conserje", "seguridad"]},
    {"cat": "NOMINA", "codigo": "NOMINA_BENEFICIOS", "nombre": "Beneficios",
     "orden": 2, "palabras": ["cestaticket", "cesta", "ticket", "vacacional", "bono", "utilidades"]},
    {"cat": "NOMINA", "codigo": "NOMINA_CARGAS",     "nombre": "Cargas sociales",
     "orden": 3, "palabras": ["ivss", "banavih", "faov", "lph", "seguro", "social"]},
    {"cat": "NOMINA", "codigo": "NOMINA_AYUDAS",     "nombre": "Ayudas y bonos",
     "orden": 4, "palabras": ["transporte", "alimentaria", "ayuda", "aporte", "subsidio"]},
    {"cat": "NOMINA", "codigo": "NOMINA_OTROS",      "nombre": "Otros nómina",
     "orden": 5, "palabras": []},
    # SERVICIOS
    {"cat": "SERVICIOS", "codigo": "SERV_PUBLICOS",       "nombre": "Servicios públicos",
     "orden": 1, "palabras": ["corpoelec", "hidrocapital", "cantv", "movilnet", "electricidad", "agua", "gas", "internet"]},
    {"cat": "SERVICIOS", "codigo": "SERV_ADMINISTRACION", "nombre": "Administración",
     "orden": 2, "palabras": ["administracion", "administrador", "gestion", "honorarios", "coordinacion"]},
    {"cat": "SERVICIOS", "codigo": "SERV_BANCARIOS",      "nombre": "Gastos bancarios",
     "orden": 3, "palabras": ["comision", "bancaria", "banco", "cuenta", "transferencia", "chequera"]},
    {"cat": "SERVICIOS", "codigo": "SERV_OTROS",          "nombre": "Otros servicios",
     "orden": 4, "palabras": []},
    # MANTENIMIENTO
    {"cat": "MANTENIMIENTO", "codigo": "MANT_MATERIALES",   "nombre": "Materiales",
     "orden": 1, "palabras": ["ferreteria", "cemento", "arena", "tubos", "pintura", "manguera", "cable", "material"]},
    {"cat": "MANTENIMIENTO", "codigo": "MANT_REPARACIONES", "nombre": "Reparaciones",
     "orden": 2, "palabras": ["reparacion", "bomba", "ascensor", "plomeria", "electricidad", "impermeabilizacion", "estructura"]},
    {"cat": "MANTENIMIENTO", "codigo": "MANT_LIMPIEZA",     "nombre": "Limpieza y aseo",
     "orden": 3, "palabras": ["limpieza", "basura", "bolsas", "desmalezado", "aseo", "desinfeccion", "palos"]},
    {"cat": "MANTENIMIENTO", "codigo": "MANT_OTROS",        "nombre": "Otros mantenimiento",
     "orden": 4, "palabras": []},
    # OTROS
    {"cat": "OTROS", "codigo": "OTROS_SIN_CLASIFICAR", "nombre": "Sin clasificar",
     "orden": 1, "palabras": []},
]


class CategoriaGastoRepository:
    def __init__(self, client: Client) -> None:
        self.client = client

    # ── Categorías base ────────────────────────────────────────────────────────

    @safe_db_operation("categoria.listar")
    def listar_categorias(self) -> list[dict]:
        return (
            self.client.table("categorias_gasto")
            .select("*")
            .eq("activo", True)
            .order("orden")
            .execute()
        ).data or []

    # ── Subcategorías ──────────────────────────────────────────────────────────

    @safe_db_operation("subcategoria.listar")
    def listar_subcategorias(self, condominio_id: int) -> list[dict]:
        return (
            self.client.table("subcategorias_gasto")
            .select("*, categorias_gasto(nombre, codigo, orden)")
            .eq("condominio_id", condominio_id)
            .eq("activo", True)
            .execute()
        ).data or []

    @safe_db_operation("subcategoria.crear")
    def crear_subcategoria(
        self, condominio_id: int, categoria_id: int, nombre: str,
        codigo: str | None = None, orden: int = 99, es_sistema: bool = False,
    ) -> dict:
        if not nombre.strip():
            raise DatabaseError("El nombre de la subcategoría es obligatorio.")
        _codigo = (codigo or re.sub(r"\W+", "_", nombre.upper().strip()))[:30]
        return (
            self.client.table("subcategorias_gasto")
            .insert({
                "condominio_id": condominio_id,
                "categoria_id":  categoria_id,
                "codigo":        _codigo,
                "nombre":        nombre.strip(),
                "orden":         orden,
                "es_sistema":    es_sistema,
            })
            .execute()
        ).data[0]

    @safe_db_operation("subcategoria.eliminar")
    def eliminar_subcategoria(self, subcategoria_id: int) -> None:
        self.client.table("subcategorias_gasto").delete().eq("id", subcategoria_id).execute()

    # ── Palabras clave ─────────────────────────────────────────────────────────

    @safe_db_operation("palabras_clave.listar")
    def listar_palabras_clave(self, condominio_id: int) -> list[dict]:
        return (
            self.client.table("palabras_clave_categoria")
            .select("*, subcategorias_gasto(nombre, codigo, categoria_id, categorias_gasto(nombre, codigo))")
            .eq("condominio_id", condominio_id)
            .execute()
        ).data or []

    @safe_db_operation("palabras_clave.agregar")
    def agregar_palabra_clave(
        self, condominio_id: int, subcategoria_id: int, palabra: str
    ) -> dict:
        p = palabra.strip().lower()
        if not p:
            raise DatabaseError("La palabra clave no puede estar vacía.")
        return (
            self.client.table("palabras_clave_categoria")
            .insert({"condominio_id": condominio_id, "subcategoria_id": subcategoria_id, "palabra": p})
            .execute()
        ).data[0]

    @safe_db_operation("palabras_clave.eliminar")
    def eliminar_palabra_clave(self, palabra_id: int) -> None:
        self.client.table("palabras_clave_categoria").delete().eq("id", palabra_id).execute()

    # ── Clasificación automática ───────────────────────────────────────────────

    def sugerir_subcategoria(
        self, condominio_id: int, texto: str,
        subcats: list[dict] | None = None,
        palabras: list[dict] | None = None,
    ) -> dict | None:
        """
        Dado un texto, retorna la subcategoría con más coincidencias de palabras clave.
        Acepta subcats/palabras pre-cargadas para evitar N+1 queries en lote.
        """
        if not texto:
            return None

        # Normalizar texto: lower, quitar ruido
        tokens = set(
            w for w in re.findall(r"[a-záéíóúñü]+", texto.lower())
            if w not in _NOISE and len(w) > 2
        )
        if not tokens:
            return None

        try:
            if palabras is None:
                palabras = self.listar_palabras_clave(condominio_id)
            if subcats is None:
                subcats  = self.listar_subcategorias(condominio_id)
        except Exception:
            return None

        # Contar coincidencias por subcategoría
        conteos: dict[int, int] = {}
        for pk in palabras:
            palabra = (pk.get("palabra") or "").strip().lower()
            if not palabra:
                continue
            # Coincidencia parcial: el token del texto contiene la palabra clave
            if any(palabra in tok or tok in palabra for tok in tokens):
                sid = pk["subcategoria_id"]
                conteos[sid] = conteos.get(sid, 0) + 1

        if not conteos:
            # Devolver "Sin clasificar"
            sin_clas = next(
                (s for s in subcats if s.get("codigo") == "OTROS_SIN_CLASIFICAR"), None
            )
            if sin_clas:
                cat_info = sin_clas.get("categorias_gasto") or {}
                return {
                    "subcategoria_id":     sin_clas["id"],
                    "subcategoria_codigo": sin_clas["codigo"],
                    "subcategoria_nombre": sin_clas["nombre"],
                    "categoria_codigo":    cat_info.get("codigo", "OTROS"),
                    "categoria_nombre":    cat_info.get("nombre", "Otros"),
                    "confianza":           0.0,
                }
            return None

        # Seleccionar la subcategoría con más coincidencias
        best_id = max(conteos, key=lambda sid: conteos[sid])
        best    = next((s for s in subcats if s["id"] == best_id), None)
        if not best:
            return None

        cat_info = best.get("categorias_gasto") or {}
        confianza = min(conteos[best_id] / max(len(tokens), 1), 1.0)
        return {
            "subcategoria_id":     best["id"],
            "subcategoria_codigo": best["codigo"],
            "subcategoria_nombre": best["nombre"],
            "categoria_codigo":    cat_info.get("codigo", "OTROS"),
            "categoria_nombre":    cat_info.get("nombre", "Otros"),
            "confianza":           round(confianza, 2),
        }

    # ── Inicialización idempotente del seed ────────────────────────────────────

    def inicializar_subcategorias_condominio(self, condominio_id: int) -> None:
        """
        Crea las subcategorías base + palabras clave para un condominio
        si aún no existen. Es idempotente — no genera duplicados.
        """
        try:
            existing = self.listar_subcategorias(condominio_id)
            existing_codigos = {s["codigo"] for s in existing}

            cats = self.listar_categorias()
            cat_by_codigo = {c["codigo"]: c["id"] for c in cats}

            palabras_existentes = self.listar_palabras_clave(condominio_id)
            palabras_existentes_set = {
                (p["subcategoria_id"], p["palabra"]) for p in palabras_existentes
            }

            for seed in _SEED_SUBCATS:
                if seed["codigo"] in existing_codigos:
                    # Ya existe — solo agregar palabras faltantes
                    sub = next((s for s in existing if s["codigo"] == seed["codigo"]), None)
                    if sub:
                        for palabra in seed["palabras"]:
                            if (sub["id"], palabra) not in palabras_existentes_set:
                                try:
                                    self.agregar_palabra_clave(condominio_id, sub["id"], palabra)
                                    palabras_existentes_set.add((sub["id"], palabra))
                                except Exception:
                                    pass
                    continue

                cat_id = cat_by_codigo.get(seed["cat"])
                if not cat_id:
                    continue

                try:
                    nueva = self.crear_subcategoria(
                        condominio_id=condominio_id,
                        categoria_id=cat_id,
                        nombre=seed["nombre"],
                        codigo=seed["codigo"],
                        orden=seed["orden"],
                        es_sistema=True,
                    )
                    for palabra in seed["palabras"]:
                        try:
                            self.agregar_palabra_clave(condominio_id, nueva["id"], palabra)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
