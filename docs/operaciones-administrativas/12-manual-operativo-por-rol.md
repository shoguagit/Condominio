# Manual operativo por rol

## Objetivo
Dar una guía práctica de uso del sistema separando las responsabilidades habituales del `admin` y del `operador`.

## Roles verificados en el código
- `admin`
- `operador`

Nota: el rol histórico `consulta` existe en algunos datos viejos, pero el código actual lo trata como compatibilidad y no como rol operativo principal.

## Rol: Administrador

### Qué controla
- selección del condominio de trabajo
- configuración base del condominio
- usuarios del sistema
- parámetros críticos del ciclo mensual
- revisión y cierre operativo del período

### Tareas de arranque
1. Entrar al sistema.
2. Seleccionar condominio si el rol es `admin`.
3. Verificar `mes_proceso` y tasa visible en header.
4. Confirmar que el condominio tenga datos base correctos.

### Tareas frecuentes

#### Diario / según necesidad
- mantener usuarios activos o inactivos
- revisar pagos, movimientos y conciliación
- consultar reportes y morosidad

#### Mensual
- verificar presupuesto del período
- revisar gastos cargados
- generar cuotas
- validar pagos del período
- revisar mora y cobros extraordinarios
- cerrar el mes

#### Excepcional
- configurar SMTP para notificaciones
- reprocesar tasas BCV en pagos históricos
- corregir procesos mal generados reiniciando cuotas del período

### Módulos prioritarios para admin
- `Condominios`
- `Usuarios`
- `Proceso mensual`
- `Reportes`
- `Movimientos bancarios`
- `Notificaciones`

### Riesgos si el admin se equivoca
- cerrar un mes con cuotas incorrectas arrastra saldos equivocados
- desactivar su propio usuario está bloqueado, pero desactivar otro admin puede dejar al equipo sin acceso
- trabajar sobre el condominio equivocado produce operaciones en contexto incorrecto

## Rol: Operador

### Qué controla
- carga operativa del día a día
- propietarios, unidades, proveedores y empleados
- registro de facturas
- registro de pagos
- importación y clasificación de movimientos bancarios
- consulta de reportes y estados de cuenta

### Tareas de arranque
1. Entrar al sistema.
2. Verificar condominio activo.
3. Confirmar `mes_proceso` visible.
4. Confirmar que trabaja en el período correcto antes de cargar pagos o movimientos.

### Tareas frecuentes

#### Diario
- registrar pagos recibidos
- importar extractos bancarios
- clasificar movimientos pendientes
- revisar alertas de conciliación
- consultar estados de cuenta de unidades

#### Semanal
- registrar facturas de proveedor
- actualizar propietarios, unidades o proveedores si hubo cambios
- revisar lista de morosos y notificaciones pendientes

#### Mensual
- cargar gastos del período
- apoyar validación del presupuesto
- verificar que no queden movimientos pendientes antes de cierre

### Módulos prioritarios para operador
- `Pagos y cobros`
- `Movimientos bancarios`
- `Facturas`
- `Unidades`
- `Propietarios`
- `Proveedores`
- `Estado de cuenta`

## Flujo operativo recomendado por frecuencia

### Flujo diario
1. Revisar dashboard.
2. Registrar pagos del día.
3. Importar movimientos bancarios si existen extractos nuevos.
4. Conciliar ingresos pendientes.
5. Corregir pagos o movimientos con inconsistencias.

### Flujo de fin de mes
1. Confirmar que todos los gastos estén cargados.
2. Validar presupuesto.
3. Generar cuotas.
4. Revisar tabla de cuotas y pre-cierre.
5. Registrar pagos faltantes.
6. Revisar conciliación bancaria.
7. Emitir reportes.
8. Enviar notificaciones si aplica.
9. Cerrar mes.

## Qué revisar antes de operar
- condominio activo correcto
- período correcto
- tasa visible razonable
- si el período está cerrado o no
- si hay cuotas ya generadas

## Qué revisar antes de cerrar un mes
- presupuesto guardado
- indivisos correctos
- cuotas generadas
- pagos y cobros extraordinarios reflejados
- conciliación razonable del período
- saldos pre-cierre coherentes

## Señales de alerta para ambos roles
- `mes_proceso` vacío o incoherente
- tasa BCV en `0`
- movimientos con alertas sin revisar
- diferencia bancaria distinta de cero al querer cerrar conciliación
- cuotas no generadas pero pagos intentando entrar al flujo mensual

## Matriz resumida de responsabilidad
| Tarea | Admin | Operador |
|---|---|---|
| Configurar condominio | Sí | No habitual |
| Crear/desactivar usuarios | Sí | No |
| Registrar propietarios/unidades/proveedores | Sí | Sí |
| Registrar pagos | Sí | Sí |
| Importar movimientos | Sí | Sí |
| Conciliar banco | Sí | Sí |
| Generar cuotas | Sí | Puede apoyar, pero normalmente lo decide admin |
| Cerrar mes | Sí | No recomendado |
| Configurar SMTP | Sí | No |

## Ruta recomendada por rol

### Si eres admin
1. `01-autenticacion-y-contexto.md`
2. `02-administracion-maestra.md`
3. `05-reportes-notificaciones-y-proceso-mensual.md`
4. `10-proceso-mensual-estados.md`
5. `11-conciliacion-bancaria.md`

### Si eres operador
1. `01-autenticacion-y-contexto.md`
2. `04-facturacion-cobros-y-bancos.md`
3. `11-conciliacion-bancaria.md`
4. `05-reportes-notificaciones-y-proceso-mensual.md`
