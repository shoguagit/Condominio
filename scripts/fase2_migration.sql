-- =============================================================================
-- FASE 2 — Cierre mensual (columnas mora futura, presupuesto vencimiento, config)
-- Ejecutar en Supabase SQL Editor después de backup.
-- =============================================================================

-- Indiviso: NUMERIC(6,4) solo admite hasta 99.9999; hace falta 100.0000 como máximo.
ALTER TABLE unidades
ALTER COLUMN indiviso_pct TYPE NUMERIC(8,4);

-- Presupuestos: fecha de vencimiento opcional
ALTER TABLE presupuestos
ADD COLUMN IF NOT EXISTS fecha_vencimiento DATE;

-- Cuotas: campos para mora (fase futura)
ALTER TABLE cuotas_unidad
ADD COLUMN IF NOT EXISTS mora_bs NUMERIC(14,2) DEFAULT 0;

ALTER TABLE cuotas_unidad
ADD COLUMN IF NOT EXISTS pct_mora NUMERIC(5,2) DEFAULT 0;

-- Configuración de mora por condominio (fase futura)
CREATE TABLE IF NOT EXISTS config_mora (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id) ON DELETE CASCADE,
    pct_mora NUMERIC(5,2) DEFAULT 5.00,
    dias_gracia INT DEFAULT 5,
    activo BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(condominio_id)
);

CREATE INDEX IF NOT EXISTS idx_config_mora_condominio ON config_mora(condominio_id);

ALTER TABLE config_mora ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_all" ON config_mora;
CREATE POLICY "service_role_all" ON config_mora FOR ALL USING (true);
