"""Reglas de registro de pago (referencia en transferencia)."""
import pytest

from utils.error_handler import DatabaseError
from repositories.pago_repository import PagoRepository


class _FakeInsert:
    def __init__(self, payload: dict):
        self._payload = payload

    def execute(self):
        class R:
            pass

        r = R()
        r.data = [{**{"id": 1}, **self._payload}]
        return r


class _FakeTable:
    def insert(self, data):
        return _FakeInsert(data)


class _FakeClient:
    def table(self, name):
        return _FakeTable()


def test_transferencia_sin_referencia_falla():
    repo = PagoRepository(_FakeClient())
    data = {
        "condominio_id": 1,
        "unidad_id": 1,
        "periodo": "2026-03-01",
        "fecha_pago": "2026-03-18",
        "monto_bs": 100.0,
        "metodo": "transferencia",
        "referencia": "",
    }
    with pytest.raises(DatabaseError) as exc:
        repo.create(data)
    assert "referencia" in str(exc.value).lower()


def test_deposito_sin_referencia_ok():
    repo = PagoRepository(_FakeClient())
    data = {
        "condominio_id": 1,
        "unidad_id": 1,
        "periodo": "2026-03-01",
        "fecha_pago": "2026-03-18",
        "monto_bs": 50.0,
        "metodo": "deposito",
        "referencia": None,
    }
    out = repo.create(data)
    assert out.get("id") == 1
