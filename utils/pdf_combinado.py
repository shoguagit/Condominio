"""
Combinar varios PDF en uno (estados de cuenta masivos).
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def combinar_pdfs(lista_pdf_bytes: list[bytes]) -> bytes:
    """
    Combina múltiples PDFs en uno solo (pypdf).
    Nunca propaga excepciones: retorna bytes vacíos si falla o no hay PDFs válidos.
    """
    validos = [b for b in lista_pdf_bytes if b and len(b) > 4 and b[:4] == b"%PDF"]
    if not validos:
        return b""
    try:
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for raw in validos:
            try:
                reader = PdfReader(io.BytesIO(raw))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                logger.warning("combinar_pdfs: omitiendo un PDF: %s", e)
                continue
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception as e:
        logger.warning("combinar_pdfs: %s", e)
        return b""
