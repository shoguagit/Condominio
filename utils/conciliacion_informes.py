"""
PDF de apoyo a la conciliación: movimientos sin conciliar (motivos) y conciliados (revisión).
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from utils.conciliacion_match import sugerir_vinculacion_desde_filas
from utils.estado_cuenta_pdf import _esc

COLOR_TITULO = colors.HexColor("#1B4F72")


def _normalizar_tipo_alerta(ta: Any) -> str:
    s = (ta or "").strip()
    return s if s else ""


def texto_por_tipo_alerta(tipo: str) -> str | None:
    if not tipo:
        return None
    m: dict[str, str] = {
        "sin_pago_sistema": (
            "Marcado o evaluado como <b>sin pago equivalente en sistema</b> para este período. "
            "Se requiere registrar el pago en el módulo Pagos (referencia, fecha y monto "
            "coherentes con el banco) o, si aplica, ejecutar la conciliación automática "
            "por cédula cuando el banco muestra la documentación en la descripción."
        ),
        "monto_no_coincide": (
            "Hay un <b>desacuerdo entre el monto del movimiento bancario</b> y el del pago "
            "vinculado o del pago sugerido (diferencia mayor al redondeo habitual). "
            "Revise cargos, descuentos u otra partida; si el pago es correcto, ajuste datos "
            "o desvincule y registre el movimiento adecuado."
        ),
        "pago_parcial": (
            "El ingreso en banco es <b>menor</b> que el monto del pago esperado en sistema "
            "(pago parcial detectado). Falta completar el cobro o registrar otro movimiento, "
            "o corregir la cuota esperada si hubo error de cálculo."
        ),
        "pago_superior": (
            "El ingreso en banco es <b>mayor</b> que el pago o cuota esperado en sistema. "
            "Puede ser sobrepago, otros conceptos en la misma transferencia o error de referencia. "
            "Acuerde contablemente el excedente o corrija la base en Pagos/cuotas."
        ),
        "fecha_fuera_periodo": (
            "<b>La fecha del movimiento</b> no pertenece al mismo mes que el período de proceso "
            "o conciliación mostrado. Corrija período de carga del movimiento si corresponde, "
            "o traslade el análisis al mes correcto."
        ),
    }
    return m.get(tipo)


def explicar_pendiente_de_conciliacion(mov: dict, sug: dict | None) -> str:
    bloques: list[str] = []
    ta = _normalizar_tipo_alerta(mov.get("tipo_alerta"))
    if ta:
        det = texto_por_tipo_alerta(ta)
        etiqueta = _esc(ta.replace("_", " "))
        part = det or ""
        bloques.append(f"<b>Alerta ({etiqueta}).</b> {part}".strip())

    if not sug or not sug.get("pago"):
        bloques.append(
            "<b>Coincidencia automática.</b> No se encontró en el período un pago que cumpla, "
            "en este orden: <b>referencia idéntica</b> a la del banco; luego <b>monto similar "
            "(±1 Bs.)</b> con <b>misma semana calendario</b> que la fecha del movimiento; luego "
            "<b>monto exacto</b> en el <b>mismo mes calendario</b> que la fecha del movimiento. "
            "Registre o corrija pagos en Pagos, o confirme datos de referencia/fecha/monto."
        )
    else:
        conf = sug.get("confianza") or ""
        razon = _esc(str(sug.get("razon") or ""))
        p = sug["pago"]
        pref = _esc(str(p.get("referencia") or p.get("id") or ""))
        mp = float(p.get("monto_bs") or 0)
        if conf == "alta":
            bloques.append(
                f"<b>Coincidencia sugerida (alta).</b> Por <b>{razon}</b> se propone "
                f"pago <b>#{pref}</b> por <b>Bs. {mp:,.2f}</b>. "
                "<b>Para conciliar</b> debe usar <b>Confirmar</b> en la pantalla de conciliación "
                "después de verificar que es el mismo cobro."
            )
        elif conf in ("media", "baja"):
            conf_e = _esc(str(conf))
            bloques.append(
                f"<b>Coincidencia posible ({conf_e}).</b> Por <b>{razon}</b> "
                f"se listó el pago <b>#{pref}</b> por <b>Bs. {mp:,.2f}</b>. "
                "Revíselo con cuidado antes de confirmar; si no corresponde, registre el pago "
                "correcto o rechace la sugerencia."
            )

    mid = int(mov["id"])
    fd = _esc(str(mov.get("fecha") or "")[:10])
    ref = _esc(str(mov.get("referencia") or "—"))
    mb = float(mov.get("monto_bs") or 0)
    hdr = (
        f"<b>Movimiento #{mid}</b> — Fecha {fd} — Ref. {ref} — Monto Bs. {mb:,.2f}<br/>"
    )
    return hdr + "<br/><br/>".join(bloques)


def _pago_embed(mov: dict) -> dict | None:
    p = mov.get("pagos")
    if isinstance(p, list) and p:
        return p[0]
    if isinstance(p, dict):
        return p
    return None


def _fila_revision_conciliado(mov: dict) -> list[str]:
    p = _pago_embed(mov) or {}
    u = p.get("unidades") or mov.get("unidades") or {}
    unidad_p = (u.get("codigo") or u.get("numero") or "").strip() or "—"
    mm = float(mov.get("monto_bs") or 0)
    mp = float(p.get("monto_bs") or 0)
    igual = "Sí" if round(mm, 2) == round(mp, 2) else f"No (Δ {abs(mm - mp):,.2f})"
    ta = _normalizar_tipo_alerta(mov.get("tipo_alerta"))
    adv = ""
    if ta == "monto_no_coincide" or igual.startswith("No"):
        adv = "Revise desempeño del vínculo."
    origen = (p.get("origen") or "manual").strip()
    return [
        str(mov.get("fecha") or "")[:10],
        _esc(str(mov.get("referencia") or "")),
        f"{mm:,.2f}",
        _esc(str(mov.get("descripcion") or "")[:80]),
        _esc(str(p.get("id") or "—")),
        str(p.get("fecha_pago") or "")[:10],
        _esc(str(p.get("referencia") or "")),
        f"{mp:,.2f}",
        _esc(unidad_p),
        _esc(origen),
        _esc(igual + (" " + adv if adv else "")),
        _esc(ta or "—"),
    ]


def generar_pdf_sin_conciliar(
    condominio_nombre: str,
    periodo_etiqueta: str,
    pendientes: list[dict],
    pagos_periodo: list[dict],
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    tit = ParagraphStyle(
        name="TitConc",
        parent=styles["Heading1"],
        textColor=COLOR_TITULO,
        fontSize=14,
        spaceAfter=10,
    )
    sub = ParagraphStyle(
        name="SubConc",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=12,
    )
    body = ParagraphStyle(
        name="BodyConc",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        spaceAfter=8,
    )

    story: list = [
        Paragraph("<b>Movimientos bancarios sin conciliar</b>", tit),
        Paragraph(
            f"{_esc(condominio_nombre)} — Período {_esc(periodo_etiqueta)} — "
            f"Emitido {_esc(datetime.now().strftime('%d/%m/%Y %H:%M'))}",
            sub,
        ),
    ]

    if not pendientes:
        story.append(Paragraph("<i>No hay ingresos pendientes de conciliar en este período.</i>", body))
    else:
        story.append(
            Paragraph(
                f"<b>Total registros pendientes:</b> {len(pendientes)}. "
                "Cada uno incluye el motivo y acciones esperadas.",
                body,
            )
        )
        story.append(Spacer(1, 0.2 * cm))
        ordenados = sorted(
            pendientes,
            key=lambda r: (str(r.get("fecha") or ""), int(r["id"])),
        )
        for mov in ordenados:
            sug = sugerir_vinculacion_desde_filas(mov, pagos_periodo)
            txt = explicar_pendiente_de_conciliacion(mov, sug)
            story.append(Paragraph(txt, body))
            story.append(Spacer(1, 0.15 * cm))

    doc.build(story)
    return buf.getvalue()


def generar_pdf_conciliados_revision(
    condominio_nombre: str,
    periodo_etiqueta: str,
    conciliados: list[dict],
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    tit = ParagraphStyle(
        name="TitConc2",
        parent=styles["Heading1"],
        textColor=COLOR_TITULO,
        fontSize=14,
        spaceAfter=10,
    )
    cap = ParagraphStyle(
        name="CapConc",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=10,
    )
    note = ParagraphStyle(name="Note", parent=styles["Normal"], fontSize=8)

    hdr = [
        "Fecha mov.",
        "Ref. banco",
        "Monto mov.",
        "Descripción",
        "Pago id",
        "Fecha pago",
        "Ref. pago",
        "Monto pago",
        "Unidad",
        "Origen pago",
        "Montos =",
        "Alerta",
    ]
    data = [hdr]
    ordenados = sorted(
        conciliados,
        key=lambda r: (str(r.get("fecha") or ""), int(r["id"])),
    )
    for mov in ordenados:
        data.append(_fila_revision_conciliado(mov))

    story: list = [
        Paragraph("<b>Movimientos conciliados — revisión</b>", tit),
        Paragraph(
            f"{_esc(condominio_nombre)} — Período {_esc(periodo_etiqueta)} — "
            f"Emitido {_esc(datetime.now().strftime('%d/%m/%Y %H:%M'))}",
            cap,
        ),
        Paragraph(
            "<i>Use esta tabla para verificar vínculos pago ↔ banco y origen del pago. "
            'Si falta información del pago, verifique permisos o la vista en Supabase.</i>',
            note,
        ),
        Spacer(1, 0.3 * cm),
    ]

    if len(data) == 1:
        story.append(Paragraph("<i>No hay ingresos conciliados en este período.</i>", styles["Normal"]))
    else:
        col_w = [
            2 * cm,
            2.4 * cm,
            1.8 * cm,
            3.2 * cm,
            1.6 * cm,
            2 * cm,
            2.2 * cm,
            2 * cm,
            1.8 * cm,
            2.2 * cm,
            2.4 * cm,
            2.2 * cm,
        ]
        t = Table(data, repeatRows=1, colWidths=col_w)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D6E4F0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), colors.white, colors.HexColor("#F8F9FA")),
                ]
            )
        )
        story.append(t)

    doc.build(story)
    return buf.getvalue()
