-- Fase 10: Sistema de categorías de gastos con clasificación automática.
-- Ejecutar en Supabase antes del deploy.

-- ── Categorías base del sistema (4 categorías fijas) ──────────────────────────
CREATE TABLE IF NOT EXISTS categorias_gasto (
    id         SERIAL PRIMARY KEY,
    codigo     VARCHAR(30)  UNIQUE NOT NULL,
    nombre     VARCHAR(100) NOT NULL,
    orden      INTEGER      NOT NULL DEFAULT 99,
    activo     BOOLEAN      DEFAULT TRUE,
    created_at TIMESTAMPTZ  DEFAULT NOW()
);

ALTER TABLE categorias_gasto ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_all" ON categorias_gasto;
CREATE POLICY "service_role_all" ON categorias_gasto FOR ALL USING (true);

-- ── Subcategorías configurables por condominio ────────────────────────────────
CREATE TABLE IF NOT EXISTS subcategorias_gasto (
    id            SERIAL PRIMARY KEY,
    condominio_id INTEGER REFERENCES condominios(id) ON DELETE CASCADE,
    categoria_id  INTEGER REFERENCES categorias_gasto(id),
    codigo        VARCHAR(30)  NOT NULL,
    nombre        VARCHAR(100) NOT NULL,
    orden         INTEGER      NOT NULL DEFAULT 99,
    es_sistema    BOOLEAN      DEFAULT FALSE,
    activo        BOOLEAN      DEFAULT TRUE,
    created_at    TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (condominio_id, codigo)
);

ALTER TABLE subcategorias_gasto ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_all" ON subcategorias_gasto;
CREATE POLICY "service_role_all" ON subcategorias_gasto FOR ALL USING (true);

-- ── Palabras clave para clasificación automática ──────────────────────────────
CREATE TABLE IF NOT EXISTS palabras_clave_categoria (
    id              SERIAL PRIMARY KEY,
    condominio_id   INTEGER REFERENCES condominios(id) ON DELETE CASCADE,
    subcategoria_id INTEGER REFERENCES subcategorias_gasto(id) ON DELETE CASCADE,
    palabra         VARCHAR(100) NOT NULL,
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

ALTER TABLE palabras_clave_categoria ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_all" ON palabras_clave_categoria;
CREATE POLICY "service_role_all" ON palabras_clave_categoria FOR ALL USING (true);

-- ── Seed: categorías base del sistema ─────────────────────────────────────────
INSERT INTO categorias_gasto (codigo, nombre, orden) VALUES
    ('NOMINA',        'Nómina',         1),
    ('SERVICIOS',     'Servicios',       2),
    ('MANTENIMIENTO', 'Mantenimiento',   3),
    ('OTROS',         'Otros',           4)
ON CONFLICT (codigo) DO NOTHING;
