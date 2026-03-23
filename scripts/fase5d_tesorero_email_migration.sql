-- Fase 5-D: correo del tesorero para PDF combinado de estados de cuenta
ALTER TABLE condominios
    ADD COLUMN IF NOT EXISTS tesorero_email VARCHAR(255);

COMMENT ON COLUMN condominios.tesorero_email IS
    'Correo del tesorero: recibe PDF con todos los recibos del envío masivo';
