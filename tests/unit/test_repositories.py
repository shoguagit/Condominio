"""
Tests unitarios para repositories/ usando Supabase mockeado.
Cubre: ProveedorRepository, CondominioRepository, UsuarioRepository.
"""
import pytest
from unittest.mock import MagicMock, call

from repositories.proveedor_repository import ProveedorRepository
from repositories.condominio_repository import CondominioRepository
from repositories.usuario_repository import UsuarioRepository
from repositories.factura_repository import FacturaRepository
from utils.error_handler import DatabaseError, AuthError


# =============================================================================
# TestProveedorRepository
# =============================================================================

class TestProveedorRepository:

    # ── get_all ───────────────────────────────────────────────────────────────

    def test_get_all_retorna_lista(self, mock_supabase, mock_chain, proveedor_data):
        mock_chain.execute.return_value.data = [proveedor_data]
        repo = ProveedorRepository(mock_supabase)
        result = repo.get_all(condominio_id=1)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["nombre"] == proveedor_data["nombre"]

    def test_get_all_filtra_por_condominio(self, mock_supabase, mock_chain):
        mock_chain.execute.return_value.data = []
        repo = ProveedorRepository(mock_supabase)
        repo.get_all(condominio_id=5)
        mock_chain.eq.assert_any_call("condominio_id", 5)

    def test_get_all_solo_activos(self, mock_supabase, mock_chain):
        mock_chain.execute.return_value.data = []
        repo = ProveedorRepository(mock_supabase)
        repo.get_all(condominio_id=1, solo_activos=True)
        mock_chain.eq.assert_any_call("activo", True)

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_retorna_registro_creado(self, mock_supabase, mock_chain, proveedor_data):
        mock_chain.execute.return_value.data = [{**proveedor_data, "id": 99}]
        repo = ProveedorRepository(mock_supabase)
        result = repo.create(proveedor_data)
        assert result["id"] == 99
        assert result["nombre"] == proveedor_data["nombre"]

    def test_create_llama_insert(self, mock_supabase, mock_chain, proveedor_data):
        mock_chain.execute.return_value.data = [proveedor_data]
        repo = ProveedorRepository(mock_supabase)
        repo.create(proveedor_data)
        mock_supabase.table.assert_called_with("proveedores")
        mock_chain.insert.assert_called_once_with(proveedor_data)

    # ── update ────────────────────────────────────────────────────────────────

    def test_update_retorna_registro_actualizado(self, mock_supabase, mock_chain, proveedor_data):
        updated = {**proveedor_data, "nombre": "Nuevo Nombre SA"}
        mock_chain.execute.return_value.data = [updated]
        repo = ProveedorRepository(mock_supabase)
        result = repo.update(1, {"nombre": "Nuevo Nombre SA"})
        assert result["nombre"] == "Nuevo Nombre SA"

    def test_update_filtra_por_id(self, mock_supabase, mock_chain, proveedor_data):
        mock_chain.execute.return_value.data = [proveedor_data]
        repo = ProveedorRepository(mock_supabase)
        repo.update(42, {"nombre": "X"})
        mock_chain.eq.assert_any_call("id", 42)

    # ── delete ────────────────────────────────────────────────────────────────

    def test_delete_llama_tabla_correcta(self, mock_supabase, mock_chain):
        repo = ProveedorRepository(mock_supabase)
        result = repo.delete(1)
        mock_supabase.table.assert_called_with("proveedores")
        assert result is True

    def test_delete_filtra_por_id(self, mock_supabase, mock_chain):
        repo = ProveedorRepository(mock_supabase)
        repo.delete(7)
        mock_chain.eq.assert_called_with("id", 7)

    # ── search ────────────────────────────────────────────────────────────────

    def test_search_usa_ilike_sobre_nombre(self, mock_supabase, mock_chain):
        mock_chain.execute.return_value.data = []
        repo = ProveedorRepository(mock_supabase)
        repo.search(condominio_id=1, term="Técnicos")
        mock_chain.ilike.assert_called_with("nombre", "%Técnicos%")

    def test_search_retorna_lista(self, mock_supabase, mock_chain, proveedor_data):
        mock_chain.execute.return_value.data = [proveedor_data]
        repo = ProveedorRepository(mock_supabase)
        result = repo.search(condominio_id=1, term="Servicios")
        assert isinstance(result, list)

    # ── toggle_activo ─────────────────────────────────────────────────────────

    def test_toggle_activo_desactiva(self, mock_supabase, mock_chain, proveedor_data):
        mock_chain.execute.return_value.data = [{**proveedor_data, "activo": False}]
        repo = ProveedorRepository(mock_supabase)
        result = repo.toggle_activo(1, False)
        assert result["activo"] is False

    def test_toggle_activo_llama_update_con_campo_correcto(self, mock_supabase, mock_chain, proveedor_data):
        mock_chain.execute.return_value.data = [proveedor_data]
        repo = ProveedorRepository(mock_supabase)
        repo.toggle_activo(1, True)
        mock_chain.update.assert_called_with({"activo": True})


# =============================================================================
# TestCondominioRepository
# =============================================================================

class TestCondominioRepository:

    def test_get_all_retorna_lista(self, mock_supabase, mock_chain, condominio_data):
        mock_chain.execute.return_value.data = [condominio_data]
        repo = CondominioRepository(mock_supabase)
        result = repo.get_all()
        assert len(result) == 1
        assert result[0]["nombre"] == condominio_data["nombre"]

    def test_get_all_solo_activos_aplica_filtro(self, mock_supabase, mock_chain):
        mock_chain.execute.return_value.data = []
        repo = CondominioRepository(mock_supabase)
        repo.get_all(solo_activos=True)
        mock_chain.eq.assert_any_call("activo", True)

    def test_create_con_documento(self, mock_supabase, mock_chain, condominio_data):
        mock_chain.execute.return_value.data = [{**condominio_data, "id": 10}]
        repo = CondominioRepository(mock_supabase)
        result = repo.create(condominio_data)
        assert result["id"] == 10
        assert result["numero_documento"] == "J-12345678-9"

    def test_create_llama_insert(self, mock_supabase, mock_chain, condominio_data):
        mock_chain.execute.return_value.data = [condominio_data]
        repo = CondominioRepository(mock_supabase)
        repo.create(condominio_data)
        mock_chain.insert.assert_called_once_with(condominio_data)

    def test_get_by_id_retorna_dict(self, mock_supabase, mock_chain, condominio_data):
        mock_chain.execute.return_value.data = condominio_data
        repo = CondominioRepository(mock_supabase)
        result = repo.get_by_id(1)
        assert result["nombre"] == condominio_data["nombre"]

    def test_search_usa_ilike(self, mock_supabase, mock_chain, condominio_data):
        mock_chain.execute.return_value.data = [condominio_data]
        repo = CondominioRepository(mock_supabase)
        repo.search("Parque")
        mock_chain.ilike.assert_called_with("nombre", "%Parque%")

    def test_delete_retorna_true(self, mock_supabase, mock_chain):
        repo = CondominioRepository(mock_supabase)
        result = repo.delete(1)
        assert result is True

    def test_toggle_activo_llama_tabla_condominios(self, mock_supabase, mock_chain, condominio_data):
        mock_chain.execute.return_value.data = [condominio_data]
        repo = CondominioRepository(mock_supabase)
        repo.toggle_activo(1, False)
        mock_supabase.table.assert_called_with("condominios")

    def test_update_filtra_por_id(self, mock_supabase, mock_chain, condominio_data):
        mock_chain.execute.return_value.data = [condominio_data]
        repo = CondominioRepository(mock_supabase)
        repo.update(3, {"nombre": "Nuevo"})
        mock_chain.eq.assert_any_call("id", 3)


# =============================================================================
# TestUsuarioRepository
# =============================================================================

class TestUsuarioRepository:

    def test_get_all_retorna_lista(self, mock_supabase, mock_chain, usuario_data):
        mock_chain.execute.return_value.data = [usuario_data]
        repo = UsuarioRepository(mock_supabase)
        result = repo.get_all(condominio_id=1)
        assert len(result) == 1
        assert result[0]["email"] == usuario_data["email"]

    def test_get_by_condominio_filtra_activos(self, mock_supabase, mock_chain):
        mock_chain.execute.return_value.data = []
        repo = UsuarioRepository(mock_supabase)
        repo.get_by_condominio(condominio_id=1)
        mock_chain.eq.assert_any_call("activo", True)

    def test_create_registra_en_auth(self, mock_supabase, mock_chain, usuario_data):
        """Verifica que create() llama a supabase.auth.admin.create_user."""
        mock_chain.execute.return_value.data = [usuario_data]
        repo = UsuarioRepository(mock_supabase)
        repo.create(usuario_data, password="secret123")
        mock_supabase.auth.admin.create_user.assert_called_once()

    def test_create_inserta_en_tabla(self, mock_supabase, mock_chain, usuario_data):
        mock_chain.execute.return_value.data = [usuario_data]
        repo = UsuarioRepository(mock_supabase)
        repo.create(usuario_data, password="secret123")
        mock_supabase.table.assert_called_with("usuarios")
        mock_chain.insert.assert_called_once()

    def test_create_no_incluye_password_en_insert(self, mock_supabase, mock_chain, usuario_data):
        """La contraseña no debe guardarse en la tabla usuarios."""
        data_con_pass = {**usuario_data, "password": "secret123"}
        mock_chain.execute.return_value.data = [usuario_data]
        repo = UsuarioRepository(mock_supabase)
        repo.create(data_con_pass, password="secret123")
        inserted_payload = mock_chain.insert.call_args[0][0]
        assert "password" not in inserted_payload

    def test_toggle_activo_desactiva_usuario(self, mock_supabase, mock_chain, usuario_data):
        mock_chain.execute.return_value.data = [{**usuario_data, "activo": False}]
        repo = UsuarioRepository(mock_supabase)
        result = repo.toggle_activo(1, False)
        assert result["activo"] is False

    def test_toggle_activo_llama_update_con_activo(self, mock_supabase, mock_chain, usuario_data):
        mock_chain.execute.return_value.data = [usuario_data]
        repo = UsuarioRepository(mock_supabase)
        repo.toggle_activo(1, True)
        mock_chain.update.assert_called_with({"activo": True})

    def test_update_no_incluye_password(self, mock_supabase, mock_chain, usuario_data):
        """update() debe ignorar el campo password si viene en el dict."""
        mock_chain.execute.return_value.data = [usuario_data]
        repo = UsuarioRepository(mock_supabase)
        repo.update(1, {"nombre": "Nuevo Nombre", "password": "DEBE_IGNORARSE"})
        updated_payload = mock_chain.update.call_args[0][0]
        assert "password" not in updated_payload

    def test_change_password_llama_list_users(self, mock_supabase, mock_chain):
        """change_password busca el auth_user por email."""
        auth_user = MagicMock()
        auth_user.email = "admin@sistema.com"
        auth_user.id    = "uuid-abc-123"
        mock_supabase.auth.admin.list_users.return_value = [auth_user]
        repo = UsuarioRepository(mock_supabase)
        result = repo.change_password("admin@sistema.com", "nuevapass123")
        mock_supabase.auth.admin.list_users.assert_called_once()
        assert result is True

    def test_change_password_usuario_no_encontrado_lanza_error(self, mock_supabase):
        mock_supabase.auth.admin.list_users.return_value = []
        repo = UsuarioRepository(mock_supabase)
        with pytest.raises(AuthError):
            repo.change_password("noexiste@email.com", "pass123")


# =============================================================================
# TestFacturaRepository
# =============================================================================

class TestFacturaRepository:

    def test_get_all_retorna_lista(self, mock_supabase, mock_chain, factura_data):
        mock_chain.execute.return_value.data = [factura_data]
        repo = FacturaRepository(mock_supabase)
        result = repo.get_all(condominio_id=1)
        assert len(result) == 1
        assert result[0]["numero"] == factura_data["numero"]

    def test_get_by_mes_proceso_filtra_por_mes(self, mock_supabase, mock_chain):
        mock_chain.execute.return_value.data = []
        repo = FacturaRepository(mock_supabase)
        repo.get_by_mes_proceso(condominio_id=1, mes_proceso="2026-03-01")
        mock_chain.eq.assert_any_call("mes_proceso", "2026-03-01")

    def test_create_retorna_factura(self, mock_supabase, mock_chain, factura_data):
        mock_chain.execute.return_value.data = [{**factura_data, "id": 55}]
        repo = FacturaRepository(mock_supabase)
        result = repo.create(factura_data)
        assert result["id"] == 55

    def test_delete_retorna_true(self, mock_supabase, mock_chain):
        repo = FacturaRepository(mock_supabase)
        result = repo.delete(1)
        assert result is True

    def test_registrar_pago_suma_al_pagado(self, mock_supabase, mock_chain, factura_data):
        """registrar_pago debe sumar el monto al campo pagado existente."""
        factura_inicial = {**factura_data, "pagado": 200.0}
        factura_actualizada = {**factura_data, "pagado": 350.0}

        # Primera llamada (get_by_id) devuelve la factura inicial
        # Segunda llamada (update) devuelve la factura actualizada
        mock_chain.execute.side_effect = [
            MagicMock(data=factura_inicial),
            MagicMock(data=[factura_actualizada]),
        ]
        repo = FacturaRepository(mock_supabase)
        result = repo.registrar_pago(factura_id=1, monto_pago=150.0)
        # Verifica que update fue llamado con pagado = 200 + 150 = 350
        mock_chain.update.assert_called_with({"pagado": 350.0})
