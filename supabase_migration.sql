-- ================================================================
-- Migration Supabase (generada por el sistema)
-- Objetivo: reglas de negocio, ajustes de esquema y nuevos módulos
-- Nota: ejecutar este SQL en Supabase (SQL Editor) con un rol
-- con permisos de ALTER/CREATE TABLE.
-- ================================================================

-- Alteraciones a tablas existentes
ALTER TABLE unidades
ADD COLUMN IF NOT EXISTS codigo VARCHAR(20);

ALTER TABLE unidades
ADD COLUMN IF NOT EXISTS alicuota_id BIGINT REFERENCES alicuotas(id);

ALTER TABLE unidades
ADD COLUMN IF NOT EXISTS saldo NUMERIC(14,2) DEFAULT 0.00;

ALTER TABLE empleados
ADD COLUMN IF NOT EXISTS area VARCHAR(100);

-- Empleados: default INACTIVO + validacion formato telefono celular
ALTER TABLE empleados
ALTER COLUMN activo SET DEFAULT FALSE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'empleados_telefono_celular_check'
    ) THEN
        ALTER TABLE empleados
        ADD CONSTRAINT empleados_telefono_celular_check
        CHECK (telefono_celular IS NULL OR telefono_celular LIKE '04%');
    END IF;
END $$;

ALTER TABLE gastos_fijos
ADD COLUMN IF NOT EXISTS tipo_gasto VARCHAR(50) DEFAULT 'Nómina';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'gastos_fijos_tipo_gasto_check'
    ) THEN
        ALTER TABLE gastos_fijos
        ADD CONSTRAINT gastos_fijos_tipo_gasto_check
        CHECK (tipo_gasto IN ('Nómina', 'Servicio recurrente', 'Contrato'));
    END IF;
END $$;

-- Conceptos: solo Gasto/Ajuste
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'conceptos_tipo_check'
    ) THEN
        ALTER TABLE conceptos
        ADD CONSTRAINT conceptos_tipo_check
        CHECK (tipo IN ('gasto', 'ajuste'));
    END IF;
END $$;

-- Unidades: codigo unico por condominio
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'unidades_condominio_codigo_uniq'
    ) THEN
        ALTER TABLE unidades
        ADD CONSTRAINT unidades_condominio_codigo_uniq
        UNIQUE (condominio_id, codigo);
    END IF;
END $$;

ALTER TABLE servicios
ALTER COLUMN precio_unitario DROP NOT NULL;

-- ================================================================
-- Unidad – Propietarios (1 unidad : N propietarios, activos/inactivos)
-- ================================================================
CREATE TABLE IF NOT EXISTS unidad_propietarios (
    id             BIGSERIAL PRIMARY KEY,
    unidad_id      BIGINT NOT NULL REFERENCES unidades(id) ON DELETE CASCADE,
    propietario_id BIGINT NOT NULL REFERENCES propietarios(id) ON DELETE CASCADE,
    activo         BOOLEAN DEFAULT TRUE,
    es_principal   BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(unidad_id, propietario_id)
);
CREATE INDEX IF NOT EXISTS idx_unidad_propietarios_unidad ON unidad_propietarios(unidad_id);
CREATE INDEX IF NOT EXISTS idx_unidad_propietarios_propietario ON unidad_propietarios(propietario_id);

-- Permitir crear unidad sin propietario ni alícuota (se asignan después)
ALTER TABLE unidades ALTER COLUMN propietario_id DROP NOT NULL;
ALTER TABLE unidades ALTER COLUMN alicuota_id DROP NOT NULL;

-- ================================================================
-- Nuevas tablas
-- ================================================================

-- 8) MOVIMIENTOS BANCARIOS
CREATE TABLE IF NOT EXISTS movimientos (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id),
    periodo DATE NOT NULL,  -- mes/año del movimiento
    fecha DATE NOT NULL,
    descripcion TEXT,
    referencia VARCHAR(100),
    tipo VARCHAR(10) CHECK(tipo IN ('egreso','ingreso')),
    monto_bs NUMERIC(14,2) DEFAULT 0,
    monto_usd NUMERIC(14,4) DEFAULT 0,
    tasa_cambio NUMERIC(12,4) DEFAULT 0,
    concepto_id BIGINT REFERENCES conceptos(id),
    unidad_id BIGINT REFERENCES unidades(id),
    propietario_id BIGINT REFERENCES propietarios(id),
    estado VARCHAR(20) DEFAULT 'pendiente',
    -- pendiente, clasificado, procesado
    fuente VARCHAR(20) DEFAULT 'manual',
    -- manual, excel
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9) PROCESO MENSUAL
CREATE TABLE IF NOT EXISTS procesos_mensuales (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id),
    periodo DATE NOT NULL,
    total_gastos_bs NUMERIC(14,2) DEFAULT 0,
    total_gastos_usd NUMERIC(14,4) DEFAULT 0,
    fondo_reserva_bs NUMERIC(14,2) DEFAULT 0,
    total_facturable_bs NUMERIC(14,2) DEFAULT 0,
    estado VARCHAR(20) DEFAULT 'borrador',
    -- borrador, procesado, cerrado
    created_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    UNIQUE(condominio_id, periodo)
);

CREATE TABLE IF NOT EXISTS cuotas_unidad (
    id BIGSERIAL PRIMARY KEY,
    proceso_id BIGINT REFERENCES procesos_mensuales(id),
    unidad_id BIGINT REFERENCES unidades(id),
    propietario_id BIGINT REFERENCES propietarios(id),
    condominio_id BIGINT REFERENCES condominios(id),
    periodo DATE NOT NULL,
    alicuota_valor NUMERIC(10,6),
    total_gastos_bs NUMERIC(14,2),
    cuota_calculada_bs NUMERIC(14,2),
    saldo_anterior_bs NUMERIC(14,2) DEFAULT 0,
    pagos_mes_bs NUMERIC(14,2) DEFAULT 0,
    total_a_pagar_bs NUMERIC(14,2),
    estado VARCHAR(20) DEFAULT 'pendiente',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================================
-- Actualizar conceptos tipos válidos
-- ================================================================
-- Recomendación (no ejecuta migración automática):
-- - Asegurar que en la tabla `conceptos` el campo `tipo` contenga
--   los valores esperados para el sistema (Gasto/Ajuste).
-- - En caso de que exista una constraint antigua, actualizarla manualmente.

