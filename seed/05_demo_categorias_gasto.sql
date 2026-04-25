-- Seed: Categorías de gasto sistema
-- Ejecutar después de crear las tablas (via fase10_categorias_gasto.sql o schema base)

INSERT INTO categorias_gasto (codigo, nombre, orden) VALUES
    ('NOMINA',        'Nómina',         1),
    ('SERVICIOS',     'Servicios',       2),
    ('MANTENIMIENTO', 'Mantenimiento',   3),
    ('OTROS',         'Otros',           4)
ON CONFLICT (codigo) DO NOTHING
RETURNING id, codigo, nombre;