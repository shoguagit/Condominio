# Runbook de incidencias

## Objetivo
Resolver las incidencias operativas más probables sin tener que releer toda la documentación del sistema.

## Cómo usar este runbook
- identifica el síntoma
- confirma las causas probables
- ejecuta las verificaciones en el orden indicado
- aplica la corrección más pequeña posible

## Incidencia: no puedo cerrar el mes

### Síntomas
- el botón `Cerrar mes` está deshabilitado
- el sistema muestra que solo está disponible en estado `procesado`
- el cierre falla aunque ya existen datos del mes

### Causas probables
- el proceso sigue en `borrador`
- no existen cuotas generadas
- el período ya está `cerrado`

### Verificaciones
1. Confirma el estado del período en `Proceso mensual`.
2. Confirma que exista presupuesto guardado.
3. Confirma que ya se generaron cuotas.
4. Confirma que no estás trabajando en otro condominio o período.

### Acciones recomendadas
- si está en `borrador`: generar cuotas
- si las cuotas están mal: reiniciarlas y regenerarlas
- si ya está `cerrado`: no intentar cerrar de nuevo; revisar histórico

## Incidencia: no se generan cuotas

### Síntomas
- al pulsar `Generar cuotas` aparece error
- el sistema indica que falta presupuesto
- el sistema exige revisar indivisos

### Causas probables
- presupuesto `<= 0`
- suma de `indiviso_pct` distinta de 100%
- ya existen cuotas y no se marcó regeneración

### Verificaciones
1. Revisa el presupuesto guardado.
2. Revisa la suma total de indivisos.
3. Revisa si ya existen cuotas en el período.

### Acciones recomendadas
- corregir presupuesto
- corregir unidades e indivisos
- marcar regeneración solo si realmente quieres reemplazar las cuotas actuales

## Incidencia: la conciliación no cuadra

### Síntomas
- `Diferencia Bs.` distinta de cero
- el sistema no deja cerrar conciliación
- hay muchos movimientos sin conciliar

### Causas probables
- pagos cargados en período incorrecto
- movimientos importados en período incorrecto
- pagos registrados sin movimiento
- movimientos duplicados o mal clasificados

### Verificaciones
1. Verifica el período de conciliación seleccionado.
2. Revisa pagos sin movimiento.
3. Revisa movimientos pendientes y alertas.
4. Revisa si hay ingresos importados duplicados.

### Acciones recomendadas
- corregir período de trabajo
- reclasificar o reconciliar movimientos pendientes
- corregir pagos mal cargados
- eliminar o corregir duplicados si se confirmaron

## Incidencia: la conciliación automática por cédula no genera pagos

### Síntomas
- se ejecuta el proceso pero no se crean pagos
- aparece mensaje de que no hubo coincidencias

### Causas probables
- la descripción bancaria no contiene cédula usable
- el propietario no existe en ese condominio
- la unidad no está vinculada al propietario
- el movimiento ya estaba conciliado

### Verificaciones
1. Revisa la descripción exacta del movimiento.
2. Confirma que la cédula exista en `propietarios`.
3. Confirma que haya vínculo con unidad.
4. Confirma que el movimiento sea de tipo `ingreso`.

### Acciones recomendadas
- corregir maestro de propietarios o vínculo con unidad
- usar conciliación manual si no hay dato suficiente en la descripción

## Incidencia: no se envían correos de notificación

### Síntomas
- el módulo de notificaciones se bloquea al entrar
- los envíos quedan fallidos
- el historial muestra errores o correo vacío

### Causas probables
- no hay SMTP configurado en el condominio
- el propietario no tiene correo registrado
- app password inválida o remitente mal configurado

### Verificaciones
1. Revisar configuración SMTP del condominio.
2. Revisar si el moroso tiene email.
3. Revisar historial del período en notificaciones.

### Acciones recomendadas
- configurar o corregir SMTP en `Condominios`
- completar correo del propietario
- reenviar después de corregir

## Incidencia: no puedo crear o cambiar contraseña de usuario

### Síntomas
- error al crear usuario
- error al cambiar contraseña
- mensaje asociado a `service_role`

### Causas probables
- falta `SUPABASE_SERVICE_KEY`

### Verificaciones
1. Confirmar que `SUPABASE_SERVICE_KEY` esté configurada.
2. Confirmar que el entorno está usando el `.env` esperado.

### Acciones recomendadas
- configurar `SUPABASE_SERVICE_KEY`
- reintentar la operación desde `Usuarios`

## Incidencia: la tasa BCV sale en cero

### Síntomas
- header muestra tasa `0`
- reportes sin equivalente USD útil
- pagos o gastos usando respaldo inesperado

### Causas probables
- fallo de scraping / API BCV
- el condominio no tiene tasa de respaldo
- histórico `tasas_bcv_dia` vacío para la fecha requerida

### Verificaciones
1. Revisar si la sesión cargó tasa.
2. Revisar tasa del condominio.
3. Revisar histórico y scripts de reproceso si es necesario.

### Acciones recomendadas
- actualizar tasa en condominio como respaldo
- reprocesar histórico con `bash scripts/reprocesar_tasas_pagos_bcv.sh --sync-api --apply`

## Incidencia: estoy viendo datos del condominio equivocado

### Síntomas
- el header muestra otro condominio
- aparecen unidades o pagos que no esperaba

### Causas probables
- el `admin` seleccionó otro condominio
- no se actualizó el contexto de sesión como esperaba

### Verificaciones
1. Revisar el header.
2. Si eres admin, usar `Cambiar condominio`.
3. Confirmar el contexto antes de cargar datos sensibles.

### Acciones recomendadas
- cambiar el condominio activo antes de continuar
- si ya registraste algo mal, revisar el módulo afectado y corregirlo en el condominio correcto

## Referencias rápidas
- cierre mensual: `13-checklist-cierre-mensual.md`
- conciliación: `14-checklist-conciliacion-bancaria.md`
- estados del proceso: `10-proceso-mensual-estados.md`
- conciliación detallada: `11-conciliacion-bancaria.md`
