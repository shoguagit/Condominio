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
    """Valida formato de correo electrónico."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if email and not re.match(pattern, email):
        return False, "Formato de email inválido"
    return True, ""


def validate_required(value, field_name: str) -> tuple[bool, str]:
    """Valida que un campo no esté vacío. El valor numérico 0 se considera válido."""
    if value is None:
        return False, f"El campo '{field_name}' es obligatorio"
    if isinstance(value, str) and not value.strip():
        return False, f"El campo '{field_name}' es obligatorio"
    if isinstance(value, (list, tuple, dict)) and len(value) == 0:
        return False, f"El campo '{field_name}' es obligatorio"
    return True, ""


def validate_form(data: dict, rules: dict) -> list[str]:
    """
    Valida un formulario completo según reglas definidas.

    Ejemplo de rules:
        {
            "nombre": {"required": True, "max_length": 200},
            "rif":    {"required": True,  "type": "rif"},
            "email":  {"required": False, "type": "email"},
        }

    Retorna lista de mensajes de error (vacía = formulario válido).
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
                errors.append(
                    f"El campo '{field}' no puede superar {rule['max_length']} caracteres"
                )

    return errors


def validate_periodo(periodo_str: str) -> tuple[bool, str]:
    """Valida formato MM/YYYY"""
    if not periodo_str:
        return False, "El período es obligatorio"
    if not re.match(r"^\d{2}/\d{4}$", periodo_str):
        return False, "Formato debe ser MM/YYYY"
    return True, ""


def validate_alicuota_valor(valor: float) -> tuple[bool, str]:
    """Valida que alícuota esté entre 0.001 y 1.000"""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return False, "Alícuota debe estar entre 0.001 y 1.000"
    if not (0.001 <= v <= 1.0):
        return False, "Alícuota debe estar entre 0.001 y 1.000"
    return True, ""


def validate_suma_alicuotas(valores: list[float]) -> tuple[bool, str]:
    """Valida que la suma sea aproximadamente 1.00 (tolerancia ±0.01)"""
    try:
        total = float(sum(float(v or 0) for v in valores))
    except (TypeError, ValueError):
        return False, "La suma de alícuotas es inválida"
    if abs(total - 1.0) > 0.01:
        return False, f"La suma de alícuotas es {total:.4f}, debe ser ≈ 1.00"
    return True, ""


def validate_telefono_venezolano(tel: str) -> tuple[bool, str]:
    """Valida teléfono móvil venezolano: debe iniciar con '04'"""
    if not tel:
        return True, ""
    if not str(tel).startswith("04"):
        return False, "El teléfono debe iniciar con 04"
    return True, ""
