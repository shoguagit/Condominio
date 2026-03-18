# Skill: Testing — Sistema de Condominio Python/Streamlit/Supabase
## Propósito
Establecer estándares de testing automatizado para el sistema de condominio.

---

## 1. Stack de Testing

```
pytest              → framework principal
pytest-mock         → mocking de Supabase
pytest-cov          → cobertura de código
streamlit testing   → para componentes UI (opcional)
```

```bash
# Instalar dependencias de testing
pip install pytest pytest-mock pytest-cov python-dotenv
```

---

## 2. Estructura de Tests

```
tests/
├── __init__.py
├── conftest.py              ← fixtures globales
├── unit/
│   ├── test_validators.py   ← tests de validaciones
│   ├── test_repositories.py ← tests de repos con mock
│   └── test_models.py       ← tests de modelos/schemas
├── integration/
│   └── test_supabase.py     ← tests contra Supabase test
└── utils/
    └── mock_data.py         ← datos de prueba
```

---

## 3. conftest.py — Fixtures Globales

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_supabase():
    """Mock del cliente Supabase para tests unitarios"""
    mock = MagicMock()
    # Simular cadena fluida: .table().select().execute()
    mock.table.return_value.select.return_value.execute.return_value.data = []
    mock.table.return_value.insert.return_value.execute.return_value.data = []
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    mock.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    return mock

@pytest.fixture
def proveedor_data():
    return {
        "nombre": "Empresa de Limpieza ABC",
        "numero_documento": "J-12345678-9",
        "telefono_celular": "0414-1234567",
        "correo": "contacto@abc.com",
        "condominio_id": 1
    }

@pytest.fixture
def condominio_data():
    return {
        "nombre": "Condominio Guaicaipuro",
        "direccion": "Av. Principal, Caracas",
        "pais_id": 1,
        "numero_documento": "J-98765432-1",
        "tasa_cambio": 438.2050
    }
```

---

## 4. Tests de Validadores

```python
# tests/unit/test_validators.py
import pytest
from utils.validators import validate_rif, validate_email, validate_form

class TestValidateRIF:
    def test_rif_valido_empresa(self):
        ok, msg = validate_rif("J-12345678-9")
        assert ok is True
        assert msg == ""
    
    def test_rif_valido_persona(self):
        ok, msg = validate_rif("V-12345678-9")
        assert ok is True
    
    def test_rif_sin_guiones(self):
        ok, msg = validate_rif("J123456789")
        assert ok is False
        assert "inválido" in msg.lower()
    
    def test_rif_vacio(self):
        ok, msg = validate_rif("")
        assert ok is False
        assert "obligatorio" in msg.lower()
    
    def test_rif_tipo_invalido(self):
        ok, msg = validate_rif("X-12345678-9")
        assert ok is False

class TestValidateEmail:
    def test_email_valido(self):
        ok, _ = validate_email("admin@condominio.com")
        assert ok is True
    
    def test_email_invalido(self):
        ok, msg = validate_email("no-es-email")
        assert ok is False
    
    def test_email_vacio_es_valido(self):
        """Email vacío es válido (campo no obligatorio)"""
        ok, _ = validate_email("")
        assert ok is True

class TestValidateForm:
    def test_form_completo_valido(self, proveedor_data):
        rules = {
            "nombre": {"required": True, "max_length": 200},
            "numero_documento": {"required": True, "type": "rif"},
        }
        errors = validate_form(proveedor_data, rules)
        assert errors == []
    
    def test_form_nombre_faltante(self):
        rules = {"nombre": {"required": True}}
        errors = validate_form({}, rules)
        assert len(errors) == 1
        assert "nombre" in errors[0].lower()
```

---

## 5. Tests de Repositorios (con Mock)

```python
# tests/unit/test_repositories.py
import pytest
from unittest.mock import MagicMock
from repositories.proveedor_repository import ProveedorRepository

class TestProveedorRepository:
    
    def test_get_all_retorna_lista(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
            {"id": 1, "nombre": "Proveedor 1"},
            {"id": 2, "nombre": "Proveedor 2"},
        ]
        repo = ProveedorRepository(mock_supabase)
        result = repo.get_all()
        assert len(result) == 2
        assert result[0]["nombre"] == "Proveedor 1"
    
    def test_create_retorna_registro(self, mock_supabase, proveedor_data):
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {**proveedor_data, "id": 1}
        ]
        repo = ProveedorRepository(mock_supabase)
        result = repo.create(proveedor_data)
        assert result["id"] == 1
        assert result["nombre"] == proveedor_data["nombre"]
    
    def test_delete_llama_supabase(self, mock_supabase):
        repo = ProveedorRepository(mock_supabase)
        repo.delete(1)
        mock_supabase.table.assert_called_with("proveedores")
    
    def test_search_usa_ilike(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value.data = []
        repo = ProveedorRepository(mock_supabase)
        repo.search("ABC")
        mock_supabase.table.return_value.select.return_value.ilike.assert_called_with("nombre", "%ABC%")
```

---

## 6. Comandos para Ejecutar Tests

```bash
# Correr todos los tests
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ --cov=. --cov-report=html

# Solo tests unitarios
pytest tests/unit/ -v

# Test específico
pytest tests/unit/test_validators.py::TestValidateRIF::test_rif_valido_empresa -v

# Ver cobertura en terminal
pytest tests/ --cov=. --cov-report=term-missing
```

---

## 7. Reglas de Testing para este Proyecto

1. **Todo validador** debe tener test: caso válido + caso inválido + campo vacío
2. **Todo repository** debe tener test con mock de Supabase
3. **Nunca** correr tests de integración contra la DB de producción
4. **Mínimo 70%** de cobertura en `utils/` y `repositories/`
5. **Nombrado:** `test_[funcion]_[escenario]` → `test_create_proveedor_duplicado`
6. **Un assert por test** cuando sea posible
7. **Fixtures** para datos de prueba, nunca hardcodear en el test
