-- =============================================================================
-- LIMPIAR DATOS — Empezar desde cero
-- Mantiene: condominios, usuarios (tabla `usuarios` de la app)
-- Borra: todo el resto (propietarios, unidades, movimientos, cuotas, etc.)
--
-- NO borra: paises, tipos_documento (catálogos del sistema)
-- NO borra: auth.users de Supabase (solo la tabla `usuarios` de negocio se conserva)
--
-- Ejecutar en Supabase → SQL Editor. Hacer backup antes en producción.
-- =============================================================================

BEGIN;

-- Orden: hijos primero; RESTART IDENTITY reinicia secuencias; CASCADE por si queda alguna FK cruzada
TRUNCATE TABLE
    cuotas_unidad,
    movimientos,
    pagos,
    presupuestos,
    unidad_propietarios,
    facturas_proveedor,
    gastos_fijos,
    fondos,
    unidades,
    empleados,
    procesos_mensuales,
    conceptos,
    servicios,
    conceptos_consumo,
    cuentas_bancos,
    alicuotas,
    propietarios,
    proveedores
RESTART IDENTITY CASCADE;

COMMIT;

-- Verificación rápida (opcional: descomentar y ejecutar)
-- SELECT 'condominios' AS t, COUNT(*) FROM condominios
-- UNION ALL SELECT 'usuarios', COUNT(*) FROM usuarios
-- UNION ALL SELECT 'unidades', COUNT(*) FROM unidades
-- UNION ALL SELECT 'propietarios', COUNT(*) FROM propietarios;
