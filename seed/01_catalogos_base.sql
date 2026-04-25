BEGIN;

INSERT INTO public.paises (id, nombre, codigo_iso, moneda, simbolo_moneda) VALUES
(1, 'Venezuela', 'VEN', 'VES', 'Bs.'),
(2, 'Colombia',  'COL', 'COP', '$'),
(3, 'Ecuador',   'ECU', 'USD', '$'),
(4, 'Perú',      'PER', 'PEN', 'S/'),
(5, 'Argentina', 'ARG', 'ARS', '$')
ON CONFLICT (id) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    codigo_iso = EXCLUDED.codigo_iso,
    moneda = EXCLUDED.moneda,
    simbolo_moneda = EXCLUDED.simbolo_moneda;

INSERT INTO public.tipos_documento (pais_id, nombre, formato_regex, descripcion) VALUES
(1, 'RIF',  '^[VJGECP]-\d{8}-\d$', 'Registro de Información Fiscal'),
(2, 'NIT',  '^\d{9,10}(-\d)?$',   'Número de Identificación Tributaria'),
(3, 'RUC',  '^\d{13}$',            'Registro Único de Contribuyentes'),
(4, 'RUC',  '^\d{11}$',            'Registro Único de Contribuyentes'),
(5, 'CUIT', '^\d{2}-\d{8}-\d$',  'Clave Única de Identificación Tributaria')
ON CONFLICT DO NOTHING;

COMMIT;
