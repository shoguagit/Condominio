"""Serialización segura para Supabase JSON."""

from datetime import date, datetime

import pytest

from utils.supabase_compat import json_safe_date, json_safe_periodo


def test_json_safe_date_desde_date():
    assert json_safe_date(date(2026, 3, 3)) == "2026-03-03"


def test_json_safe_date_desde_datetime():
    assert json_safe_date(datetime(2026, 3, 3, 15, 30)) == "2026-03-03"


def test_json_safe_date_desde_timestamp():
    pd = pytest.importorskip("pandas")
    assert json_safe_date(pd.Timestamp("2026-03-03")) == "2026-03-03"


def test_json_safe_periodo_string():
    assert json_safe_periodo("2026-03-01") == "2026-03-01"
