import logging
from functools import wraps

# Streamlit se importa de forma lazy para que los tests unitarios
# puedan importar este módulo sin necesitar Streamlit instalado.
try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    st = None  # type: ignore[assignment]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CondominioError(Exception):
    """Error base del sistema."""


class DatabaseError(CondominioError):
    """Error de base de datos."""


class ValidationError(CondominioError):
    """Error de validación de datos."""


class AuthError(CondominioError):
    """Error de autenticación."""


def safe_db_operation(operation_name: str):
    """Decorador para operaciones de base de datos con manejo de errores unificado."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except CondominioError:
                # Errores propios del dominio se propagan sin re-envolver
                raise
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error en {operation_name}: {error_msg}")

                if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                    raise DatabaseError(
                        "Ya existe un registro con esos datos. Verifique el documento o nombre."
                    )
                elif "foreign key" in error_msg.lower():
                    raise DatabaseError(
                        "No se puede eliminar porque tiene registros asociados."
                    )
                elif "not null" in error_msg.lower():
                    raise DatabaseError("Faltan campos obligatorios.")
                elif (
                    "22003" in error_msg
                    or ("numeric" in error_msg.lower() and "overflow" in error_msg.lower())
                    or "numeric field overflow" in error_msg.lower()
                ):
                    raise DatabaseError(
                        "Un valor numérico supera lo permitido en la base de datos. "
                        "Si editó el indiviso a 100%, ejecute en Supabase el script "
                        "scripts/fase2_migration.sql (ALTER indiviso_pct a NUMERIC(8,4))."
                    )
                elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                    raise DatabaseError("Error de conexión. Verifique su internet.")
                else:
                    raise DatabaseError(f"Error en {operation_name}: {error_msg}")
        return wrapper
    return decorator


def handle_create(data: dict, repo) -> None:
    """Ejecuta la creación de un registro mostrando feedback en Streamlit."""
    try:
        repo.create(data)
        st.success("✅ Registro creado exitosamente.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {e}")
    except ValidationError as e:
        st.warning(f"⚠️ {e}")
    except Exception as e:
        st.error("❌ Error inesperado. Contacte al administrador.")
        logger.error(f"Error no controlado en create: {e}")


def handle_update(record_id: int, data: dict, repo) -> None:
    """Ejecuta la actualización de un registro mostrando feedback en Streamlit."""
    try:
        repo.update(record_id, data)
        st.success("✅ Registro actualizado correctamente.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {e}")
    except Exception as e:
        st.error("❌ Error inesperado al actualizar.")
        logger.error(f"Error no controlado en update: {e}")


def handle_delete(record_id: int, repo, nombre: str = "el registro") -> None:
    """Ejecuta la eliminación de un registro mostrando feedback en Streamlit."""
    try:
        repo.delete(record_id)
        st.success(f"✅ {nombre} eliminado correctamente.")
        st.rerun()
    except DatabaseError as e:
        st.error(f"❌ {e}")
    except Exception as e:
        st.error("❌ No se pudo eliminar.")
        logger.error(f"Error no controlado en delete: {e}")


def confirm_delete_dialog(nombre: str, key: str) -> bool:
    """
    Muestra un diálogo de confirmación antes de eliminar.
    Retorna True si el usuario confirma la eliminación.
    """
    state_key = f"confirm_delete_{key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False

    if st.button("🗑 Eliminar", key=f"btn_delete_{key}", type="secondary"):
        st.session_state[state_key] = True

    if st.session_state[state_key]:
        st.warning(
            f"⚠️ ¿Está seguro que desea eliminar **{nombre}**? Esta acción no se puede deshacer."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Sí, eliminar", key=f"yes_{key}", type="primary"):
                return True
        with col2:
            if st.button("❌ Cancelar", key=f"no_{key}"):
                st.session_state[state_key] = False
    return False
