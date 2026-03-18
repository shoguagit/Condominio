# Prompt: Crear aplicación completa

Prompt para crear la aplicación de gestión de condominios y agregarle todo. Solo módulos y de qué se trata.

---

## El prompt (copiar desde aquí)

```
Crear una aplicación web completa de gestión de condominios y agregarle todo lo necesario.

La aplicación sirve para administrar uno o varios edificios o conjuntos residenciales (multi-condominio y multi-país). Los usuarios entran con email y contraseña; tienen roles (Administrador, Operador, Solo consulta) y trabajan sobre un condominio activo (con su mes en proceso y tasa de cambio). Después del login hay un inicio (dashboard) con acceso a todos los módulos.

Módulos que debe tener la aplicación:

**Condominios** — Dar de alta y editar los condominios: nombre, dirección, país, tipo de documento fiscal según el país (RIF, NIT, RUC, CUIT, etc.), número de documento validado, teléfono, email, mes en proceso, tasa de cambio, moneda principal. Al cambiar el país debe actualizarse el tipo de documento.

**Unidades** — Gestionar las unidades de cada condominio: tipo (apartamento, local, oficina, estacionamiento, maletero), número, piso, propietario asignado, tipo de condómino (propietario o arrendatario), cuota fija mensual, activo/inactivo.

**Propietarios** — Registro de propietarios: nombre, documento (tipo y número), teléfono, correo, dirección, notas, activo.

**Empleados** — Personal del condominio: nombre, cargo, dirección, teléfonos, correo, notas.

**Usuarios** — Quienes pueden entrar al sistema (no son propietarios): nombre, email, rol, condominio asignado, contraseña al crear, activo. Solo el administrador puede crear o eliminar usuarios; al crear se registra también en el sistema de autenticación.

**Proveedores** — Proveedores del condominio: nombre o razón social, tipo y número de documento (con validación si es RIF u otro), dirección, teléfonos, correo, contacto, notas, saldo, activo. Incluir dentro del mismo módulo la gestión de facturas de proveedor (número, fechas, proveedor, descripción, total, pagado, saldo; filtro por mes en proceso o todo).

**Facturas** — Listado y alta de facturas de proveedor: número, fecha, vencimiento, proveedor, descripción, total, pagado, saldo; filtro por mes (en proceso o todo).

**Alícuotas** — Definir la cuota parte de gastos que corresponde a cada condómino: descripción, si se autocalcula o no, cantidad de unidades, total alícuota, activo.

**Fondos** — Fondos de reserva u otros: nombre, alícuota asociada, saldo inicial, saldo actual, tipo, cantidad, activo.

**Servicios** — Servicios que ofrece el condominio (parrilleras, salón de fiestas, etc.): nombre, precio unitario, activo.

**Conceptos** — Conceptos para gastos o ingresos del mes (por ejemplo “Gastos Generales”): nombre, tipo (gasto o ingreso), activo.

**Gastos fijos** — Gastos fijos mensuales: descripción, monto, alícuota o condominio, activo.

**Conceptos de consumo** — Conceptos que dependen del consumo (agua, gas, luz): nombre, unidad de medida, precio unitario, tipo de precio (fijo o tabulador), activo.

**Cuentas y bancos** — Cuentas bancarias del condominio: descripción, número de cuenta, saldo inicial, saldo, moneda, activo.

**Reportes** — Módulo para ver resúmenes y reportes (ingresos, gastos, saldos, etc.) con filtros por condominio y mes; puede empezar con pantalla base e ir agregando reportes.

Cada módulo debe permitir listar, crear, modificar y eliminar (o desactivar cuando corresponda) sus registros, con búsqueda donde tenga sentido. Los datos se filtran siempre por el condominio activo del usuario. La aplicación debe ser funcional de punta a punta: login, dashboard, y todos estos módulos operativos.
```
