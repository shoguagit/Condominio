-- Fase 9: tabla para agrupaciones de gastos por período.
-- Permite al administrador agrupar los egresos en conceptos consolidados
-- y asignar cada grupo a Recibo, Balance o ambos.
--
-- grupos JSONB: array de objetos con la estructura:
--   { nombre, movimiento_ids[], total_bs, total_usd, recibo, balance }

CREATE TABLE IF NOT EXISTS agrupaciones_gasto (
    id            BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT      NOT NULL,
    periodo       DATE        NOT NULL,
    grupos        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (condominio_id, periodo)
);

ALTER TABLE agrupaciones_gasto ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON agrupaciones_gasto;
CREATE POLICY "service_role_all" ON agrupaciones_gasto
    FOR ALL USING (true);
