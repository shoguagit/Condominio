"""
PDF estado de cuenta estilo recibo venezolano (Sisconin) — ReportLab.
No propaga excepciones: ante error devuelve PDF mínimo de aviso.
"""

from __future__ import annotations

import base64
import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

AZUL_CONDOMINIO = colors.HexColor("#1B4F8A")
AMARILLO_HEADER = colors.HexColor("#FFFACD")
GRIS_FILA = colors.HexColor("#F5F5F5")
GRIS_TOTAL = colors.HexColor("#E8E8E8")
BLANCO = colors.white
NEGRO = colors.black


def _esc(s: str) -> str:
    t = str(s or "")
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _fmt_usd(v: float) -> str:
    return f"${float(v):,.2f}"


def _logo_bytes_a_image(
    logo_input: bytes | str | None,
    ancho: float,
    alto: float,
) -> Any:
    """
    Convierte logo a Image de ReportLab.
    Acepta bytes de imagen cruda, data URL (str o bytes utf-8), o None.
    """
    if not logo_input:
        return None
    try:
        img_bytes: bytes
        if isinstance(logo_input, str):
            data = logo_input.strip()
            if data.startswith("data:"):
                if "," not in data:
                    return None
                _hdr, b64_data = data.split(",", 1)
                b64_data = b64_data.strip()
                pad = (-len(b64_data)) % 4
                if pad:
                    b64_data += "=" * pad
                img_bytes = base64.b64decode(b64_data)
            else:
                return None
        else:
            raw = logo_input
            if raw.startswith(b"data:"):
                s = raw.decode("utf-8", errors="ignore").strip()
                return _logo_bytes_a_image(s, ancho, alto)
            img_bytes = raw

        bio = io.BytesIO(img_bytes)
        return Image(ImageReader(bio), width=ancho, height=alto)
    except Exception:
        return None


def _pdf_error_bytes(msg: str = "Error al generar el documento") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    st = getSampleStyleSheet()
    doc.build([Paragraph(_esc(msg), st["Normal"])])
    return buf.getvalue()


def generar_estado_cuenta_pdf(
    condominio_nombre: str,
    condominio_rif: str,
    condominio_email: str,
    logo_bytes: bytes | str | None,
    pie_titular: str,
    pie_cuerpo: str,
    propietario_nombre: str,
    propietario_email: str,
    unidad_codigo: str,
    indiviso_pct: float,
    periodo_nombre: str,
    tasa_cambio: float,
    cuota_bs: float,
    cuota_usd: float,
    saldo_anterior_usd: float,
    mora_usd: float,
    cobros_ext_usd: float,
    pagos_recibidos_usd: float,
    saldo_actual_usd: float,
    fondo_reserva_usd: float,
    total_gastos_usd: float,
    acumulado_usd: float,
    meses_acumulados: int,
    gastos_detalle: list[dict[str, Any]],
    saldo_ant_edificio: float,
    deducciones_edificio: float,
    ingresos_edificio: float,
    saldo_act_edificio: float,
    emision_str: str = "",
    mes_corto: str = "",
    total_comun_usd: float = 0.0,
    **_: Any,
) -> bytes:
    """
    Genera PDF individual. Retorna bytes; nunca propaga excepciones.
    """
    try:
        mc = mes_corto or (periodo_nombre.split()[0] if periodo_nombre else "")
        return _generar_estado_cuenta_pdf_impl(
            condominio_nombre=condominio_nombre,
            condominio_rif=condominio_rif,
            condominio_email=condominio_email,
            logo_bytes=logo_bytes,
            pie_titular=pie_titular,
            pie_cuerpo=pie_cuerpo,
            propietario_nombre=propietario_nombre,
            propietario_email=propietario_email,
            unidad_codigo=unidad_codigo,
            indiviso_pct=indiviso_pct,
            periodo_nombre=periodo_nombre,
            tasa_cambio=tasa_cambio,
            cuota_bs=cuota_bs,
            cuota_usd=cuota_usd,
            saldo_anterior_usd=saldo_anterior_usd,
            mora_usd=mora_usd,
            cobros_ext_usd=cobros_ext_usd,
            pagos_recibidos_usd=pagos_recibidos_usd,
            saldo_actual_usd=saldo_actual_usd,
            fondo_reserva_usd=fondo_reserva_usd,
            total_gastos_usd=total_gastos_usd,
            acumulado_usd=acumulado_usd,
            meses_acumulados=meses_acumulados,
            gastos_detalle=gastos_detalle,
            saldo_ant_edificio=saldo_ant_edificio,
            deducciones_edificio=deducciones_edificio,
            ingresos_edificio=ingresos_edificio,
            saldo_act_edificio=saldo_act_edificio,
            emision_str=emision_str,
            mes_corto=mc,
            total_comun_usd=total_comun_usd,
        )
    except Exception:
        return _pdf_error_bytes()


def _generar_estado_cuenta_pdf_impl(
    *,
    condominio_nombre: str,
    condominio_rif: str,
    condominio_email: str,
    logo_bytes: bytes | str | None,
    pie_titular: str,
    pie_cuerpo: str,
    propietario_nombre: str,
    propietario_email: str,
    unidad_codigo: str,
    indiviso_pct: float,
    periodo_nombre: str,
    tasa_cambio: float,
    cuota_bs: float,
    cuota_usd: float,
    saldo_anterior_usd: float,
    mora_usd: float,
    cobros_ext_usd: float,
    pagos_recibidos_usd: float,
    saldo_actual_usd: float,
    fondo_reserva_usd: float,
    total_gastos_usd: float,
    acumulado_usd: float,
    meses_acumulados: int,
    gastos_detalle: list[dict[str, Any]],
    saldo_ant_edificio: float,
    deducciones_edificio: float,
    ingresos_edificio: float,
    saldo_act_edificio: float,
    emision_str: str,
    mes_corto: str,
    total_comun_usd: float,
) -> bytes:
    styles = getSampleStyleSheet()
    w_txt = letter[0] - inch
    col_logo = 1.15 * inch
    col_rest = w_txt - col_logo

    elems: list = []

    # —— Encabezado azul ——
    logo_img = _logo_bytes_a_image(logo_bytes, 1.0 * inch, 1.0 * inch)
    logo_cell: Any = logo_img if logo_img is not None else ""

    hdr_right = (
        f"<b><font color='white' size='12'>{_esc(condominio_nombre)}</font></b><br/>"
        f"<font color='white' size='9'>RIF: {_esc(condominio_rif)}</font><br/>"
        f"<font color='white' size='9'>email: {_esc(condominio_email)}</font><br/>"
        f"<font color='white' size='10'><b>Relación de Gastos</b></font>"
    )
    t_hdr = Table(
        [[logo_cell, Paragraph(hdr_right, styles["Normal"])]],
        colWidths=[col_logo, col_rest],
    )
    t_hdr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL_CONDOMINIO),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elems.append(t_hdr)
    elems.append(Spacer(1, 0.15 * inch))

    # —— Datos propietario (amarillo) ——
    mes_label = (mes_corto or periodo_nombre or "MES")[:12]
    monto_usd_txt = f"${float(cuota_usd):,.2f}"
    data_y = [
        ["Propietario", _esc(propietario_nombre), "MOV.MES", mes_label],
        ["Correo", _esc(propietario_email), "Inmueble", _esc(unidad_codigo)],
        ["Emisión", _esc(emision_str or "—"), "Alícuota", f"{float(indiviso_pct):.2f}%"],
        ["", "", "Monto USD", monto_usd_txt],
        ["Acumulado US$", _fmt_usd(acumulado_usd), "Mes(es)", str(int(meses_acumulados))],
    ]
    cw = [1.25 * inch, col_rest / 2 - 0.6 * inch, 1.0 * inch, col_rest / 2 - 0.65 * inch]
    t_y = Table(data_y, colWidths=cw)
    t_y.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AMARILLO_HEADER),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D4D4AA")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ]
        )
    )
    elems.append(t_y)
    elems.append(Spacer(1, 0.18 * inch))

    # —— Tabla gastos ——
    hdr_g = ["CONCEPTO DE GASTOS", "Mes Acum.", mes_label]
    rows_g: list[list[str]] = [hdr_g]
    for g in gastos_detalle:
        c = str(g.get("concepto") or "—")
        mu = float(g.get("monto_usd") or 0)
        s = _fmt_usd(mu)
        rows_g.append([c, s, s])
    tw = [w_txt - 2.2 * inch, 1.1 * inch, 1.1 * inch]
    t_g = Table(rows_g, colWidths=tw)
    ts_g = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_CONDOMINIO),
        ("TEXTCOLOR", (0, 0), (-1, 0), BLANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_FILA]),
    ]
    t_g.setStyle(TableStyle(ts_g))
    elems.append(t_g)
    elems.append(Spacer(1, 0.12 * inch))

    tcu = total_comun_usd if total_comun_usd > 0 else sum(
        float(x.get("monto_usd") or 0) for x in gastos_detalle
    )
    tot_rows = [
        [
            f"TOTAL GASTOS COMUNES {periodo_nombre}",
            _fmt_usd(tcu),
            _fmt_usd(tcu),
        ],
        [
            "MAS: FONDO DE RESERVA (10%)",
            _fmt_usd(fondo_reserva_usd),
            _fmt_usd(fondo_reserva_usd),
        ],
        ["TOTAL GASTOS EN DIVISAS", _fmt_usd(total_gastos_usd), ""],
        [
            f"CUOTA MES {periodo_nombre} EN DIVISA",
            "",
            _fmt_usd(cuota_usd),
        ],
    ]
    t_tot = Table(tot_rows, colWidths=tw)
    t_tot.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GRIS_TOTAL),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, -1), (2, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    elems.append(t_tot)
    elems.append(Spacer(1, 0.15 * inch))

    # —— Saldos acumulados ——
    st_s = [
        ["", "Edificio", "Reserva"],
        ["SALDO ANTERIOR", _fmt_usd(saldo_ant_edificio), "$0.00"],
        ["MENOS: DEDUCCIONES", _fmt_usd(deducciones_edificio), "$0.00"],
        ["MAS: INGRESOS COBRANZA", _fmt_usd(ingresos_edificio), "$0.00"],
        ["SALDO ACTUAL", _fmt_usd(saldo_act_edificio), "$0.00"],
    ]
    t_s = Table(st_s, colWidths=[2.8 * inch, 1.4 * inch, 1.4 * inch])
    t_s.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9D9D9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    elems.append(t_s)
    elems.append(Spacer(1, 0.2 * inch))

    # —— Pie bloque 1 (azul) ——
    p1 = pie_titular.strip() or "Texto de pie titular no configurado."
    sty_w = ParagraphStyle(
        name="PieAzul",
        parent=styles["Normal"],
        textColor=BLANCO,
        fontSize=8,
        leading=10,
        alignment=1,
    )
    t_p1 = Table([[Paragraph(_esc(p1), sty_w)]], colWidths=[w_txt])
    t_p1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL_CONDOMINIO),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elems.append(t_p1)
    elems.append(Spacer(1, 0.12 * inch))

    # —— Pie bloque 2 ——
    p2 = pie_cuerpo.strip() or ""
    sty_b = ParagraphStyle(
        name="PieBorde",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        alignment=1,
        textColor=NEGRO,
    )
    t_p2 = Table([[Paragraph(_esc(p2), sty_b)]], colWidths=[w_txt])
    t_p2.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elems.append(t_p2)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    doc.build(elems)
    return buf.getvalue()
