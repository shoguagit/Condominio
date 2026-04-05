#!/usr/bin/env bash
# Reprocesar tasas BCV en pagos — usa siempre el .venv del repo (sin pelear con python del sistema).
# Uso (desde cualquier carpeta):
#   bash /ruta/a/Condominio/scripts/reprocesar_tasas_pagos_bcv.sh --sync-api --apply
# O desde la raíz del repo:
#   bash scripts/reprocesar_tasas_pagos_bcv.sh --sync-api --apply

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY=""
for cand in "$ROOT/.venv/bin/python3" "$ROOT/.venv/bin/python"; do
  if [[ -x "$cand" ]]; then
    PY="$cand"
    break
  fi
done

if [[ -z "$PY" ]]; then
  echo "No encontré Python en $ROOT/.venv/bin/" >&2
  echo "Ejecute una vez:" >&2
  echo "  cd \"$ROOT\" && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

exec "$PY" "$ROOT/scripts/reprocesar_tasas_pagos_bcv.py" "$@"
