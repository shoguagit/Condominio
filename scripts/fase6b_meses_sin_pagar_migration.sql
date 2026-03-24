-- =============================================================================
-- FASE 6-B — Meses sin pagar y primer período (saldo inicial / reporte PDF)
-- Ejecutar en Supabase SQL Editor.
-- =============================================================================

ALTER TABLE unidades
    ADD COLUMN IF NOT EXISTS meses_sin_pagar INTEGER DEFAULT 0;

ALTER TABLE unidades
    ADD COLUMN IF NOT EXISTS primer_periodo VARCHAR(7);

COMMENT ON COLUMN unidades.meses_sin_pagar IS 'Meses de deuda según carga Excel morosos (o 0)';
COMMENT ON COLUMN unidades.primer_periodo IS 'Primer mes con cuota pendiente YYYY-MM (ej. 2026-02)';
