#!/usr/bin/env python3
"""
Reprocesamiento único: recalcula tasa_cambio y monto_usd en `pagos` según la tasa BCV
oficial del día de fecha_pago (misma lógica que la app).

Usa la tabla `tasas_bcv_dia` (caché). Si está vacía o con `--sync-api`, sincroniza desde la API
antes de recalcular. Ejecute antes `scripts/fase7_tasas_bcv_dia_migration.sql` en Supabase.

**Forma simple (recomendada):** no invoque este .py con el python3 del sistema; use el wrapper:

  bash scripts/reprocesar_tasas_pagos_bcv.sh --sync-api --apply

(Desde la raíz del repo Condominio; el .sh usa automáticamente .venv/bin/python3.)

Cliente Supabase:
  - Lo ideal es definir SUPABASE_SERVICE_KEY en .env (rol service_role) para leer/actualizar
    todos los pagos sin depender de RLS.
  - Si no está definida, el script usa SUPABASE_KEY (anon). Eso puede fallar en lectura o
    escritura si las políticas RLS no lo permiten.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

try:
    from requests.exceptions import RequestsDependencyWarning
except ImportError:
    RequestsDependencyWarning = UserWarning  # type: ignore[misc, assignment]

warnings.filterwarnings("ignore", category=RequestsDependencyWarning)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import supabase  # noqa: F401
except ModuleNotFoundError:
    sh = ROOT / "scripts" / "reprocesar_tasas_pagos_bcv.sh"
    print(
        "Falta el paquete 'supabase' en este Python.\n\n"
        "Use el wrapper (no el python3 del sistema):\n"
        f"  bash {sh} --sync-api --apply\n\n"
        "Si aún no tiene el venv:\n"
        f"  cd {ROOT} && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from config.supabase_client import get_admin_client, get_supabase_client  # noqa: E402
from repositories.tasa_bcv_repository import TasaBcvRepository  # noqa: E402
from utils.dolar_oficial_ve import (  # noqa: E402
    monto_usd_desde_bs,
    tasa_bcv_bs_por_usd_para_fecha_con_serie,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Recalcular tasas BCV y USD en pagos.")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar cambios en Supabase (sin esto solo se simula).",
    )
    p.add_argument(
        "--condominio-id",
        type=int,
        default=None,
        help="Solo pagos de este condominio (opcional).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Máximo de filas a procesar (útil para prueba).",
    )
    p.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Tamaño de página al leer pagos (default 500).",
    )
    p.add_argument(
        "--sync-api",
        action="store_true",
        help="Volver a descargar el histórico desde DolarAPI y actualizar tasas_bcv_dia antes de reprocesar.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        client = get_admin_client()
    except ValueError:
        print(
            "ADVERTENCIA: SUPABASE_SERVICE_KEY no está en .env; se usa la clave anónima "
            "(SUPABASE_KEY). Si ve 0 filas o errores al actualizar, añada la service_role "
            "en Supabase (Settings → API) y defina SUPABASE_SERVICE_KEY en .env.",
            file=sys.stderr,
        )
        client = get_supabase_client()

    repo_rates = TasaBcvRepository(client)
    if args.sync_api:
        n_sync = repo_rates.merge_from_api()
        print(f"Sincronizadas {n_sync} filas en tasas_bcv_dia desde la API.")
    serie = repo_rates.list_sorted_pairs()
    if not serie:
        n_sync = repo_rates.merge_from_api()
        if n_sync <= 0:
            print(
                "Error: tasas_bcv_dia vacía y la API no devolvió datos. "
                "¿Ejecutó scripts/fase7_tasas_bcv_dia_migration.sql? "
                "Red / https://ve.dolarapi.com/v1/historicos/dolares",
                file=sys.stderr,
            )
            return 1
        serie = repo_rates.list_sorted_pairs()
    if not serie:
        print("Error: no hay tasas en tasas_bcv_dia tras sincronizar.", file=sys.stderr)
        return 1

    processed = 0
    would_update = 0
    skipped = 0
    errors = 0
    samples: list[str] = []

    start = 0
    page = max(50, int(args.page_size or 500))

    def _query_page(offset: int, lim: int):
        b = (
            client.table("pagos")
            .select("id, condominio_id, fecha_pago, monto_bs, tasa_cambio, monto_usd")
            .order("id", desc=False)
        )
        if args.condominio_id is not None:
            b = b.eq("condominio_id", int(args.condominio_id))
        return b.range(offset, offset + lim - 1).execute()

    while True:
        if args.limit is not None and processed >= args.limit:
            break
        resp = _query_page(start, page)
        rows = resp.data or []
        if not rows:
            break

        for row in rows:
            if args.limit is not None and processed >= args.limit:
                break
            processed += 1
            pid = row.get("id")
            fp = row.get("fecha_pago")
            mbs = float(row.get("monto_bs") or 0)
            old_tc = float(row.get("tasa_cambio") or 0)
            old_usd = float(row.get("monto_usd") or 0)

            if fp is None or str(fp).strip() == "":
                skipped += 1
                continue
            fp_s = str(fp)[:10]

            t_new, meta = tasa_bcv_bs_por_usd_para_fecha_con_serie(fp_s, serie)
            if not t_new or t_new <= 0:
                skipped += 1
                continue

            usd_new = monto_usd_desde_bs(mbs, t_new)
            tc_changed = abs(old_tc - t_new) > 1e-6
            usd_changed = abs(old_usd - usd_new) > 5e-5
            if not tc_changed and not usd_changed:
                continue

            would_update += 1
            if len(samples) < 15:
                samples.append(
                    f"  id={pid} fecha_pago={fp_s} tasa {old_tc:.4f}→{t_new:.4f} "
                    f"USD {old_usd:.4f}→{usd_new:.4f} ({meta})"
                )

            if args.apply:
                try:
                    (
                        client.table("pagos")
                        .update(
                            {
                                "tasa_cambio": float(t_new),
                                "monto_usd": float(usd_new),
                            }
                        )
                        .eq("id", int(pid))
                        .execute()
                    )
                except Exception as ex:
                    errors += 1
                    print(f"Error actualizando id={pid}: {ex}", file=sys.stderr)

        if len(rows) < page:
            break
        start += page

    mode = "APLICADO" if args.apply else "SIMULACIÓN"
    print(f"Modo: {mode}")
    print(f"Filas revisadas: {processed}")
    print(f"Cambios {'aplicados' if args.apply else 'propuestos'}: {would_update}")
    print(f"Omitidas (sin fecha o sin tasa BCV): {skipped}")
    if args.apply:
        print(f"Errores al actualizar: {errors}")
    if samples:
        print("Ejemplos:")
        print("\n".join(samples))
    if not args.apply and would_update:
        print("\nPara escribir en la base de datos ejecute de nuevo con --apply.")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
