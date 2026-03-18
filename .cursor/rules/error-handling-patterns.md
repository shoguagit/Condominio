# Skill: Error Handling Patterns — Python + Supabase + Streamlit
## Propósito
Garantizar manejo robusto y consistente de errores en todo el sistema de condominio.

---

## 1. Wrapper Global para Operaciones Supabase

```python
# utils/error_handler.py
import streamlit as st
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CondominioError(Exception):
    """Error base del sistema"""
    pass

class DatabaseError(CondominioError):
    """Error de base de datos"""
    pass

class ValidationError(CondominioError):
    """Error de validación de datos"""
    pass

class AuthError(CondominioError):
    """Error de autenticación"""
    pass

def safe_db_operation(operation_name: str):
    """Decorador para operaciones de base de datos"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error en {operation_name}: {error_msg}")
                
                # Clasificar el error para el usuario
                if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                    raise DatabaseError(f"Ya existe un registro con esos datos. Verifique el documento o nombre.")
                elif "foreign key" in error_msg.lower():
                    raise DatabaseError(f"No se puede eliminar porque tiene registros asociados.")
                elif "not null" in error_msg.lower():
                    raise DatabaseError(f"Faltan campos obligatorios.")
                elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                    raise DatabaseError(f"Error de conexión. Verifique su internet.")
                else:
                    raise DatabaseError(f"Error en {operation_name}: {error_msg}")
        return wrapper
    return decorator
```

---

## 2. Manejo de Errores en Streamlit (UI Layer)

```python
# Patrón estándar para CRUD en páginas Streamlit
def handle_create(data: dict, repo):
    try:
        result = repo.create(data)
        st.success(f"✅ Registro creado exitosamente.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {str(e)}")
    except ValidationError as e:
        st.warning(f"⚠️ {str(e)}")
    except Exception as e:
        st.error(f"❌ Error inesperado. Contacte al administrador.")
        logger.error(f"Error no controlado: {e}")

def handle_update(id: int, data: dict, repo):
    try:
        repo.update(id, data)
        st.success(f"✅ Registro actualizado correctamente.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {str(e)}")
    except Exception as e:
        st.error(f"❌ Error inesperado al actualizar.")
        logger.error(f"Error update: {e}")

def handle_delete(id: int, repo, nombre: str = "el registro"):
    try:
        repo.delete(id)
        st.success(f"✅ {nombre} eliminado correctamente.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {str(e)}")
    except Exception as e:
        st.error(f"❌ No se pudo eliminar.")
        logger.error(f"Error delete: {e}")
```

---

## 3. Validaciones de Formulario

```python
# utils/validators.py
import re

def validate_rif(rif: str) -> tuple[bool, str]:
    """Valida formato RIF venezolano: J-12345678-9"""
    pattern = r'^[VJGECP]-\d{8}-\d$'
    if not rif:
        return False, "El RIF es obligatorio"
    if not re.match(pattern, rif.upper()):
        return False, "Formato RIF inválido. Ejemplo: J-12345678-9"
    return True, ""

def validate_email(email: str) -> tuple[bool, str]:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if email and not re.match(pattern, email):
        return False, "Formato de email inválido"
    return True, ""

def validate_required(value, field_name: str) -> tuple[bool, str]:
    if not value or (isinstance(value, str) and not value.strip()):
        return False, f"El campo '{field_name}' es obligatorio"
    return True, ""

def validate_form(data: dict, rules: dict) -> list[str]:
    """
    rules = {
        "nombre": {"required": True, "max_length": 200},
        "rif": {"required": True, "type": "rif"},
        "email": {"required": False, "type": "email"},
    }
    Returns: lista de errores (vacía = válido)
    """
    errors = []
    for field, rule in rules.items():
        value = data.get(field)
        
        if rule.get("required"):
            ok, msg = validate_required(value, field)
            if not ok:
                errors.append(msg)
                continue
        
        if value:
            if rule.get("type") == "rif":
                ok, msg = validate_rif(value)
                if not ok:
                    errors.append(msg)
            elif rule.get("type") == "email":
                ok, msg = validate_email(value)
                if not ok:
                    errors.append(msg)
            
            if rule.get("max_length") and len(str(value)) > rule["max_length"]:
                errors.append(f"El campo '{field}' no puede superar {rule['max_length']} caracteres")
    
    return errors
```

---

## 4. Confirmación antes de Eliminar

```python
# Siempre usar diálogo de confirmación antes de DELETE
def confirm_delete_dialog(nombre: str, key: str):
    """
    Patrón estándar de confirmación de eliminación
    """
    if f"confirm_delete_{key}" not in st.session_state:
        st.session_state[f"confirm_delete_{key}"] = False
    
    if st.button(f"🗑 Eliminar", key=f"btn_delete_{key}", type="secondary"):
        st.session_state[f"confirm_delete_{key}"] = True
    
    if st.session_state[f"confirm_delete_{key}"]:
        st.warning(f"⚠️ ¿Está seguro que desea eliminar **{nombre}**? Esta acción no se puede deshacer.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Sí, eliminar", key=f"yes_{key}", type="primary"):
                return True
        with col2:
            if st.button("❌ Cancelar", key=f"no_{key}"):
                st.session_state[f"confirm_delete_{key}"] = False
    return False
```

---

## 5. Manejo de Sesión y Autenticación

```python
# utils/auth.py
def check_authentication():
    """Verificar sesión activa. Llamar al inicio de cada página."""
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("❌ Sesión no iniciada. Por favor inicie sesión.")
        st.stop()

def check_permission(required_role: str):
    """Verificar permisos por rol."""
    user_role = st.session_state.get("user_role", "consulta")
    role_hierarchy = {"admin": 3, "operador": 2, "consulta": 1}
    
    if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 99):
        st.error(f"❌ No tiene permisos para realizar esta acción.")
        st.stop()
```

---

## 6. Loading States Obligatorios

```python
# Siempre usar spinner en operaciones que contactan Supabase
with st.spinner("Cargando datos..."):
    data = repo.get_all()

with st.spinner("Guardando..."):
    handle_create(form_data, repo)

# Para carga inicial de página
@st.cache_data(ttl=300)  # Cache 5 minutos para datos estáticos
def load_paises():
    return pais_repo.get_all()
```
