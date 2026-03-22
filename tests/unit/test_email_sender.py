"""Tests de utilidades de correo (sin envío SMTP real)."""

from utils.email_sender import EmailConfig, generar_plantilla_mora, validar_config_smtp


def test_validar_config_smtp_correcta():
    config = EmailConfig("admin@gmail.com", "abcd efgh ijkl mnop", "Admin")
    assert validar_config_smtp(config) == []


def test_validar_smtp_email_no_gmail():
    config = EmailConfig("admin@outlook.com", "abcdabcdabcdabcd", "Admin")
    errores = validar_config_smtp(config)
    assert any("gmail" in e.lower() for e in errores)


def test_validar_smtp_password_corta():
    config = EmailConfig("admin@gmail.com", "corta", "Admin")
    errores = validar_config_smtp(config)
    assert any("password" in e.lower() or "16" in e for e in errores)


def test_generar_plantilla_mora_contiene_datos():
    resultado = generar_plantilla_mora(
        "Condominio Test",
        "Juan Pérez",
        "Apto 1A",
        "03/2026",
        252000.0,
        2,
        455.25,
    )
    assert "Juan Pérez" in resultado["cuerpo"]
    assert "Apto 1A" in resultado["cuerpo"]
    assert "252" in resultado["cuerpo"]


def test_generar_plantilla_asunto_contiene_unidad():
    resultado = generar_plantilla_mora(
        "Condo X", "Ana", "Casa 5", "03/2026", 100000.0, 1, 455.25
    )
    assert "Casa 5" in resultado["asunto"]
