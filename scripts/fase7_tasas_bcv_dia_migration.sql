-- =============================================================================
-- FASE 7 — Caché local de tasas BCV oficiales por día (Bs. por USD)
-- Ejecutar en Supabase SQL Editor.
-- La app consulta primero esta tabla; si falta el día, sincroniza desde DolarAPI.
-- =============================================================================

CREATE TABLE IF NOT EXISTS tasas_bcv_dia (
    fecha            DATE PRIMARY KEY,
    tasa_bs_por_usd  NUMERIC(18, 6) NOT NULL,
    fuente           TEXT NOT NULL DEFAULT 'oficial',
    actualizado_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT tasas_bcv_dia_tasa_positiva CHECK (tasa_bs_por_usd > 0)
);

CREATE INDEX IF NOT EXISTS idx_tasas_bcv_dia_fecha ON tasas_bcv_dia (fecha DESC);

COMMENT ON TABLE tasas_bcv_dia IS 'Histórico oficial Bs/USD por fecha (caché de ve.dolarapi.com).';

ALTER TABLE tasas_bcv_dia ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON tasas_bcv_dia;
CREATE POLICY "service_role_all" ON tasas_bcv_dia FOR ALL USING (true);
