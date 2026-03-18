"""
Obtiene la tasa oficial USD/VES del Banco Central de Venezuela.

Estrategia (en orden de prioridad):
  1. Scraping directo de bcv.org.ve  →  div#dolar strong
  2. API pública alternativa          →  ve.dolarapi.com (sin auth, JSON)
  3. Devuelve 0.0 si ambas fallan    →  el operador puede ingresar manualmente
"""

import re

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ModuleNotFoundError:
    _HAS_STREAMLIT = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_rate(text: str) -> float:
    """Limpia y convierte el texto de la tasa (ej. '438,20500000') a float."""
    clean = text.strip().replace("\xa0", "").replace(" ", "")
    clean = re.sub(r"[Bb][Ss]\.?\s*", "", clean)   # quita "Bs."
    clean = clean.replace(",", ".")                  # coma decimal → punto
    # Si hay múltiples puntos queda solo el último como decimal
    parts = clean.split(".")
    if len(parts) > 2:
        clean = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return round(float(clean), 4)
    except ValueError:
        return 0.0


def _fetch_from_bcv() -> float:
    """Scraping de la página principal de BCV."""
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-VE,es;q=0.9",
        }
        resp = requests.get(
            "https://www.bcv.org.ve/",
            headers=headers,
            timeout=12,
            verify=True,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Selector principal: <div id="dolar"> ... <strong>438,20...</strong>
        div = soup.find("div", {"id": "dolar"})
        if div:
            strong = div.find("strong")
            if strong:
                rate = _parse_rate(strong.get_text())
                if rate > 0:
                    return rate

        # Fallback: buscar cualquier strong que parezca tasa USD (>10)
        for tag in soup.find_all("strong"):
            txt = tag.get_text(strip=True)
            val = _parse_rate(txt)
            if val > 10:
                return val

    except Exception:
        pass
    return 0.0


def _fetch_from_dolarapi() -> float:
    """API alternativa gratuita: ve.dolarapi.com."""
    try:
        import requests

        resp = requests.get(
            "https://ve.dolarapi.com/v1/dolares/oficial",
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        # Estructura: {"promedio": 438.205, "fechaActualizacion": "..."}
        promedio = data.get("promedio") or data.get("tasa") or data.get("price")
        if promedio:
            return round(float(promedio), 4)
    except Exception:
        pass
    return 0.0


# ── API pública ────────────────────────────────────────────────────────────────

def _fetch_bcv_rate_uncached() -> tuple[float, str]:
    """
    Devuelve (tasa, fuente).  La tasa es 0.0 si no pudo obtenerse.
    """
    # Intento 1: BCV directo
    rate = _fetch_from_bcv()
    if rate > 0:
        return rate, "BCV oficial"

    # Intento 2: API alternativa
    rate = _fetch_from_dolarapi()
    if rate > 0:
        return rate, "dolarapi.com"

    return 0.0, "no disponible"


# Versión con caché de Streamlit (1 hora) — usada en producción
if _HAS_STREAMLIT:
    fetch_bcv_rate = st.cache_data(ttl=3600, show_spinner=False)(_fetch_bcv_rate_uncached)
else:
    fetch_bcv_rate = _fetch_bcv_rate_uncached
