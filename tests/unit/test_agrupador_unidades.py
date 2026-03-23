"""Tests para utils/agrupador_unidades.py."""

from __future__ import annotations

from utils.agrupador_unidades import agrupar_unidades, detectar_grupo, detectar_numero
from utils.estado_cuenta_coherencia import calcular_alertas_coherencia


def test_detectar_grupo_letra_numero():
    assert detectar_grupo("A01") == "A"
    assert detectar_grupo("M04") == "M"
    assert detectar_grupo("AB12") == "A"


def test_detectar_grupo_numero_letra():
    assert detectar_grupo("01A") == "A"
    assert detectar_grupo("12B") == "B"


def test_detectar_grupo_solo_numero():
    assert detectar_grupo("101") == "100"
    assert detectar_grupo("205") == "200"


def test_detectar_grupo_sin_patron():
    assert detectar_grupo("") == "SIN_GRUPO"


def test_detectar_numero_extrae():
    assert detectar_numero("A01") == "01"
    assert detectar_numero("B12") == "12"
    assert detectar_numero("101") == "101"


def test_agrupar_unidades_agrupa_correctamente():
    unidades = [
        {
            "unidad_id": 1,
            "unidad_codigo": "A01",
            "propietario_nombre": "Ana",
            "propietario_email": "ana@x.com",
        },
        {
            "unidad_id": 2,
            "unidad_codigo": "A02",
            "propietario_nombre": "Bob",
            "propietario_email": None,
        },
        {
            "unidad_id": 3,
            "unidad_codigo": "B01",
            "propietario_nombre": "Carlos",
            "propietario_email": "c@x.com",
        },
    ]
    grupos = agrupar_unidades(unidades)
    assert "A" in grupos
    assert "B" in grupos
    assert grupos["A"].total == 2
    assert grupos["A"].con_email == 1
    assert grupos["B"].con_email == 1


def test_coherencia_alerta_primer_mes():
    def fetch(uid: int, cid: int, per: str):
        if uid == 1:
            return {
                "meses_acumulados": 1,
                "acumulado_usd": 10.0,
                "cuota_usd": 5.0,
            }
        return None

    unidades = [
        {"unidad_id": 1, "unidad_codigo": "A1", "propietario_nombre": "X"},
    ]
    alertas = calcular_alertas_coherencia(unidades, 1, "2026-03-01", fetch)
    assert len(alertas) == 1
    assert "Diferencia (USD)" in alertas[0]


def test_coherencia_sin_alerta_cuando_coincide():
    def fetch(uid: int, cid: int, per: str):
        return {
            "meses_acumulados": 1,
            "acumulado_usd": 100.0,
            "cuota_usd": 100.0,
        }

    unidades = [{"unidad_id": 1, "unidad_codigo": "A1", "propietario_nombre": "Y"}]
    alertas = calcular_alertas_coherencia(unidades, 1, "2026-01-01", fetch)
    assert alertas == []


def test_coherencia_ignora_si_no_es_primer_mes():
    def fetch(uid: int, cid: int, per: str):
        return {
            "meses_acumulados": 3,
            "acumulado_usd": 999.0,
            "cuota_usd": 1.0,
        }

    unidades = [{"unidad_id": 1, "unidad_codigo": "A1", "propietario_nombre": "Z"}]
    assert calcular_alertas_coherencia(unidades, 1, "2026-01-01", fetch) == []
