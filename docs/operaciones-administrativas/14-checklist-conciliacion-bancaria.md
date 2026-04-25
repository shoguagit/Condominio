# Checklist de conciliación bancaria

## Objetivo
Conciliar un período bancario con seguridad, detectando diferencias y evitando cerrar conciliaciones incorrectas.

## Cuándo usarlo
- después de importar movimientos bancarios
- antes de cerrar una conciliación
- cuando el dashboard o el módulo de movimientos muestran pendientes o alertas

## Responsable recomendado
- `admin` o `operador`

## Checklist previo

### Contexto
- [ ] Estoy en el condominio correcto
- [ ] Estoy conciliando el período correcto en `MM/YYYY`
- [ ] Confirmé que el período de conciliación no es otro distinto al período de carga/listado

### Datos de entrada
- [ ] Ya importé el extracto bancario del período correcto
- [ ] Revisé que los movimientos importados no estén duplicados
- [ ] Ya están registrados en el sistema los pagos del período que deberían cuadrar con el banco

### Calidad de datos
- [ ] Las referencias bancarias lucen completas cuando el banco las trae
- [ ] Las descripciones contienen suficiente información si espero conciliación automática por cédula
- [ ] No hay movimientos de otro mes mezclados en este período

## Checklist de ejecución

### Paso 1. Revisar resumen del período
- [ ] Revisé `Movimientos banco`
- [ ] Revisé `Conciliados`
- [ ] Revisé `Sin conciliar`
- [ ] Revisé `Diferencia Bs.`

### Paso 2. Revisar alertas activas
- [ ] Revisé si hay `fecha_fuera_periodo`
- [ ] Revisé si hay `sin_pago_sistema`
- [ ] Revisé si hay `pago_parcial`
- [ ] Revisé si hay `pago_superior`
- [ ] Revisé si hay `monto_no_coincide`

### Paso 3. Ejecutar conciliación automática por cédula si aplica
- [ ] Solo la ejecuté si los ingresos están importados y aún no conciliados
- [ ] Confirmé que las descripciones bancarias traen cédulas identificables
- [ ] Revisé el mensaje de resultado: movimientos conciliados y pagos creados

### Paso 4. Revisar movimientos pendientes
Por cada ingreso pendiente:
- [ ] Revisé fecha
- [ ] Revisé referencia
- [ ] Revisé monto
- [ ] Revisé sugerencia automática si existe
- [ ] Confirmé vínculo si era correcto
- [ ] O lo marqué como `sin_pago_sistema` si no correspondía a ningún pago

### Paso 5. Revisar pagos sin movimiento
- [ ] Revisé la tabla de pagos registrados sin movimiento bancario
- [ ] Confirmé si esos casos son errores, desfases de importación o pagos legítimos sin soporte bancario aún

## Criterio para cerrar conciliación
Solo avanzar si:
- [ ] `Diferencia Bs.` es exactamente `0,00`
- [ ] No quedan alertas críticas sin revisar
- [ ] Los pagos sin movimiento fueron entendidos y aceptados como situación del período

## Ejecución de cierre
- [ ] Pulsé `Cerrar conciliación del período`
- [ ] El sistema confirmó el cierre correctamente
- [ ] Se generó el registro resumen de conciliación

## Verificación posterior
- [ ] El período quedó conciliado
- [ ] Ya no hay diferencias abiertas
- [ ] Los ingresos vinculados muestran `conciliado = true`

## NO cerrar la conciliación si...
- [ ] la diferencia no es cero
- [ ] todavía no revisaste movimientos pendientes
- [ ] acabas de importar y sospechas que el período seleccionado es incorrecto
- [ ] la conciliación automática generó resultados que aún no validaste

## Señales de alerta
- [ ] muchos `sin_pago_sistema` en un período normalmente estable
- [ ] referencias bancarias repetidas con montos distintos
- [ ] pagos automáticos por cédula distribuidos en unidades inesperadas
- [ ] diferencia cero pero con pagos sin movimiento que nadie puede explicar

Si ocurre alguno de estos casos, revisa `15-runbook-incidencias.md`.

## Referencias
- `11-conciliacion-bancaria.md`
- `04-facturacion-cobros-y-bancos.md`
- `12-manual-operativo-por-rol.md`
- `15-runbook-incidencias.md`
