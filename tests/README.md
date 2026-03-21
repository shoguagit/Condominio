# Tests

## Mismo Python que las dependencias

El comando `pytest` del PATH puede apuntar a **otro** Python que el de tu `.venv`
(por ejemplo Homebrew `python3.12` mientras el venv es 3.14). Entonces verás
`ModuleNotFoundError: reportlab` aunque `pip install reportlab` haya funcionado.

**Recomendado:**

```bash
# Activar venv, instalar dependencias (incluye pytest y reportlab)
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest tests/unit/test_reportes.py -v
```

Si el venv tiene `reportlab` pero **no** `pytest`, verá `No module named pytest`.
Instale con: `python -m pip install pytest` (o `pip install -r requirements.txt` tras el último pull).

O sin activar:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests/unit -v
```

Los tests de `test_reportes.py` hacen `pytest.importorskip("reportlab")`: si falta
reportlab en ese intérprete, el archivo se omite (skipped) en lugar de fallar la recolección.
