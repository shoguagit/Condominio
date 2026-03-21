"""
Ensamblado de documentos PDF por tipo de reporte (Fase 3).
"""

from __future__ import annotations

from datetime import datetime

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from utils.reportes_logic import map_categoria_gasto
from utils.validators import date_periodo_to_mm_yyyy
from utils.pdf_generator import (
    crear_encabezado,
    crear_fila_total,
    crear_tabla_estilo,
    formato_bs,
    formato_usd,
    generar_pdf_bytes,
    monto_bs_a_usd,
    par_bs_usd,
    pie_documento,
)


def _pct(part: float, total: float) -> str:
    if total <= 0:
        return "0.00%"
    return f"{(part / total) * 100:.2f}%"


def pdf_estado_cuenta_individual(
    condominio: dict,
    periodo_mm_yyyy: str,
    periodo_db: str,
    tasa: float,
    estado: dict,
    historico: list[dict],
) -> bytes:
    styles = getSampleStyleSheet()
    elems = crear_encabezado(condominio, periodo_mm_yyyy, "Estado de cuenta individual")
    u = estado.get("unidad") or {}
    prop = estado.get("propietario") or {}
    cod = u.get("codigo") or u.get("numero") or "—"
    ind = float(u.get("indiviso_pct") or 0)
    elems.append(Paragraph("<b>Datos del propietario</b>", styles["Heading3"]))
    elems.append(Paragraph(f"Nombre: {prop.get('nombre') or '—'}", styles["Normal"]))
    elems.append(Paragraph(f"Cédula / RIF: {prop.get('cedula') or '—'}", styles["Normal"]))
    elems.append(Paragraph(f"Unidad: {cod}", styles["Normal"]))
    elems.append(Paragraph(f"Indiviso: {ind:.2f}%", styles["Normal"]))
    elems.append(Spacer(1, 0.3 * cm))

    sa = float(estado.get("saldo_anterior_bs") or 0)
    co = float(estado.get("cuota_ordinaria_bs") or 0)
    mo = float(estado.get("mora_bs") or 0)
    tap = sa + co + mo
    pr = float(estado.get("pagos_recibidos_bs") or 0)
    sc = float(estado.get("saldo_cierre_bs") or 0)

    rows = [
        ["Concepto", "Monto Bs.", "Monto USD"],
        ["Saldo mes anterior", *par_bs_usd(sa, tasa)],
        ["Cuota ordinaria", *par_bs_usd(co, tasa)],
        ["Intereses de mora", *par_bs_usd(mo, tasa)],
        ["TOTAL A PAGAR", *par_bs_usd(tap, tasa)],
        ["Pagos recibidos", f"({formato_bs(pr)})", f"({formato_usd(monto_bs_a_usd(pr, tasa))})"],
        ["SALDO AL CIERRE", *par_bs_usd(sc, tasa)],
    ]
    elems.append(crear_tabla_estilo(rows, col_widths=[7 * cm, 4 * cm, 4 * cm]))
    elems.append(Spacer(1, 0.4 * cm))

    elems.append(Paragraph("<b>Histórico (últimos 3 períodos)</b>", styles["Heading3"]))
    hrows = [["Período", "Cuota Bs.", "Pagado Bs.", "Saldo Bs."]]
    for h in historico:
        per = date_periodo_to_mm_yyyy(str(h.get("periodo") or "")[:10])
        hrows.append(
            [
                per,
                formato_bs(float(h.get("cuota_bs") or 0)),
                formato_bs(float(h.get("pagado_bs") or 0)),
                formato_bs(float(h.get("saldo_bs") or 0)),
            ]
        )
    elems.append(crear_tabla_estilo(hrows, col_widths=[3.5 * cm, 4 * cm, 4 * cm, 4 * cm]))
    elems.extend(pie_documento())
    return generar_pdf_bytes(elems)


def pdf_morosidad(
    condominio: dict,
    periodo_mm_yyyy: str,
    tasa: float,
    filas: list[dict],
    total_unidades_activas: int,
) -> bytes:
    elems = crear_encabezado(condominio, periodo_mm_yyyy, "Reporte de morosidad")
    styles = getSampleStyleSheet()
    rows = [
        [
            "Unidad",
            "Propietario",
            "Meses atraso",
            "Deuda Bs.",
            "Mora Bs.",
            "Total Bs.",
            "Total USD",
        ]
    ]
    tot_bs = 0.0
    for r in filas:
        tb = float(r.get("total_bs") or 0)
        tot_bs += tb
        rows.append(
            [
                r.get("codigo", "—"),
                (r.get("propietario") or "—")[:28],
                str(r.get("meses_atraso", 0)),
                formato_bs(float(r.get("deuda_bs") or 0)),
                formato_bs(float(r.get("mora_bs") or 0)),
                formato_bs(tb),
                formato_usd(monto_bs_a_usd(tb, tasa)),
            ]
        )
    elems.append(crear_tabla_estilo(rows, col_widths=[2 * cm, 3.2 * cm, 1.8 * cm, 2.2 * cm, 2 * cm, 2.2 * cm, 2 * cm]))
    elems.append(Spacer(1, 0.3 * cm))
    n_m = len(filas)
    pct_m = (n_m / total_unidades_activas * 100) if total_unidades_activas else 0.0
    elems.append(
        Paragraph(
            f"<b>Totales:</b> Deuda {formato_bs(tot_bs)} — {formato_usd(monto_bs_a_usd(tot_bs, tasa))} | "
            f"Unidades en reporte: {n_m} | % morosidad (sobre activas): {pct_m:.2f}%",
            styles["Normal"],
        )
    )
    elems.extend(pie_documento())
    return generar_pdf_bytes(elems)


def pdf_balance_general(condominio: dict, periodo_mm_yyyy: str, tasa: float, bal: dict) -> bytes:
    elems = crear_encabezado(condominio, periodo_mm_yyyy, "Balance general")
    styles = getSampleStyleSheet()
    elems.append(Paragraph("<b>Ingresos del período</b>", styles["Heading3"]))
    ing = [
        ["Concepto", "Monto Bs.", "Monto USD"],
        [
            "Cuotas ordinarias cobradas",
            *par_bs_usd(float(bal.get("cuotas_cobradas_bs") or 0), tasa),
        ],
        [
            "Cobros extraordinarios",
            *par_bs_usd(float(bal.get("cobros_extraordinarios_bs") or 0), tasa),
        ],
        ["Intereses de mora", *par_bs_usd(float(bal.get("intereses_mora_bs") or 0), tasa)],
        ["TOTAL INGRESOS", *par_bs_usd(float(bal.get("total_ingresos_bs") or 0), tasa)],
    ]
    elems.append(crear_tabla_estilo(ing, col_widths=[8 * cm, 3.5 * cm, 3.5 * cm]))
    elems.append(Spacer(1, 0.3 * cm))
    elems.append(Paragraph("<b>Gastos del período</b>", styles["Heading3"]))
    gast = [["Concepto", "Monto Bs.", "Monto USD"]]
    gpc = bal.get("gastos_por_concepto") or {}
    for nom, (bs, usd) in sorted(gpc.items(), key=lambda x: -x[1][0]):
        gast.append([nom[:40], formato_bs(bs), formato_usd(usd if usd else monto_bs_a_usd(bs, tasa))])
    gast.append(
        [
            "TOTAL GASTOS",
            formato_bs(float(bal.get("total_gastos_bs") or 0)),
            formato_usd(
                float(bal.get("total_gastos_usd") or 0)
                or monto_bs_a_usd(float(bal.get("total_gastos_bs") or 0), tasa)
            ),
        ]
    )
    elems.append(crear_tabla_estilo(gast, col_widths=[8 * cm, 3.5 * cm, 3.5 * cm]))
    elems.append(Spacer(1, 0.3 * cm))
    sup_bs = float(bal.get("superavit_bs") or 0)
    label = "SUPERÁVIT" if sup_bs >= 0 else "DÉFICIT"
    elems.append(Paragraph("<b>Resultado</b>", styles["Heading3"]))
    elems.append(
        crear_fila_total(
            label,
            formato_bs(abs(sup_bs)),
            formato_usd(abs(float(bal.get("superavit_usd") or monto_bs_a_usd(sup_bs, tasa)))),
        )
    )
    elems.extend(pie_documento())
    return generar_pdf_bytes(elems)


def pdf_libro_cobros(condominio: dict, periodo_mm_yyyy: str, tasa: float, pagos: list[dict]) -> bytes:
    elems = crear_encabezado(condominio, periodo_mm_yyyy, "Libro de cobros")
    styles = getSampleStyleSheet()
    rows = [
        [
            "Fecha",
            "Unidad",
            "Propietario",
            "Método",
            "Ref.",
            "Bs.",
            "USD",
            "Estado",
        ]
    ]
    tot_met = {"transferencia": 0.0, "deposito": 0.0, "efectivo": 0.0}
    for p in pagos:
        u = p.get("unidades") or {}
        pr = p.get("propietarios") or {}
        m = float(p.get("monto_bs") or 0)
        met = (p.get("metodo") or "").lower()
        if met in tot_met:
            tot_met[met] += m
        rows.append(
            [
                str(p.get("fecha_pago") or ""),
                u.get("codigo") or u.get("numero") or "—",
                (pr.get("nombre") or "—")[:18],
                met,
                (p.get("referencia") or "")[:12],
                formato_bs(m),
                formato_usd(float(p.get("monto_usd") or 0) or monto_bs_a_usd(m, tasa)),
                p.get("estado") or "—",
            ]
        )
    elems.append(
        crear_tabla_estilo(
            rows,
            col_widths=[2 * cm, 1.8 * cm, 2.5 * cm, 2 * cm, 2 * cm, 2.2 * cm, 2 * cm, 1.8 * cm],
        )
    )
    elems.append(Spacer(1, 0.3 * cm))
    elems.append(Paragraph("<b>Totales por método</b>", styles["Heading3"]))
    sm = [
        ["Transferencias", formato_bs(tot_met["transferencia"])],
        ["Depósitos", formato_bs(tot_met["deposito"])],
        ["Efectivo", formato_bs(tot_met["efectivo"])],
        ["TOTAL", formato_bs(sum(tot_met.values()))],
    ]
    elems.append(crear_tabla_estilo(sm, col_widths=[6 * cm, 6 * cm], header_row=True))
    elems.extend(pie_documento())
    return generar_pdf_bytes(elems)


def pdf_libro_gastos(condominio: dict, periodo_mm_yyyy: str, tasa: float, movs: list[dict]) -> bytes:
    elems = crear_encabezado(condominio, periodo_mm_yyyy, "Libro de gastos")
    styles = getSampleStyleSheet()
    rows = [["Fecha", "Descripción", "Concepto", "Proveedor", "Bs.", "USD"]]
    sub = {"Mantenimiento": 0.0, "Servicios": 0.0, "Personal": 0.0, "Otros": 0.0}
    for m in movs:
        c = m.get("conceptos") or {}
        nom_c = c.get("nombre") or "—"
        cat = map_categoria_gasto(nom_c)
        sub[cat] = sub.get(cat, 0.0) + float(m.get("monto_bs") or 0)
        bs = float(m.get("monto_bs") or 0)
        rows.append(
            [
                str(m.get("fecha") or ""),
                (m.get("descripcion") or "—")[:24],
                nom_c[:20],
                "—",
                formato_bs(bs),
                formato_usd(float(m.get("monto_usd") or 0) or monto_bs_a_usd(bs, tasa)),
            ]
        )
    elems.append(crear_tabla_estilo(rows, col_widths=[2 * cm, 3.5 * cm, 3 * cm, 2 * cm, 2.5 * cm, 2.5 * cm]))
    elems.append(Spacer(1, 0.3 * cm))
    elems.append(Paragraph("<b>Subtotales por categoría</b>", styles["Heading3"]))
    sm = [["Categoría", "Monto Bs."]]
    for k, v in sub.items():
        sm.append([k, formato_bs(v)])
    sm.append(["TOTAL GASTOS", formato_bs(sum(sub.values()))])
    elems.append(crear_tabla_estilo(sm, col_widths=[6 * cm, 6 * cm]))
    elems.extend(pie_documento())
    return generar_pdf_bytes(elems)


def pdf_origen_aplicacion(
    condominio: dict, periodo_mm_yyyy: str, tasa: float, oa: dict
) -> bytes:
    elems = crear_encabezado(condominio, periodo_mm_yyyy, "Origen y aplicación de fondos")
    styles = getSampleStyleSheet()
    orig = oa.get("origen") or {}
    tot_tuple = orig.get("total") or (0, 0)
    total_o_bs = float(tot_tuple[0] or 0)
    total_o_usd = float(tot_tuple[1] or 0) if len(tot_tuple) > 1 else 0.0
    elems.append(Paragraph("<b>Origen de fondos</b>", styles["Heading3"]))
    orows = [["Concepto", "Monto Bs.", "Monto USD", "%"]]
    cu = orig.get("cuotas", (0, 0))
    ex = orig.get("extraordinarios", (0, 0))
    sa = orig.get("saldo_anterior", (0, 0))
    for label, pair in [
        ("Cuotas ordinarias cobradas", cu),
        ("Cobros extraordinarios", ex),
        ("Saldo anterior disponible", sa),
    ]:
        bs, usd = pair[0], pair[1]
        orows.append(
            [
                label,
                formato_bs(bs),
                formato_usd(usd if usd else monto_bs_a_usd(bs, tasa)),
                _pct(bs, total_o_bs) if total_o_bs else "0%",
            ]
        )
    orows.append(
        [
            "TOTAL ORIGEN",
            formato_bs(total_o_bs),
            formato_usd(total_o_usd if total_o_usd else monto_bs_a_usd(total_o_bs, tasa)),
            "100%",
        ]
    )
    elems.append(crear_tabla_estilo(orows, col_widths=[6 * cm, 3.5 * cm, 3.5 * cm, 2 * cm]))
    elems.append(Spacer(1, 0.3 * cm))

    aplic_bs = float(oa.get("total_aplicacion_bs") or 0)
    elems.append(Paragraph("<b>Aplicación de fondos</b>", styles["Heading3"]))
    arows = [["Concepto", "Monto Bs.", "Monto USD", "%"]]
    for nom, bs in oa.get("aplicacion") or []:
        arows.append(
            [
                nom[:35],
                formato_bs(bs),
                formato_usd(monto_bs_a_usd(bs, tasa)),
                _pct(bs, aplic_bs) if aplic_bs else "0%",
            ]
        )
    arows.append(
        [
            "TOTAL APLICACIÓN",
            formato_bs(aplic_bs),
            formato_usd(monto_bs_a_usd(aplic_bs, tasa)),
            "100%" if aplic_bs else "0%",
        ]
    )
    elems.append(crear_tabla_estilo(arows, col_widths=[6 * cm, 3.5 * cm, 3.5 * cm, 2 * cm]))
    elems.append(Spacer(1, 0.3 * cm))
    elems.append(
        Paragraph(
            f"<b>Resultado:</b> Fondos disponibles {formato_bs(float(oa.get('fondos_disponibles_bs') or 0))} | "
            f"Fondos aplicados {formato_bs(float(oa.get('fondos_aplicados_bs') or 0))} | "
            f"REMANENTE/DÉFICIT {formato_bs(float(oa.get('remanente_bs') or 0))}",
            styles["Normal"],
        )
    )
    elems.extend(pie_documento())
    return generar_pdf_bytes(elems)


def pdf_libro_solventes(
    condominio: dict,
    periodo_mm_yyyy: str,
    tasa: float,
    solventes: list[dict],
    total_unidades_activas: int,
) -> bytes:
    elems = crear_encabezado(
        condominio,
        periodo_mm_yyyy,
        "Libro de solventes",
        subtitulo="CERTIFICACIÓN DE SOLVENCIA",
    )
    styles = getSampleStyleSheet()
    rows = [["N°", "Unidad", "Propietario", "Cédula/RIF", "Cuota Bs.", "Pagado Bs.", "Estado"]]
    for i, s in enumerate(solventes, start=1):
        rows.append(
            [
                str(i),
                s.get("codigo", "—"),
                (s.get("propietario") or "—")[:22],
                s.get("cedula", "—"),
                formato_bs(float(s.get("cuota_bs") or 0)),
                formato_bs(float(s.get("pagado_bs") or 0)),
                s.get("estado", "Al día"),
            ]
        )
    elems.append(crear_tabla_estilo(rows, col_widths=[1 * cm, 2 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2 * cm]))
    elems.append(Spacer(1, 0.4 * cm))
    n_s = len(solventes)
    pct = (n_s / total_unidades_activas * 100) if total_unidades_activas else 0.0
    elems.append(
        Paragraph(
            f"Total unidades solventes: <b>{n_s}</b> de <b>{total_unidades_activas}</b> — "
            f"Solvencia: <b>{pct:.2f}%</b>",
            styles["Normal"],
        )
    )
    hoy = datetime.now().strftime("%d/%m/%Y")
    elems.append(Spacer(1, 0.5 * cm))
    elems.append(Paragraph(f"Certificado generado el {hoy}", styles["Normal"]))
    elems.append(Spacer(1, 1.2 * cm))
    elems.append(Paragraph("_" * 40, styles["Normal"]))
    elems.append(Paragraph("Administrador del condominio", styles["Normal"]))
    elems.extend(pie_documento())
    return generar_pdf_bytes(elems)
