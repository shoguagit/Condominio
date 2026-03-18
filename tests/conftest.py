import pytest
from unittest.mock import MagicMock


# =============================================================================
# HELPER — construye un mock de Supabase con cadenas fluidas configuradas
# =============================================================================

def _make_chain(**kwargs):
    """
    Retorna un MagicMock que simula la cadena fluida de Supabase:
        .table().select().eq().order().execute() → data
    Acepta kwargs para sobreescribir .data en distintos puntos de la cadena.
    """
    m = MagicMock()

    # Cadenas más comunes — cada método devuelve el mismo mock para que
    # las cadenas arbitrarias sigan funcionando.
    chain = MagicMock()
    chain.select.return_value     = chain
    chain.insert.return_value     = chain
    chain.update.return_value     = chain
    chain.delete.return_value     = chain
    chain.eq.return_value         = chain
    chain.neq.return_value        = chain
    chain.ilike.return_value      = chain
    chain.order.return_value      = chain
    chain.range.return_value      = chain
    chain.single.return_value     = chain
    chain.limit.return_value      = chain
    chain.execute.return_value    = MagicMock(data=kwargs.get("data", []))

    m.table.return_value = chain
    return m, chain


# =============================================================================
# FIXTURE PRINCIPAL — mock_supabase
# =============================================================================

@pytest.fixture
def mock_supabase():
    """
    Cliente Supabase mockeado con cadena fluida completa.
    Retorna (client, chain) para que los tests puedan configurar
    chain.execute.return_value.data según el caso.
    """
    client, chain = _make_chain(data=[])
    # Auth admin mock
    client.auth = MagicMock()
    client.auth.admin = MagicMock()
    client.auth.admin.create_user.return_value = MagicMock(user=MagicMock(id="uuid-123"))
    client.auth.admin.list_users.return_value  = []
    return client


@pytest.fixture
def mock_chain(mock_supabase):
    """Acceso directo a la cadena fluida del mock para configurar .data."""
    return mock_supabase.table.return_value


# =============================================================================
# FIXTURES DE DATOS
# =============================================================================

@pytest.fixture
def condominio_data():
    return {
        "id":               1,
        "nombre":           "Residencias El Parque",
        "direccion":        "Av. Principal, Caracas",
        "pais_id":          1,
        "tipo_documento_id": 1,
        "numero_documento": "J-12345678-9",
        "telefono":         "0212-5551234",
        "email":            "admin@elparque.com",
        "mes_proceso":      "2026-03-01",
        "tasa_cambio":      36.5000,
        "moneda_principal": "USD",
        "activo":           True,
    }


@pytest.fixture
def proveedor_data():
    return {
        "id":               1,
        "condominio_id":    1,
        "nombre":           "Servicios Técnicos CA",
        "tipo_documento_id": 1,
        "numero_documento": "J-98765432-1",
        "telefono_fijo":    "0212-4441234",
        "telefono_celular": "0414-1234567",
        "correo":           "contacto@servicios.com",
        "contacto":         "Juan Pérez",
        "notas":            None,
        "saldo":            0.0,
        "activo":           True,
    }


@pytest.fixture
def usuario_data():
    return {
        "id":            1,
        "condominio_id": 1,
        "nombre":        "Ana Administradora",
        "email":         "admin@sistema.com",
        "rol":           "admin",
        "activo":        True,
        "ultimo_acceso": None,
    }


@pytest.fixture
def factura_data():
    return {
        "id":               1,
        "condominio_id":    1,
        "numero":           "0001-00012345",
        "fecha":            "2026-03-05",
        "fecha_vencimiento":"2026-03-20",
        "proveedor_id":     1,
        "descripcion":      "Servicio de mantenimiento",
        "total":            500.00,
        "pagado":           200.00,
        "mes_proceso":      "2026-03-01",
        "activo":           True,
    }


@pytest.fixture
def pais_data():
    return [
        {"id": 1, "nombre": "Venezuela", "codigo_iso": "VEN",
         "moneda": "VES", "simbolo_moneda": "Bs."},
        {"id": 2, "nombre": "Colombia",  "codigo_iso": "COL",
         "moneda": "COP", "simbolo_moneda": "$"},
    ]


@pytest.fixture
def tipo_doc_data():
    return [
        {"id": 1, "pais_id": 1, "nombre": "RIF",
         "formato_regex": r"^[VJGECP]-\d{8}-\d$",
         "descripcion": "Registro de Información Fiscal"},
        {"id": 2, "pais_id": 2, "nombre": "NIT",
         "formato_regex": r"^\d{9,10}(-\d)?$",
         "descripcion": "Número de Identificación Tributaria"},
    ]
