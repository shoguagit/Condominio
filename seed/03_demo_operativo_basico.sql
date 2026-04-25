BEGIN;

DO $$
DECLARE
    v_condo_id BIGINT;
    v_proveedor_id BIGINT;
    v_concepto_gasto_id BIGINT;
    v_proceso_id BIGINT;
    v_u1 BIGINT;
    v_u2 BIGINT;
    v_u3 BIGINT;
    v_p1 BIGINT;
    v_p2 BIGINT;
    v_p3 BIGINT;
BEGIN
    SELECT id INTO v_condo_id FROM public.condominios WHERE nombre = 'Condominio Demo Norte' LIMIT 1;
    IF v_condo_id IS NULL THEN
        RAISE EXCEPTION 'No existe el condominio demo. Ejecuta primero seed/02_demo_maestros.sql';
    END IF;

    INSERT INTO public.tasas_bcv_dia (fecha, tasa_bs_por_usd, fuente) VALUES
    (DATE '2026-03-10', 96.80, 'oficial'),
    (DATE '2026-03-11', 96.95, 'oficial'),
    (DATE '2026-03-12', 97.00, 'oficial'),
    (DATE '2026-03-13', 97.05, 'oficial'),
    (DATE '2026-03-14', 97.10, 'oficial'),
    (DATE '2026-03-15', 97.15, 'oficial')
    ON CONFLICT (fecha) DO UPDATE SET
        tasa_bs_por_usd = EXCLUDED.tasa_bs_por_usd,
        fuente = EXCLUDED.fuente,
        actualizado_at = NOW();

    SELECT id INTO v_proveedor_id FROM public.proveedores
    WHERE condominio_id = v_condo_id AND nombre = 'Servicios Técnicos CA'
    LIMIT 1;

    INSERT INTO public.facturas_proveedor (
        condominio_id, numero, fecha, fecha_vencimiento,
        proveedor_id, descripcion, total, pagado, mes_proceso, activo
    )
    SELECT v_condo_id, 'DEMO-0001', DATE '2026-03-05', DATE '2026-03-20',
           v_proveedor_id, 'Mantenimiento general de áreas comunes', 500.00, 200.00, DATE '2026-03-01', TRUE
    WHERE v_proveedor_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM public.facturas_proveedor WHERE condominio_id = v_condo_id AND numero = 'DEMO-0001'
      );

    SELECT id INTO v_concepto_gasto_id FROM public.conceptos
    WHERE condominio_id = v_condo_id AND nombre = 'Mantenimiento general'
    LIMIT 1;

    INSERT INTO public.movimientos (
        condominio_id, periodo, fecha, descripcion, referencia, tipo,
        monto_bs, monto_usd, tasa_cambio, concepto_id, estado, fuente
    )
    SELECT v_condo_id, DATE '2026-03-01', DATE '2026-03-10',
           'Pago de vigilancia del mes', 'EGR-DEMO-001', 'egreso',
           450.00, 4.65, 96.80, v_concepto_gasto_id, 'clasificado', 'manual'
    WHERE NOT EXISTS (
        SELECT 1 FROM public.movimientos WHERE condominio_id = v_condo_id AND referencia = 'EGR-DEMO-001'
    );

    INSERT INTO public.movimientos (
        condominio_id, periodo, fecha, descripcion, referencia, tipo,
        monto_bs, monto_usd, tasa_cambio, concepto_id, estado, fuente
    )
    SELECT v_condo_id, DATE '2026-03-01', DATE '2026-03-12',
           'Compra de materiales de limpieza', 'EGR-DEMO-002', 'egreso',
           180.00, 1.86, 97.00, v_concepto_gasto_id, 'clasificado', 'manual'
    WHERE NOT EXISTS (
        SELECT 1 FROM public.movimientos WHERE condominio_id = v_condo_id AND referencia = 'EGR-DEMO-002'
    );

    INSERT INTO public.procesos_mensuales (
        condominio_id, periodo, total_gastos_bs, total_gastos_usd,
        fondo_reserva_bs, total_facturable_bs, estado
    )
    SELECT v_condo_id, DATE '2026-03-01', 630.00, 6.51, 63.00, 693.00, 'procesado'
    WHERE NOT EXISTS (
        SELECT 1 FROM public.procesos_mensuales WHERE condominio_id = v_condo_id AND periodo = DATE '2026-03-01'
    );

    SELECT id INTO v_proceso_id FROM public.procesos_mensuales
    WHERE condominio_id = v_condo_id AND periodo = DATE '2026-03-01'
    LIMIT 1;

    SELECT id, propietario_id INTO v_u1, v_p1 FROM public.unidades WHERE condominio_id = v_condo_id AND codigo = 'A-101' LIMIT 1;
    SELECT id, propietario_id INTO v_u2, v_p2 FROM public.unidades WHERE condominio_id = v_condo_id AND codigo = 'A-102' LIMIT 1;
    SELECT id, propietario_id INTO v_u3, v_p3 FROM public.unidades WHERE condominio_id = v_condo_id AND codigo = 'B-201' LIMIT 1;

    INSERT INTO public.cuotas_unidad (
        proceso_id, unidad_id, propietario_id, condominio_id, periodo,
        alicuota_valor, total_gastos_bs, cuota_calculada_bs,
        saldo_anterior_bs, pagos_mes_bs, total_a_pagar_bs, estado
    )
    SELECT v_proceso_id, v_u1, v_p1, v_condo_id, DATE '2026-03-01',
           0.333333, 630.00, 231.00, 30.00, 0.00, 261.00, 'pendiente'
    WHERE v_proceso_id IS NOT NULL AND v_u1 IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM public.cuotas_unidad WHERE proceso_id = v_proceso_id AND unidad_id = v_u1
      );

    INSERT INTO public.cuotas_unidad (
        proceso_id, unidad_id, propietario_id, condominio_id, periodo,
        alicuota_valor, total_gastos_bs, cuota_calculada_bs,
        saldo_anterior_bs, pagos_mes_bs, total_a_pagar_bs, estado
    )
    SELECT v_proceso_id, v_u2, v_p2, v_condo_id, DATE '2026-03-01',
           0.333333, 630.00, 231.00, 0.00, 0.00, 231.00, 'pendiente'
    WHERE v_proceso_id IS NOT NULL AND v_u2 IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM public.cuotas_unidad WHERE proceso_id = v_proceso_id AND unidad_id = v_u2
      );

    INSERT INTO public.cuotas_unidad (
        proceso_id, unidad_id, propietario_id, condominio_id, periodo,
        alicuota_valor, total_gastos_bs, cuota_calculada_bs,
        saldo_anterior_bs, pagos_mes_bs, total_a_pagar_bs, estado
    )
    SELECT v_proceso_id, v_u3, v_p3, v_condo_id, DATE '2026-03-01',
           0.333334, 630.00, 231.00, 150.50, 0.00, 381.50, 'pendiente'
    WHERE v_proceso_id IS NOT NULL AND v_u3 IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM public.cuotas_unidad WHERE proceso_id = v_proceso_id AND unidad_id = v_u3
      );
END $$;

COMMIT;
