-- Añadir Chile y México a paises y sus tipos de documento (RUT, RFC).
-- Ejecutar en Supabase SQL Editor si desea que aparezcan en el formulario de Condominios.

INSERT INTO paises (id, nombre, codigo_iso, moneda, simbolo_moneda) VALUES
(6, 'Chile',   'CHL', 'CLP', '$'),
(7, 'México',  'MEX', 'MXN', '$')
ON CONFLICT (id) DO NOTHING;

INSERT INTO tipos_documento (pais_id, nombre, formato_regex, descripcion) VALUES
(6, 'RUT', '^\d{7,8}-[\dkK]$', 'Rol Único Tributario'),
(7, 'RFC', '^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{2}[0-9A]$', 'Registro Federal de Contribuyentes')
ON CONFLICT DO NOTHING;
