-- =============================================================================
-- FASE 4-D — Políticas RLS para tabla movimientos (carga Excel / PostgREST)
-- =============================================================================
-- Si en la app aparece:
--   new row violates row-level security policy for table "movimientos" (42501)
-- es porque RLS está activo en movimientos y falta una política permisiva
-- alineada con el resto del proyecto (p. ej. pagos en fase1_migration.sql).
--
-- Ejecutar en Supabase → SQL Editor. Luego, si hace falta:
-- Settings → API → Reload schema.
-- =============================================================================

ALTER TABLE movimientos ENABLE ROW LEVEL SECURITY;

-- Quitar políticas que suelen bloquear inserts (nombres típicos / intentos previos)
DROP POLICY IF EXISTS "service_role_all" ON movimientos;
DROP POLICY IF EXISTS "movimientos_select" ON movimientos;
DROP POLICY IF EXISTS "movimientos_insert" ON movimientos;
DROP POLICY IF EXISTS "movimientos_update" ON movimientos;
DROP POLICY IF EXISTS "movimientos_delete" ON movimientos;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON movimientos;
DROP POLICY IF EXISTS "Enable read access for all users" ON movimientos;
DROP POLICY IF EXISTS "Authenticated users can read movimientos" ON movimientos;
DROP POLICY IF EXISTS "Users can insert their own movimientos" ON movimientos;

-- Mismo patrón que pagos / presupuestos (fase1): acceso vía cliente con anon + JWT
CREATE POLICY "service_role_all" ON movimientos
    FOR ALL
    USING (true)
    WITH CHECK (true);
