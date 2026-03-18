"""
Tests unitarios para utils/validators.py
Cobertura: validate_rif, validate_email, validate_required, validate_form
"""
import pytest

from utils.validators import validate_rif, validate_email, validate_required, validate_form


# =============================================================================
# validate_rif
# =============================================================================

class TestValidateRIF:

    # ── Casos válidos ─────────────────────────────────────────────────────────

    def test_rif_valido_empresa_j(self):
        ok, msg = validate_rif("J-12345678-9")
        assert ok is True
        assert msg == ""

    def test_rif_valido_persona_v(self):
        ok, msg = validate_rif("V-12345678-0")
        assert ok is True

    def test_rif_valido_persona_e(self):
        ok, msg = validate_rif("E-12345678-3")
        assert ok is True

    def test_rif_valido_gobierno_g(self):
        ok, msg = validate_rif("G-20004100-8")
        assert ok is True

    def test_rif_valido_comunidad_c(self):
        ok, msg = validate_rif("C-12345678-0")
        assert ok is True

    def test_rif_acepta_minusculas(self):
        """La función debe normalizar a mayúsculas antes de validar."""
        ok, msg = validate_rif("j-12345678-9")
        assert ok is True

    # ── Casos inválidos ───────────────────────────────────────────────────────

    def test_rif_vacio_retorna_error(self):
        ok, msg = validate_rif("")
        assert ok is False
        assert "obligatorio" in msg.lower()

    def test_rif_sin_guiones(self):
        ok, msg = validate_rif("J123456789")
        assert ok is False
        assert "inválido" in msg.lower()

    def test_rif_tipo_x_invalido(self):
        ok, msg = validate_rif("X-12345678-9")
        assert ok is False

    def test_rif_demasiados_digitos(self):
        ok, msg = validate_rif("J-123456789-9")
        assert ok is False

    def test_rif_pocos_digitos(self):
        ok, msg = validate_rif("J-1234567-9")
        assert ok is False

    def test_rif_solo_letras(self):
        ok, msg = validate_rif("JXXXXXXXXX")
        assert ok is False

    def test_rif_none_retorna_error(self):
        ok, msg = validate_rif(None)
        assert ok is False


# =============================================================================
# validate_email
# =============================================================================

class TestValidateEmail:

    # ── Casos válidos ─────────────────────────────────────────────────────────

    def test_email_valido_simple(self):
        ok, _ = validate_email("admin@condominio.com")
        assert ok is True

    def test_email_valido_con_punto(self):
        ok, _ = validate_email("juan.perez@empresa.com.ve")
        assert ok is True

    def test_email_valido_con_mas(self):
        ok, _ = validate_email("admin+test@condominio.org")
        assert ok is True

    def test_email_vacio_es_valido(self):
        """Email vacío es válido porque el campo no siempre es obligatorio."""
        ok, _ = validate_email("")
        assert ok is True

    def test_email_none_es_valido(self):
        ok, _ = validate_email(None)
        assert ok is True

    # ── Casos inválidos ───────────────────────────────────────────────────────

    def test_email_sin_arroba(self):
        ok, msg = validate_email("nodomain.com")
        assert ok is False
        assert "inválido" in msg.lower()

    def test_email_sin_dominio(self):
        ok, msg = validate_email("usuario@")
        assert ok is False

    def test_email_sin_tld(self):
        ok, msg = validate_email("usuario@dominio")
        assert ok is False

    def test_email_con_espacios(self):
        ok, msg = validate_email("usuario @dominio.com")
        assert ok is False


# =============================================================================
# validate_required
# =============================================================================

class TestValidateRequired:

    def test_campo_con_valor_es_valido(self):
        ok, _ = validate_required("Residencias El Parque", "nombre")
        assert ok is True

    def test_campo_vacio_string_falla(self):
        ok, msg = validate_required("", "nombre")
        assert ok is False
        assert "nombre" in msg.lower()

    def test_campo_solo_espacios_falla(self):
        ok, msg = validate_required("   ", "direccion")
        assert ok is False
        assert "direccion" in msg.lower()

    def test_campo_none_falla(self):
        ok, msg = validate_required(None, "rif")
        assert ok is False

    def test_campo_cero_es_valido(self):
        """El valor 0 (numérico) no es vacío."""
        ok, _ = validate_required(0, "monto")
        assert ok is True

    def test_campo_lista_no_vacia_es_valido(self):
        ok, _ = validate_required([1, 2], "ids")
        assert ok is True


# =============================================================================
# validate_form
# =============================================================================

class TestValidateForm:

    def test_form_completo_sin_errores(self, proveedor_data):
        rules = {
            "nombre":           {"required": True,  "max_length": 200},
            "numero_documento": {"required": True,  "type": "rif"},
            "correo":           {"required": False, "type": "email"},
        }
        errors = validate_form(proveedor_data, rules)
        assert errors == []

    def test_form_nombre_faltante(self):
        rules = {"nombre": {"required": True}}
        errors = validate_form({}, rules)
        assert len(errors) == 1
        assert "nombre" in errors[0].lower()

    def test_form_multiples_errores(self):
        rules = {
            "nombre":    {"required": True},
            "direccion": {"required": True},
        }
        errors = validate_form({"nombre": "", "direccion": ""}, rules)
        assert len(errors) == 2

    def test_form_rif_invalido_genera_error(self):
        rules = {"numero_documento": {"required": True, "type": "rif"}}
        errors = validate_form({"numero_documento": "NO-ES-RIF"}, rules)
        assert len(errors) == 1

    def test_form_email_invalido_genera_error(self):
        rules = {"correo": {"required": False, "type": "email"}}
        errors = validate_form({"correo": "noesemail"}, rules)
        assert len(errors) == 1

    def test_form_campo_supera_max_length(self):
        rules = {"nombre": {"required": True, "max_length": 5}}
        errors = validate_form({"nombre": "Nombre muy largo"}, rules)
        assert len(errors) == 1
        assert "5" in errors[0]

    def test_form_campo_opcional_vacio_no_genera_error(self):
        rules = {"correo": {"required": False, "type": "email"}}
        errors = validate_form({"correo": ""}, rules)
        assert errors == []

    def test_form_vacío_con_reglas_opcionales_no_genera_errores(self):
        rules = {
            "telefono": {"required": False},
            "notas":    {"required": False},
        }
        errors = validate_form({}, rules)
        assert errors == []

    def test_form_condominio_completo(self, condominio_data):
        rules = {
            "nombre":           {"required": True,  "max_length": 200},
            "direccion":        {"required": True},
            "numero_documento": {"required": True},
            "email":            {"required": False, "type": "email"},
        }
        errors = validate_form(condominio_data, rules)
        assert errors == []
