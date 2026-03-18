"""Datos de prueba reutilizables para todos los módulos."""

PAISES = [
    {"id": 1, "nombre": "Venezuela", "codigo_iso": "VEN", "moneda": "VES", "simbolo_moneda": "Bs."},
    {"id": 2, "nombre": "Colombia",  "codigo_iso": "COL", "moneda": "COP", "simbolo_moneda": "$"},
    {"id": 3, "nombre": "Ecuador",   "codigo_iso": "ECU", "moneda": "USD", "simbolo_moneda": "$"},
]

TIPOS_DOCUMENTO = [
    {"id": 1, "pais_id": 1, "nombre": "RIF",  "descripcion": "Registro de Información Fiscal"},
    {"id": 2, "pais_id": 2, "nombre": "NIT",  "descripcion": "Número de Identificación Tributaria"},
    {"id": 3, "pais_id": 3, "nombre": "RUC",  "descripcion": "Registro Único de Contribuyentes"},
]

CONDOMINIOS = [
    {
        "id": 1,
        "nombre": "Residencias El Parque",
        "direccion": "Av. Principal, Caracas",
        "pais_id": 1,
        "numero_documento": "J-12345678-9",
        "mes_proceso": "2026-03-01",
        "tasa_cambio": 36.50,
        "activo": True,
    }
]

PROVEEDORES = [
    {
        "id": 1,
        "condominio_id": 1,
        "nombre": "Servicios Técnicos CA",
        "numero_documento": "J-98765432-1",
        "correo": "contacto@servicios.com",
        "saldo": 0.0,
        "activo": True,
    }
]

USUARIOS = [
    {
        "id": 1,
        "condominio_id": 1,
        "nombre": "Administrador",
        "email": "admin@sistema.com",
        "rol": "admin",
        "activo": True,
    }
]

PROPIETARIOS = [
    {
        "id": 1,
        "condominio_id": 1,
        "nombre": "María González",
        "cedula": "V-12345678",
        "telefono": "0414-9876543",
        "correo": "maria@email.com",
        "activo": True,
    }
]

UNIDADES = [
    {
        "id": 1,
        "condominio_id": 1,
        "propietario_id": 1,
        "tipo_propiedad": "Apartamento",
        "numero": "3B",
        "piso": "3",
        "tipo_condomino": "Propietario",
        "cuota_fija": 50.00,
        "activo": True,
    }
]
