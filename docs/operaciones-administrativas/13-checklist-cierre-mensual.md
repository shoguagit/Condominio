# Checklist de cierre mensual

## Objetivo
Ejecutar el cierre mensual de forma segura, minimizando errores que contaminen saldos, estados de pago o el siguiente período.

## Cuándo usarlo
- al final del período operativo
- antes de pulsar `Cerrar mes`
- cuando un administrador quiera validar que el mes está listo para consolidarse

## Responsable recomendado
- `admin`

## Checklist previo

### Contexto y sesión
- [ ] Estoy en el condominio correcto
- [ ] El `mes_proceso` visible corresponde al mes que voy a cerrar
- [ ] La tasa visible no está en `0` si necesito referencias monetarias consistentes

### Datos base
- [ ] Las unidades activas del condominio están correctas
- [ ] Los `indiviso_pct` suman 100%
- [ ] No hay cambios pendientes en propietarios o unidades que deban reflejarse antes de calcular cuotas

### Gastos y presupuesto
- [ ] Todos los gastos del período ya fueron cargados
- [ ] Si hubo importación desde banco, los gastos fueron revisados
- [ ] El presupuesto del período está guardado
- [ ] El monto del presupuesto es coherente con los gastos reales del mes

### Cuotas
- [ ] Ya se generaron cuotas para el período
- [ ] La tabla de cuotas generadas luce razonable por unidad
- [ ] La vista de pre-cierre no muestra valores absurdos o saldos inesperados

### Pagos y cobros extraordinarios
- [ ] Los pagos del período ya están registrados
- [ ] Los cobros extraordinarios del período ya fueron creados o anulados según corresponda
- [ ] No hay pagos pendientes de corrección manual

### Conciliación y control
- [ ] La conciliación bancaria del período fue revisada
- [ ] No hay alertas críticas sin revisar en movimientos
- [ ] No hay diferencias importantes que todavía deban corregirse antes de consolidar el mes

## Checklist de ejecución

### Paso 1. Confirmar estado del proceso
- [ ] El período está en estado `procesado`
- [ ] No está en `borrador`
- [ ] No está ya `cerrado`

Si no está en `procesado`, NO cierres el mes.

### Paso 2. Revisar resumen financiero pre-cierre
- [ ] Total cuotas emitidas consistente
- [ ] Total cobrado consistente
- [ ] Total pendiente comprensible
- [ ] Eficiencia de cobro razonable para el mes

### Paso 3. Confirmar impacto del cierre
Al cerrar el mes el sistema:
- [ ] actualizará `cuotas_unidad.estado` a `cerrado`
- [ ] recalculará y guardará `unidades.saldo`
- [ ] recalculará `unidades.estado_pago`
- [ ] marcará movimientos del período como `procesado`
- [ ] moverá `condominios.mes_proceso` al mes siguiente

### Paso 4. Ejecutar cierre
- [ ] Pulsé `Cerrar mes`
- [ ] Revisé el mensaje de confirmación final
- [ ] Confirmé el cierre definitivo

## Verificación posterior al cierre

### Verificación inmediata
- [ ] El sistema muestra mensaje de cierre exitoso
- [ ] El período aparece como `cerrado`
- [ ] `mes_proceso` avanzó al siguiente mes

### Verificación operativa
- [ ] Las unidades ahora muestran saldo actualizado
- [ ] Los estados de pago (`al_dia`, `parcial`, `moroso`) son coherentes
- [ ] Los movimientos del período quedaron procesados
- [ ] No es posible seguir registrando pagos en el período cerrado

## Señales de alerta después del cierre
- [ ] Saldos exageradamente altos o negativos sin justificación
- [ ] Todas las unidades cambiaron a un mismo estado sin sentido de negocio
- [ ] El mes no avanzó aunque el cierre dijo ser exitoso
- [ ] Se siguen permitiendo pagos en el período cerrado

Si ocurre cualquiera de estos casos, revisa `15-runbook-incidencias.md`.

## NO cerrar el mes si...
- [ ] aún faltan gastos por registrar
- [ ] todavía no validaste el presupuesto
- [ ] no generaste cuotas
- [ ] estás en el condominio equivocado
- [ ] hay inconsistencias graves en la previsualización de saldos

## Referencias
- `10-proceso-mensual-estados.md`
- `05-reportes-notificaciones-y-proceso-mensual.md`
- `12-manual-operativo-por-rol.md`
- `15-runbook-incidencias.md`
