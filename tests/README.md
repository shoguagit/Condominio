# Tests

## Mismo Python que las dependencias

El comando `pytest` del PATH puede apuntar a **otro** Python que el de tu `.venv`
(por ejemplo Homebrew `python3.12` mientras el venv es 3.14). Entonces verás
`ModuleNotFoundError: reportlab` aunque `pip install reportlab` haya funcionado.

**Recomendado:**

```bash
# Activar venv y usar SIEMPRE el python del venv para pytest
source .venv/bin/activate
python -m pytest tests/unit/test_reportes.py -v
```

O sin activar:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests/unit -v
```

Los tests de `test_reportes.py` hacen `pytest.importorskip("reportlab")`: si falta
reportlab en ese intérprete, el archivo se omite (skipped) en lugar de fallar la recolección.
