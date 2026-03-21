-- =============================================================================
-- FASE 4-A — Día límite de pago (condominios), mora en cuotas, config_mora
-- Ejecutar en Supabase SQL Editor (orden sugerido).
-- Nota: config_mora ya existe en fase2 con condominio_id BIGINT, pct_mora, activo.
-- =============================================================================

-- 1) Día límite de pago por condominio (1–28)
ALTER TABLE condominios
ADD COLUMN IF NOT EXISTS dia_limite_pago INTEGER DEFAULT 15;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'condominios_dia_limite_pago_check'
    ) THEN
        ALTER TABLE condominios
        ADD CONSTRAINT condominios_dia_limite_pago_check
        CHECK (dia_limite_pago BETWEEN 1 AND 28);
    END IF;
END $$;

-- 2) Columna mora en cuotas (además de mora_bs de fase2)
ALTER TABLE cuotas_unidad
ADD COLUMN IF NOT EXISTS mora NUMERIC(14,2) DEFAULT 0;

-- 3) Filas config_mora para condominios sin registro
INSERT INTO config_mora (condominio_id, pct_mora, activo)
SELECT c.id, 0.00, FALSE
FROM condominios c
WHERE NOT EXISTS (
    SELECT 1 FROM config_mora m WHERE m.condominio_id = c.id
);
