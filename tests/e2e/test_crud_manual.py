import os
import sys
from dataclasses import dataclass
from typing import Callable, Any


# Permitir imports relativos al ejecutar como script (python tests/e2e/test_crud_manual.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.supabase_client import get_supabase_client  # type: ignore  # noqa: E402
from repositories.condominio_repository import CondominioRepository  # type: ignore  # noqa: E402
from repositories.alicuota_repository import AlicuotaRepository  # type: ignore  # noqa: E402
from repositories.proveedor_repository import ProveedorRepository  # type: ignore  # noqa: E402
from repositories.unidad_repository import UnidadRepository  # type: ignore  # noqa: E402
from repositories.empleado_repository import EmpleadoRepository  # type: ignore  # noqa: E402


@dataclass
class CrudResult:
    module: str
    created: bool = False
    read: bool = False
    updated: bool = False
    deleted: bool = False
    filter_by_condo: bool = False
    error: str | None = None


def pick_first_condominio_id() -> int:
    client = get_supabase_client()
    repo = CondominioRepository(client)
    all_condos = repo.get_all(solo_activos=False)
    if not all_condos:
        raise RuntimeError("No hay condominios en la base de datos para ejecutar pruebas.")
    return int(all_condos[0]["id"])


def _run_crud(
    module: str,
    repo: Any,
    condominio_id: int,
    build_payload: Callable[[int], dict],
    pick_update: Callable[[dict], dict],
) -> CrudResult:
    res = CrudResult(module=module)
    try:
        # Create
        payload = build_payload(condominio_id)
        created = repo.create(payload)
        res.created = bool(created and created.get("id"))
        entity_id = int(created["id"])

        # Read
        fetched = repo.get_by_id(entity_id)
        res.read = bool(fetched and int(fetched["id"]) == entity_id)

        # Update
        updated_data = pick_update(fetched or created)
        updated = repo.update(entity_id, updated_data)
        # verificar que al menos uno de los campos cambió
        changed = any(
            updated.get(k) != (fetched or created).get(k)
            for k in updated_data.keys()
        )
        res.updated = bool(updated and changed)

        # Filter by condominio_id (no aplica a Condominios, que es global)
        if module == "Condominios":
            # Simplemente verificar que el creado sigue apareciendo en get_all()
            all_condos = repo.get_all(solo_activos=False)
            res.filter_by_condo = any(int(r.get("id")) == entity_id for r in all_condos)
        else:
            all_for_condo = repo.get_all(condominio_id)
            res.filter_by_condo = all(
                int(r.get("condominio_id")) == condominio_id for r in all_for_condo
            ) and any(int(r.get("id")) == entity_id for r in all_for_condo)

        # Delete y verificación
        repo.delete(entity_id)
        if module == "Condominios":
            remaining = repo.get_all(solo_activos=False)
        else:
            remaining = repo.get_all(condominio_id)
        res.deleted = all(int(r.get("id")) != entity_id for r in remaining)

    except Exception as exc:  # noqa: BLE001
        res.error = f"{type(exc).__name__}: {exc}"

    return res


def run_all() -> list[CrudResult]:
    condo_id = pick_first_condominio_id()
    client = get_supabase_client()

    results: list[CrudResult] = []

    # 1. Condominios
    condo_repo = CondominioRepository(client)

    def build_condo_payload(_: int) -> dict:
        return {
            "nombre": "TEST-CONDO",
            "direccion": "Dirección de prueba",
            "pais_id": None,
            "tipo_documento_id": None,
            "numero_documento": "J-00000000-0",
            "telefono": "0000000",
            "email": "test-condo@example.com",
            "activo": True,
        }

    def update_condo(data: dict) -> dict:
        return {"nombre": f"{data.get('nombre', 'TEST-CONDO')}-EDITADO"}

    results.append(
        _run_crud("Condominios", condo_repo, condo_id, build_condo_payload, update_condo)
    )

    # 2. Alícuotas
    ali_repo = AlicuotaRepository(client)

    def build_ali_payload(c_id: int) -> dict:
        return {
            "condominio_id": c_id,
            "descripcion": "ALICUOTA TEST",
            "autocalcular": False,
            "cantidad_unidades": 1,
            "total_alicuota": 1.0,
            "activo": True,
        }

    def update_ali(data: dict) -> dict:
        return {"descripcion": f"{data.get('descripcion', 'ALICUOTA TEST')}-EDITADA"}

    results.append(
        _run_crud("Alícuotas", ali_repo, condo_id, build_ali_payload, update_ali)
    )

    # 3. Proveedores
    prov_repo = ProveedorRepository(client)

    def build_prov_payload(c_id: int) -> dict:
        return {
            "condominio_id": c_id,
            "nombre": "PROVEEDOR TEST",
            "tipo_documento_id": None,
            "numero_documento": "J-11111111-1",
            "direccion": "Dirección proveedor test",
            "telefono_fijo": "0000000",
            "telefono_celular": "0000000000",
            "correo": "proveedor@test.com",
            "contacto": "Contacto Test",
            "notas": "Notas test",
            "saldo": 0,
            "activo": True,
        }

    def update_prov(data: dict) -> dict:
        return {"nombre": f"{data.get('nombre', 'PROVEEDOR TEST')}-EDITADO"}

    results.append(
        _run_crud("Proveedores", prov_repo, condo_id, build_prov_payload, update_prov)
    )

    # 4. Unidades
    uni_repo = UnidadRepository(client)

    def build_uni_payload(c_id: int) -> dict:
        return {
            "condominio_id": c_id,
            "tipo_propiedad": "Apartamento",
            "numero": "U-TEST",
            "piso": "1",
            "propietario_id": None,
            "tipo_condomino": "Propietario",
            "cuota_fija": 0.0,
            "activo": True,
        }

    def update_uni(data: dict) -> dict:
        return {"numero": f"{data.get('numero', 'U-TEST')}-EDITADA"}

    results.append(
        _run_crud("Unidades", uni_repo, condo_id, build_uni_payload, update_uni)
    )

    # 5. Empleados
    emp_repo = EmpleadoRepository(client)

    def build_emp_payload(c_id: int) -> dict:
        return {
            "condominio_id": c_id,
            "nombre": "EMPLEADO TEST",
            "cargo": "Cargo Test",
            "direccion": "Dirección empleado test",
            "telefono_fijo": "0000000",
            "telefono_celular": "0000000000",
            "correo": "empleado@test.com",
            "notas": "Notas test",
            "activo": True,
        }

    def update_emp(data: dict) -> dict:
        return {"cargo": f"{data.get('cargo', 'Cargo Test')}-EDITADO"}

    results.append(
        _run_crud("Empleados", emp_repo, condo_id, build_emp_payload, update_emp)
    )

    return results


def main() -> None:
    results = run_all()

    # Encabezado tabla
    print("\nRESULTADOS CRUD MANUAL (Supabase / repositories)\n")
    header = f"{'Módulo':<15} {'Create':<8} {'Read':<8} {'Update':<8} {'Delete':<8} {'FiltroCond.':<12} {'Error'}"
    print(header)
    print("-" * len(header))

    for r in results:
        def mark(ok: bool) -> str:
            return "✅ PASS" if ok else "❌ FAIL"

        line = f"{r.module:<15} {mark(r.created):<8} {mark(r.read):<8} {mark(r.updated):<8} {mark(r.deleted):<8} {mark(r.filter_by_condo):<12} {r.error or ''}"
        print(line)

    # Exit code distinto de 0 si algo falló
    if any(not (res.created and res.read and res.updated and res.deleted and res.filter_by_condo and not res.error) for res in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

