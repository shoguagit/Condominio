"""Tests unitarios bank_parser (sin BD)."""

from datetime import date

import pandas as pd
import pytest

from utils.bank_parser import (
    MovimientoParsed,
    detectar_banco,
    es_duplicado,
    limpiar_monto,
)


# ── DETECCIÓN DE BANCO ──────────────────────────────────────


def test_detectar_bdv():
    df = pd.DataFrame(
        [
            [
                "fecha",
                "referencia",
                "concepto",
                "saldo",
                "monto",
                "tipoMovimiento",
                "rif",
                "numeroCuenta",
            ]
        ]
    )
    assert detectar_banco(df) == "BDV"


def test_detectar_banesco():
    df = pd.DataFrame(
        [
            [
                "Fecha",
                "Referencia",
                "Descripción",
                "Monto",
                "Balance",
            ]
        ]
    )
    assert detectar_banco(df) == "Banesco"


def test_detectar_bancamiga():
    df = pd.DataFrame(
        [
            [None, None, None, None, None, None, None],
            [
                "Bancamiga Banco Universal",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
        ]
    )
    assert detectar_banco(df) == "Bancamiga"


def test_detectar_mercantil():
    df = pd.DataFrame(
        [
            [None, None, None, None],
            [None, None, "Monto total:", -4629.80],
        ]
    )
    assert detectar_banco(df) == "Mercantil"


def test_detectar_banco_desconocido_lanza_error():
    df = pd.DataFrame([["col1", "col2", "col3"]])
    with pytest.raises(ValueError):
        detectar_banco(df)


# ── LIMPIEZA DE MONTOS ──────────────────────────────────────


def test_limpiar_monto_europeo_positivo():
    assert limpiar_monto("32.760,00", "europeo") == 32760.0


def test_limpiar_monto_europeo_negativo():
    assert limpiar_monto("-4.629,80", "europeo") == pytest.approx(-4629.80)


def test_limpiar_monto_estandar_positivo():
    assert limpiar_monto("1251334.05", "estandar") == 1251334.05


def test_limpiar_monto_estandar_con_comas():
    assert limpiar_monto("1,251,334.05", "estandar") == 1251334.05


def test_limpiar_monto_entero():
    assert limpiar_monto(68000, "estandar") == 68000.0


# ── ANTI-DUPLICADOS ─────────────────────────────────────────


def test_duplicado_con_referencia_real():
    mov = MovimientoParsed(
        fecha=date(2026, 3, 5),
        referencia="00471832",
        concepto="Pago Apto 1A",
        monto=252000.0,
        es_ingreso=True,
        banco_detectado="BDV",
    )
    existentes = [
        {
            "referencia": "00471832",
            "monto": 252000.0,
            "fecha": "2026-03-05",
            "concepto": "Pago Apto 1A",
        }
    ]
    assert es_duplicado(mov, existentes) is True


def test_duplicado_con_referencia_cero():
    mov = MovimientoParsed(
        fecha=date(2026, 1, 30),
        referencia="0",
        concepto="COM.SERV.MTTO CTA",
        monto=8.0,
        es_ingreso=False,
        banco_detectado="Banesco",
    )
    existentes = [
        {
            "referencia": "0",
            "monto": 8.0,
            "fecha": "2026-01-30",
            "concepto": "COM.SERV.MTTO CTA",
        }
    ]
    assert es_duplicado(mov, existentes) is True


def test_no_duplicado_misma_ref_distinto_monto():
    mov = MovimientoParsed(
        fecha=date(2026, 3, 5),
        referencia="00471832",
        concepto="Pago Apto 1A",
        monto=126000.0,
        es_ingreso=True,
        banco_detectado="BDV",
    )
    existentes = [
        {
            "referencia": "00471832",
            "monto": 252000.0,
            "fecha": "2026-03-05",
            "concepto": "Pago Apto 1A",
        }
    ]
    assert es_duplicado(mov, existentes) is False


def test_no_duplicado_ref_cero_distinto_concepto():
    mov = MovimientoParsed(
        fecha=date(2026, 1, 30),
        referencia="0",
        concepto="EMISION DE ESTADO DE CUENTA",
        monto=8.0,
        es_ingreso=False,
        banco_detectado="Banesco",
    )
    existentes = [
        {
            "referencia": "0",
            "monto": 8.0,
            "fecha": "2026-01-30",
            "concepto": "COM.SERV.MTTO CTA",
        }
    ]
    assert es_duplicado(mov, existentes) is False
