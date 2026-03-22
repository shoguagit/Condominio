"""
Envío de correo vía Gmail SMTP (lógica pura, sin BD).
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


@dataclass
class EmailConfig:
    smtp_email: str
    app_password: str
    nombre_remitente: str


@dataclass
class EmailMessage:
    destinatario_email: str
    destinatario_nombre: str
    asunto: str
    cuerpo: str


def _app_password_normalizado(app_password: str) -> str:
    return (app_password or "").replace(" ", "").strip()


def validar_config_smtp(config: EmailConfig) -> list[str]:
    """
    Lista vacía = válida. No lanza excepciones.
    """
    errores: list[str] = []
    email = (config.smtp_email or "").strip()
    if not email:
        errores.append("El correo Gmail del administrador es obligatorio.")
    elif "@gmail.com" not in email.lower():
        errores.append("Debe usar una cuenta de correo @gmail.com para esta integración.")

    pwd = _app_password_normalizado(config.app_password or "")
    if not pwd:
        errores.append("La App Password de Gmail es obligatoria.")
    elif len(pwd) < 16:
        errores.append("La App Password debe tener al menos 16 caracteres (sin contar espacios).")

    nombre = (config.nombre_remitente or "").strip()
    if not nombre:
        errores.append("El nombre del remitente es obligatorio.")

    return errores


def plantilla_correo_mora_editor_base(
    condominio_nombre: str,
    periodo_mmyy: str,
) -> dict:
    """
    Asunto y cuerpo iniciales para el editor, con marcadores
    [Nombre del propietario], [Unidad], [Periodo], [Meses], [Saldo], [USD].
    """
    cn = (condominio_nombre or "—").strip()
    per = (periodo_mmyy or "—").strip()
    asunto = f"Aviso de deuda pendiente — [Unidad] — {cn}"
    cuerpo = f"""Estimado/a [Nombre del propietario],

Le informamos que su unidad [Unidad] presenta una deuda pendiente con el condominio {cn}.

Detalle:
- Período: [Periodo]
- Meses de atraso: [Meses]
- Saldo adeudado: Bs. [Saldo] (≈ USD [USD] según tasa BCV al envío)

Le solicitamos regularizar su situación a la brevedad.
Para consultas, comuníquese con la administración.

Atentamente,
{cn}
"""
    return {"asunto": asunto, "cuerpo": cuerpo}


def generar_plantilla_mora(
    condominio_nombre: str,
    propietario_nombre: str,
    unidad_codigo: str,
    periodo: str,
    saldo_bs: float,
    meses_atraso: int,
    tasa_cambio: float,
) -> dict:
    """
    Texto plano. periodo en formato MM/YYYY para el cuerpo.
    """
    cn = (condominio_nombre or "—").strip()
    pn = (propietario_nombre or "—").strip()
    uc = (unidad_codigo or "—").strip()
    per = (periodo or "—").strip()
    sb = float(saldo_bs or 0)
    ma = int(meses_atraso or 0)
    tasa = float(tasa_cambio or 0)

    if tasa > 0:
        usd_equiv = sb / tasa
        saldo_linea_usd = f"(≈ USD {usd_equiv:,.2f} a tasa BCV)"
    else:
        saldo_linea_usd = "(≈ USD N/D — tasa BCV no disponible)"

    asunto = f"Aviso de deuda pendiente — {uc} — {cn}"

    cuerpo = f"""Estimado/a {pn},

Le informamos que su unidad {uc} presenta una deuda pendiente con el condominio {cn}.

Detalle:
- Período: {per}
- Meses de atraso: {ma}
- Saldo adeudado: Bs. {sb:,.2f}
  {saldo_linea_usd}

Le solicitamos regularizar su situación a la brevedad.
Para consultas, comuníquese con la administración.

Atentamente,
{cn}
"""
    return {"asunto": asunto, "cuerpo": cuerpo}


def texto_linea_saldo_usd(saldo_bs: float, tasa_cambio: float) -> str:
    tasa = float(tasa_cambio or 0)
    sb = float(saldo_bs or 0)
    if tasa > 0:
        return f"≈ USD {sb / tasa:,.2f} a tasa BCV"
    return "≈ USD N/D (tasa BCV no disponible)"


def plantilla_mora_marcadores_inicial() -> dict[str, str]:
    """
    Texto inicial del editor (primera carga) con marcadores {{clave}}
    alineados al tono de generar_plantilla_mora.
    """
    asunto = "Aviso de deuda pendiente — {{unidad_codigo}} — {{condominio_nombre}}"
    cuerpo = """Estimado/a {{propietario_nombre}},

Le informamos que su unidad {{unidad_codigo}} presenta una deuda pendiente con el condominio {{condominio_nombre}}.

Detalle:
- Período: {{periodo}}
- Meses de atraso: {{meses_atraso}}
- Saldo adeudado: Bs. {{saldo_bs}} ({{saldo_usd_linea}})

Le solicitamos regularizar su situación a la brevedad.
Para consultas, comuníquese con la administración.

Atentamente,
{{condominio_nombre}}
"""
    return {"asunto": asunto, "cuerpo": cuerpo}


def sustituir_marcadores_plantilla(texto: str, valores: dict[str, str]) -> str:
    """Reemplaza {{clave}} por valores (orden no importa)."""
    out = texto or ""
    for k, v in valores.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def enviar_correo(config: EmailConfig, mensaje: EmailMessage) -> dict:
    """
    Envía un correo vía Gmail SMTP.
    Retorna: {'exito': bool, 'error': str | None}
    Nunca propaga excepciones.
    """
    try:
        dest = (mensaje.destinatario_email or "").strip()
        if not dest:
            return {"exito": False, "error": "Sin correo registrado"}

        errs = validar_config_smtp(config)
        if errs:
            return {"exito": False, "error": "; ".join(errs)}

        msg = MIMEMultipart()
        msg["Subject"] = (mensaje.asunto or "").strip() or "Notificación"
        msg["From"] = f"{(config.nombre_remitente or '').strip()} <{config.smtp_email.strip()}>"
        msg["To"] = dest
        msg.attach(MIMEText(mensaje.cuerpo or "", "plain", "utf-8"))

        pwd = _app_password_normalizado(config.app_password)
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(config.smtp_email.strip(), pwd)
            server.sendmail(
                config.smtp_email.strip(),
                [dest],
                msg.as_string(),
            )
        return {"exito": True, "error": None}
    except Exception as e:  # noqa: BLE001 — contrato: nunca propagar
        return {"exito": False, "error": str(e)}
