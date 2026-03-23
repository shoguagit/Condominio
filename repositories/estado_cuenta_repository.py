"""
Datos para estados de cuenta PDF masivos (Fase 5-C) y configuración de recibo.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.request import Request, urlopen

from supabase import Client

from utils.error_handler import safe_db_operation
from utils.pdf_generator import monto_bs_a_usd, rif_condominio_texto

logger = logging.getLogger(__name__)

_MESES = (
    "",
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
)


def _normaliza_periodo_sql_date(periodo: str) -> tuple[str, str]:
    """
    Normaliza el período para columnas PostgreSQL **DATE**.

    Solo se debe filtrar con **YYYY-MM-DD**. Valores como ``2026-03`` provocan
    ``invalid input syntax for type date`` (22007).

    Retorna:
        - ``periodo_full``: siempre ``YYYY-MM-DD`` (día 01 si el input era ``YYYY-MM``).
        - ``periodo_ym``: ``YYYY-MM`` para etiquetas / logs.
    """
    s = (periodo or "").strip()
    if not s:
        return "", ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        full = s[:10]
        ym = full[:7]
    else:
        ym = s[:7] if len(s) >= 7 else s[:10]
        if len(ym) == 7 and ym[4] == "-":
            full = f"{ym}-01"
        else:
            full = s[:10]
    return full, ym


def periodo_db_a_nombre(periodo_db: str) -> str:
    s = (periodo_db or "")[:10]
    try:
        y, m, _ = s.split("-")
        mi = int(m)
        if 1 <= mi <= 12:
            return f"{_MESES[mi]} {y}"
    except (ValueError, IndexError):
        pass
    return s or "—"


class EstadoCuentaRepository:
    def __init__(self, client: Client):
        self.client = client
        self._condo = "condominios"
        self._uni = "unidades"
        self._mov = "movimientos"
        self._cuo = "cuotas_unidad"
        self._proc = "procesos_mensuales"

    def obtener_logo_bytes(self, logo_url: str | bytes | None) -> bytes | None:
        """
        Retorna bytes para el generador PDF.
        - data URL: el texto UTF-8 codificado en bytes (lo procesa _logo_bytes_a_image).
        - http(s): bytes crudos de la imagen descargada.
        """
        if not logo_url:
            return None
        try:
            logo_str: str
            if isinstance(logo_url, bytes):
                logo_str = logo_url.decode("utf-8")
            else:
                logo_str = str(logo_url).strip()
            logo_str = logo_str.lstrip("\ufeff")
            if not logo_str:
                return None
            low = logo_str.lower()
            if low.startswith("data:"):
                return logo_str.encode("utf-8")
            if low.startswith("http://") or low.startswith("https://"):
                req = Request(logo_str, headers={"User-Agent": "CondominioApp/1.0"})
                with urlopen(req, timeout=15) as resp:
                    return resp.read()
            return None
        except Exception as e:
            logger.warning("obtener_logo_bytes: %s", e)
            return None

    @safe_db_operation("estado_cuenta.obtener_config_condominio_pdf")
    def obtener_config_condominio_pdf(self, condominio_id: int) -> dict | None:
        rows = (
            self.client.table(self._condo)
            .select(
                "id, nombre, email, numero_documento, logo_url, "
                "pie_pagina_titular, pie_pagina_cuerpo, "
                "smtp_email, smtp_app_password, smtp_nombre_remitente, "
                "tesorero_email, tasa_cambio, "
                "tipos_documento(nombre)"
            )
            .eq("id", int(condominio_id))
            .limit(1)
            .execute()
        ).data or []
        if not rows:
            return None
        r = rows[0]
        rif = rif_condominio_texto(r)
        return {
            "nombre": (r.get("nombre") or "").strip() or "—",
            "rif": rif,
            "email": (r.get("email") or "").strip() or "—",
            "logo_url": r.get("logo_url"),
            "pie_pagina_titular": r.get("pie_pagina_titular") or "",
            "pie_pagina_cuerpo": r.get("pie_pagina_cuerpo") or "",
            "smtp_email": (r.get("smtp_email") or "").strip(),
            "smtp_app_password": r.get("smtp_app_password") or "",
            "smtp_nombre_remitente": (r.get("smtp_nombre_remitente") or "").strip()
            or "Administración del Condominio",
            "tesorero_email": (r.get("tesorero_email") or "").strip(),
            "tasa_cambio": float(r.get("tasa_cambio") or 0),
        }

    @safe_db_operation("estado_cuenta.actualizar_pie_pagina")
    def actualizar_pie_pagina(
        self, condominio_id: int, titular: str, cuerpo: str
    ) -> dict:
        resp = (
            self.client.table(self._condo)
            .update(
                {
                    "pie_pagina_titular": titular or "",
                    "pie_pagina_cuerpo": cuerpo or "",
                }
            )
            .eq("id", int(condominio_id))
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else {}

    @safe_db_operation("estado_cuenta.actualizar_logo_url")
    def actualizar_logo_url(self, condominio_id: int, logo_url: str | None) -> dict:
        resp = (
            self.client.table(self._condo)
            .update({"logo_url": logo_url})
            .eq("id", int(condominio_id))
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else {}

    @safe_db_operation("estado_cuenta.actualizar_tesorero_email")
    def actualizar_tesorero_email(self, condominio_id: int, email: str | None) -> dict:
        em = (email or "").strip() or None
        resp = (
            self.client.table(self._condo)
            .update({"tesorero_email": em})
            .eq("id", int(condominio_id))
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else {}

    @safe_db_operation("estado_cuenta.listar_todas_unidades")
    def listar_todas_unidades(self, condominio_id: int) -> list[dict]:
        """
        Todas las unidades activas con datos de propietario (con o sin correo).
        propietario_email: str, lista de str si hay varios separados por coma/; o None.
        """
        rows = (
            self.client.table(self._uni)
            .select("id, codigo, numero, activo, indiviso_pct, propietarios(nombre, correo)")
            .eq("condominio_id", int(condominio_id))
            .eq("activo", True)
            .execute()
        ).data or []
        out: list[dict] = []
        for r in rows:
            p = r.get("propietarios") or {}
            if not isinstance(p, dict):
                p = {}
            cod = (r.get("codigo") or r.get("numero") or str(r.get("id")) or "—").strip()
            raw_correo = (p.get("correo") or p.get("email") or "").strip()
            prop_email: str | list[str] | None
            if not raw_correo:
                prop_email = None
            else:
                parts = [x.strip() for x in re.split(r"[,;]+", raw_correo) if x.strip()]
                if not parts:
                    prop_email = None
                elif len(parts) == 1:
                    prop_email = parts[0]
                else:
                    prop_email = parts
            out.append(
                {
                    "unidad_id": int(r["id"]),
                    "unidad_codigo": cod,
                    "propietario_nombre": (p.get("nombre") or "—").strip(),
                    "propietario_email": prop_email,
                    "indiviso_pct": float(r.get("indiviso_pct") or 0),
                }
            )
        out.sort(key=lambda x: (x["unidad_codigo"].lower()))
        return out

    @safe_db_operation("estado_cuenta.listar_unidades_con_email")
    def listar_unidades_con_email(self, condominio_id: int) -> list[dict]:
        rows = (
            self.client.table(self._uni)
            .select("id, codigo, numero, activo, propietarios(nombre, correo)")
            .eq("condominio_id", int(condominio_id))
            .eq("activo", True)
            .execute()
        ).data or []
        out: list[dict] = []
        for r in rows:
            p = r.get("propietarios") or {}
            if not isinstance(p, dict):
                continue
            em = (p.get("correo") or p.get("email") or "").strip()
            if not em:
                continue
            cod = (r.get("codigo") or r.get("numero") or str(r.get("id")) or "—").strip()
            out.append(
                {
                    "unidad_id": int(r["id"]),
                    "unidad_codigo": cod,
                    "propietario_nombre": (p.get("nombre") or "—").strip(),
                    "propietario_email": em,
                }
            )
        out.sort(key=lambda x: x["unidad_codigo"].lower())
        return out

    @safe_db_operation("estado_cuenta.listar_unidades_sin_email")
    def listar_unidades_sin_email(self, condominio_id: int) -> list[dict]:
        rows = (
            self.client.table(self._uni)
            .select("id, codigo, numero, activo, propietarios(nombre, correo)")
            .eq("condominio_id", int(condominio_id))
            .eq("activo", True)
            .execute()
        ).data or []
        out: list[dict] = []
        for r in rows:
            p = r.get("propietarios") or {}
            if not isinstance(p, dict):
                continue
            em = (p.get("correo") or p.get("email") or "").strip()
            if em:
                continue
            cod = (r.get("codigo") or r.get("numero") or str(r.get("id")) or "—").strip()
            out.append(
                {
                    "unidad_id": int(r["id"]),
                    "unidad_codigo": cod,
                    "propietario_nombre": (p.get("nombre") or "—").strip(),
                }
            )
        out.sort(key=lambda x: x["unidad_codigo"].lower())
        return out

    @safe_db_operation("estado_cuenta.obtener_datos_unidad_periodo")
    def obtener_datos_unidad_periodo(
        self,
        unidad_id: int,
        condominio_id: int,
        periodo: str,
        tasa_cambio: float = 0.0,
    ) -> dict[str, Any] | None:
        """
        Datos financieros y de unidad para PDF (USD principal, Bs. referencia en cuota_bs).

        ``tasa_cambio``: si > 0, se usa para convertir Bs.→USD (p. ej. ``st.session_state``).
        Si es 0, se lee ``condominios.tasa_cambio``; si sigue en 0, se usa 1 y se registra warning
        (evita división por cero y montos USD siempre en cero).
        """
        periodo_full, periodo_ym = _normaliza_periodo_sql_date(str(periodo))
        logger.info(
            "obtener_datos_unidad_periodo: periodo_recibido=%r unidad_id=%r periodo_sql_date=%r",
            periodo,
            unidad_id,
            periodo_full,
        )
        tasa = float(tasa_cambio or 0)
        if tasa <= 0:
            tasa_row = (
                self.client.table(self._condo)
                .select("tasa_cambio")
                .eq("id", int(condominio_id))
                .limit(1)
                .execute()
            ).data or [{}]
            tasa = float((tasa_row[0] or {}).get("tasa_cambio") or 0)
        if tasa <= 0:
            logger.warning(
                "obtener_datos_unidad_periodo: tasa_cambio es 0 para condominio_id=%s; usando 1.0",
                condominio_id,
            )
            tasa = 1.0

        urows = (
            self.client.table(self._uni)
            .select("id, codigo, numero, indiviso_pct, propietarios(nombre, correo)")
            .eq("id", int(unidad_id))
            .eq("condominio_id", int(condominio_id))
            .limit(1)
            .execute()
        ).data or []
        if not urows:
            return None
        u = urows[0]
        p = u.get("propietarios") or {}
        if not isinstance(p, dict):
            p = {}
        cod = (u.get("codigo") or u.get("numero") or "—").strip()

        if not periodo_full:
            logger.warning("obtener_datos_unidad_periodo: período vacío tras normalizar")
            return None

        crows = (
            self.client.table(self._cuo)
            .select("*")
            .eq("unidad_id", int(unidad_id))
            .eq("condominio_id", int(condominio_id))
            .eq("periodo", periodo_full)
            .limit(1)
            .execute()
        ).data or []
        logger.info(
            "obtener_datos_unidad_periodo: fila_cuota_encontrada=%s periodo_en_fila=%r",
            bool(crows),
            (crows[0].get("periodo") if crows else None),
        )
        if not crows:
            logger.warning(
                "obtener_datos_unidad_periodo: sin cuota unidad_id=%s condominio_id=%s periodo_sql=%s",
                unidad_id,
                condominio_id,
                periodo_full,
            )
            try:
                dbg = (
                    self.client.table(self._cuo)
                    .select("periodo, unidad_id, cuota_calculada_bs")
                    .eq("condominio_id", int(condominio_id))
                    .limit(5)
                    .execute()
                )
                logger.warning(
                    "obtener_datos_unidad_periodo: muestra cuotas condominio (máx 5): %r",
                    dbg.data or [],
                )
            except Exception as e:
                logger.warning("obtener_datos_unidad_periodo: consulta debug cuotas falló: %s", e)
            return None
        c = crows[0]

        cuota_bs = float(c.get("cuota_calculada_bs") or 0)
        cuota_usd = monto_bs_a_usd(cuota_bs, tasa)
        if cuota_usd == 0 and cuota_bs > 0 and tasa > 0:
            cuota_usd = round(float(cuota_bs) / float(tasa), 2)
        elif cuota_usd == 0:
            try:
                v_bd = float(c.get("cuota_usd") or 0)
                if v_bd > 0:
                    cuota_usd = round(v_bd, 2)
            except (TypeError, ValueError):
                pass

        saldo_ant_bs = float(c.get("saldo_anterior_bs") or 0)
        mora_bs = float(c.get("mora_bs") or 0)
        cobros_bs = float(c.get("cobros_extraordinarios") or 0)
        pagos_bs = float(c.get("pagos_mes_bs") or 0)
        total_pagar_bs = float(c.get("total_a_pagar_bs") or 0)

        saldo_anterior_usd = monto_bs_a_usd(saldo_ant_bs, tasa)
        mora_usd = monto_bs_a_usd(mora_bs, tasa)
        cobros_ext_usd = monto_bs_a_usd(cobros_bs, tasa)
        pagos_recibidos_usd = monto_bs_a_usd(pagos_bs, tasa)
        saldo_actual_usd = monto_bs_a_usd(total_pagar_bs, tasa)

        mrows = (
            self.client.table(self._mov)
            .select("monto_bs, conceptos(nombre)")
            .eq("condominio_id", int(condominio_id))
            .eq("periodo", periodo_full)
            .eq("tipo", "egreso")
            .execute()
        ).data or []

        agg: dict[str, float] = {}
        for m in mrows:
            conc = m.get("conceptos") or {}
            nom = (conc.get("nombre") if isinstance(conc, dict) else None) or "Sin concepto"
            agg[nom] = agg.get(nom, 0.0) + float(m.get("monto_bs") or 0)

        gastos_detalle: list[dict[str, Any]] = []
        total_comun_bs = 0.0
        for nombre, m_bs in sorted(agg.items(), key=lambda x: x[0].lower()):
            mud = monto_bs_a_usd(m_bs, tasa)
            total_comun_bs += m_bs
            gastos_detalle.append({"concepto": nombre, "monto_usd": round(mud, 2)})

        if not gastos_detalle:
            gastos_detalle.append({"concepto": "Sin egresos registrados en el período", "monto_usd": 0.0})

        proc_rows = (
            self.client.table(self._proc)
            .select("fondo_reserva_bs")
            .eq("condominio_id", int(condominio_id))
            .eq("periodo", periodo_full)
            .limit(1)
            .execute()
        ).data or []
        fondo_bs_cfg = float(proc_rows[0].get("fondo_reserva_bs") or 0) if proc_rows else 0.0
        total_comun_usd = monto_bs_a_usd(total_comun_bs, tasa)
        if fondo_bs_cfg > 0:
            fondo_reserva_usd = monto_bs_a_usd(fondo_bs_cfg, tasa)
        else:
            fondo_reserva_usd = round(0.10 * total_comun_usd, 2)
        total_gastos_usd = round(total_comun_usd + fondo_reserva_usd, 2)

        hrows = (
            self.client.table(self._cuo)
            .select("periodo, total_a_pagar_bs")
            .eq("unidad_id", int(unidad_id))
            .eq("condominio_id", int(condominio_id))
            .lte("periodo", periodo_full)
            .order("periodo", desc=False)
            .execute()
        ).data or []

        meses_con_deuda = 0
        for h in hrows:
            tp = float(h.get("total_a_pagar_bs") or 0)
            if tp > 0:
                meses_con_deuda += 1
        acumulado_usd = round(
            saldo_anterior_usd + cuota_usd + mora_usd + cobros_ext_usd,
            2,
        )
        meses_acumulados = max(meses_con_deuda, 1)

        saldo_ant_edificio = saldo_anterior_usd
        deducciones_edificio = 0.0
        ingresos_edificio = pagos_recibidos_usd
        saldo_act_edificio = saldo_actual_usd

        periodo_ref = periodo_full or periodo_ym or str(c.get("periodo") or "")[:10]

        return {
            "propietario_nombre": (p.get("nombre") or "—").strip(),
            "propietario_email": (p.get("correo") or p.get("email") or "").strip(),
            "unidad_codigo": cod,
            "indiviso_pct": float(u.get("indiviso_pct") or 0),
            "periodo_nombre": periodo_db_a_nombre(periodo_ref),
            "tasa_cambio": tasa,
            "cuota_bs": round(cuota_bs, 2),
            "cuota_usd": round(cuota_usd, 2),
            "saldo_anterior_usd": round(saldo_anterior_usd, 2),
            "mora_usd": round(mora_usd, 2),
            "cobros_ext_usd": round(cobros_ext_usd, 2),
            "pagos_recibidos_usd": round(pagos_recibidos_usd, 2),
            "saldo_actual_usd": round(saldo_actual_usd, 2),
            "fondo_reserva_usd": round(fondo_reserva_usd, 2),
            "total_gastos_usd": round(total_gastos_usd, 2),
            "acumulado_usd": round(float(acumulado_usd), 2),
            "meses_acumulados": int(meses_acumulados),
            "gastos_detalle": gastos_detalle,
            "saldo_ant_edificio": round(saldo_ant_edificio, 2),
            "deducciones_edificio": round(deducciones_edificio, 2),
            "ingresos_edificio": round(ingresos_edificio, 2),
            "saldo_act_edificio": round(saldo_act_edificio, 2),
            "total_comun_usd": round(total_comun_usd, 2),
            "emision_str": datetime.now().strftime("%d-%m-%Y"),
            "mes_corto": _mes_corto_seguro(periodo_ref),
        }


def _mes_corto_seguro(periodo_db: str) -> str:
    try:
        m = int(str(periodo_db)[5:7])
        if 1 <= m <= 12:
            return _MESES[m]
    except (ValueError, IndexError):
        pass
    return ""
