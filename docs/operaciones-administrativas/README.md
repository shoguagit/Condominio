# Operaciones Administrativas

Esta carpeta documenta las operaciones administrativas verificadas en el código del sistema.

## Alcance
- Autenticación de usuarios y selección de condominio
- Gestión de condominios, unidades, propietarios, empleados, proveedores y usuarios
- Configuración de alícuotas, conceptos, servicios y gastos fijos
- Facturación, pagos, movimientos bancarios, recibos y estados de cuenta
- Reportes, notificaciones y procesos mensuales
- Manejo de tasa BCV y cálculos en bolívares / USD

## Cómo leer esta documentación
- `Función principal`: para qué existe el módulo en términos de negocio.
- `Subprocesos`: operaciones concretas que ejecuta el usuario o la aplicación.
- `Entradas`: datos obligatorios, opcionales y dependencias de sesión.
- `Devuelve / genera`: resultado funcional y técnico.
- `Conceptos`: vocabulario de negocio que el módulo usa.
- `Diagrama`: secuencia resumida entre UI, repositorios, Supabase y utilidades.

## Índice
1. [Autenticación y contexto](./01-autenticacion-y-contexto.md)
2. [Administración maestra](./02-administracion-maestra.md)
3. [Configuración financiera](./03-configuracion-financiera.md)
4. [Facturación, cobros y bancos](./04-facturacion-cobros-y-bancos.md)
5. [Reportes, notificaciones y proceso mensual](./05-reportes-notificaciones-y-proceso-mensual.md)
6. [Tasa BCV y moneda](./06-tasa-bcv-y-monedas.md)
7. [Respuestas de repositorios](./07-respuestas-de-repositorios.md)
8. [Modelo de datos](./08-modelo-de-datos.md)
9. [Resumen ejecutivo](./09-resumen-ejecutivo.md)
10. [Estados del proceso mensual](./10-proceso-mensual-estados.md)
11. [Conciliación bancaria](./11-conciliacion-bancaria.md)
12. [Manual operativo por rol](./12-manual-operativo-por-rol.md)
13. [Checklist de cierre mensual](./13-checklist-cierre-mensual.md)
14. [Checklist de conciliación bancaria](./14-checklist-conciliacion-bancaria.md)
15. [Runbook de incidencias](./15-runbook-incidencias.md)

## Arquitectura funcional resumida
- `app.py` resuelve login, autologin de QA, selección de condominio para admins y dashboard inicial.
- `pages/NN_*.py` implementan los casos de uso visibles para el usuario.
- `repositories/` encapsula acceso a Supabase por dominio.
- `utils/` concentra validaciones, sesión, cálculo de mora, tasa BCV, PDF y conciliación.
- `components/` arma la shell visual reutilizable: header, sidebar, tablas, breadcrumbs y paneles laterales.

## Dependencias transversales
- `SUPABASE_URL` y `SUPABASE_KEY` son obligatorios desde import-time.
- `SUPABASE_SERVICE_KEY` se necesita para administración de usuarios y ciertos procesos de mantenimiento.
- `st.session_state` transporta el contexto operativo: usuario, rol, condominio activo, `mes_proceso`, tasa y banderas de flujo.
