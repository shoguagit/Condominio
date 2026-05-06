"""
PDF de apoyo a la conciliación: movimientos sin conciliar y conciliados (tablas).
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

from utils.cedula_extractor import extraer_cedulas
from utils.conciliacion_match import sugerir_vinculacion_desde_filas
from utils.estado_cuenta_pdf import _esc

COLOR_TITULO = colors.HexColor("#1B4F72")


def _apartamento_mov(mov: dict) -> str:
    u = mov.get("unidades") or {}
    return (u.get("codigo") or u.get("numero") or "").strip() or "—"


def enriquecer_apartamentos_desde_cedula_bd(
    pendientes: list[dict],
    condominio_id: int,
    client: Any,
) -> None:
    """
    Para cada movimiento con cédula en la descripción, busca apartamento(s) en BD
    con la misma lógica que la conciliación por cédula.

    Usa ``buscar_unidades_por_cedula_core`` (sin decorador que oculte errores) y
    amplía la búsqueda a propietarios inactivos si hace falta, igual criterio
    propietario→unidad que en conciliación por cédula.
    """
    from repositories.conciliacion_cedula_repository import buscar_unidades_por_cedula_core

    cache: dict[tuple[str, ...], list[dict]] = {}
    for m in pendientes:
        mc = extraer_cedulas(str(m.get("descripcion") or ""))
        if not mc:
            continue
        key = tuple(sorted(set(mc)))
        if key not in cache:
            try:
                filas = buscar_unidades_por_cedula_core(
                    client,
                    list(key),
                    int(condominio_id),
                    solo_propietarios_activos=False,
                )
                if not filas:
                    filas = buscar_unidades_por_cedula_core(
                        client,
                        list(key),
                        int(condominio_id),
                        solo_propietarios_activos=True,
                    )
                cache[key] = filas or []
            except Exception:
                cache[key] = []
        filas = cache[key]
        codigos = sorted(
            {
                str(r.get("codigo_unidad") or "").strip()
                for r in filas
                if (str(r.get("codigo_unidad") or "").strip())
            }
        )
        if codigos:
            m["_apartamento_desde_cedula"] = ", ".join(codigos)


def _texto_concepto_movimiento(mov: dict) -> str:
    """Concepto + descripción del banco para revisar cuando no hay cédula detectada."""
    conceptos = mov.get("conceptos") or {}
    nombre = (conceptos.get("nombre") or "").strip()
    desc = str(mov.get("descripcion") or "").strip()
    parts: list[str] = []
    if nombre:
        parts.append(f"Concepto: {nombre}")
    if desc:
        parts.append(desc[:320])
    return " — ".join(parts) if parts else "Sin concepto ni descripción en el movimiento."


def _normalizar_tipo_alerta(ta: Any) -> str:
    s = (ta or "").strip()
    return s if s else ""


def observacion_y_explicacion_corta(mov: dict, sug: dict | None) -> tuple[str, str]:
    """
    Textos fijos y cortos para columnas Observación / Explicación en PDF pendientes.
    """
    ta = _normalizar_tipo_alerta(mov.get("tipo_alerta"))
    desc = str(mov.get("descripcion") or "")
    tiene_ced = bool(extraer_cedulas(desc))

    if ta == "sin_pago_sistema":
        if not tiene_ced:
            return (
                "Sin cédula en descripción",
                "Registrar pago en Pagos o incluir cédula en el texto del banco para conciliar automático.",
            )
        return (
            "Sin pago en sistema",
            "Registrar el cobro en Pagos con referencia/fecha/monto alineados al banco.",
        )
    if ta == "monto_no_coincide":
        return ("Montos no coinciden", "Revise vínculo con Pagos o ajuste montos.")
    if ta == "pago_parcial":
        return ("Pago menor al esperado", "Completar cobro o revisar cuota del período.")
    if ta == "pago_superior":
        return ("Pago mayor al esperado", "Verificar sobrepago o registrar otro concepto.")
    if ta == "fecha_fuera_periodo":
        return ("Fecha fuera del período", "Corregir período del movimiento o conciliar el mes correcto.")

    if sug and sug.get("pago"):
        conf = (sug.get("confianza") or "").lower()
        if conf == "alta":
            return ("Coincidencia por referencia", "Pulse Confirmar en pantalla si el pago es correcto.")
        if conf in ("media", "baja"):
            return ("Posible coincidencia", "Revise referencia y monto antes de confirmar.")

    return (
        "Sin coincidencia automática",
        "No hay pago en el período que coincida por referencia ni por reglas de monto/fecha.",
    )


def _fila_pendiente_tabla(mov: dict, sug: dict | None) -> list[str]:
    fecha = str(mov.get("fecha") or "")[:10]
    ref = str(mov.get("referencia") or "").strip() or "—"
    monto = f"{float(mov.get('monto_bs') or 0):,.2f}"
    desc = str(mov.get("descripcion") or "")
    ceds = extraer_cedulas(desc)
    ced_txt = ", ".join(ceds) if ceds else "—"
    if ceds:
        apt_bd = (mov.get("_apartamento_desde_cedula") or "").strip()
        apt_mov = _apartamento_mov(mov)
        apt_txt = apt_bd or (apt_mov if apt_mov != "—" else "—")
    else:
        apt_txt = "—"
    obs, expl_std = observacion_y_explicacion_corta(mov, sug)
    if ceds:
        expl = expl_std
    else:
        expl = _texto_concepto_movimiento(mov)
    return [
        _esc(fecha),
        _esc(ref),
        _esc(monto),
        _esc(ced_txt),
        _esc(apt_txt),
        _esc(obs),
        _esc(expl),
    ]


def _pago_embed(mov: dict) -> dict | None:
    p = mov.get("pagos")
    if isinstance(p, list) and p:
        return p[0]
    if isinstance(p, dict):
        return p
    return None


def _fila_conciliado_tabla(mov: dict) -> list[str]:
    """Fecha, Referencia, Cédula, Apartamento, Monto, Estatus."""
    p = _pago_embed(mov) or {}
    u = p.get("unidades") or mov.get("unidades") or {}
    apt = (u.get("codigo") or u.get("numero") or "").strip() or "—"
    desc = str(mov.get("descripcion") or "")
    ceds = extraer_cedulas(desc)
    if not ceds and (p.get("observaciones") or ""):
        ceds = extraer_cedulas(str(p.get("observaciones") or ""))
    cedula_txt = ", ".join(ceds) if ceds else "—"
    mm = float(mov.get("monto_bs") or 0)
    return [
        str(mov.get("fecha") or "")[:10],
        _esc(str(mov.get("referencia") or "")),
        _esc(cedula_txt),
        _esc(apt),
        f"{mm:,.2f}",
        "Conciliado",
    ]


def _tabla_estilo() -> TableStyle:
    colors_alt = [colors.white, colors.HexColor("#F8F9FA")]
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D6E4F0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), colors_alt),
        ]
    )


def generar_pdf_sin_conciliar(
    condominio_nombre: str,
    periodo_etiqueta: str,
    pendientes: list[dict],
    pagos_periodo: list[dict],
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

    hdr = [
        "Fecha",
        "Referencia",
        "Monto (Bs.)",
        "Cédula",
        "Apartamento",
        "Observación",
        "Explicación",
    ]
    data: list[list[str]] = [hdr]

    ordenados = sorted(
        pendientes,
        key=lambda r: (str(r.get("fecha") or ""), int(r["id"])),
    )
    for mov in ordenados:
        sug = sugerir_vinculacion_desde_filas(mov, pagos_periodo)
        data.append(_fila_pendiente_tabla(mov, sug))

    story: list = [
        Paragraph("<b>Movimientos bancarios sin conciliar</b>", tit),
        Paragraph(
            f"{_esc(condominio_nombre)} — Período {_esc(periodo_etiqueta)} — "
            f"Emitido {_esc(datetime.now().strftime('%d/%m/%Y %H:%M'))}",
            sub,
        ),
    ]

    if len(data) == 1:
        story.append(
            Paragraph("<i>No hay ingresos pendientes de conciliar en este período.</i>", styles["Normal"])
        )
    else:
        story.append(
            Paragraph(
                f"<b>Total pendientes:</b> {len(ordenados)}.",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.25 * cm))
        col_w = [
            2 * cm,
            2.6 * cm,
            1.9 * cm,
            2.4 * cm,
            2 * cm,
            4 * cm,
            10 * cm,
        ]
        t = Table(data, repeatRows=1, colWidths=col_w)
        t.setStyle(_tabla_estilo())
        story.append(t)

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

    hdr = ["Fecha", "Referencia", "Cédula", "Apartamento", "Monto (Bs.)", "Estatus"]
    data: list[list[str]] = [hdr]
    def _clave_apto(m: dict) -> tuple[str, str, int]:
        p = _pago_embed(m) or {}
        u = p.get("unidades") or m.get("unidades") or {}
        apt = (u.get("codigo") or u.get("numero") or "").strip().lower()
        # Sin apartamento al final; desempate por fecha e id
        apt_ord = apt if apt else "\uffff"
        return (apt_ord, str(m.get("fecha") or ""), int(m["id"]))

    ordenados = sorted(conciliados, key=_clave_apto)
    for mov in ordenados:
        data.append(_fila_conciliado_tabla(mov))

    story: list = [
        Paragraph("<b>Movimientos conciliados</b>", tit),
        Paragraph(
            f"{_esc(condominio_nombre)} — Período {_esc(periodo_etiqueta)} — "
            f"Emitido {_esc(datetime.now().strftime('%d/%m/%Y %H:%M'))}",
            cap,
        ),
        Spacer(1, 0.2 * cm),
    ]

    if len(data) == 1:
        story.append(Paragraph("<i>No hay ingresos conciliados en este período.</i>", styles["Normal"]))
    else:
        story.append(
            Paragraph(f"<b>Total conciliados:</b> {len(ordenados)}.", styles["Normal"])
        )
        story.append(Spacer(1, 0.25 * cm))
        col_w = [2.6 * cm, 3.4 * cm, 3.2 * cm, 2.8 * cm, 2.8 * cm, 3.2 * cm]
        t = Table(data, repeatRows=1, colWidths=col_w)
        t.setStyle(_tabla_estilo())
        story.append(t)

    doc.build(story)
    return buf.getvalue()
