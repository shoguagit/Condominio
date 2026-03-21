"""
Utilidades ReportLab para reportes PDF (Fase 3). Sin CSS de Streamlit.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COLOR_PRIMARIO = colors.HexColor("#1B4F72")
COLOR_SECUNDARIO = colors.HexColor("#2E86C1")
COLOR_GRIS = colors.HexColor("#6B7280")
COLOR_CLARO = colors.HexColor("#F4F6F7")


def formato_bs(monto: float) -> str:
    return f"Bs. {float(monto):,.2f}"


def formato_usd(monto: float) -> str:
    return f"$ {float(monto):,.2f}"


def monto_bs_a_usd(monto_bs: float, tasa: float) -> float:
    if tasa and float(tasa) > 0:
        return round(float(monto_bs) / float(tasa), 2)
    return 0.0


def par_bs_usd(monto_bs: float, tasa: float) -> tuple[str, str]:
    return formato_bs(monto_bs), formato_usd(monto_bs_a_usd(monto_bs, tasa))


def rif_condominio_texto(condominio: dict) -> str:
    td = condominio.get("tipos_documento") or {}
    tipo = (td.get("nombre") or "").strip()
    num = (condominio.get("numero_documento") or "").strip()
    if tipo and num:
        return f"{tipo} {num}"
    return num or "—"


def crear_encabezado(
    condominio: dict,
    periodo_mm_yyyy: str,
    titulo_reporte: str,
    subtitulo: str | None = None,
) -> list:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="RepTitle",
        parent=styles["Title"],
        textColor=COLOR_PRIMARIO,
        fontSize=14,
        spaceAfter=6,
    )
    normal = styles["Normal"]
    elems: list = [
        Paragraph(f"<b>{titulo_reporte}</b>", title_style),
    ]
    if subtitulo:
        elems.append(Paragraph(f"<i>{subtitulo}</i>", normal))
    elems.append(Spacer(1, 0.2 * cm))
    nom = (condominio.get("nombre") or "—").replace("&", "&amp;")
    elems.append(Paragraph(f"<b>{nom}</b>", styles["Heading2"]))
    elems.append(Paragraph(f"RIF / Documento: {rif_condominio_texto(condominio)}", normal))
    dir_ = (condominio.get("direccion") or "—").replace("&", "&amp;")
    elems.append(Paragraph(f"Dirección: {dir_}", normal))
    elems.append(Paragraph(f"Período: {periodo_mm_yyyy}", normal))
    hoy = datetime.now().strftime("%d/%m/%Y")
    elems.append(Paragraph(f"Fecha de emisión: {hoy}", normal))
    elems.append(Spacer(1, 0.4 * cm))
    return elems


def crear_tabla_estilo(
    data: Sequence[Sequence[Any]],
    col_widths: Sequence[float] | None = None,
    header_row: bool = True,
) -> Table:
    rr = 1 if header_row and len(data) > 1 else 0
    t = Table(list(data), colWidths=col_widths, repeatRows=rr)
    st_cmd: list = [
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, COLOR_GRIS),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header_row and len(data) > 0:
        st_cmd.insert(0, ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARIO))
        st_cmd.insert(1, ("TEXTCOLOR", (0, 0), (-1, 0), colors.white))
        st_cmd.insert(2, ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
        if len(data) > 1:
            st_cmd.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_CLARO]))
    else:
        st_cmd.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, COLOR_CLARO]))
    t.setStyle(TableStyle(st_cmd))
    return t


def crear_fila_total(label: str, monto_bs: str, monto_usd: str) -> Table:
    data = [[label, monto_bs, monto_usd]]
    t = Table(data, colWidths=[8 * cm, 4 * cm, 4 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_SECUNDARIO),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.white),
            ]
        )
    )
    return t


def pie_documento(texto: str | None = None) -> list:
    styles = getSampleStyleSheet()
    hoy = datetime.now().strftime("%d/%m/%Y")
    msg = texto or f"Documento generado por Sistema de Condominio el {hoy}"
    return [Spacer(1, 0.6 * cm), Paragraph(f"<font color='gray' size=8>{msg}</font>", styles["Normal"])]


def generar_pdf_bytes(elementos: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    doc.build(elementos)
    return buffer.getvalue()
