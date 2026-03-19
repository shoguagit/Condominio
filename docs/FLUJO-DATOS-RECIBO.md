# Flujo de datos y dependencias para el recibo

## Orden de trabajo (dependencias)

1. **Condominio** — Entidad principal (nombre, RIF, correo, etc.).
2. **Unidades (apartamentos)** — Cada inmueble del condominio (NRO: A13, B01, B06…). Se crean sin propietario ni alícuota.
3. **Propietarios** — Personas del condominio (nombre, cédula, correo). Un mismo propietario puede estar en varias unidades.
4. **Asignar a cada unidad** — En el módulo Unidades (editar):
   - **Propietario(s):** una unidad puede tener 1 o varios propietarios (activos/inactivos); uno se marca como principal (para el recibo).
   - **Alícuota:** una alícuota por unidad (ej. 0,33; 0,45).
5. **Alícuotas** — Definición por condominio (descripción, valor). La suma debe ser ≈ 1,00.
6. **Gastos / Proceso mensual** — Para armar el recibo: gastos del mes, fondo reserva 10 %, cuota por alícuota.

## Relación 1 apartamento : N propietarios

- Tabla **unidad_propietarios**: `unidad_id`, `propietario_id`, `activo`, `es_principal`.
- **unidad.propietario_id** = propietario principal (para recibo y listados).

## Datos necesarios para el recibo (según ejemplo)

- Condominio: nombre, RIF, correo.
- Mes, fecha emisión.
- Unidad (inmueble): código (ej. B06).
- Propietario: nombre, correo (del principal o todos).
- Alícuota: valor (ej. 0,33).
- Tabla de gastos: concepto, total mes acum., parte individual (total × alícuota).
- Total gastos comunes, fondo reserva 10 %, total gastos relacionados, cuota mes en USD, saldo acumulado.

## Mapeo con datos del contador (segunda imagen)

- **NRO** → unidad.codigo (o numero).
- **NOMBRE Y APELLIDO** → propietarios (varios por unidad).
- **Cta (Alicuota)** → alícuota asignada a la unidad.
- **CORREO** → propietario.correo.
- **Saldo, Cob., Cuota, Meses** → proceso mensual / cuotas_unidad / estado de cuenta.
