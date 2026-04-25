# Resumen ejecutivo

## Qué es este sistema
Es una aplicación para administrar la operación mensual de uno o varios condominios desde una sola plataforma.

En términos simples, permite:
- saber quiénes son los propietarios, usuarios, proveedores y empleados
- llevar el control de las unidades del condominio
- registrar gastos, facturas y pagos
- ver quién está solvente y quién está moroso
- emitir reportes y recibos
- trabajar con tasa BCV y referencia USD cuando hace falta

## Cómo opera el negocio dentro del sistema

### 1. Se define el contexto operativo
Primero el usuario entra al sistema y queda trabajando sobre un condominio activo y un período activo.

Eso significa que casi todo lo que ve o registra queda asociado a:
- un `condominio`
- un `mes en proceso`

### 2. Se mantiene la base maestra
Antes de cobrar o reportar, el sistema necesita la estructura del condominio:
- condominios
- unidades
- propietarios
- empleados
- proveedores
- usuarios con acceso al sistema

Sin esa base, no se puede operar correctamente.

### 3. Se configura la lógica financiera
Luego se definen las reglas con las que se reparte y clasifica el dinero:
- alícuotas
- conceptos
- servicios
- gastos fijos

Esto sirve para que los movimientos y cuotas tengan sentido contable y operativo.

### 4. Se registran los hechos económicos
Durante el mes se registran:
- facturas de proveedor
- pagos de condóminos
- movimientos bancarios
- gastos del período

Aquí es donde el sistema empieza a reflejar la realidad financiera del condominio.

### 5. Se procesa el mes
Con esa información el sistema puede:
- consolidar gastos
- calcular cuotas por unidad
- aplicar mora cuando corresponde
- considerar cobros extraordinarios
- cerrar el mes

Ese proceso convierte datos sueltos en un estado financiero coherente por unidad y por condominio.

### 6. Se comunica y se controla
Finalmente el sistema permite:
- emitir estados de cuenta
- generar recibos
- producir reportes PDF
- notificar morosos por correo

## Qué módulos tienen mayor impacto operativo

### Críticos para el funcionamiento diario
- `Autenticación y contexto`
- `Unidades`
- `Pagos y cobros`
- `Movimientos bancarios`
- `Proceso mensual`

### Críticos para control administrativo
- `Condominios`
- `Usuarios`
- `Proveedores`
- `Facturas`
- `Reportes`
- `Notificaciones`

### De soporte y parametrización
- `Alícuotas`
- `Conceptos`
- `Servicios`
- `Gastos fijos`

## Riesgos operativos importantes
- Si no hay `condominio activo`, el usuario no puede operar módulos clave.
- Si no hay `mes en proceso`, pagos, reportes y proceso mensual quedan incompletos.
- Si la tasa BCV no está disponible, el sistema usa respaldos; eso evita romper la operación, pero puede afectar exactitud monetaria de referencia.
- Si `SUPABASE_SERVICE_KEY` no está configurada, la administración de usuarios y ciertos mantenimientos quedan limitados.

## Qué debe entender un lector no técnico
- El sistema NO es solo un conjunto de pantallas: sigue un ciclo administrativo mensual.
- La información maestra alimenta el cálculo financiero.
- Los pagos y movimientos modifican el estado real de cobranza.
- El proceso mensual consolida y cierra el período.
- Los reportes y notificaciones salen de ese estado consolidado.

## Ruta recomendada de lectura
1. `01-autenticacion-y-contexto.md`
2. `02-administracion-maestra.md`
3. `03-configuracion-financiera.md`
4. `04-facturacion-cobros-y-bancos.md`
5. `05-reportes-notificaciones-y-proceso-mensual.md`
6. `06-tasa-bcv-y-monedas.md`
7. `08-modelo-de-datos.md`

## Para lectores técnicos
Si necesitas ver estructuras reales, sigue con:
- `07-respuestas-de-repositorios.md`
- `08-modelo-de-datos.md`
