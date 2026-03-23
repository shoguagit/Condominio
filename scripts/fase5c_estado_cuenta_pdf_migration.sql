-- =============================================================================
-- FASE 5-C — Logo y textos de pie para estados de cuenta PDF (Sisconin)
-- Ejecutar en Supabase SQL Editor después de backup.
-- =============================================================================

ALTER TABLE condominios
    ADD COLUMN IF NOT EXISTS logo_url TEXT,
    ADD COLUMN IF NOT EXISTS pie_pagina_titular TEXT,
    ADD COLUMN IF NOT EXISTS pie_pagina_cuerpo TEXT;

COMMENT ON COLUMN condominios.logo_url IS 'Logo recibo/PDF: data URL base64 o URL https';
COMMENT ON COLUMN condominios.pie_pagina_titular IS 'Pie PDF bloque azul (titular)';
COMMENT ON COLUMN condominios.pie_pagina_cuerpo IS 'Pie PDF bloque con borde (cuerpo)';
