"""
Generador de PDF "Balance Mensual de Gastos" — formato A4.

Produce un reporte administrativo con todos los grupos de gastos asignados
al Balance, mostrando totales en Bs. y USD.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)

logger = logging.getLogger(__name__)

# ── COLORES (mismo palette que recibo_pdf) ────────────────────────────────────
BLUE_HDR   = colors.HexColor("#2E74B5")
BLUE_DARK  = colors.HexColor("#1F3864")
BLUE_LT    = colors.HexColor("#BDD7EE")
GRAY_ROW   = colors.HexColor("#F2F2F2")
GRAY_TOT   = colors.HexColor("#D9D9D9")
WHITE      = colors.white
BLACK      = colors.black
BORDER     = colors.HexColor("#BBBBBB")
BORDER_MED = colors.HexColor("#888888")

# ── PÁGINA ────────────────────────────────────────────────────────────────────
PW, PH = A4
ML = MR = 1.5 * cm
MT = MB = 1.5 * cm
UW = PW - ML - MR

_PAD = [
    ("TOPPADDING",    (0, 0), (-1, -1), 2),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
]


def _ps(name: str, size: int = 9, bold: bool = False, italic: bool = False,
        color: Any = BLACK, align: int = TA_LEFT, leading: float | None = None) -> ParagraphStyle:
    fn = "Helvetica"
    if bold and italic:
        fn = "Helvetica-BoldOblique"
    elif bold:
        fn = "Helvetica-Bold"
    elif italic:
        fn = "Helvetica-Oblique"
    return ParagraphStyle(
        name, fontName=fn, fontSize=size, textColor=color,
        alignment=align, leading=leading or size + 2,
        spaceAfter=0, spaceBefore=0,
    )


def _esc(s: str) -> str:
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _fven(v: float | None) -> str:
    """Formato venezolano: punto=miles, coma=decimal."""
    if v is None:
        return ""
    try:
        s = f"{float(v):,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)


def _fven_usd(v: float | None) -> str:
    if v is None:
        return ""
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return str(v)


def generar_balance_pdf(
    *,
    condominio_nombre: str,
    condominio_rif: str,
    mes_nombre: str,
    anio: str,
    grupos: list[dict],           # {nombre, total_bs, total_usd}
    logo_bytes: bytes | str | None = None,
    pie_titular: str = "",
    pie_cuerpo: str = "",
) -> bytes:
    """
    Genera el PDF del Balance Mensual de Gastos.
    `grupos` debe contener solo los grupos marcados para Balance.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT, bottomMargin=MB,
    )

    elems: list = []
    titulo_mes = f"{mes_nombre} {anio}"

    # ── Logo/encabezado ──────────────────────────────────────────────────────
    logo_cell: Any = Paragraph("", _ps("x"))
    if logo_bytes:
        try:
            from utils.estado_cuenta_pdf import _logo_bytes_a_image
            img = _logo_bytes_a_image(logo_bytes, 2.0, 1.1)
            if img:
                logo_cell = img
        except Exception:
            pass

    col_logo = 2.2 * cm
    col_info = UW - col_logo

    elems.append(Table(
        [[logo_cell,
          Paragraph(
              f"<b><font color='white' size='12'>{_esc(condominio_nombre)}</font></b><br/>"
              f"<font color='white' size='8'>RIF: {_esc(condominio_rif)}</font>",
              _ps("hdr", align=TA_CENTER)
          ),
          Paragraph(
              "<b><font color='white' size='10'>Balance Mensual\nde Gastos</font></b>",
              _ps("hdr2", size=10, bold=True, color=WHITE, align=TA_CENTER, leading=12)
          )]],
        colWidths=[col_logo, col_info * 0.62, col_info * 0.38],
        rowHeights=[1.2 * cm],
    ))
    elems[-1].setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (-1, 0), BLUE_HDR),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("BOX",        (1, 0), (-1, 0), 0.5, BORDER_MED),
        ("LINEAFTER",  (1, 0), (1, 0), 1, WHITE),
    ]))

    # ── Sub-encabezado: período ───────────────────────────────────────────────
    elems.append(Table(
        [[Paragraph("", _ps("x")),
          Paragraph(f"PERÍODO: {titulo_mes}",
                    _ps("per", 9, bold=True, color=WHITE, align=TA_CENTER)),
          Paragraph("", _ps("x"))]],
        colWidths=[col_logo, col_info * 0.62, col_info * 0.38],
        rowHeights=[0.45 * cm],
    ))
    elems[-1].setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, 0), BLUE_DARK),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ] + _PAD))

    elems.append(Spacer(1, 0.3 * cm))

    # ── Encabezado tabla conceptos ────────────────────────────────────────────
    cN  = UW * 0.06    # #
    cC  = UW * 0.60    # concepto
    cBS = UW * 0.17    # total Bs.
    cUD = UW * 0.17    # total USD

    hdr_row = [
        Paragraph("#",             _ps("h", 8, bold=True, color=WHITE, align=TA_CENTER)),
        Paragraph("CONCEPTO",      _ps("h", 8, bold=True, color=WHITE, align=TA_CENTER)),
        Paragraph("Total Bs.",     _ps("h", 8, bold=True, color=WHITE, align=TA_CENTER)),
        Paragraph("Total USD",     _ps("h", 8, bold=True, color=WHITE, align=TA_CENTER)),
    ]
    rows = [hdr_row]
    styles: list = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE_HDR),
        ("GRID",       (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBEFORE", (2, 0), (-1, -1), 0.5, BORDER_MED),
    ]

    total_bs = total_usd = 0.0
    for i, g in enumerate(grupos, start=1):
        bg = WHITE if i % 2 == 1 else GRAY_ROW
        styles.append(("BACKGROUND", (0, i), (-1, i), bg))
        bs  = float(g.get("total_bs",  0) or 0)
        usd = float(g.get("total_usd", 0) or 0)
        total_bs  += bs
        total_usd += usd
        rows.append([
            Paragraph(str(i),             _ps("n",  8, align=TA_CENTER)),
            Paragraph(_esc(g.get("nombre") or "—"), _ps("c",  8)),
            Paragraph(_fven(bs),          _ps("bs", 8, align=TA_RIGHT)),
            Paragraph(_fven_usd(usd),     _ps("ud", 8, align=TA_RIGHT)),
        ])

    t = Table(rows, colWidths=[cN, cC, cBS, cUD])
    t.setStyle(TableStyle(styles + _PAD))
    elems.append(t)

    # ── Fila TOTAL ───────────────────────────────────────────────────────────
    n_rows = len(rows)
    tot_row = Table(
        [[Paragraph(""),
          Paragraph("TOTAL", _ps("tot", 9, bold=True, align=TA_RIGHT)),
          Paragraph(_fven(total_bs),      _ps("tot", 9, bold=True, align=TA_RIGHT)),
          Paragraph(_fven_usd(total_usd), _ps("tot", 9, bold=True, align=TA_RIGHT))]],
        colWidths=[cN, cC, cBS, cUD],
        rowHeights=[0.5 * cm],
    )
    tot_row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRAY_TOT),
        ("BOX",        (0, 0), (-1, -1), 0.5, BORDER_MED),
        ("LINEBEFORE", (2, 0), (-1, 0), 0.5, BORDER_MED),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ] + _PAD))
    elems.append(tot_row)

    elems.append(Spacer(1, 0.5 * cm))

    # ── Fondo de reserva 10% ─────────────────────────────────────────────────
    fr_bs  = round(total_bs  * 0.10, 2)
    fr_usd = round(total_usd * 0.10, 2)
    tot_rel_bs  = round(total_bs  + fr_bs,  2)
    tot_rel_usd = round(total_usd + fr_usd, 2)

    resumen = [
        [f"Total Gastos Comunes {mes_nombre}:", _fven(total_bs),    _fven_usd(total_usd)],
        ["Fondo de Reserva (10%):",              _fven(fr_bs),       _fven_usd(fr_usd)],
        [f"Total Gastos Relacionados {mes_nombre}:", _fven(tot_rel_bs), _fven_usd(tot_rel_usd)],
    ]
    cL = UW * 0.56
    cR = UW * 0.22
    for j, row in enumerate(resumen):
        last = j == len(resumen) - 1
        bg   = BLUE_LT if last else WHITE
        t2 = Table(
            [[Paragraph(row[0], _ps("rl", 8, bold=last)),
              Paragraph(row[1], _ps("rv", 8, bold=last, align=TA_RIGHT)),
              Paragraph(row[2], _ps("rv", 8, bold=last, align=TA_RIGHT))]],
            colWidths=[cL, cR, cR],
            rowHeights=[0.42 * cm],
        )
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX",        (0, 0), (-1, -1), 0.3, BORDER),
            ("LINEBEFORE", (1, 0), (-1, 0), 0.5, BORDER_MED),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ] + _PAD))
        elems.append(t2)

    # ── Footer ────────────────────────────────────────────────────────────────
    elems.append(Spacer(1, 0.4 * cm))
    if pie_titular:
        t3 = Table(
            [[Paragraph(pie_titular,
                        _ps("ft1", 8, bold=True, italic=True, color=WHITE, align=TA_CENTER))]],
            colWidths=[UW], rowHeights=[0.7 * cm],
        )
        t3.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BLUE_DARK),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ] + _PAD))
        elems.append(t3)
    if pie_cuerpo:
        t4 = Table(
            [[Paragraph(pie_cuerpo, _ps("ft2", 7, align=TA_CENTER))]],
            colWidths=[UW], rowHeights=[0.9 * cm],
        )
        t4.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX",        (0, 0), (-1, -1), 0.5, BORDER_MED),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ] + _PAD))
        elems.append(t4)

    doc.build(elems)
    return buf.getvalue()
