-- =============================================================================
-- FASE 6-A — Saldo inicial histórico por unidad (carga Excel + revisión manual)
-- Ejecutar en Supabase SQL Editor después de backup.
-- =============================================================================

ALTER TABLE unidades
    ADD COLUMN IF NOT EXISTS saldo_inicial_bs NUMERIC(14, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS requiere_revision BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS nota_revision TEXT;

COMMENT ON COLUMN unidades.saldo_inicial_bs IS 'Saldo pendiente histórico registrado al inicio (Bs.)';
COMMENT ON COLUMN unidades.requiere_revision IS 'TRUE si la diferencia del Excel supera el umbral';
COMMENT ON COLUMN unidades.nota_revision IS 'Motivo o nota de revisión / corrección manual';
