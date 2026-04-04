-- FASE 4-E — Columnas en pagos para conciliación automática por cédula
ALTER TABLE pagos
ADD COLUMN IF NOT EXISTS tipo_pago VARCHAR(20) DEFAULT 'total';

ALTER TABLE pagos
ADD COLUMN IF NOT EXISTS origen VARCHAR(50) DEFAULT 'manual';

ALTER TABLE pagos
ADD COLUMN IF NOT EXISTS movimiento_id BIGINT REFERENCES movimientos(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_pagos_movimiento_id ON pagos(movimiento_id);
CREATE INDEX IF NOT EXISTS idx_pagos_origen ON pagos(condominio_id, origen);
