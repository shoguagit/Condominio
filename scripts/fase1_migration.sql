-- =============================================================================
-- FASE 1 — Unidades (indiviso %), Pagos, Presupuestos
-- Ejecutar en Supabase SQL Editor después de backup.
-- =============================================================================

-- Unidades: indiviso %, estado de pago, tipo (PDF)
ALTER TABLE unidades
ADD COLUMN IF NOT EXISTS indiviso_pct NUMERIC(8,4) DEFAULT 0.0000;

ALTER TABLE unidades
ADD COLUMN IF NOT EXISTS estado_pago VARCHAR(20) DEFAULT 'al_dia';

ALTER TABLE unidades
ADD COLUMN IF NOT EXISTS tipo VARCHAR(50) DEFAULT 'Apartamento';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'unidades_estado_pago_check'
    ) THEN
        ALTER TABLE unidades
        ADD CONSTRAINT unidades_estado_pago_check
        CHECK (estado_pago IN ('al_dia', 'moroso', 'parcial'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'unidades_tipo_unidad_check'
    ) THEN
        ALTER TABLE unidades
        ADD CONSTRAINT unidades_tipo_unidad_check
        CHECK (tipo IN ('Apartamento', 'Casa', 'Local comercial', 'Estacionamiento'));
    END IF;
END $$;

-- Alinear tipo_propiedad con valores del PDF (sustituir CHECK antiguo si existe)
ALTER TABLE unidades DROP CONSTRAINT IF EXISTS unidades_tipo_propiedad_check;
ALTER TABLE unidades
ADD CONSTRAINT unidades_tipo_propiedad_check
CHECK (tipo_propiedad IN ('Apartamento', 'Casa', 'Local comercial', 'Estacionamiento'));

-- Migrar datos legacy a valores válidos
UPDATE unidades SET tipo_propiedad = 'Local comercial' WHERE tipo_propiedad = 'Local';
UPDATE unidades SET tipo_propiedad = 'Apartamento' WHERE tipo_propiedad IN ('Oficina', 'Maletero');
UPDATE unidades SET tipo = tipo_propiedad WHERE tipo IS NULL OR tipo = '';

-- Tabla pagos
CREATE TABLE IF NOT EXISTS pagos (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id) ON DELETE RESTRICT,
    unidad_id BIGINT REFERENCES unidades(id) ON DELETE RESTRICT,
    propietario_id BIGINT REFERENCES propietarios(id) ON DELETE SET NULL,
    periodo DATE NOT NULL,
    fecha_pago DATE NOT NULL,
    monto_bs NUMERIC(14,2) NOT NULL,
    monto_usd NUMERIC(14,4) DEFAULT 0,
    tasa_cambio NUMERIC(12,4) DEFAULT 0,
    metodo VARCHAR(20) NOT NULL
        CHECK (metodo IN ('transferencia', 'deposito', 'efectivo')),
    referencia VARCHAR(100),
    observaciones TEXT,
    estado VARCHAR(20) DEFAULT 'confirmado',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pagos_condominio ON pagos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_pagos_periodo ON pagos(condominio_id, periodo);
CREATE INDEX IF NOT EXISTS idx_pagos_unidad ON pagos(unidad_id);

-- Tabla presupuestos
CREATE TABLE IF NOT EXISTS presupuestos (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id) ON DELETE RESTRICT,
    periodo DATE NOT NULL,
    monto_bs NUMERIC(14,2) NOT NULL,
    monto_usd NUMERIC(14,4) DEFAULT 0,
    descripcion TEXT,
    estado VARCHAR(20) DEFAULT 'activo',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(condominio_id, periodo)
);

CREATE INDEX IF NOT EXISTS idx_presupuestos_condominio ON presupuestos(condominio_id);

-- RLS (mismo patrón que el resto del proyecto)
ALTER TABLE pagos ENABLE ROW LEVEL SECURITY;
ALTER TABLE presupuestos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON pagos;
CREATE POLICY "service_role_all" ON pagos FOR ALL USING (true);

DROP POLICY IF EXISTS "service_role_all" ON presupuestos;
CREATE POLICY "service_role_all" ON presupuestos FOR ALL USING (true);
