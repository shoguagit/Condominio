"""Coincidencia cédula banco vs BD (repositorio conciliación cédula)."""

from repositories.conciliacion_cedula_repository import (
    _cedula_coincide_lista,
    _cedula_comparable_key,
)


def test_comparable_key_leading_zeros():
    assert _cedula_comparable_key("V05220576") == _cedula_comparable_key("V5220576")


def test_comparable_key_dots_and_dashes():
    a = _cedula_comparable_key("V-05.220.576")
    b = _cedula_comparable_key("V05220576")
    assert a == b


def test_coincide_lista():
    assert _cedula_coincide_lista(["V15834987"], "V15834987")
    assert _cedula_coincide_lista(["V15834987"], "V-15834987")
    assert _cedula_coincide_lista(["V05220576"], "V5220576")
    assert not _cedula_coincide_lista(["V11111111"], "V22222222")
