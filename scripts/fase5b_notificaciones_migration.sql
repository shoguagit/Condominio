-- =============================================================================
-- FASE 5-B — SMTP por condominio + auditoría de notificaciones a morosos
-- Ejecutar en Supabase SQL Editor (BACKUP antes).
-- IDs BIGINT alineados con condominios/unidades del proyecto.
--
-- Si ejecutó una versión anterior de este script con UUID como PK, elimine
-- primero la tabla: DROP TABLE IF EXISTS notificaciones_enviadas;
-- =============================================================================

ALTER TABLE condominios
ADD COLUMN IF NOT EXISTS smtp_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS smtp_app_password VARCHAR(255),
ADD COLUMN IF NOT EXISTS smtp_nombre_remitente VARCHAR(255)
    DEFAULT 'Administración del Condominio';

CREATE TABLE IF NOT EXISTS notificaciones_enviadas (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    periodo VARCHAR(7) NOT NULL,
    unidad_id BIGINT REFERENCES unidades(id) ON DELETE SET NULL,
    propietario_email VARCHAR(255),
    propietario_nombre VARCHAR(255),
    asunto VARCHAR(255),
    cuerpo TEXT,
    enviado BOOLEAN DEFAULT FALSE,
    error_mensaje TEXT,
    tipo VARCHAR(50) DEFAULT 'mora',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    enviado_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notif_env_condo_periodo
    ON notificaciones_enviadas (condominio_id, periodo);

ALTER TABLE notificaciones_enviadas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_all" ON notificaciones_enviadas;
CREATE POLICY "service_role_all" ON notificaciones_enviadas
    FOR ALL TO service_role USING (true) WITH CHECK (true);
