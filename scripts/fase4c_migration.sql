-- =============================================================================
-- FASE 4-C — Conciliación bancaria (movimientos ↔ pagos)
-- BIGINT alineado con condominios/pagos/movimientos del proyecto.
-- =============================================================================

ALTER TABLE movimientos
ADD COLUMN IF NOT EXISTS conciliado BOOLEAN DEFAULT FALSE;

ALTER TABLE movimientos
ADD COLUMN IF NOT EXISTS pago_id BIGINT REFERENCES pagos(id) ON DELETE SET NULL;

ALTER TABLE movimientos
ADD COLUMN IF NOT EXISTS tipo_alerta VARCHAR(50) DEFAULT NULL;

ALTER TABLE movimientos
ADD COLUMN IF NOT EXISTS revisado BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS conciliaciones (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    periodo VARCHAR(7) NOT NULL,
    fecha_conciliacion TIMESTAMPTZ DEFAULT NOW(),
    saldo_banco NUMERIC(14, 2) NOT NULL,
    saldo_sistema NUMERIC(14, 2) NOT NULL,
    diferencia NUMERIC(14, 2) GENERATED ALWAYS AS (saldo_banco - saldo_sistema) STORED,
    estado VARCHAR(20) DEFAULT 'pendiente',
    movimientos_banco INTEGER DEFAULT 0,
    movimientos_conciliados INTEGER DEFAULT 0,
    pagos_sin_movimiento INTEGER DEFAULT 0,
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conciliaciones_condo_periodo
    ON conciliaciones (condominio_id, periodo);

ALTER TABLE conciliaciones ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON conciliaciones;
CREATE POLICY "service_role_all" ON conciliaciones
    FOR ALL TO service_role USING (true) WITH CHECK (true);
