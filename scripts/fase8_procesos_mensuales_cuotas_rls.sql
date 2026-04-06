-- =============================================================================
-- FASE 8 — RLS en procesos_mensuales y cuotas_unidad
-- Sin política permisiva, INSERT/SELECT fallan con:
--   new row violates row-level security policy for table "procesos_mensuales" (42501)
-- Mismo patrón que fase1 (pagos, presupuestos) y docs/supabase_schema.sql.
-- Ejecutar en Supabase → SQL Editor (tras backup si aplica).
-- =============================================================================

ALTER TABLE IF EXISTS procesos_mensuales ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cuotas_unidad ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON procesos_mensuales;
CREATE POLICY "service_role_all" ON procesos_mensuales FOR ALL USING (true);

DROP POLICY IF EXISTS "service_role_all" ON cuotas_unidad;
CREATE POLICY "service_role_all" ON cuotas_unidad FOR ALL USING (true);
