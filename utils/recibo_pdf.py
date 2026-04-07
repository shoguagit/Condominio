"""
Generador de PDF "Relación de Gastos" — formato fiel al código de referencia.

Layout A4 (como el generador original):
  Fila 1: Logo | Nombre condominio (azul) | "Relacion de Gastos" (azul)
  Fila 2: vacío | RIF | MOV.MES | mes/año
  Fila 3-5: info (Propietario, Correo, Emisión / Inmueble, Alícuota, Monto USD)
  Fila 6: Acumulado US$ (amarillo)
  Fila 7: encab. conceptos (azul claro) – "CONCEPTO DE GASTOS | Mes | Acum."
  Filas 8+: un ítem por línea (concepto | bs | usd) — porción de la unidad
  Totales: TOTAL GASTOS COMUNES, FONDO RESERVA, TOTAL RELACIONADO, CUOTA (azul)
  Saldos:  encab. gris | SALDO ANTERIOR | MENOS COBRANZA | SALDO ACTUAL
  Footer:  pie del condominio
"""

from __future__ import annotations

import io
import logging
from datetime import date
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak,
)

logger = logging.getLogger(__name__)

# ── COLORES ────────────────────────────────────────────────────────────────────
BLUE_HDR   = colors.HexColor("#2E74B5")
BLUE_DARK  = colors.HexColor("#1F3864")
BLUE_LT    = colors.HexColor("#BDD7EE")
YELLOW_ACC = colors.HexColor("#FFFFCC")
GRAY_HDR   = colors.HexColor("#808080")
GRAY_ROW   = colors.HexColor("#F2F2F2")
WHITE      = colors.white
BLACK      = colors.black
BORDER     = colors.HexColor("#BBBBBB")
BORDER_MED = colors.HexColor("#888888")

# ── PÁGINA ────────────────────────────────────────────────────────────────────
PW, PH = A4
ML = MR = 1.2 * cm
MT = MB = 1.2 * cm
UW = PW - ML - MR

cA   = 2.1 * cm          # columna logo
cD   = 1.65 * cm         # columna Bs
cE   = 1.65 * cm         # columna USD
cBC  = UW - cA - cD - cE  # columna central (concepto/info)

RH_TOP = 1.35 * cm
RH_RIF = 0.50 * cm
RH_INF = 0.50 * cm
RH_ACU = 0.50 * cm
RH_CHD = 0.48 * cm
RH_ITM = 0.405 * cm
RH_TOT = 0.43 * cm
RH_SHD = 0.43 * cm
RH_SAL = 0.43 * cm

_PAD = [
    ("TOPPADDING",    (0, 0), (-1, -1), 1.2),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
    ("LEFTPADDING",   (0, 0), (-1, -1), 3),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
]

MESES_ES = {
    1: "ENERO",    2: "FEBRERO",  3: "MARZO",     4: "ABRIL",
    5: "MAYO",     6: "JUNIO",    7: "JULIO",      8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _ps(name: str, size: int = 8, bold: bool = False, italic: bool = False,
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
        alignment=align, leading=leading or size + 1.5,
        spaceAfter=0, spaceBefore=0,
    )


def _tbl(data: list, cw: list, rh: float | list, cmds: list) -> Table:
    rh_arg = [rh] * len(data) if isinstance(rh, (int, float)) else rh
    t = Table(data, colWidths=cw, rowHeights=rh_arg)
    t.setStyle(TableStyle(cmds + _PAD))
    return t


def _fven(v: float | None) -> str:
    """Formato venezolano: punto=miles, coma=decimal, prefijo $."""
    if v is None:
        return ""
    try:
        s = f"{float(v):,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${s}"
    except Exception:
        return str(v)


def _esc(s: str) -> str:
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _p(text: str, **kw: Any) -> Paragraph:
    return Paragraph(_esc(str(text or "")), _ps("_", **kw))


# ── CONSTRUCCIÓN DE UN RECIBO (una unidad) ─────────────────────────────────────

def _build_recibo(d: dict, logo_img: Any = None) -> list:
    """
    Construye la lista de elementos ReportLab para una unidad.

    d keys: org, rif, mes_v, owner, inmueble, email, alicuota_fmt,
            emision, monto_usd, acum_usd, mes_acum,
            items [{ conc, bs, usd }],  bs/usd = porción de la unidad
            totals [{ lbl, bs, usd }],
            saldos [{ lbl, edif, res }],
            pie_titular, pie_cuerpo
    """
    elems: list = []

    # ── 1. Fila principal: logo | org | "Relacion de Gastos" ──────────────────
    logo_cell = logo_img if logo_img is not None else _p("")
    elems.append(_tbl(
        [[logo_cell,
          _p(d["org"], size=10, bold=True, color=WHITE, align=TA_CENTER, leading=13),
          _p("Relacion de\nGastos", size=9, bold=True, color=WHITE, align=TA_CENTER, leading=11)]],
        [cA, cBC, cD + cE], RH_TOP,
        [("BACKGROUND", (1, 0), (1, 0), BLUE_HDR),
         ("BACKGROUND", (2, 0), (2, 0), BLUE_HDR),
         ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
         ("LINEAFTER",  (1, 0), (1, 0), 1.5, WHITE),
         ("BOX",        (1, 0), (2, 0), 0.5, BORDER),
         ("TOPPADDING",    (0, 0), (0, 0), 1),
         ("BOTTOMPADDING", (0, 0), (0, 0), 1),
         ("LEFTPADDING",   (0, 0), (0, 0), 1),
         ("RIGHTPADDING",  (0, 0), (0, 0), 1)],
    ))

    # ── 2. Fila RIF / MOV.MES ────────────────────────────────────────────────
    elems.append(_tbl(
        [[_p(""),
          _p(d["rif"], size=7, bold=True, color=WHITE, align=TA_CENTER),
          _p("MOV.\nMES", size=6, bold=True, color=WHITE, align=TA_CENTER, leading=8),
          _p(d["mes_v"], size=8, bold=True, color=WHITE, align=TA_CENTER)]],
        [cA, cBC, cD, cE], RH_RIF,
        [("BACKGROUND", (1, 0), (-1, 0), BLUE_HDR),
         ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
         ("LINEAFTER", (2, 0), (2, 0), 1, WHITE),
         ("BOX",       (1, 0), (3, 0), 0.5, BORDER)],
    ))

    # ── 3. Bloque info (3 filas) ──────────────────────────────────────────────
    info_rows = [
        [_p("Propietario", bold=True), _p(d["owner"]),
         _p("Inmueble",   bold=True, align=TA_RIGHT), _p(d["inmueble"], size=9, bold=True, align=TA_CENTER)],
        [_p("Correo",     bold=True), _p(d["email"], size=7),
         _p("Alicuota",  bold=True, align=TA_RIGHT), _p(d["alicuota_fmt"], align=TA_RIGHT)],
        [_p("Emision",    bold=True), _p(d["emision"], bold=True, align=TA_CENTER),
         _p("Monto\nUSD:", size=6, bold=True, align=TA_RIGHT, leading=8),
         _p(_fven(d["monto_usd"]), size=8, bold=True, align=TA_CENTER)],
    ]
    elems.append(_tbl(
        info_rows, [cA, cBC, cD, cE], RH_INF,
        [("GRID",       (0, 0), (-1, -1), 0.5, BORDER_MED),
         ("BACKGROUND", (0, 0), (-1, -1), GRAY_ROW),
         ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
         ("LINEAFTER",  (1, 0), (1, -1), 1, BORDER_MED)],
    ))

    # ── 4. Fila Acumulado (amarillo) ──────────────────────────────────────────
    elems.append(_tbl(
        [[_p("Acumulado\nUS$", size=6, bold=True, align=TA_RIGHT, leading=8),
          _p(_fven(d["acum_usd"]), size=9, bold=True, align=TA_CENTER),
          _p(""), _p("")]],
        [cA, cBC, cD, cE], RH_ACU,
        [("BACKGROUND", (0, 0), (1, 0), YELLOW_ACC),
         ("BOX",        (0, 0), (1, 0), 0.5, BORDER_MED),
         ("VALIGN",     (0, 0), (-1, -1), "MIDDLE")],
    ))

    # ── 5. Encabezado columnas conceptos ─────────────────────────────────────
    mac = str(d.get("mes_acum", "")) if d.get("mes_acum") else ""
    elems.append(_tbl(
        [[_p(""),
          _p("CONCEPTO DE GASTOS", size=8, bold=True, color=BLUE_HDR, align=TA_CENTER),
          _p("Mes",     size=8, bold=True, color=BLUE_HDR, align=TA_CENTER),
          _p(f"Acum.\n{mac}", size=7, bold=True, color=BLUE_HDR, align=TA_CENTER, leading=9)]],
        [cA, cBC, cD, cE], RH_CHD,
        [("BACKGROUND", (0, 0), (-1, -1), BLUE_LT),
         ("GRID",       (0, 0), (-1, -1), 0.5, BORDER_MED),
         ("VALIGN",     (0, 0), (-1, -1), "MIDDLE")],
    ))

    # ── 6. Filas de ítems ────────────────────────────────────────────────────
    items = (d.get("items") or [])[:35]
    if items:
        rows, styles = [], []
        for i, it in enumerate(items):
            bg = WHITE if i % 2 == 0 else GRAY_ROW
            styles.append(("BACKGROUND", (0, i), (-1, i), bg))
            rows.append([
                Paragraph(_esc(str(it.get("conc") or "")), _ps("ik", 7)),
                _p(""),
                Paragraph(_fven(it.get("bs")), _ps("ir", 7, align=TA_RIGHT)),
                Paragraph(_fven(it.get("usd")), _ps("iu", 7, align=TA_RIGHT)),
            ])
        t = Table(rows,
                  colWidths=[cA + cBC * 0.58, cBC * 0.42, cD, cE],
                  rowHeights=[RH_ITM] * len(rows))
        t.setStyle(TableStyle(styles + [
            ("GRID",       (0, 0), (-1, -1), 0.3, BORDER),
            ("LINEBEFORE", (2, 0), (3, -1), 0.5, BORDER_MED),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ] + _PAD))
        elems.append(t)

    # ── 7. Filas de totales ───────────────────────────────────────────────────
    for tot in (d.get("totals") or []):
        cuota = "CUOTA" in str(tot.get("lbl", "")).upper()
        bg = BLUE_HDR if cuota else GRAY_ROW
        tc = WHITE    if cuota else BLACK
        elems.append(_tbl(
            [[_p(tot["lbl"], size=7, bold=True, color=tc),
              _p(""),
              _p(_fven(tot.get("bs")), size=7, bold=True, color=tc, align=TA_RIGHT),
              _p(_fven(tot.get("usd")), size=7, bold=True, color=tc, align=TA_RIGHT)]],
            [cA + cBC * 0.58, cBC * 0.42, cD, cE], RH_TOT,
            [("BACKGROUND", (0, 0), (-1, -1), bg),
             ("BOX",        (0, 0), (-1, -1), 0.5, BORDER_MED),
             ("LINEBEFORE", (2, 0), (-1, 0), 0.5, BORDER_MED),
             ("VALIGN",     (0, 0), (-1, -1), "MIDDLE")],
        ))

    # ── 8. Saldos acumulados ─────────────────────────────────────────────────
    elems.append(_tbl(
        [[_p("SALDOS ACUMULADOS", size=8, bold=True, color=WHITE),
          _p(""),
          _p("Edificio", size=8, bold=True, color=WHITE, align=TA_CENTER),
          _p("Reserva",  size=8, bold=True, color=WHITE, align=TA_CENTER)]],
        [cA + cBC * 0.58, cBC * 0.42, cD, cE], RH_SHD,
        [("BACKGROUND", (0, 0), (-1, -1), GRAY_HDR),
         ("LINEBEFORE", (2, 0), (-1, 0), 0.5, WHITE),
         ("VALIGN",     (0, 0), (-1, -1), "MIDDLE")],
    ))
    for i, s in enumerate((d.get("saldos") or [])):
        bg = WHITE if i % 2 == 0 else GRAY_ROW
        elems.append(_tbl(
            [[_p(s["lbl"], bold=True),
              _p(""),
              _p(_fven(s.get("edif")), align=TA_RIGHT),
              _p(_fven(s.get("res")),  align=TA_RIGHT)]],
            [cA + cBC * 0.58, cBC * 0.42, cD, cE], RH_SAL,
            [("BACKGROUND", (0, 0), (-1, -1), bg),
             ("GRID",       (0, 0), (-1, -1), 0.3, BORDER),
             ("LINEBEFORE", (2, 0), (-1, 0), 0.5, BORDER_MED),
             ("VALIGN",     (0, 0), (-1, -1), "MIDDLE")],
        ))

    # ── 9. Footer ─────────────────────────────────────────────────────────────
    pie = str(d.get("pie_titular") or "").strip()
    sub = str(d.get("pie_cuerpo") or "").strip()
    if pie:
        elems.append(_tbl(
            [[_p(pie, size=8, bold=True, italic=True, color=WHITE, align=TA_CENTER, leading=10)]],
            [UW], 0.85 * cm,
            [("BACKGROUND", (0, 0), (-1, -1), BLUE_DARK),
             ("VALIGN",     (0, 0), (-1, -1), "MIDDLE")],
        ))
    if sub:
        elems.append(_tbl(
            [[_p(sub, size=6, color=BLACK, align=TA_CENTER, leading=8)]],
            [UW], 1.20 * cm,
            [("BACKGROUND", (0, 0), (-1, -1), WHITE),
             ("BOX",        (0, 0), (-1, -1), 0.5, BORDER_MED),
             ("VALIGN",     (0, 0), (-1, -1), "MIDDLE")],
        ))

    return elems


# ── API PÚBLICA ────────────────────────────────────────────────────────────────

def preparar_datos_recibo(
    *,
    condominio: dict,
    unidad: dict,
    mes_nombre: str,
    anio: str,
    lineas_gasto: list[dict],          # {nombre, total_bs, total_usd}
    total_gastos_bs: float,
    total_gastos_usd: float,
    fondo_reserva_bs: float,
    fondo_reserva_usd: float,
    total_relacionado_bs: float,
    total_relacionado_usd: float,
    cuota_mes_bs: float,
    cuota_mes_usd: float,
    saldo_anterior_bs: float,
    pagos_mes_bs: float,
    saldo_nuevo_bs: float,
    meses_acum: int = 1,
) -> dict:
    """
    Convierte datos del dominio en el dict que espera `_build_recibo`.
    Cada ítem muestra la **porción de la unidad** (total × alícuota).
    """
    alicuota = float(unidad.get("indiviso_pct") or 0) / 100.0
    prop = unidad.get("propietarios") or {}

    # Formato alícuota venezolano (coma como decimal)
    alic_fmt = f"{float(unidad.get('indiviso_pct') or 0):.2f}".replace(".", ",")
    mes_v = f"{mes_nombre} {anio}"

    items = []
    for lg in lineas_gasto:
        bs_unit  = round(float(lg.get("total_bs",  0)) * alicuota, 2)
        usd_unit = round(float(lg.get("total_usd", 0)) * alicuota, 4)
        items.append({
            "conc": lg.get("nombre") or "Sin descripción",
            "bs":   bs_unit,
            "usd":  usd_unit,
        })

    tc_bs  = round(total_gastos_bs  * alicuota, 2)
    tc_usd = round(total_gastos_usd * alicuota, 4)
    fr_bs  = round(fondo_reserva_bs  * alicuota, 2)
    fr_usd = round(fondo_reserva_usd * alicuota, 4)

    totals = [
        {"lbl": f"TOTAL GASTOS COMUNES {mes_nombre}",         "bs": tc_bs,         "usd": tc_usd},
        {"lbl": "MAS: FONDO DE RESERVA 10%",                   "bs": fr_bs,         "usd": fr_usd},
        {"lbl": f"TOTAL GASTOS RELACIONADOS DEL MES {mes_nombre}", "bs": round(total_relacionado_bs * alicuota, 2), "usd": round(total_relacionado_usd * alicuota, 4)},
        {"lbl": f"CUOTA MES {mes_nombre} EN DIVISA {anio}",    "bs": cuota_mes_bs,  "usd": cuota_mes_usd},
    ]

    saldos = [
        {"lbl": "SALDO ANTERIOR",         "edif": saldo_anterior_bs, "res": None},
        {"lbl": "MENOS: COBRANZA MES",    "edif": -pagos_mes_bs,     "res": None},
        {"lbl": "SALDO ACTUAL",           "edif": saldo_nuevo_bs,    "res": None},
    ]

    cond = condominio or {}
    return dict(
        org=cond.get("nombre") or "—",
        rif=cond.get("numero_documento") or "",
        mes_v=mes_v,
        owner=(prop.get("nombre") or "—"),
        inmueble=(unidad.get("codigo") or unidad.get("numero") or "—"),
        email=(prop.get("correo") or ""),
        alicuota_fmt=alic_fmt,
        emision=date.today().strftime("%d-%m-%Y"),
        monto_usd=cuota_mes_usd,
        acum_usd=cuota_mes_usd,      # acumulado = cuota si solo hay 1 mes
        mes_acum=meses_acum,
        items=items,
        totals=totals,
        saldos=saldos,
        pie_titular=cond.get("pie_pagina_titular") or "",
        pie_cuerpo=cond.get("pie_pagina_cuerpo") or "",
    )


def generar_recibos_pdf(
    unidades_data: list[dict],
    logo_bytes: bytes | str | None = None,
) -> bytes:
    """
    Genera un PDF con un recibo por página.
    `unidades_data`: lista de dicts devueltos por `preparar_datos_recibo`.
    """
    try:
        from utils.estado_cuenta_pdf import _logo_bytes_a_image  # reutiliza lógica existente
        logo_img = _logo_bytes_a_image(logo_bytes, 2.0, 1.2) if logo_bytes else None
    except Exception:
        logo_img = None

    all_elems: list = []
    for i, d in enumerate(unidades_data):
        try:
            all_elems.extend(_build_recibo(d, logo_img))
        except Exception as e:
            logger.warning("generar_recibos_pdf: error unidad %s: %s", d.get("inmueble"), e)
        if i < len(unidades_data) - 1:
            all_elems.append(PageBreak())

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=MT, bottomMargin=MB,
    )
    doc.build(all_elems)
    return buf.getvalue()
