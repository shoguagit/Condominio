"""
Reporte PDF — saldos acumulados iniciales (ReportLab + fusión portrait/landscape).
No propaga excepciones: ante error devuelve PDF mínimo de aviso.
"""

from __future__ import annotations

import io
import logging
import re
from collections import defaultdict
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from utils.estado_cuenta_pdf import (
    AZUL_CONDOMINIO,
    _esc,
    _logo_bytes_a_image,
    _pdf_error_bytes,
)
from utils.pdf_combinado import combinar_pdfs
from utils.pdf_generator import monto_bs_a_usd

logger = logging.getLogger(__name__)

AZUL = colors.HexColor("#1B4F8A")
AZUL_CLARO = colors.HexColor("#D6E4F0")
GRIS = colors.HexColor("#F5F5F5")
AMARILLO = colors.HexColor("#FFF9C4")
BLANCO = colors.white
NEGRO = colors.black

PERIODO_REFERENCIA = "Febrero 2026"


def _build_portada(
    condominio_nombre: str,
    condominio_rif: str,
    logo_bytes: bytes | None,
    tasa_cambio: float,
    unidades: list[dict[str, Any]],
    fecha_generacion: str,
) -> bytes:
    styles = getSampleStyleSheet()
    w_txt = letter[0] - inch
    col_logo = 1.15 * inch
    col_rest = w_txt - col_logo

    logo_img = _logo_bytes_a_image(logo_bytes, 2.54, 2.54)
    if logo_img is not None:
        logo_cell = Table(
            [[logo_img]],
            colWidths=[col_logo],
            rowHeights=[1.0 * inch],
        )
        logo_cell.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
    else:
        logo_cell = ""

    hdr_right = (
        f"<b><font color='white' size='11'>{_esc(condominio_nombre)}</font></b><br/>"
        f"<font color='white' size='9'>RIF: {_esc(condominio_rif)}</font><br/>"
        f"<font color='white' size='10'><b>REPORTE DE SALDOS ACUMULADOS INICIALES</b></font><br/>"
        f"<font color='white' size='8'>Generado: {_esc(fecha_generacion)}</font><br/>"
        f"<font color='white' size='8'>Período de referencia: {PERIODO_REFERENCIA}</font>"
    )
    t_hdr = Table(
        [[logo_cell, Paragraph(hdr_right, styles["Normal"])]],
        colWidths=[col_logo, col_rest],
        rowHeights=[1.15 * inch],
    )
    t_hdr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL_CONDOMINIO),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elems: list = [t_hdr, Spacer(1, 0.2 * inch)]

    total = len(unidades)
    revisar = sum(1 for u in unidades if u.get("requiere_revision"))
    total_bs = sum(float(u.get("saldo_inicial_bs") or 0) for u in unidades)
    tasa = float(tasa_cambio or 0)
    total_usd = monto_bs_a_usd(total_bs, tasa) if tasa > 0 else 0.0

    datos_resumen = [
        ["Concepto", "Valor"],
        ["Total unidades con saldo", str(total)],
        ["Total unidades requieren revisión", str(revisar)],
        ["Saldo total acumulado", f"Bs. {total_bs:,.2f}"],
        [
            "Equivalente USD",
            f"${total_usd:,.2f}" if tasa > 0 else "N/D",
        ],
        ["Tasa BCV utilizada", f"Bs. {tasa:,.4f}" if tasa > 0 else "N/D"],
    ]
    tr = Table(datos_resumen, colWidths=[3.2 * inch, 3.0 * inch])
    tr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), BLANCO),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BLANCO, GRIS]),
            ]
        )
    )
    elems.append(Paragraph("<b>Resumen general</b>", styles["Heading3"]))
    elems.append(tr)
    elems.append(Spacer(1, 0.25 * inch))

    # Distribución por meses sin pagar (usa meses_sin_pagar efectivo de cada unidad)
    grupos: dict[int, list[dict]] = defaultdict(list)
    for u in unidades:
        m = int(u.get("meses_sin_pagar") or 0)
        grupos[m].append(u)

    meses_orden = sorted(grupos.keys())
    elems.append(Paragraph("<b>Distribución por meses de deuda</b>", styles["Heading3"]))
    if total > 0 and meses_orden == [0]:
        elems.append(
            Paragraph(
                "Los datos de meses se actualizarán al re-cargar los archivos con "
                "<b>Actualizar meses y período</b>.",
                styles["Normal"],
            )
        )
    else:
        dist_data: list[list[str]] = [
            ["Meses sin pagar", "N° unidades", "Subtotal Bs.", "Subtotal USD"],
        ]
        sum_u = 0
        sum_bs = 0.0
        sum_usd = 0.0
        for m in meses_orden:
            lst = grupos[m]
            n = len(lst)
            sub_bs = sum(float(x.get("saldo_inicial_bs") or 0) for x in lst)
            sub_usd = monto_bs_a_usd(sub_bs, tasa) if tasa > 0 else 0.0
            sum_u += n
            sum_bs += sub_bs
            sum_usd += sub_usd
            label = f"{m} mes{'es' if m != 1 else ''}" if m != 0 else "0 meses (sin registro en BD)"
            dist_data.append(
                [
                    label,
                    str(n),
                    f"Bs. {sub_bs:,.2f}",
                    f"${sub_usd:,.2f}" if tasa > 0 else "N/D",
                ]
            )
        dist_data.append(
            [
                "TOTAL",
                str(sum_u),
                f"Bs. {sum_bs:,.2f}",
                f"${sum_usd:,.2f}" if tasa > 0 else "N/D",
            ]
        )

        td = Table(dist_data, colWidths=[2.2 * inch, 1.2 * inch, 1.8 * inch, 1.5 * inch])
        ts_td: list = [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, 0), (-1, 0), BLANCO),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]
        for ri in range(1, len(dist_data) - 1):
            bg = GRIS if ri % 2 == 0 else BLANCO
            ts_td.append(("BACKGROUND", (0, ri), (-1, ri), bg))
        ts_td.append(("BACKGROUND", (0, -1), (-1, -1), AZUL_CLARO))
        td.setStyle(TableStyle(ts_td))
        elems.append(td)

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


def _build_detalle_landscape(
    tasa_cambio: float,
    unidades: list[dict[str, Any]],
) -> bytes:
    styles = getSampleStyleSheet()
    sty_small = ParagraphStyle(
        name="SaldosSmall",
        parent=styles["Normal"],
        fontSize=7,
        leading=8,
    )
    page_size = landscape(letter)
    margin = 0.4 * inch
    avail_w = page_size[0] - 2 * margin

    # landscape letter: N° | Código | Propietario | Alícuota% | Meses | Saldo Bs. | Saldo USD
    cw = [
        0.4 * inch,
        0.9 * inch,
        3.2 * inch,
        0.8 * inch,
        0.7 * inch,
        1.5 * inch,
        1.1 * inch,
    ]
    scale = avail_w / sum(cw)
    cw = [c * scale for c in cw]

    headers = [
        "N°",
        "Código",
        "Propietario",
        "Alícuota %",
        "Meses",
        "Saldo Bs.",
        "Saldo USD",
    ]
    tasa = float(tasa_cambio or 0)

    data: list[list[Any]] = [headers]
    tot_bs = 0.0
    tot_usd = 0.0
    for i, u in enumerate(unidades, start=1):
        sbs = float(u.get("saldo_inicial_bs") or 0)
        susd = float(u.get("saldo_usd") or 0) if tasa > 0 else 0.0
        tot_bs += sbs
        tot_usd += susd
        prop = _esc(str(u.get("propietario_nombre") or "—")[:42])
        data.append(
            [
                str(i),
                _esc(str(u.get("numero_unidad") or "—")),
                Paragraph(prop, sty_small),
                f"{float(u.get('indiviso_pct') or 0):.2f}",
                str(int(u.get("meses_sin_pagar") or 0)),
                f"Bs. {sbs:,.2f}",
                f"${susd:,.2f}" if tasa > 0 else "N/D",
            ]
        )

    data.append(
        [
            "TOTAL",
            "",
            "",
            "",
            "",
            f"Bs. {tot_bs:,.2f}",
            f"${tot_usd:,.2f}" if tasa > 0 else "N/D",
        ]
    )

    t = Table(data, colWidths=cw, repeatRows=1)
    ts: list = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), BLANCO),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.2, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]
    last = len(data) - 1
    for ri in range(1, last):
        u = unidades[ri - 1]
        if u.get("requiere_revision"):
            ts.append(("BACKGROUND", (0, ri), (-1, ri), AMARILLO))
        else:
            bg = GRIS if ri % 2 == 0 else BLANCO
            ts.append(("BACKGROUND", (0, ri), (-1, ri), bg))
    ts.append(("BACKGROUND", (0, last), (-1, last), AZUL_CLARO))
    t.setStyle(TableStyle(ts))

    elems: list = [
        Paragraph("<b>Detalle por unidad</b>", styles["Heading3"]),
        Spacer(1, 0.1 * inch),
        t,
    ]

    rev = [u for u in unidades if u.get("requiere_revision")]
    if rev:
        elems.append(Spacer(1, 0.3 * inch))
        elems.append(
            Paragraph("<b>Desglose — unidades pendientes de revisión</b>", styles["Heading3"])
        )
        for u in rev:
            cod = _esc(str(u.get("numero_unidad") or "—"))
            nota = _esc(str(u.get("nota_revision") or "—"))
            elems.append(Paragraph(f"<b>{cod}</b>: {nota}", sty_small))
            elems.append(Spacer(1, 0.06 * inch))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    doc.build(elems)
    return buf.getvalue()


def generar_reporte_saldos_pdf(
    condominio_nombre: str,
    condominio_rif: str,
    logo_bytes: bytes | None,
    tasa_cambio: float,
    unidades: list[dict[str, Any]],
    fecha_generacion: str,
) -> bytes:
    """
    Genera el PDF de saldos acumulados. Nunca propaga excepciones.
    """
    try:
        u_sorted = list(unidades or [])

        def _nk(s: str) -> list:
            s = s or ""
            return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", s)]

        u_sorted.sort(key=lambda x: _nk(str(x.get("numero_unidad") or "")))

        p1 = _build_portada(
            condominio_nombre=condominio_nombre,
            condominio_rif=condominio_rif,
            logo_bytes=logo_bytes,
            tasa_cambio=tasa_cambio,
            unidades=u_sorted,
            fecha_generacion=fecha_generacion,
        )
        p2 = _build_detalle_landscape(tasa_cambio, u_sorted)
        merged = combinar_pdfs([p1, p2])
        if not merged:
            return _pdf_error_bytes("No se pudo combinar las secciones del PDF.")
        return merged
    except Exception as e:
        logger.warning("generar_reporte_saldos_pdf: %s", e)
        return _pdf_error_bytes("No se pudo generar el reporte de saldos acumulados.")
