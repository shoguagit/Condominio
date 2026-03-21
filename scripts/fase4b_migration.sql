-- =============================================================================
-- FASE 4-B — Cobros extraordinarios por indiviso (BIGINT id, período YYYY-MM)
-- Ejecutar en Supabase SQL Editor después de backup.
-- =============================================================================

CREATE TABLE IF NOT EXISTS cobros_extraordinarios (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    periodo VARCHAR(7) NOT NULL,
    concepto VARCHAR(255) NOT NULL,
    monto_total NUMERIC(14, 2) NOT NULL CHECK (monto_total > 0),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cobros_ext_condo_periodo
    ON cobros_extraordinarios (condominio_id, periodo);

CREATE TABLE IF NOT EXISTS cobros_extraordinarios_unidad (
    id BIGSERIAL PRIMARY KEY,
    cobro_extraordinario_id BIGINT NOT NULL
        REFERENCES cobros_extraordinarios(id) ON DELETE CASCADE,
    unidad_id BIGINT NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    condominio_id BIGINT NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    periodo VARCHAR(7) NOT NULL,
    monto NUMERIC(14, 2) NOT NULL,
    pagado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cobros_ext_u_unidad_periodo
    ON cobros_extraordinarios_unidad (unidad_id, periodo);

ALTER TABLE cuotas_unidad
ADD COLUMN IF NOT EXISTS cobros_extraordinarios NUMERIC(14, 2) DEFAULT 0;

ALTER TABLE cobros_extraordinarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE cobros_extraordinarios_unidad ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON cobros_extraordinarios;
CREATE POLICY "service_role_all" ON cobros_extraordinarios FOR ALL USING (true);

DROP POLICY IF EXISTS "service_role_all" ON cobros_extraordinarios_unidad;
CREATE POLICY "service_role_all" ON cobros_extraordinarios_unidad FOR ALL USING (true);
