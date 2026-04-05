"""Resolver BCV: prioriza filas simuladas de repositorio (sin Supabase)."""

from datetime import date

import pytest

from utils import tasa_bcv_resolver as tr


def test_resolver_acierta_en_primera_consulta_bd(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Repo:
        def get_last_on_or_before(self, fp: date):
            return (date(2026, 3, 10), 400.0)

        def merge_from_api(self) -> int:
            raise AssertionError("no debe llamar API si hay fila en BD")

        def get_earliest(self):
            raise AssertionError("no debe pedir earliest")

        def list_sorted_pairs(self):
            raise AssertionError("no debe listar")

    monkeypatch.setattr(tr, "TasaBcvRepository", lambda _c: _Repo())

    r, meta = tr.resolver_tasa_para_fecha(None, date(2026, 3, 10))  # type: ignore[arg-type]
    assert r == 400.0
    assert meta == "2026-03-10"


def test_resolver_fin_de_semana_usa_ultimo_dia_en_bd(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Repo:
        def get_last_on_or_before(self, fp: date):
            return (date(2026, 3, 14), 450.0)

        def merge_from_api(self) -> int:
            raise AssertionError("no debe llamar API")

        def get_earliest(self):
            raise AssertionError("no debe pedir earliest")

        def list_sorted_pairs(self):
            raise AssertionError("no debe listar")

    monkeypatch.setattr(tr, "TasaBcvRepository", lambda _c: _Repo())

    r, meta = tr.resolver_tasa_para_fecha(None, date(2026, 3, 16))  # type: ignore[arg-type]
    assert r == 450.0
    assert "2026-03-14" in meta


def test_resolver_vacia_llama_api_y_reintenta(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    class _Repo:
        def get_last_on_or_before(self, fp: date):
            calls["n"] += 1
            if calls["n"] == 1:
                return None
            return (date(2026, 1, 5), 300.0)

        def merge_from_api(self) -> int:
            return 10

        def get_earliest(self):
            return None

        def list_sorted_pairs(self):
            return []

    monkeypatch.setattr(tr, "TasaBcvRepository", lambda _c: _Repo())

    r, meta = tr.resolver_tasa_para_fecha(None, date(2026, 1, 5))  # type: ignore[arg-type]
    assert r == 300.0
    assert calls["n"] == 2
