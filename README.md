# Condominio

Aplicación web de gestión de condominios construida con `Streamlit` y `Supabase`.

## Qué resuelve
- autenticación de usuarios y selección de condominio activo
- administración maestra de condominios, unidades, propietarios, empleados, proveedores y usuarios
- configuración financiera de alícuotas, conceptos, servicios y gastos fijos
- registro de facturas, pagos, movimientos bancarios, recibos y estados de cuenta
- reportes operativos, notificaciones a morosos y proceso mensual
- manejo de tasa BCV y equivalentes en bolívares / USD

## Ejecutar localmente
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## Variables de entorno
- `SUPABASE_URL`: obligatoria
- `SUPABASE_KEY`: obligatoria
- `SUPABASE_SERVICE_KEY`: necesaria para administración de usuarios y scripts de mantenimiento que deben saltar RLS

`config/settings.py` carga `.env` al importar y falla inmediatamente si faltan `SUPABASE_URL` o `SUPABASE_KEY`.

## Testing
Usa siempre el intérprete del `venv` para evitar falsos `ModuleNotFoundError`:

```bash
.venv/bin/python -m pytest tests/unit -v
```

Más detalles en `tests/README.md`.

## Documentación funcional y técnica
- Índice general: `docs/operaciones-administrativas/README.md`
- Autenticación y contexto: `docs/operaciones-administrativas/01-autenticacion-y-contexto.md`
- Administración maestra: `docs/operaciones-administrativas/02-administracion-maestra.md`
- Configuración financiera: `docs/operaciones-administrativas/03-configuracion-financiera.md`
- Facturación, cobros y bancos: `docs/operaciones-administrativas/04-facturacion-cobros-y-bancos.md`
- Reportes, notificaciones y proceso mensual: `docs/operaciones-administrativas/05-reportes-notificaciones-y-proceso-mensual.md`
- Tasa BCV y moneda: `docs/operaciones-administrativas/06-tasa-bcv-y-monedas.md`
- Checklists y runbooks: `docs/operaciones-administrativas/13-checklist-cierre-mensual.md`, `docs/operaciones-administrativas/14-checklist-conciliacion-bancaria.md`, `docs/operaciones-administrativas/15-runbook-incidencias.md`

## Estructura útil
- `app.py`: login, autologin de QA, selección de condominio y dashboard inicial
- `pages/`: módulos funcionales del sistema
- `repositories/`: acceso a Supabase por dominio
- `utils/`: validaciones, sesión, cálculos, PDFs, conciliación y tasa BCV
- `components/`: shell visual reutilizable
- `scripts/`: SQL y utilidades de mantenimiento

## Migraciones y mantenimiento
- Las migraciones SQL se aplican manualmente en Supabase SQL Editor.
- Instrucción base: `scripts/INSTRUCCIONES-MIGRACION.md`
- Para una base vacía en Supabase self-hosted, el orden correcto NO es ejecutar solo `supabase_migration.sql`.
- El bootstrap correcto es:

```text
1. docs/supabase_schema.sql
2. supabase_migration.sql
```

- Motivo: `supabase_migration.sql` es incremental y asume que ya existen tablas base como `unidades`, `empleados`, `conceptos` y `servicios`.
- Si intentas correr `supabase_migration.sql` primero en una base vacía, fallará con errores como `relation "unidades" does not exist`.

### Inicializar Supabase self-hosted desde cero

1. Aplicar el esquema base del sistema desde `docs/supabase_schema.sql`.
2. Aplicar los ajustes incrementales desde `supabase_migration.sql`.
3. Verificar que existan las tablas críticas y columnas agregadas por la migración incremental.

### Validación mínima recomendada

Tablas que deben existir después del bootstrap + ajustes:
- `paises`
- `tipos_documento`
- `condominios`
- `usuarios`
- `proveedores`
- `propietarios`
- `unidades`
- `alicuotas`
- `fondos`
- `servicios`
- `conceptos`
- `gastos_fijos`
- `conceptos_consumo`
- `cuentas_bancos`
- `facturas_proveedor`
- `empleados`
- `unidad_propietarios`
- `movimientos`
- `procesos_mensuales`
- `cuotas_unidad`
- `tasas_bcv_dia`

Columnas incrementales clave que también deben existir:
- En `unidades`: `codigo`, `alicuota_id`, `saldo`
- En `empleados`: `area`
- En `gastos_fijos`: `tipo_gasto`

### Estado verificado en este repositorio

Se aplicó correctamente en Supabase self-hosted el siguiente orden:
- migración `base_condominio_schema`
- migración `condominio_incremental_adjustments`

## Seeds demo

La carpeta `seed/` contiene semillas SQL re-ejecutables para poblar una base nueva con catálogos y datos demo.

Orden recomendado:

```text
1. seed/01_catalogos_base.sql
2. seed/02_demo_maestros.sql
3. seed/03_demo_operativo_basico.sql
4. seed/04_demo_usuarios_auth.sql
5. seed/05_demo_categorias_gasto.sql
```

Qué crean:
- catálogos base (`paises`, `tipos_documento`)
- categorías de gasto sistema (`categorias_gasto`: NOMINA, SERVICIOS, MANTENIMIENTO, OTROS)
- un condominio demo
- usuarios demo en tabla `usuarios` y `auth.users`
- propietarios, unidades, empleados y proveedores demo
- alícuotas, fondos, servicios, conceptos, conceptos de consumo, gastos fijos y cuentas demo
- una factura demo de proveedor
- movimientos demo, proceso mensual demo con cuotas por unidad
- tasas BCV demo en `tasas_bcv_dia`
- pagos (tabla) y presupuestos
- notificaciones_enviadas (tabla de auditoría de notificaciones)
- conciliaciones (tabla de conciliaciones bancario)
- config_mora (configuración de mora y recargos)
- reportes_generados (historial de reportes generados)

### Columnas SMTP en condominios

El schema base incluye columnas SMTP en la tabla `condominios`:
- `smtp_host`, `smtp_port`, `smtp_usuario`, `smtp_password`
- `smtp_email`, `smtp_secure`
- `smtp_app_password`, `smtp_nombre_remitente`
- `logo_url`, `nombrereport`
- `pie_pagina_titular`, `pie_pagina_cuerpo`, `pie_pagina_contacto`
- `mostrar_logo`
- `tesorero_email`, `tesorero_nombre`
- `administrador_email`, `administrador_nombre`

La tabla `unidades` incluye:
- `indiviso_pct` (porcentaje de indiviso)
- `estado_pago`

La tabla `movimientos` incluye:
- `conciliado`, `fecha_conciliacion`, `notas_conciliacion`
- `tipo_alerta`, `revisado`
- `pago_id`, `factura_id`, `es_ajuste`, `ajuste_motivo`, `mes_contable`

La tabla `cuotas_unidad` incluye:
- `cobros_extraordinarios`, `total_cobros_extraordinarios_bs`

### Correcciones de código

Se corrigieron bugs de formato de período en:
- `pages/14_facturas.py` — conversión "MM/YYYY" → "YYYY-MM-DD"
- `pages/13_proveedores.py` — conversión "MM/YYYY" → "YYYY-MM-DD"
- `repositories/dashboard_repository.py` — función `_norm_periodo()` para manejar múltiples formatos

 Estas columnas se agregan en la migración `scripts/fase5b_notificaciones_migration.sql`.

### Columnas saldo_inicial en unidades

La tabla `unidades` incluye columnas para saldo inicial y control de deuda:
- `saldo`, `saldo_inicial_bs`, `saldo_inicial_usd`, `saldo_inicial_fecha`
- `saldo_fecha_ultimo_pago`, `fecha_ultimo_pago`
- `meses_sin_pagar`, `months_deuda`
- `requiere_revision`, `nota_revision`
- `tipo_deuda`, `deuda_inicial_bs`, `deuda_inicial_usd`
- `observaciones`, `codigo`, `alicuota_id`, `primer_periodo`

Estas columnas están en el schema base `docs/supabase_schema.sql`.

- Reproceso de tasas BCV en pagos:

```bash
bash scripts/reprocesar_tasas_pagos_bcv.sh --sync-api --apply
```
