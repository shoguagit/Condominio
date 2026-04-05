-- =============================================================================
-- Limpiar movimientos (y pagos automáticos por cédula) para volver a importar
-- el Excel sin “omitidos por duplicado”.
--
-- 1) Cambia condominio_id y la fecha periodo (primer día del mes, como en la app).
-- 2) Ejecuta todo el bloque en Supabase → SQL Editor.
--
-- Orden: primero borra pagos con origen conciliacion_automatica de ese mes;
-- luego borra movimientos. Otras tablas: pagos.movimiento_id pasa a NULL si aplica FK.
-- =============================================================================

BEGIN;

-- ▼▼▼ EDITAR ▼▼▼
DELETE FROM pagos p
WHERE p.condominio_id = 11
  AND p.periodo = DATE '2026-03-01'
  AND COALESCE(p.origen, '') = 'conciliacion_automatica';

DELETE FROM movimientos m
WHERE m.condominio_id = 11
  AND m.periodo = DATE '2026-03-01';
-- ▲▲▲▲▲▲▲▲▲▲▲

COMMIT;

-- -----------------------------------------------------------------------------
-- Solo movimientos (sin tocar pagos manuales ni automáticos):
-- -----------------------------------------------------------------------------
/*
BEGIN;
DELETE FROM movimientos m
WHERE m.condominio_id = 11
  AND m.periodo = DATE '2026-03-01';
COMMIT;
*/

-- -----------------------------------------------------------------------------
-- Ver cuántas filas vas a borrar (ejecutar antes, sin DELETE):
-- -----------------------------------------------------------------------------
/*
SELECT COUNT(*) AS movimientos
FROM movimientos
WHERE condominio_id = 11 AND periodo = DATE '2026-03-01';

SELECT COUNT(*) AS pagos_auto
FROM pagos
WHERE condominio_id = 11
  AND periodo = DATE '2026-03-01'
  AND COALESCE(origen, '') = 'conciliacion_automatica';
*/
