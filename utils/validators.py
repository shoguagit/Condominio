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
