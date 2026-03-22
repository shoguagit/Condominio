"""
Valores seguros para JSON/PostgREST (Supabase Python client).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd


def json_safe_date(value: Any) -> str:
    """
    Convierte fecha a 'YYYY-MM-DD' para insert/update vía JSON.
    Cubre date, datetime, pandas.Timestamp y strings.
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    s = str(value).strip()
    if not s:
        return ""
    if "T" in s:
        return s.split("T", 1)[0][:10]
    return s[:10] if len(s) >= 10 else s


def json_safe_periodo(value: Any) -> str:
    """Período tipo DATE en BD: string YYYY-MM-DD."""
    return json_safe_date(value) if value else ""
