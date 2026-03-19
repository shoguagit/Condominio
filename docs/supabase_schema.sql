-- =============================================================================
-- SISTEMA DE CONDOMINIO — Schema completo para Supabase (PostgreSQL)
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query
-- Orden de ejecución: este archivo completo, de arriba a abajo
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Función genérica para actualizar updated_at automáticamente
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- 1. PAÍSES
-- =============================================================================
CREATE TABLE IF NOT EXISTS paises (
    id             SERIAL PRIMARY KEY,
    nombre         VARCHAR(100) NOT NULL,
    codigo_iso     VARCHAR(3)   NOT NULL,
    moneda         VARCHAR(10),
    simbolo_moneda VARCHAR(5)
);

INSERT INTO paises (id, nombre, codigo_iso, moneda, simbolo_moneda) VALUES
(1, 'Venezuela', 'VEN', 'VES', 'Bs.'),
(2, 'Colombia',  'COL', 'COP', '$'),
(3, 'Ecuador',   'ECU', 'USD', '$'),
(4, 'Perú',      'PER', 'PEN', 'S/'),
(5, 'Argentina', 'ARG', 'ARS', '$')
ON CONFLICT (id) DO NOTHING;


-- =============================================================================
-- 2. TIPOS DE DOCUMENTO
-- =============================================================================
CREATE TABLE IF NOT EXISTS tipos_documento (
    id            SERIAL PRIMARY KEY,
    pais_id       INT REFERENCES paises(id) ON DELETE RESTRICT,
    nombre        VARCHAR(50)  NOT NULL,
    formato_regex VARCHAR(100),
    descripcion   VARCHAR(200)
);

INSERT INTO tipos_documento (pais_id, nombre, formato_regex, descripcion) VALUES
(1, 'RIF',  '^[VJGECP]-\d{8}-\d$',         'Registro de Información Fiscal'),
(2, 'NIT',  '^\d{9,10}(-\d)?$',             'Número de Identificación Tributaria'),
(3, 'RUC',  '^\d{13}$',                     'Registro Único de Contribuyentes'),
(4, 'RUC',  '^\d{11}$',                     'Registro Único de Contribuyentes'),
(5, 'CUIT', '^\d{2}-\d{8}-\d$',             'Clave Única de Identificación Tributaria')
ON CONFLICT DO NOTHING;


-- =============================================================================
-- 3. CONDOMINIOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS condominios (
    id                  BIGSERIAL PRIMARY KEY,
    nombre              VARCHAR(200) NOT NULL,
    direccion           TEXT         NOT NULL,
    pais_id             INT          REFERENCES paises(id)         ON DELETE RESTRICT DEFAULT 1,
    tipo_documento_id   INT          REFERENCES tipos_documento(id) ON DELETE RESTRICT,
    numero_documento    VARCHAR(30),
    telefono            VARCHAR(20),
    email               VARCHAR(100),
    mes_proceso         DATE         DEFAULT DATE_TRUNC('month', CURRENT_DATE),
    tasa_cambio         NUMERIC(12, 4) DEFAULT 0,
    moneda_principal    VARCHAR(10)  DEFAULT 'USD',
    activo              BOOLEAN      DEFAULT TRUE,
    created_at          TIMESTAMPTZ  DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_condominios_activo ON condominios(activo);

DROP TRIGGER IF EXISTS trg_condominios_updated_at ON condominios;
CREATE TRIGGER trg_condominios_updated_at
    BEFORE UPDATE ON condominios
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- =============================================================================
-- 4. USUARIOS DEL SISTEMA
-- =============================================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id             BIGSERIAL   PRIMARY KEY,
    condominio_id  BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    nombre         VARCHAR(150) NOT NULL,
    email          VARCHAR(100) UNIQUE NOT NULL,
    rol            VARCHAR(30)  DEFAULT 'operador'
                   CHECK (rol IN ('admin', 'operador', 'consulta')),
    activo         BOOLEAN     DEFAULT TRUE,
    ultimo_acceso  TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
    -- La contraseña es gestionada por Supabase Auth
);

CREATE INDEX IF NOT EXISTS idx_usuarios_condominio ON usuarios(condominio_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_activo     ON usuarios(activo);

DROP TRIGGER IF EXISTS trg_usuarios_updated_at ON usuarios;
CREATE TRIGGER trg_usuarios_updated_at
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- =============================================================================
-- 5. PROVEEDORES
-- =============================================================================
CREATE TABLE IF NOT EXISTS proveedores (
    id                BIGSERIAL   PRIMARY KEY,
    condominio_id     BIGINT      REFERENCES condominios(id)     ON DELETE RESTRICT,
    nombre            VARCHAR(200) NOT NULL,
    tipo_documento_id INT         REFERENCES tipos_documento(id) ON DELETE RESTRICT,
    numero_documento  VARCHAR(30),
    direccion         TEXT,
    telefono_fijo     VARCHAR(20),
    telefono_celular  VARCHAR(20),
    correo            VARCHAR(100),
    contacto          VARCHAR(150),
    notas             TEXT,
    saldo             NUMERIC(14, 2) DEFAULT 0,
    activo            BOOLEAN     DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proveedores_condominio ON proveedores(condominio_id);
CREATE INDEX IF NOT EXISTS idx_proveedores_activo     ON proveedores(activo);
CREATE INDEX IF NOT EXISTS idx_proveedores_nombre     ON proveedores(nombre);

DROP TRIGGER IF EXISTS trg_proveedores_updated_at ON proveedores;
CREATE TRIGGER trg_proveedores_updated_at
    BEFORE UPDATE ON proveedores
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- =============================================================================
-- 6. PROPIETARIOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS propietarios (
    id             BIGSERIAL   PRIMARY KEY,
    condominio_id  BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    nombre         VARCHAR(200) NOT NULL,
    cedula         VARCHAR(30),
    telefono       VARCHAR(20),
    correo         VARCHAR(100),
    direccion      TEXT,
    notas          TEXT,
    activo         BOOLEAN     DEFAULT TRUE,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_propietarios_condominio ON propietarios(condominio_id);
CREATE INDEX IF NOT EXISTS idx_propietarios_activo     ON propietarios(activo);


-- =============================================================================
-- 7. UNIDADES
-- =============================================================================
CREATE TABLE IF NOT EXISTS unidades (
    id              BIGSERIAL   PRIMARY KEY,
    condominio_id   BIGINT      REFERENCES condominios(id)  ON DELETE RESTRICT,
    propietario_id  BIGINT      REFERENCES propietarios(id) ON DELETE RESTRICT,
    tipo_propiedad  VARCHAR(50)
                    CHECK (tipo_propiedad IN ('Apartamento','Local','Oficina','Estacionamiento','Maletero')),
    numero          VARCHAR(20),
    piso            VARCHAR(10),
    tipo_condomino  VARCHAR(30)
                    CHECK (tipo_condomino IN ('Propietario','Arrendatario')),
    cuota_fija      NUMERIC(14, 2) DEFAULT 0,
    activo          BOOLEAN     DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_unidades_condominio ON unidades(condominio_id);
CREATE INDEX IF NOT EXISTS idx_unidades_activo     ON unidades(activo);

-- Unidad – Propietarios (1 unidad : N propietarios; ver supabase_migration.sql)
-- unidad_propietarios(id, unidad_id, propietario_id, activo, es_principal)


-- =============================================================================
-- 8. ALÍCUOTAS
-- =============================================================================
CREATE TABLE IF NOT EXISTS alicuotas (
    id                 BIGSERIAL   PRIMARY KEY,
    condominio_id      BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    descripcion        VARCHAR(200) NOT NULL,
    autocalcular       BOOLEAN     DEFAULT FALSE,
    cantidad_unidades  INT         DEFAULT 0,
    total_alicuota     NUMERIC(10, 6) DEFAULT 0,
    activo             BOOLEAN     DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_alicuotas_condominio ON alicuotas(condominio_id);
CREATE INDEX IF NOT EXISTS idx_alicuotas_activo     ON alicuotas(activo);


-- =============================================================================
-- 9. FONDOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS fondos (
    id             BIGSERIAL   PRIMARY KEY,
    condominio_id  BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    nombre         VARCHAR(150) NOT NULL,
    alicuota_id    BIGINT      REFERENCES alicuotas(id)  ON DELETE RESTRICT,
    saldo_inicial  NUMERIC(14, 2) DEFAULT 0,
    saldo          NUMERIC(14, 2) DEFAULT 0,
    tipo           VARCHAR(30),
    cantidad       NUMERIC(14, 4) DEFAULT 0,
    activo         BOOLEAN     DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_fondos_condominio ON fondos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_fondos_activo     ON fondos(activo);


-- =============================================================================
-- 10. SERVICIOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS servicios (
    id              BIGSERIAL   PRIMARY KEY,
    condominio_id   BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    nombre          VARCHAR(150) NOT NULL,
    precio_unitario NUMERIC(14, 2) DEFAULT 0,
    activo          BOOLEAN     DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_servicios_condominio ON servicios(condominio_id);
CREATE INDEX IF NOT EXISTS idx_servicios_activo     ON servicios(activo);


-- =============================================================================
-- 11. CONCEPTOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS conceptos (
    id             BIGSERIAL   PRIMARY KEY,
    condominio_id  BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    nombre         VARCHAR(150) NOT NULL,
    tipo           VARCHAR(10)  NOT NULL
                   CHECK (tipo IN ('gasto', 'ingreso')),
    activo         BOOLEAN     DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_conceptos_condominio ON conceptos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_conceptos_activo     ON conceptos(activo);


-- =============================================================================
-- 12. GASTOS FIJOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS gastos_fijos (
    id             BIGSERIAL   PRIMARY KEY,
    condominio_id  BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    descripcion    VARCHAR(200) NOT NULL,
    monto          NUMERIC(14, 2) DEFAULT 0,
    alicuota_id    BIGINT      REFERENCES alicuotas(id)  ON DELETE RESTRICT,
    activo         BOOLEAN     DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_gastos_fijos_condominio ON gastos_fijos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_gastos_fijos_activo     ON gastos_fijos(activo);


-- =============================================================================
-- 13. CONCEPTOS DE CONSUMO
-- =============================================================================
CREATE TABLE IF NOT EXISTS conceptos_consumo (
    id              BIGSERIAL   PRIMARY KEY,
    condominio_id   BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    nombre          VARCHAR(150) NOT NULL,
    unidad_medida   VARCHAR(30),
    precio_unitario NUMERIC(14, 4) DEFAULT 0,
    tipo_precio     VARCHAR(20)  DEFAULT 'fijo'
                    CHECK (tipo_precio IN ('fijo', 'tabulador')),
    activo          BOOLEAN     DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_conceptos_consumo_condominio ON conceptos_consumo(condominio_id);
CREATE INDEX IF NOT EXISTS idx_conceptos_consumo_activo     ON conceptos_consumo(activo);


-- =============================================================================
-- 14. CUENTAS / BANCOS
-- =============================================================================
CREATE TABLE IF NOT EXISTS cuentas_bancos (
    id             BIGSERIAL   PRIMARY KEY,
    condominio_id  BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    descripcion    VARCHAR(150) NOT NULL,
    numero_cuenta  VARCHAR(30),
    saldo_inicial  NUMERIC(14, 2) DEFAULT 0,
    saldo          NUMERIC(14, 2) DEFAULT 0,
    moneda         VARCHAR(10)  DEFAULT 'USD',
    activo         BOOLEAN     DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_cuentas_bancos_condominio ON cuentas_bancos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_cuentas_bancos_activo     ON cuentas_bancos(activo);


-- =============================================================================
-- 15. FACTURAS DE PROVEEDOR
-- =============================================================================
CREATE TABLE IF NOT EXISTS facturas_proveedor (
    id                BIGSERIAL   PRIMARY KEY,
    condominio_id     BIGINT      REFERENCES condominios(id)  ON DELETE RESTRICT,
    numero            VARCHAR(30),
    fecha             DATE        DEFAULT CURRENT_DATE,
    fecha_vencimiento DATE,
    proveedor_id      BIGINT      REFERENCES proveedores(id)  ON DELETE RESTRICT,
    descripcion       TEXT,
    total             NUMERIC(14, 2) DEFAULT 0,
    pagado            NUMERIC(14, 2) DEFAULT 0,
    saldo             NUMERIC(14, 2)
                      GENERATED ALWAYS AS (total - pagado) STORED,
    mes_proceso       DATE,
    activo            BOOLEAN     DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facturas_condominio   ON facturas_proveedor(condominio_id);
CREATE INDEX IF NOT EXISTS idx_facturas_proveedor    ON facturas_proveedor(proveedor_id);
CREATE INDEX IF NOT EXISTS idx_facturas_mes_proceso  ON facturas_proveedor(mes_proceso);
CREATE INDEX IF NOT EXISTS idx_facturas_activo       ON facturas_proveedor(activo);

DROP TRIGGER IF EXISTS trg_facturas_updated_at ON facturas_proveedor;
CREATE TRIGGER trg_facturas_updated_at
    BEFORE UPDATE ON facturas_proveedor
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- =============================================================================
-- ROW LEVEL SECURITY (RLS) — Activar en todas las tablas de negocio
-- Los usuarios solo ven datos de su propio condominio
-- =============================================================================

ALTER TABLE condominios        ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios           ENABLE ROW LEVEL SECURITY;
ALTER TABLE proveedores        ENABLE ROW LEVEL SECURITY;
ALTER TABLE propietarios       ENABLE ROW LEVEL SECURITY;
ALTER TABLE unidades           ENABLE ROW LEVEL SECURITY;
ALTER TABLE alicuotas          ENABLE ROW LEVEL SECURITY;
ALTER TABLE fondos             ENABLE ROW LEVEL SECURITY;
ALTER TABLE servicios          ENABLE ROW LEVEL SECURITY;
ALTER TABLE conceptos          ENABLE ROW LEVEL SECURITY;
ALTER TABLE gastos_fijos       ENABLE ROW LEVEL SECURITY;
ALTER TABLE conceptos_consumo  ENABLE ROW LEVEL SECURITY;
ALTER TABLE cuentas_bancos     ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturas_proveedor ENABLE ROW LEVEL SECURITY;

-- Política: service_role (backend) tiene acceso total
-- El frontend usa la service_role key desde Python, así que esto es suficiente.
-- Si en el futuro se usan JWT de usuarios individuales, añadir políticas por auth.uid().

DROP POLICY IF EXISTS "service_role_all" ON condominios;
DROP POLICY IF EXISTS "service_role_all" ON usuarios;
DROP POLICY IF EXISTS "service_role_all" ON proveedores;
DROP POLICY IF EXISTS "service_role_all" ON propietarios;
DROP POLICY IF EXISTS "service_role_all" ON unidades;
DROP POLICY IF EXISTS "service_role_all" ON alicuotas;
DROP POLICY IF EXISTS "service_role_all" ON fondos;
DROP POLICY IF EXISTS "service_role_all" ON servicios;
DROP POLICY IF EXISTS "service_role_all" ON conceptos;
DROP POLICY IF EXISTS "service_role_all" ON gastos_fijos;
DROP POLICY IF EXISTS "service_role_all" ON conceptos_consumo;
DROP POLICY IF EXISTS "service_role_all" ON cuentas_bancos;
DROP POLICY IF EXISTS "service_role_all" ON facturas_proveedor;

CREATE POLICY "service_role_all" ON condominios        FOR ALL USING (true);
CREATE POLICY "service_role_all" ON usuarios           FOR ALL USING (true);
CREATE POLICY "service_role_all" ON proveedores        FOR ALL USING (true);
CREATE POLICY "service_role_all" ON propietarios       FOR ALL USING (true);
CREATE POLICY "service_role_all" ON unidades           FOR ALL USING (true);
CREATE POLICY "service_role_all" ON alicuotas          FOR ALL USING (true);
CREATE POLICY "service_role_all" ON fondos             FOR ALL USING (true);
CREATE POLICY "service_role_all" ON servicios          FOR ALL USING (true);
CREATE POLICY "service_role_all" ON conceptos          FOR ALL USING (true);
CREATE POLICY "service_role_all" ON gastos_fijos       FOR ALL USING (true);
CREATE POLICY "service_role_all" ON conceptos_consumo  FOR ALL USING (true);
CREATE POLICY "service_role_all" ON cuentas_bancos     FOR ALL USING (true);
CREATE POLICY "service_role_all" ON facturas_proveedor FOR ALL USING (true);


-- =============================================================================
-- EMPLEADOS (tabla adicional requerida por Prompt 9)
-- =============================================================================
CREATE TABLE IF NOT EXISTS empleados (
    id             BIGSERIAL   PRIMARY KEY,
    condominio_id  BIGINT      REFERENCES condominios(id) ON DELETE RESTRICT,
    nombre         VARCHAR(200) NOT NULL,
    cargo          VARCHAR(100),
    direccion      TEXT,
    telefono_fijo  VARCHAR(20),
    telefono_celular VARCHAR(20),
    correo         VARCHAR(100),
    notas          TEXT,
    activo         BOOLEAN     DEFAULT TRUE,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_empleados_condominio ON empleados(condominio_id);
CREATE INDEX IF NOT EXISTS idx_empleados_activo     ON empleados(activo);

ALTER TABLE empleados ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "service_role_all" ON empleados;
CREATE POLICY "service_role_all" ON empleados FOR ALL USING (true);

DROP TRIGGER IF EXISTS trg_empleados_updated_at ON empleados;
CREATE TRIGGER trg_empleados_updated_at
    BEFORE UPDATE ON empleados
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- =============================================================================
-- VERIFICACIÓN FINAL
-- Ejecuta este SELECT para confirmar que todas las tablas fueron creadas:
-- =============================================================================
-- SELECT table_name
-- FROM information_schema.tables
-- WHERE table_schema = 'public'
--   AND table_name IN (
--     'paises','tipos_documento','condominios','usuarios','proveedores',
--     'propietarios','unidades','alicuotas','fondos','servicios','conceptos',
--     'gastos_fijos','conceptos_consumo','cuentas_bancos','facturas_proveedor','empleados'
--   )
-- ORDER BY table_name;
