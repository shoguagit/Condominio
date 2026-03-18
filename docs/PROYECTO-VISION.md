# Sistema de Gestión de Condominios — Visión y Alcance del Proyecto

Este documento describe **qué se desea hacer y construir**: el propósito del sistema, a quién va dirigido, los módulos y funcionalidades, la tecnología y los criterios de diseño. Sirve como referencia única del proyecto para desarrolladores y para la IA.

---

## 1. ¿Qué es este proyecto?

**Sistema de gestión de condominios** (Condominio / CondoSys): una aplicación web para administrar uno o varios edificios o conjuntos residenciales. Permite llevar el registro de unidades, propietarios, proveedores, facturas, fondos, alícuotas, servicios, gastos e ingresos, con soporte multi‑país (documentos fiscales por país) y multi‑condominio (varios edificios desde la misma aplicación).

La idea es tener **una sola aplicación** donde la junta de condominio o el administrador pueda:

- Gestionar la información maestra (condominios, unidades, propietarios, empleados, usuarios, proveedores).
- Configurar la parte financiera (alícuotas, fondos, conceptos, gastos fijos, conceptos de consumo, cuentas bancarias).
- Registrar y seguir facturas de proveedores y pagos.
- Consultar reportes y resúmenes.

El diseño y el flujo se inspiran en sistemas como **Sisconin**, adaptados a una interfaz moderna en Streamlit, con estilo corporativo y tablas tipo Tremor (limpias, legibles, sin bordes pesados).

---

## 2. ¿Para quién es?

- **Administradores de condominios** y personal de juntas de condominio.
- **Usuarios con roles** (Administrador, Operador, Solo consulta) que acceden con email y contraseña.
- Entornos **multi‑condominio**: un mismo despliegue puede servir a varios edificios; el usuario trabaja sobre un condominio activo (nombre, mes en proceso, tasa de cambio, etc.).

---

## 3. Objetivos del proyecto

| Objetivo | Descripción |
|----------|-------------|
| **Centralizar la información** | Un solo lugar para condominios, unidades, propietarios, proveedores, facturas y parámetros financieros. |
| **Multi‑país** | Soporte para distintos países (p. ej. Venezuela, Colombia, Ecuador, Perú, Argentina) con tipos de documento (RIF, NIT, RUC, CUIT, etc.) y validaciones por país. |
| **Multi‑condominio** | Varios condominios en la misma base; el usuario elige el condominio activo y trabaja siempre en su contexto. |
| **Interfaz clara y moderna** | UI corporativa, consistente, con tablas legibles (estilo Tremor), formularios homogéneos (2 columnas, secciones, Guardar/Cancelar) y sin botones ilegibles (evitar azul oscuro con texto negro). |
| **Seguridad y roles** | Login con Supabase Auth; roles (admin, operador, consulta); permisos por módulo cuando aplique. |
| **Trazabilidad** | Campos `created_at` / `updated_at` en tablas; en el futuro, auditoría o historial donde se requiera. |
| **Mantenible y testeable** | Código organizado (repositories, utils, components, pages), validaciones reutilizables, tests con pytest y mocks. |

---

## 4. Stack tecnológico

- **Frontend y lógica de presentación:** Python + **Streamlit** (app multi‑página).
- **Backend y persistencia:** **Supabase** (PostgreSQL + Auth).
- **Entorno:** Variables en `.env` (SUPABASE_URL, SUPABASE_KEY, SECRET_KEY, etc.); opcional autologin para QA (CONDOSYS_DEV_AUTOLOGIN).
- **Tests:** pytest, pytest-mock, pytest-cov; fixtures en `conftest.py`, mocks en `tests/utils/mock_data.py`.
- **Herramientas de desarrollo:** Cursor IDE; reglas en `.cursor/rules/` (interface-design, api-design-principles, error-handling-patterns, testing-patterns) para guiar a la IA.

---

## 5. Módulos y funcionalidades que se desean construir

A continuación se listan **todos los módulos** que el proyecto pretende tener, con lo que se desea en cada uno.

### 5.1 Autenticación y navegación

- **Login:** Pantalla centrada con email y contraseña; autenticación con Supabase Auth; mensajes claros de error.
- **Sesión:** Tras el login, guardar en sesión: usuario, rol, condominio activo, mes en proceso, tasa de cambio (y fuente, p. ej. BCV).
- **Dashboard (inicio):** Página principal con cards de acceso a cada módulo, agrupadas por categoría (Configuración, Proveedores, Reportes, etc.); diseño corporativo.
- **Header global:** Siempre visible: nombre del condominio activo, mes en proceso (MM/AAAA), tasa de cambio, usuario logueado.
- **Sidebar:** Navegación por módulos; fondo corporativo (#1B4F72); ítem activo resaltado; opción de cerrar sesión.

### 5.2 Configuración maestra

| Módulo | Qué se desea |
|--------|----------------|
| **Condominios** | CRUD de condominios. Campos: nombre, dirección, país, tipo de documento (según país), número de documento (validado), teléfono, email, mes en proceso, tasa de cambio, moneda principal, activo. Al cambiar país, el tipo de documento debe actualizarse (Venezuela→RIF, Colombia→NIT, etc.). |
| **Unidades** | CRUD de unidades por condominio. Tipo de propiedad (Apartamento, Local, Oficina, Estacionamiento, Maletero), número, piso, propietario (dropdown), tipo condómino (Propietario/Arrendatario), cuota fija mensual, activo. Manejo seguro de campos opcionales (p. ej. `piso` vacío no debe provocar error). |
| **Propietarios** | CRUD de propietarios. Nombre, documento (tipo + número), teléfono, correo, dirección, notas, activo. |
| **Empleados** | CRUD de empleados del condominio. Nombre, cargo, dirección, teléfonos, correo, notas. |
| **Usuarios** | CRUD de usuarios del sistema (quienes hacen login). Nombre, email (único), rol (Administrador / Operador / Solo consulta), condominio asignado, contraseña (solo al crear o al cambiar), activo. Integración con Supabase Auth; solo administrador puede crear/eliminar usuarios. |

### 5.3 Configuración financiera

| Módulo | Qué se desea |
|--------|----------------|
| **Alícuotas** | Definir alícuotas (cuota parte de gastos). Descripción, autocalcular (sí/no), cantidad de unidades, total alícuota, activo. |
| **Fondos** | Fondos de reserva u otros. Nombre, alícuota asociada, saldo inicial, saldo actual, tipo, cantidad, activo. |
| **Servicios** | Servicios del condominio (parrilleras, salón de fiestas, etc.). Nombre, precio unitario, activo. |
| **Conceptos** | Conceptos de gasto o ingreso (p. ej. “Gastos Generales”). Nombre, tipo (gasto/ingreso), activo. |
| **Gastos fijos** | Gastos fijos mensuales. Descripción, monto, alícuota o condominio, activo. |
| **Conceptos de consumo** | Conceptos que dependen del consumo (agua, gas, luz). Nombre, unidad de medida, precio unitario, tipo de precio (fijo/tabulador), activo. |
| **Cuentas/Bancos** | Cuentas bancarias del condominio. Descripción, número de cuenta, saldo inicial, saldo, moneda, activo. Registro por defecto sugerido: “Cuenta Principal”. |

### 5.4 Proveedores y facturación

| Módulo | Qué se desea |
|--------|----------------|
| **Proveedores** | CRUD de proveedores. Nombre/razón social, tipo y número de documento (con validación RIF u otra según país), dirección, teléfonos, correo, contacto, notas, saldo, activo. Sub‑módulo o pestaña **Facturas** dentro del mismo módulo. |
| **Facturas (de proveedor)** | Listado y CRUD de facturas. Columnas: Id, Número, Fecha, Vencimiento, Proveedor, Descripción/Total, Pagado, Saldo. Filtro por mes (En proceso / Todo). Formulario: número, fechas, proveedor, descripción, total. Interfaz de listado con tabla tipo Tremor y botón “Nuevo” con estilo outline legible. |

### 5.5 Reportes

- **Reportes:** Módulo dedicado a reportes y resúmenes (ingresos, gastos, saldos, etc.). Se desea ir incorporando reportes según necesidad, con filtros por condominio y mes.

---

## 6. Criterios de diseño de interfaz que se desean

- **Tema corporativo global:** Paleta definida en `.cursor/rules/interface-design.md`: primario #1B4F72, secundario #2E86C1, acento éxito #28B463, fondos y textos coherentes. Header y sidebar siempre con la misma identidad. |
- **Formularios homogéneos:** Dos columnas cuando haya muchos campos; secciones con títulos (IDENTIFICACIÓN, PROPIETARIO Y CUOTA, etc.); botonera única Guardar / Cancelar al final; campos obligatorios marcados con *; hints y tooltips donde ayude. |
- **Listados (CRUD):** No usar un grid pesado. Usar **tabla estilo Tremor**: sin bordes externos, encabezados en gris sin fondo de color, filas con separador muy sutil, tipografía simple (datos sin negrita), hover suave en fila, tabla al 100% del ancho. Barra superior: búsqueda + botón “Nuevo” con estilo **outline** (fondo claro, borde gris, texto oscuro legible). Acciones por fila: Ver, Editar, Eliminar como enlaces o botones discretos (nunca azul oscuro con letras negras). |
- **Dashboard:** KPI o resúmenes breves cuando aplique; cards de acceso a módulos; menú por categoría. |
- **Panel de ayuda:** En módulos que lo tengan, panel lateral derecho con ícono, título del módulo y descripción corta (estilo Sisconin). |
| **Mensajes:** Éxito con ✅, errores con ❌; validaciones con mensajes claros y sin tecnicismos innecesarios. |

---

## 7. Estructura del proyecto (resumen)

```
Condominio/
├── app.py                    # Entrada: login, dashboard, sidebar, inyección de estilos
├── config/                   # settings, supabase_client
├── repositories/             # Una clase por tabla (condominio, unidad, propietario, factura, etc.)
├── utils/                    # validators, error_handler, auth, formatters, bcv_rate, etc.
├── pages/                    # Una página Streamlit por módulo (01_condominios … 15_reportes)
├── components/               # header, sidebar, styles, record_table, crud_toolbar, help_panel, etc.
├── tests/                    # conftest, unit tests, mock_data
├── docs/
│   ├── GUIA-COMPLETA.md      # Prompts paso a paso para construir el sistema
│   └── PROYECTO-VISION.md   # Este documento: qué se desea hacer y construir
├── .cursor/rules/            # Reglas para IA (interface, API, errores, testing)
├── .env / .env.example
└── requirements.txt
```

---

## 8. Base de datos (Supabase / PostgreSQL)

Se desea que todas las entidades mencionadas tengan su tabla en Supabase, con:

- Nombres en **snake_case**, tablas en plural.
- Foreign keys (condominio_id, pais_id, etc.) con restricciones adecuadas (p. ej. ON DELETE RESTRICT).
- Campos `created_at` y `updated_at` donde aplique; triggers para actualizar `updated_at`.
- Índices en condominio_id, activo y otros campos consultados con frecuencia.
- Datos iniciales para países y tipos de documento (Venezuela/RIF, Colombia/NIT, etc.).

El detalle de tablas y columnas está descrito en la GUIA-COMPLETA (Prompt 2) y debe respetar los principios de diseño de API en `.cursor/rules/api-design-principles.md`.

---

## 9. Estado actual vs. lo que se desea

- **Hecho:** Estructura del proyecto, login, dashboard, sidebar, header, estilos globales y tema corporativo. CRUD con listados tipo Tremor (record_table con tabla HTML y botón Nuevo outline) en Condominios, Unidades, Propietarios, Empleados, Usuarios, Proveedores, Facturas. Formularios homogeneizados (2 columnas, secciones, Guardar/Cancelar). Módulos de configuración financiera (alícuotas, fondos, servicios, conceptos, gastos fijos, conceptos de consumo, cuentas/bancos) con st.dataframe y estilo Tremor. Repositories y validaciones; corrección de bugs (p. ej. `piso` None en unidades).
- **Deseado / en evolución:** Reportes más completos; más validaciones por país y tipo de documento; mejoras de UX en formularios y mensajes; tests ampliados; en el futuro, auditoría o historial de cambios donde se requiera.

---

## 10. Cómo usar este documento

- **Para desarrolladores:** Referencia única de qué es el sistema, para quién es y qué se quiere en cada módulo y en la UI.
- **Para la IA (Cursor):** Contexto de visión y alcance; combinar con `docs/GUIA-COMPLETA.md` para los pasos de implementación y con `.cursor/rules/` para estilo de código, API y errores.
- **Para priorizar:** Los módulos de configuración maestra y facturación son el núcleo; reportes y mejoras incrementales pueden ir después.

Si algo no está en este documento pero forma parte de lo que “deseas hacer y construir”, conviene añadirlo aquí para mantener una sola fuente de verdad del proyecto.
