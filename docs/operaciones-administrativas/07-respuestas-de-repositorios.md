# Respuestas de repositorios

Este anexo muestra ejemplos de respuesta que devuelve la capa `repositories/` después de leer o escribir en Supabase.

## Cómo usar este documento
- Sirve para integrar pantallas nuevas, automatizaciones o validaciones.
- Los ejemplos reflejan el comportamiento del código activo, no un contrato formal versionado.
- Cuando hay joins, la forma real de la respuesta depende del `select(...)` del repositorio.

## CondominioRepository

### `get_by_id(condominio_id)`
```json
{
  "id": 3,
  "nombre": "Residencias El Parque",
  "direccion": "Av. Principal, Caracas",
  "pais_id": 1,
  "tipo_documento_id": 1,
  "numero_documento": "J-12345678-9",
  "telefono": "0212-5551234",
  "email": "admin@elparque.com",
  "mes_proceso": "2026-03-01",
  "tasa_cambio": 97.15,
  "activo": true,
  "paises": {
    "nombre": "Venezuela",
    "simbolo_moneda": "Bs."
  },
  "tipos_documento": {
    "nombre": "RIF"
  }
}
```

### `actualizar_dia_limite(condominio_id, dia)`
```json
{
  "id": 3,
  "dia_limite_pago": 15
}
```

## UnidadRepository

### `get_all(condominio_id)`
```json
[
  {
    "id": 18,
    "condominio_id": 3,
    "codigo": "A-3B",
    "tipo_propiedad": "Apartamento",
    "indiviso_pct": 4.5,
    "saldo": 30.0,
    "estado_pago": "parcial",
    "activo": true,
    "propietarios": {
      "id": 42,
      "nombre": "María Pérez",
      "cedula": "V12345678",
      "correo": "maria@example.com"
    }
  }
]
```

### `get_indicadores(condominio_id)`
```json
{
  "total": 24,
  "al_dia": 18,
  "morosos": 4,
  "pct_asignado": 100.0
}
```

## PropietarioRepository

### `get_by_id(propietario_id)`
```json
{
  "id": 42,
  "condominio_id": 3,
  "nombre": "María Pérez",
  "cedula": "V12345678",
  "telefono": "04141234567",
  "correo": "maria@example.com",
  "direccion": "Torre A, piso 3",
  "notas": "Propietaria principal",
  "activo": true
}
```

## EmpleadoRepository

### `get_all(condominio_id)`
```json
[
  {
    "id": 7,
    "condominio_id": 3,
    "nombre": "Carlos Gómez",
    "cargo": "Conserje",
    "area": "Mantenimiento",
    "telefono_celular": "04141234567",
    "correo": "carlos@example.com",
    "activo": true
  }
]
```

## ProveedorRepository

### `get_by_id(proveedor_id)`
```json
{
  "id": 55,
  "condominio_id": 3,
  "nombre": "Servicios Técnicos CA",
  "tipo_documento_id": 1,
  "numero_documento": "J-98765432-1",
  "telefono_fijo": "02124441234",
  "telefono_celular": "04141234567",
  "correo": "contacto@servicios.com",
  "saldo": 500.0,
  "activo": true,
  "tipos_documento": {
    "nombre": "RIF"
  }
}
```

## UsuarioRepository

### `get_all(condominio_id)`
```json
[
  {
    "id": 12,
    "condominio_id": 3,
    "nombre": "Ana Administradora",
    "email": "admin@condominio.com",
    "rol": "admin",
    "activo": true,
    "ultimo_acceso": "2026-04-25T10:33:01+00:00",
    "condominios": {
      "nombre": "Residencias El Parque"
    }
  }
]
```

### `change_password(email, new_password)`
```json
true
```

## AlicuotaRepository

### `get_all(condominio_id)`
```json
[
  {
    "id": 8,
    "condominio_id": 3,
    "descripcion": "Alicuota general",
    "autocalcular": false,
    "cantidad_unidades": 24,
    "total_alicuota": 0.041667,
    "activo": true
  }
]
```

### `recalcular_desde_unidades(alicuota_id, total_unidades)`
```json
{
  "id": 8,
  "cantidad_unidades": 24,
  "total_alicuota": 0.041667
}
```

## ConceptoRepository

### `get_all(condominio_id, solo_activos=true)`
```json
[
  {
    "id": 7,
    "condominio_id": 3,
    "nombre": "Mantenimiento ascensor",
    "tipo": "gasto",
    "activo": true
  }
]
```

### `can_delete(id, condominio_id)`
```json
false
```

## GastoFijoRepository

### `get_all(condominio_id)`
```json
[
  {
    "id": 21,
    "condominio_id": 3,
    "descripcion": "Servicio de vigilancia",
    "monto": 450.0,
    "tipo_gasto": "Contrato",
    "alicuota_id": 8,
    "alicuotas": {
      "descripcion": "Alicuota general"
    }
  }
]
```

## FacturaRepository

### `get_by_mes_proceso(condominio_id, mes_proceso)`
```json
[
  {
    "id": 100,
    "condominio_id": 3,
    "numero": "0001-00012345",
    "fecha": "2026-03-05",
    "fecha_vencimiento": "2026-03-20",
    "proveedor_id": 55,
    "descripcion": "Mantenimiento general",
    "total": 500.0,
    "pagado": 200.0,
    "saldo": 300.0,
    "mes_proceso": "2026-03-01",
    "activo": true,
    "proveedores": {
      "id": 55,
      "nombre": "Servicios Técnicos CA"
    }
  }
]
```

## PagoRepository

### `get_by_periodo(condominio_id, periodo)`
```json
[
  {
    "id": 301,
    "condominio_id": 3,
    "unidad_id": 18,
    "propietario_id": 42,
    "periodo": "2026-03-01",
    "fecha_pago": "2026-03-15",
    "monto_bs": 120.5,
    "monto_usd": 1.24,
    "tasa_cambio": 97.15,
    "metodo": "transferencia",
    "referencia": "00991234",
    "estado": "confirmado",
    "unidades": {
      "codigo": "A-3B",
      "numero": null
    }
  }
]
```

### `get_indicadores_mes(...)`
```json
{
  "total_cobrado_bs": 2450.0,
  "n_pagos": 18,
  "unidades_al_dia": 15,
  "pendiente_cobrar_bs": 630.0
}
```

## MovimientoRepository

### `get_by_tipo(condominio_id, periodo, "ingreso")`
```json
[
  {
    "id": 801,
    "condominio_id": 3,
    "periodo": "2026-03-01",
    "fecha": "2026-03-14",
    "descripcion": "TRANSFERENCIA PAGO CONDOMINIO",
    "referencia": "99881234",
    "tipo": "ingreso",
    "monto_bs": 120.5,
    "monto_usd": 0.0,
    "tasa_cambio": 0.0,
    "estado": "pendiente",
    "fuente": "excel",
    "conceptos": {
      "nombre": "Pago de condominio"
    },
    "unidades": {
      "id": 18,
      "codigo": "A-3B",
      "numero": null
    },
    "propietarios": {
      "id": 42,
      "nombre": "María Pérez"
    }
  }
]
```

## DashboardRepository

### `obtener_metricas_cobranza(condominio_id, periodo)`
```json
{
  "cuotas_esperadas_bs": 2400.0,
  "cobros_extraordinarios_bs": 120.0,
  "total_esperado_bs": 2520.0,
  "total_cobrado_bs": 2450.0,
  "pct_cobranza": 97.22,
  "unidades_al_dia": 15,
  "unidades_morosas": 4,
  "unidades_parcial": 5
}
```

### `obtener_morosos(condominio_id, periodo)`
```json
{
  "total_morosos": 4,
  "monto_total_adeudado_bs": 630.0,
  "lista": [
    {
      "unidad_id": 18,
      "unidad": "A-3B",
      "propietario": "María Pérez",
      "email": "maria@example.com",
      "saldo_bs": 150.5,
      "meses_atraso": 2
    }
  ]
}
```

## NotificacionRepository

### `obtener_config_smtp(condominio_id)`
```json
{
  "smtp_email": "condominio@gmail.com",
  "smtp_app_password": "xxxx xxxx xxxx xxxx",
  "smtp_nombre_remitente": "Administración del Condominio"
}
```

### `registrar_envio(...)`
```json
{
  "id": 44,
  "condominio_id": 3,
  "periodo": "2026-03",
  "unidad_id": 18,
  "propietario_email": "maria@example.com",
  "enviado": true,
  "tipo": "mora"
}
```

## ProcesoMensualRepository

### `get_or_create(condominio_id, periodo)`
```json
{
  "id": 9,
  "condominio_id": 3,
  "periodo": "2026-03-01",
  "estado": "borrador",
  "total_gastos_bs": 0.0,
  "total_gastos_usd": 0.0,
  "fondo_reserva_bs": 0.0,
  "total_facturable_bs": 0.0
}
```

### `get_cuotas(condominio_id, periodo)`
```json
[
  {
    "id": 1001,
    "proceso_id": 9,
    "unidad_id": 18,
    "propietario_id": 42,
    "condominio_id": 3,
    "periodo": "2026-03-01",
    "alicuota_valor": 0.045,
    "cuota_calculada_bs": 120.5,
    "saldo_anterior_bs": 30.0,
    "pagos_mes_bs": 0.0,
    "total_a_pagar_bs": 150.5,
    "estado": "pendiente",
    "unidades": {
      "codigo": "A-3B",
      "numero": null
    },
    "propietarios": {
      "nombre": "María Pérez"
    }
  }
]
```

## TasaBcvRepository

### `get_last_on_or_before(fecha)`
```json
["2026-03-15", 97.15]
```

### `list_sorted_pairs()`
```json
[
  ["2026-03-13", 96.9],
  ["2026-03-14", 97.02],
  ["2026-03-15", 97.15]
]
```
