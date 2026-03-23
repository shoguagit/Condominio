"""Tests para utils/pdf_combinado.py."""

from __future__ import annotations

import io

import pytest

pypdf = pytest.importorskip("pypdf")

from utils.pdf_combinado import combinar_pdfs


def _pdf_una_pagina_vacia() -> bytes:
    w = pypdf.PdfWriter()
    w.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_combinar_pdfs_vacio():
    assert combinar_pdfs([]) == b""
    assert combinar_pdfs([b"not-a-pdf"]) == b""


def test_combinar_dos_pdfs():
    a = _pdf_una_pagina_vacia()
    b = _pdf_una_pagina_vacia()
    out = combinar_pdfs([a, b])
    assert out.startswith(b"%PDF")
    r = pypdf.PdfReader(io.BytesIO(out))
    assert len(r.pages) == 2
