# Skill: API Design Principles — Supabase + Python
## Propósito
Guiar a la IA para interactuar con Supabase de forma correcta, segura y consistente desde Python/Streamlit.

---

## Principios de Acceso a Datos con Supabase

### 1. Cliente Supabase — Inicialización
```python
# config/supabase_client.py
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)
```

### 2. Patrón Repository — Una clase por entidad
```python
# Cada módulo tiene su propio repository en /repositories/
class ProveedorRepository:
    def __init__(self, client: Client):
        self.client = client
        self.table = "proveedores"
    
    def get_all(self) -> list[dict]:
        response = self.client.table(self.table).select("*").order("nombre").execute()
        return response.data
    
    def get_by_id(self, id: int) -> dict | None:
        response = self.client.table(self.table).select("*").eq("id", id).single().execute()
        return response.data
    
    def create(self, data: dict) -> dict:
        response = self.client.table(self.table).insert(data).execute()
        return response.data[0]
    
    def update(self, id: int, data: dict) -> dict:
        response = self.client.table(self.table).update(data).eq("id", id).execute()
        return response.data[0]
    
    def delete(self, id: int) -> bool:
        self.client.table(self.table).delete().eq("id", id).execute()
        return True
    
    def search(self, term: str) -> list[dict]:
        response = self.client.table(self.table).select("*").ilike("nombre", f"%{term}%").execute()
        return response.data
```

### 3. Nombrado de Tablas en Supabase (snake_case, plural)
```
condominios          → tabla principal
unidades             → unidades del condominio
alicuotas            → alícuotas por condominio
fondos               → fondos de reserva
servicios            → servicios del condominio
conceptos            → conceptos de gasto/ingreso
gastos_fijos         → gastos fijos mensuales
conceptos_consumo    → conceptos variables (agua, luz)
cuentas_bancos       → cuentas de caja y bancos
empleados            → empleados del condominio
propietarios         → propietarios/clientes
usuarios             → usuarios del sistema (login)
proveedores          → proveedores externos
facturas_proveedor   → facturas de proveedores
paises               → tabla catálogo de países
tipos_documento      → RIF, NIT, RUC, CUIT, etc.
```

### 4. Reglas de Queries
- **Siempre** usar `.execute()` al final
- **Siempre** capturar errores con try/except
- **Nunca** hacer SELECT * en joins complejos — especificar columnas
- **Paginación** obligatoria para tablas con más de 100 registros: `.range(offset, offset+limit-1)`
- **Filtros** de búsqueda usar `.ilike()` para case-insensitive
- **Soft delete**: columna `activo boolean default true`, nunca DELETE físico en producción
- **Timestamps**: siempre incluir `created_at` y `updated_at` (Supabase los maneja automáticamente)

### 5. Manejo de Relaciones
```python
# JOIN con select anidado de Supabase
def get_facturas_con_proveedor(self):
    response = self.client.table("facturas_proveedor").select(
        "*, proveedores(id, nombre, rif)"
    ).execute()
    return response.data

# Relación unidades → propietarios → condominio
def get_unidades_completas(self, condominio_id: int):
    response = self.client.table("unidades").select(
        "*, propietarios(nombre, cedula), condominios(nombre)"
    ).eq("condominio_id", condominio_id).execute()
    return response.data
```

### 6. Variables de Entorno (NUNCA hardcodear keys)
```python
# .env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SECRET_KEY=clave_secreta_para_sesiones
```

### 7. Autenticación con Supabase Auth
```python
# Para login de usuarios del sistema
def login(email: str, password: str):
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    return response.user, response.session

def logout():
    client.auth.sign_out()
```

---

## Estructura de Tablas SQL (Supabase / PostgreSQL)

### Tabla: condominios
```sql
CREATE TABLE condominios (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    direccion TEXT NOT NULL,
    pais_id INT REFERENCES paises(id) DEFAULT 1,
    tipo_documento_id INT REFERENCES tipos_documento(id),
    numero_documento VARCHAR(20),  -- RIF, NIT, RUC según país
    telefono VARCHAR(20),
    email VARCHAR(100),
    mes_proceso DATE DEFAULT CURRENT_DATE,
    tasa_cambio NUMERIC(12,4) DEFAULT 0,
    moneda_principal VARCHAR(10) DEFAULT 'USD',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: paises + tipos_documento
```sql
CREATE TABLE paises (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    codigo_iso VARCHAR(3) NOT NULL,
    moneda VARCHAR(10),
    simbolo_moneda VARCHAR(5)
);

CREATE TABLE tipos_documento (
    id SERIAL PRIMARY KEY,
    pais_id INT REFERENCES paises(id),
    nombre VARCHAR(50) NOT NULL,  -- RIF, NIT, RUC, CUIT, CNPJ
    formato_regex VARCHAR(100),   -- Validación del formato
    descripcion VARCHAR(200)
);

-- Datos iniciales
INSERT INTO paises VALUES (1,'Venezuela','VEN','VES','Bs.');
INSERT INTO paises VALUES (2,'Colombia','COL','COP','$');
INSERT INTO paises VALUES (3,'Ecuador','ECU','USD','$');
INSERT INTO paises VALUES (4,'Perú','PER','PEN','S/');
INSERT INTO paises VALUES (5,'Argentina','ARG','ARS','$');

INSERT INTO tipos_documento(pais_id, nombre, descripcion) VALUES
(1, 'RIF', 'Registro de Información Fiscal'),
(2, 'NIT', 'Número de Identificación Tributaria'),
(3, 'RUC', 'Registro Único de Contribuyentes'),
(4, 'RUC', 'Registro Único de Contribuyentes'),
(5, 'CUIT', 'Clave Única de Identificación Tributaria');
```

### Tabla: proveedores
```sql
CREATE TABLE proveedores (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id),
    nombre VARCHAR(200) NOT NULL,
    tipo_documento_id INT REFERENCES tipos_documento(id),
    numero_documento VARCHAR(30),
    direccion TEXT,
    telefono_fijo VARCHAR(20),
    telefono_celular VARCHAR(20),
    correo VARCHAR(100),
    contacto VARCHAR(150),
    notas TEXT,
    saldo NUMERIC(14,2) DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: usuarios
```sql
CREATE TABLE usuarios (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id),
    nombre VARCHAR(150) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    rol VARCHAR(30) DEFAULT 'operador',  -- admin, operador, consulta
    activo BOOLEAN DEFAULT TRUE,
    ultimo_acceso TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
    -- password manejado por Supabase Auth
);
```

### Tabla: unidades
```sql
CREATE TABLE unidades (
    id BIGSERIAL PRIMARY KEY,
    condominio_id BIGINT REFERENCES condominios(id),
    propietario_id BIGINT REFERENCES propietarios(id),
    tipo_propiedad VARCHAR(50),  -- Apartamento, Local, Oficina, etc.
    numero VARCHAR(20),
    piso VARCHAR(10),
    tipo_condomino VARCHAR(30),  -- Propietario, Arrendatario
    cuota_fija NUMERIC(14,2) DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```
