BEGIN;

DO $$
DECLARE
    v_condo_id BIGINT;
    v_tipo_rif INT;
    v_ali_id BIGINT;
    v_prop1 BIGINT;
    v_prop2 BIGINT;
    v_prop3 BIGINT;
BEGIN
    SELECT id INTO v_tipo_rif FROM public.tipos_documento
    WHERE pais_id = 1 AND nombre = 'RIF'
    ORDER BY id
    LIMIT 1;

    SELECT id INTO v_condo_id FROM public.condominios
    WHERE nombre = 'Condominio Demo Norte'
    LIMIT 1;

    IF v_condo_id IS NULL THEN
INSERT INTO public.condominios (
        nombre, direccion, pais_id, tipo_documento_id, numero_documento,
        telefono, email, mes_proceso, tasa_cambio, moneda_principal, activo,
        smtp_host, smtp_port, smtp_usuario, smtp_email, smtp_secure,
        smtp_app_password, smtp_nombre_remitente
    ) VALUES (
        'Condominio Demo Norte',
        'Av. Principal, Torre Norte, Caracas',
        1,
        v_tipo_rif,
        'J-12345678-9',
        '0212-5551234',
        'administracion@demo.local',
        DATE '2026-03-01',
        97.15,
        'USD',
        TRUE,
        'smtp.gmail.com',
        587,
        'admin.demo@condominio.local',
        'admin.demo@condominio.local',
        TRUE,
        'Condominio123',
        'Administración Condominio Demo'
    ) RETURNING id INTO v_condo_id;
    END IF;

    INSERT INTO public.usuarios (condominio_id, nombre, email, rol, activo)
    SELECT v_condo_id, 'Admin Demo', 'admin.demo@condominio.local', 'admin', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.usuarios WHERE email = 'admin.demo@condominio.local'
    );

    INSERT INTO public.usuarios (condominio_id, nombre, email, rol, activo)
    SELECT v_condo_id, 'Operador Demo', 'operador.demo@condominio.local', 'operador', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.usuarios WHERE email = 'operador.demo@condominio.local'
    );

    INSERT INTO public.empleados (
        condominio_id, nombre, cargo, area, direccion,
        telefono_fijo, telefono_celular, correo, notas, activo
    )
    SELECT v_condo_id, 'Carlos Gómez', 'Conserje', 'Mantenimiento', 'Residencias Demo Norte',
           '0212-5550001', '04141234567', 'carlos.gomez@demo.local', 'Turno mañana', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.empleados WHERE condominio_id = v_condo_id AND nombre = 'Carlos Gómez'
    );

    INSERT INTO public.empleados (
        condominio_id, nombre, cargo, area, direccion,
        telefono_fijo, telefono_celular, correo, notas, activo
    )
    SELECT v_condo_id, 'Mariana López', 'Administración', 'Administración', 'Oficina administrativa',
           '0212-5550002', '04141234568', 'mariana.lopez@demo.local', 'Apoyo contable', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.empleados WHERE condominio_id = v_condo_id AND nombre = 'Mariana López'
    );

    INSERT INTO public.propietarios (condominio_id, nombre, cedula, telefono, correo, direccion, notas, activo)
    SELECT v_condo_id, 'María Pérez', 'V12345678', '04141230001', 'maria.perez@demo.local', 'Apto A-101', 'Propietaria principal', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.propietarios WHERE condominio_id = v_condo_id AND cedula = 'V12345678'
    );

    INSERT INTO public.propietarios (condominio_id, nombre, cedula, telefono, correo, direccion, notas, activo)
    SELECT v_condo_id, 'José Ramírez', 'V23456789', '04141230002', 'jose.ramirez@demo.local', 'Apto A-102', 'Propietario principal', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.propietarios WHERE condominio_id = v_condo_id AND cedula = 'V23456789'
    );

    INSERT INTO public.propietarios (condominio_id, nombre, cedula, telefono, correo, direccion, notas, activo)
    SELECT v_condo_id, 'Laura Suárez', 'V34567890', '04141230003', 'laura.suarez@demo.local', 'Apto B-201', 'Propietaria principal', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.propietarios WHERE condominio_id = v_condo_id AND cedula = 'V34567890'
    );

    SELECT id INTO v_prop1 FROM public.propietarios WHERE condominio_id = v_condo_id AND cedula = 'V12345678' LIMIT 1;
    SELECT id INTO v_prop2 FROM public.propietarios WHERE condominio_id = v_condo_id AND cedula = 'V23456789' LIMIT 1;
    SELECT id INTO v_prop3 FROM public.propietarios WHERE condominio_id = v_condo_id AND cedula = 'V34567890' LIMIT 1;

    INSERT INTO public.alicuotas (condominio_id, descripcion, autocalcular, cantidad_unidades, total_alicuota, activo)
    SELECT v_condo_id, 'Alicuota general demo', FALSE, 3, 0.333333, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.alicuotas WHERE condominio_id = v_condo_id AND descripcion = 'Alicuota general demo'
    );

    SELECT id INTO v_ali_id FROM public.alicuotas WHERE condominio_id = v_condo_id AND descripcion = 'Alicuota general demo' LIMIT 1;

    INSERT INTO public.unidades (
        condominio_id, propietario_id, alicuota_id, codigo, numero, piso,
        tipo_propiedad, tipo_condomino, cuota_fija,
        saldo, activo
    )
    SELECT v_condo_id, v_prop1, v_ali_id, 'A-101', 'A-101', '1',
           'Apartamento', 'Propietario', 0,
           30.00, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.unidades WHERE condominio_id = v_condo_id AND codigo = 'A-101'
    );

    INSERT INTO public.unidades (
        condominio_id, propietario_id, alicuota_id, codigo, numero, piso,
        tipo_propiedad, tipo_condomino, cuota_fija,
        saldo, activo
    )
    SELECT v_condo_id, v_prop2, v_ali_id, 'A-102', 'A-102', '1',
           'Apartamento', 'Propietario', 0,
           0.00, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.unidades WHERE condominio_id = v_condo_id AND codigo = 'A-102'
    );

    INSERT INTO public.unidades (
        condominio_id, propietario_id, alicuota_id, codigo, numero, piso,
        tipo_propiedad, tipo_condomino, cuota_fija,
        saldo, activo
    )
    SELECT v_condo_id, v_prop3, v_ali_id, 'B-201', 'B-201', '2',
           'Apartamento', 'Propietario', 0,
           150.50, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.unidades WHERE condominio_id = v_condo_id AND codigo = 'B-201'
    );

    INSERT INTO public.unidad_propietarios (unidad_id, propietario_id, activo, es_principal)
    SELECT u.id, u.propietario_id, TRUE, TRUE
    FROM public.unidades u
    WHERE u.condominio_id = v_condo_id
      AND u.propietario_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM public.unidad_propietarios up
          WHERE up.unidad_id = u.id AND up.propietario_id = u.propietario_id
      );

    INSERT INTO public.proveedores (
        condominio_id, nombre, tipo_documento_id, numero_documento, direccion,
        telefono_fijo, telefono_celular, correo, contacto, notas, saldo, activo
    )
    SELECT v_condo_id, 'Servicios Técnicos CA', v_tipo_rif, 'J-98765432-1', 'Caracas',
           '0212-4441234', '04141234569', 'contacto@serviciostecnicos.local', 'Juan Pérez',
           'Proveedor de mantenimiento general', 0, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.proveedores WHERE condominio_id = v_condo_id AND nombre = 'Servicios Técnicos CA'
    );

    INSERT INTO public.servicios (condominio_id, nombre, precio_unitario, activo)
    SELECT v_condo_id, 'Salón de fiestas', 0, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.servicios WHERE condominio_id = v_condo_id AND nombre = 'Salón de fiestas'
    );

    INSERT INTO public.servicios (condominio_id, nombre, precio_unitario, activo)
    SELECT v_condo_id, 'Parrillera', 0, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.servicios WHERE condominio_id = v_condo_id AND nombre = 'Parrillera'
    );

    INSERT INTO public.conceptos (condominio_id, nombre, tipo, activo)
    SELECT v_condo_id, 'Mantenimiento general', 'gasto', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.conceptos WHERE condominio_id = v_condo_id AND nombre = 'Mantenimiento general'
    );

    INSERT INTO public.conceptos (condominio_id, nombre, tipo, activo)
    SELECT v_condo_id, 'Limpieza general', 'gasto', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.conceptos WHERE condominio_id = v_condo_id AND nombre = 'Limpieza general'
    );

    INSERT INTO public.conceptos_consumo (condominio_id, nombre, unidad_medida, precio_unitario, tipo_precio, activo)
    SELECT v_condo_id, 'Agua', 'm3', 1.25, 'fijo', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.conceptos_consumo WHERE condominio_id = v_condo_id AND nombre = 'Agua'
    );

    INSERT INTO public.conceptos_consumo (condominio_id, nombre, unidad_medida, precio_unitario, tipo_precio, activo)
    SELECT v_condo_id, 'Gas', 'm3', 0.95, 'fijo', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.conceptos_consumo WHERE condominio_id = v_condo_id AND nombre = 'Gas'
    );

    INSERT INTO public.gastos_fijos (condominio_id, descripcion, monto, tipo_gasto, alicuota_id, activo)
    SELECT v_condo_id, 'Servicio de vigilancia', 450.00, 'Contrato', v_ali_id, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.gastos_fijos WHERE condominio_id = v_condo_id AND descripcion = 'Servicio de vigilancia'
    );

    INSERT INTO public.gastos_fijos (condominio_id, descripcion, monto, tipo_gasto, alicuota_id, activo)
    SELECT v_condo_id, 'Limpieza de áreas comunes', 180.00, 'Servicio recurrente', v_ali_id, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.gastos_fijos WHERE condominio_id = v_condo_id AND descripcion = 'Limpieza de áreas comunes'
    );

    INSERT INTO public.cuentas_bancos (condominio_id, descripcion, numero_cuenta, saldo_inicial, saldo, moneda, activo)
    SELECT v_condo_id, 'Cuenta Principal Demo', '0102-0001-00-1234567890', 1500.00, 1500.00, 'USD', TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.cuentas_bancos WHERE condominio_id = v_condo_id AND descripcion = 'Cuenta Principal Demo'
    );

    INSERT INTO public.fondos (condominio_id, nombre, alicuota_id, saldo_inicial, saldo, tipo, cantidad, activo)
    SELECT v_condo_id, 'Fondo de reserva', v_ali_id, 500.00, 500.00, 'reserva', 1, TRUE
    WHERE NOT EXISTS (
        SELECT 1 FROM public.fondos WHERE condominio_id = v_condo_id AND nombre = 'Fondo de reserva'
    );
END $$;

COMMIT;
