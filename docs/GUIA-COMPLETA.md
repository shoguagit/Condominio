# 🏢 GUÍA COMPLETA — Sistema de Condominio
## Stack: Python + Streamlit + Supabase | Cursor IDE

---

# PARTE 1: ESTRUCTURA DEL PROYECTO

```
condominio-app/
├── .cursor/
│   └── rules/               ← Skills de Cursor (copiar aquí los .md)
├── .env                     ← Variables de entorno (NO subir a Git)
├── .env.example
├── .gitignore
├── requirements.txt
├── app.py                   ← Punto de entrada principal
│
├── config/
│   ├── __init__.py
│   ├── settings.py          ← Carga variables de entorno
│   └── supabase_client.py   ← Cliente Supabase singleton
│
├── repositories/            ← Una clase por tabla
│   ├── __init__.py
│   ├── condominio_repository.py
│   ├── proveedor_repository.py
│   ├── usuario_repository.py
│   ├── unidad_repository.py
│   ├── propietario_repository.py
│   └── pais_repository.py
│
├── utils/
│   ├── __init__.py
│   ├── validators.py        ← Validaciones de formularios
│   ├── error_handler.py     ← Manejo de errores
│   ├── auth.py              ← Autenticación y sesión
│   └── formatters.py        ← Formateo de moneda, fechas, etc.
│
├── pages/                   ← Una página por módulo (Streamlit multi-page)
│   ├── 01_condominios.py
│   ├── 02_unidades.py
│   ├── 03_alicuotas.py
│   ├── 04_fondos.py
│   ├── 05_servicios.py
│   ├── 06_conceptos.py
│   ├── 07_gastos_fijos.py
│   ├── 08_conceptos_consumo.py
│   ├── 09_cuentas_bancos.py
│   ├── 10_empleados.py
│   ├── 11_propietarios.py
│   ├── 12_usuarios.py
│   ├── 13_proveedores.py
│   ├── 14_facturas.py
│   └── 15_reportes.py
│
├── components/              ← Componentes reutilizables
│   ├── __init__.py
│   ├── header.py            ← Header global con condominio activo
│   ├── crud_toolbar.py      ← Barra Incluir/Modificar/Eliminar
│   ├── help_panel.py        ← Panel de ayuda lateral derecho
│   └── data_table.py        ← Tabla con paginación y búsqueda
│
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_validators.py
    │   └── test_repositories.py
    └── utils/
        └── mock_data.py
```

---

# PARTE 2: INSTALACIÓN DE SKILLS EN CURSOR

## Paso a paso:
1. Dentro de tu proyecto, crear carpeta `.cursor/rules/`
2. Copiar los 4 archivos `.md` de skills dentro de esa carpeta:
   - `interface-design.md`
   - `api-design-principles.md`
   - `error-handling-patterns.md`
   - `testing-patterns.md`
3. En Cursor, los skills se activan automáticamente o llamándolos con `@nombrearchivo`

---

# PARTE 3: PROMPTS PASO A PASO PARA CURSOR

> **IMPORTANTE:** Ejecutar los prompts EN ORDEN. Abrir ventana nueva de Cursor Chat para cada paso.

---

## 🔷 PROMPT 1 — Configuración inicial del proyecto

```
Crea la estructura completa del proyecto Python para un sistema de gestión de condominios usando Streamlit + Supabase.

Sigue exactamente esta estructura de carpetas:
- config/ (settings.py, supabase_client.py)
- repositories/ (una clase por tabla)
- utils/ (validators.py, error_handler.py, auth.py, formatters.py)
- pages/ (módulos del sistema)
- components/ (header, crud_toolbar, help_panel, data_table)
- tests/

Crea los siguientes archivos base:
1. requirements.txt con: streamlit, supabase, python-dotenv, pytest, pytest-mock, pytest-cov
2. .env.example con las variables: SUPABASE_URL, SUPABASE_KEY, SECRET_KEY
3. .gitignore que excluya .env y __pycache__
4. config/settings.py que cargue las variables del .env
5. config/supabase_client.py con función get_supabase_client() como singleton

@api-design-principles
@error-handling-patterns
```

---

## 🔷 PROMPT 2 — Base de datos en Supabase

```
Genera el script SQL completo para crear todas las tablas del sistema de condominio en Supabase (PostgreSQL).

Las tablas requeridas son:
1. paises (id, nombre, codigo_iso, moneda, simbolo_moneda)
2. tipos_documento (id, pais_id FK, nombre, formato_regex, descripcion)
3. condominios (id, nombre, direccion, pais_id FK, tipo_documento_id FK, numero_documento, telefono, email, mes_proceso, tasa_cambio, moneda_principal, activo, created_at, updated_at)
4. usuarios (id, condominio_id FK, nombre, email UNIQUE, rol, activo, ultimo_acceso, created_at, updated_at)
5. proveedores (id, condominio_id FK, nombre, tipo_documento_id FK, numero_documento, direccion, telefono_fijo, telefono_celular, correo, contacto, notas, saldo, activo, created_at, updated_at)
6. propietarios (id, condominio_id FK, nombre, cedula, telefono, correo, direccion, notas, activo, created_at)
7. unidades (id, condominio_id FK, propietario_id FK, tipo_propiedad, numero, piso, tipo_condomino, cuota_fija, activo, created_at)
8. alicuotas (id, condominio_id FK, descripcion, autocalcular boolean, cantidad_unidades int, total_alicuota numeric, activo)
9. fondos (id, condominio_id FK, nombre, alicuota_id FK, saldo_inicial numeric, saldo numeric, tipo varchar, cantidad numeric, activo)
10. servicios (id, condominio_id FK, nombre, precio_unitario numeric, activo)
11. conceptos (id, condominio_id FK, nombre, tipo varchar CHECK('gasto','ingreso'), activo)
12. gastos_fijos (id, condominio_id FK, descripcion, monto numeric, alicuota_id FK, activo)
13. conceptos_consumo (id, condominio_id FK, nombre, unidad_medida varchar, precio_unitario numeric, tipo_precio varchar CHECK('fijo','tabulador'), activo)
14. cuentas_bancos (id, condominio_id FK, descripcion, numero_cuenta varchar, saldo_inicial numeric, saldo numeric, moneda varchar, activo)
15. facturas_proveedor (id, condominio_id FK, numero varchar, fecha date, fecha_vencimiento date, proveedor_id FK, descripcion text, total numeric, pagado numeric, saldo numeric, mes_proceso date, activo)

Incluye:
- INSERT de datos iniciales para paises y tipos_documento (Venezuela/RIF, Colombia/NIT, Ecuador/RUC, Perú/RUC, Argentina/CUIT)
- Todos los campos con sus tipos correctos
- Foreign keys con ON DELETE RESTRICT
- Índices en los campos más consultados (condominio_id, activo)
- Triggers para updated_at automático

@api-design-principles
```

---

## 🔷 PROMPT 3 — Componentes reutilizables

```
Crea los componentes reutilizables de Streamlit para el sistema de condominio:

1. components/header.py
   - Función render_header() que muestra: nombre del condominio activo, mes en proceso (MM/AAAA), tasa de cambio BCV en Bs., usuario logueado
   - Leer estos datos de st.session_state
   - Fondo azul corporativo #1B4F72, texto blanco, layout horizontal

2. components/crud_toolbar.py
   - Función render_toolbar(on_incluir, on_modificar, on_eliminar) 
   - Botones: [+ Incluir] [✏ Modificar] [🗑 Eliminar] con separador | [⬅] [◀] [N de TOTAL] [▶] [⮕]
   - Navegación entre registros como el sistema Sisconin original

3. components/help_panel.py
   - Función render_help_panel(icono, titulo, descripcion_corta, descripcion_larga)
   - Panel derecho blanco con borde, igual al panel de ayuda del sistema Sisconin

4. components/data_table.py
   - Función render_data_table(data, columns_config, search_field)
   - Incluir campo de búsqueda "Buscar por:" arriba
   - Selector de fila para saber cuál está seleccionada
   - Paginación de 20 registros por página
   - Fila de header azul oscuro

@interface-design
@error-handling-patterns
```

---

## 🔷 PROMPT 4 — Módulo LOGIN + app.py principal

```
Crea el sistema de autenticación y el punto de entrada principal:

1. app.py (página de login):
   - Pantalla de login centrada con logo/título del sistema
   - Campos: email y contraseña
   - Validación con Supabase Auth (supabase.auth.sign_in_with_password)
   - Al autenticarse: guardar en st.session_state: authenticated=True, user_email, user_role, condominio_id, condominio_nombre, mes_proceso, tasa_cambio
   - Si ya está autenticado, redirigir al dashboard
   - Botón de cerrar sesión en el sidebar

2. Dashboard principal (página de inicio después del login):
   - Cards de acceso a cada módulo con su ícono
   - Mostrar: Condominios, Unidades, Alícuotas, Fondos, Servicios, Conceptos, Gastos Fijos, Conceptos de Consumo, Cuentas/Bancos, Empleados, Propietarios, Usuarios, Proveedores, Facturas, Reportes
   - Layout de 4 columnas con cards iguales al diseño corporativo
   - Header con datos del condominio activo

3. Sidebar de navegación:
   - Fondo azul #1B4F72
   - Menú agrupado: Configuración / Proveedores / Reportes
   - Item activo resaltado con borde verde

@interface-design
@error-handling-patterns
```

---

## 🔷 PROMPT 5 — CRUD Condominios (con documento por país)

```
Crea el módulo completo de Condominios en pages/01_condominios.py

Funcionalidades:
1. Tabla con columnas: Id, Nombre, Dirección, País, Documento (RIF/NIT/etc), Teléfono, Email
2. Barra de herramientas: Incluir, Modificar, Eliminar + navegación de registros
3. Panel de ayuda lateral derecho con descripción del módulo
4. Búsqueda por nombre

Formulario de Incluir/Modificar:
- Nombre del condominio (obligatorio)
- Dirección (obligatorio)
- País (dropdown que carga de tabla paises)
- Al cambiar el país → el campo "Tipo de Documento" cambia dinámicamente:
  * Venezuela → RIF (formato: J-XXXXXXXX-X)
  * Colombia → NIT
  * Ecuador → RUC
  * Perú → RUC
  * Argentina → CUIT
- Número de Documento (con validación según el tipo seleccionado)
- Teléfono, Email, Moneda principal, Tasa de Cambio BCV

Crear también:
- repositories/condominio_repository.py con métodos: get_all, get_by_id, create, update, delete, search
- repositories/pais_repository.py con get_all, get_tipos_documento_by_pais

@api-design-principles
@interface-design
@error-handling-patterns
```

---

## 🔷 PROMPT 6 — CRUD Proveedores

```
Crea el módulo completo de Proveedores en pages/13_proveedores.py

Basándote en las imágenes del sistema Sisconin original, el módulo debe tener:

1. Tabla principal con columnas: Id, Proveedor (nombre), Teléfono Fijo, Teléfono Celular, Correo Electrónico, Saldo
2. Barra de herramientas: [+ Incluir] [✏ Modificar] [🗑 Eliminar] + navegación
3. Filtro de búsqueda "Buscar por:" en la parte superior
4. Panel de ayuda lateral derecho con: ícono 📄, título "Proveedores", descripción de qué es un proveedor

Formulario completo:
- Nombre/Razón Social (obligatorio)
- Tipo de Documento (dropdown: RIF, Cédula, Pasaporte)
- Número de Documento (con validación de RIF si selecciona RIF)
- Dirección
- Teléfono Fijo
- Teléfono Celular  
- Correo Electrónico (con validación de formato)
- Contacto (persona de contacto)
- Notas (textarea)

Sub-módulo Facturas de Proveedor (tab dentro del módulo):
- Accesible desde botón "Facturas" en el toolbar
- Tabla: Id, Número, Fecha, Proveedor, Descripción, Total, Pagado, Saldo
- Filtro: "Mes: ● En proceso ○ Todo"
- Formulario: número factura, fecha emisión, fecha vencimiento, proveedor (dropdown), descripción, total

Crear:
- repositories/proveedor_repository.py
- repositories/factura_repository.py

@api-design-principles
@interface-design
@error-handling-patterns
```

---

## 🔷 PROMPT 7 — CRUD Usuarios

```
Crea el módulo completo de Usuarios del sistema en pages/12_usuarios.py

Este módulo gestiona los usuarios que pueden hacer LOGIN en el sistema (no propietarios).

1. Tabla: Id, Nombre, Email, Rol, Último Acceso, Activo
2. Barra: Incluir, Modificar, Desactivar (no eliminar físicamente)
3. Panel ayuda: ícono 🔐, descripción de usuarios del sistema

Formulario:
- Nombre completo (obligatorio)
- Email (obligatorio, único, validar formato)
- Rol (dropdown: Administrador / Operador / Solo Consulta)
- Condominio asignado (dropdown de condominios activos)
- Contraseña (solo al crear, con confirmación)
- Activo (checkbox)

Lógica especial:
- Al crear: registrar en Supabase Auth Y en tabla usuarios
- Al modificar: no mostrar campo contraseña (opción separada para cambiar contraseña)
- Solo el rol Administrador puede crear/eliminar usuarios
- Proteger con check_permission("admin") al inicio de la página

Crear:
- repositories/usuario_repository.py con métodos adicionales: toggle_activo, change_password

@api-design-principles
@interface-design
@error-handling-patterns
```

---

## 🔷 PROMPT 8 — Tests automáticos

```
Crea los tests automáticos para el sistema de condominio:

1. tests/conftest.py con fixtures:
   - mock_supabase (cliente Supabase mockeado)
   - proveedor_data, condominio_data, usuario_data (datos de prueba)

2. tests/unit/test_validators.py:
   - TestValidateRIF: válido empresa (J-), válido persona (V-), sin guiones, vacío, tipo X inválido
   - TestValidateEmail: válido, inválido, vacío (válido porque no es obligatorio)
   - TestValidateForm: form completo, nombre faltante, RIF inválido

3. tests/unit/test_repositories.py:
   - TestProveedorRepository: get_all retorna lista, create retorna registro, delete llama supabase, search usa ilike
   - TestCondominioRepository: get_all, create con documento, get_by_pais
   - TestUsuarioRepository: create registra en auth, toggle_activo, get_by_condominio

4. tests/utils/mock_data.py con datos de prueba para todos los módulos

Al final muestra cómo ejecutar:
- pytest tests/ -v
- pytest tests/ --cov=. --cov-report=term-missing

@testing-patterns
@error-handling-patterns
```

---

## 🔷 PROMPT 9 — Módulos restantes (batch)

```
Crea los siguientes módulos restantes del sistema, todos siguiendo el mismo patrón de los ya creados:

Para cada uno crear: página en pages/ + repository en repositories/

1. pages/02_unidades.py + repositories/unidad_repository.py
   Tabla: Id, Tipo de Propiedad, Condominio (nombre), Tipo de Condómino, Cuota Fija
   Formulario: tipo_propiedad(dropdown: Apartamento/Local/Oficina/Estacionamiento/Maletero), número, piso, propietario(dropdown), tipo_condomino(Propietario/Arrendatario), cuota_fija

2. pages/10_empleados.py + repositories/empleado_repository.py
   Tabla: Id, Empleado, Cargo, Teléfono Fijo, Teléfono Celular, Correo
   Formulario: nombre, cargo, dirección, teléfono fijo, celular, correo, notas

3. pages/11_propietarios.py + repositories/propietario_repository.py
   Tabla: Id, Nombre, Cédula/Doc, Teléfono, Correo
   Formulario: nombre, tipo_documento, numero_documento, telefono, correo, dirección, notas

Todos deben incluir:
- Header corporativo
- Barra CRUD
- Panel de ayuda lateral
- Búsqueda
- Validaciones con error_handler

@api-design-principles
@interface-design
@error-handling-patterns
```

---

## 🔷 PROMPT 10 — Módulos de configuración financiera

```
Crea los módulos de configuración financiera del condominio:

1. pages/03_alicuotas.py
   Tabla: Id, Descripción, Autocalcular, Cantidad de Unidades, Total Alícuota
   Tooltip: "Cuota parte o porcentaje de los gastos que corresponde a cada condómino"
   Formulario: descripción, autocalcular(checkbox), cantidad_unidades, total_alicuota

2. pages/04_fondos.py  
   Tabla: Id, Fondo, Alícuota, Saldo Inicial, Saldo, Tipo, Cantidad, Activo
   
3. pages/05_servicios.py
   Tabla: Id, Servicio, Precio Unitario
   Tooltip: "Servicios ofrecidos por el condominio como parrilleras, salón de fiestas, etc."

4. pages/06_conceptos.py
   Tabla: Id, Concepto (solo muestra "Gastos Generales" y similares)
   Tooltip: "Conceptos para ser utilizados en los gastos o ingresos del mes"

5. pages/07_gastos_fijos.py
   Tabla: Id, Descripción, Monto, Alícuota o Condominio

6. pages/08_conceptos_consumo.py
   Tabla: Id, Concepto, Unidad de Medida
   Tooltip: "Dependen de la cantidad consumida (agua, gas, luz)"

7. pages/09_cuentas_bancos.py
   Tabla: Id, Descripción, Número de Cuenta, Saldo Inicial, Saldo, Moneda
   Registro por defecto: "Cuenta Principal"

@api-design-principles
@interface-design
@error-handling-patterns
```

---

# PARTE 4: ORDEN DE EJECUCIÓN RECOMENDADO

```
Semana 1:
  ✅ Prompt 1 → Estructura base del proyecto
  ✅ Prompt 2 → SQL en Supabase (ejecutar en Supabase SQL Editor)
  ✅ Prompt 3 → Componentes reutilizables
  ✅ Prompt 4 → Login + Dashboard

Semana 2:
  ✅ Prompt 5 → CRUD Condominios (el más importante, base de todo)
  ✅ Prompt 6 → CRUD Proveedores + Facturas
  ✅ Prompt 7 → CRUD Usuarios

Semana 3:
  ✅ Prompt 8 → Tests automáticos
  ✅ Prompt 9 → Empleados, Propietarios, Unidades
  ✅ Prompt 10 → Módulos financieros
```

---

# PARTE 5: CONFIGURACIÓN EN CURSOR

## Cómo activar los Skills:
1. Abre Cursor → Settings → Rules for AI
2. O coloca los archivos .md en `.cursor/rules/`
3. Para invocar en el chat: escribe `@interface-design` o `@api-design-principles`

## Tips de uso:
- Siempre inicia cada prompt en una **ventana nueva** de chat para evitar saturar el contexto
- Incluye `@` con el skill relevante al final de cada prompt
- Si el resultado no es bueno, añade: "Sigue estrictamente el skill @interface-design"
- Para debugging: añade `@error-handling-patterns` y describe el error exacto
