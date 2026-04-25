# Seeds

Esta carpeta contiene semillas SQL re-ejecutables para poblar una base nueva con datos base y demo.

## Orden recomendado

```text
1. seed/01_catalogos_base.sql
2. seed/02_demo_maestros.sql
3. seed/03_demo_operativo_basico.sql
```

## Qué carga cada archivo
- `01_catalogos_base.sql`: países y tipos de documento.
- `02_demo_maestros.sql`: condominio demo, usuarios demo en tabla `usuarios`, propietarios, unidades, empleados, proveedores, alícuotas, fondos, servicios, conceptos, conceptos de consumo, gastos fijos y cuentas bancarias.
- `03_demo_operativo_basico.sql`: tasas BCV demo, una factura de proveedor, movimientos demo y un proceso mensual demo con cuotas por unidad.

## Importante
- Los usuarios creados aquí se insertan en la tabla `usuarios`, pero NO crean cuentas en Supabase Auth. Para login real hace falta crear el mismo correo en Auth.
- El esquema self-hosted actual verificado NO tiene la tabla `pagos`, así que estos seeds no insertan pagos demo. Si más adelante se agrega esa tabla, el seed operativo puede ampliarse.
- El esquema self-hosted actual verificado tampoco tiene `unidades.estado_pago`; por eso los seeds demo no cargan ese campo aunque la app lo use en algunos flujos.
- El esquema self-hosted actual verificado tampoco tiene `unidades.indiviso_pct`; por eso el seed operativo crea `cuotas_unidad` demo directamente y no depende de cálculo por indiviso desde `unidades`.
- El esquema self-hosted actual verificado también mantiene una restricción en `conceptos.tipo` que no aceptó `ajuste`; por eso el seed usa conceptos demo de tipo `gasto` para asegurar compatibilidad con la base actual.

## Condominio demo
- Nombre: `Condominio Demo Norte`
- Correo admin demo tabla: `admin.demo@condominio.local`
- Correo operador demo tabla: `operador.demo@condominio.local`
