-- =============================================================================
-- FASE 3 — Registro opcional de reportes generados
-- Ejecutar en Supabase SQL Editor después de backup.
-- =============================================================================

CREATE TABLE IF NOT EXISTS reportes_generados (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id) ON DELETE CASCADE,
    tipo_reporte VARCHAR(50) NOT NULL,
    periodo DATE NOT NULL,
    unidad_id BIGINT REFERENCES unidades(id) ON DELETE SET NULL,
    generado_por VARCHAR(100),
    generado_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reportes_generados_condominio
    ON reportes_generados(condominio_id);
CREATE INDEX IF NOT EXISTS idx_reportes_generados_periodo
    ON reportes_generados(condominio_id, periodo);

ALTER TABLE reportes_generados ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_all" ON reportes_generados;
CREATE POLICY "service_role_all" ON reportes_generados FOR ALL USING (true);
