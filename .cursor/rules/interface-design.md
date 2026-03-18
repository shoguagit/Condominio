# Skill: Interface Design — Sistema de Condominio
## Propósito
Guiar a la IA para generar interfaces corporativas claras, modernas y consistentes en Streamlit para un sistema de gestión de condominios venezolano.

---

## Paleta de Colores Corporativa
- **Primario:** `#1B4F72` (azul corporativo oscuro)
- **Secundario:** `#2E86C1` (azul medio)
- **Acento:** `#28B463` (verde éxito)
- **Alerta:** `#E74C3C` (rojo error)
- **Advertencia:** `#F39C12` (naranja advertencia)
- **Fondo principal:** `#F4F6F7`
- **Fondo sidebar:** `#1B4F72`
- **Texto principal:** `#2C3E50`
- **Texto secundario:** `#717D7E`
- **Bordes/divisores:** `#D5D8DC`
- **Blanco cards:** `#FFFFFF`

---

## Estructura Visual Obligatoria

### Header Global (siempre visible)
```
[LOGO] NOMBRE DEL CONDOMINIO    |  Mes en Proceso: MM/AAAA  |  Tasa BCV: Bs. X,XXXX  |  Usuario: ADMIN
```
- Fondo: `#1B4F72`
- Texto: blanco
- Separadores: línea vertical `#2E86C1`

### Sidebar de Navegación
- Fondo: `#1B4F72`
- Items activos: fondo `#2E86C1`, texto blanco, borde izquierdo 4px `#28B463`
- Items inactivos: texto `#AED6F1`, hover fondo `#21618C`
- Iconos: usar emojis representativos o st.icon si disponible
- Secciones agrupadas con separador y título en mayúscula pequeña

### Cards de Módulo (en menú principal y dashboards)
- Fondo: `#FFFFFF`
- Borde: `1px solid #D5D8DC`
- Border-radius: `12px`
- Sombra: `box-shadow: 0 2px 8px rgba(0,0,0,0.08)`
- Padding: `24px`
- Hover: borde `#2E86C1`, sombra más pronunciada

### Tablas de Datos (st.dataframe / st.data_editor)
- Header: fondo `#1B4F72`, texto blanco, font-weight bold
- Filas alternas: blanco y `#EBF5FB`
- Fila seleccionada: `#D6EAF8`
- Texto: `#2C3E50`
- Bordes: `#D5D8DC`
- Columna ID: ancho fijo 60px, centrada
- Columnas de acciones: botones pequeños inline

### Formularios (Incluir / Modificar)
- Fondo: `#FFFFFF` con borde `#D5D8DC`
- Labels: `#2C3E50`, font-weight 500
- Inputs: borde `#AED6F1`, focus borde `#2E86C1`
- Campos obligatorios: asterisco rojo `*` al lado del label
- Botón GUARDAR: fondo `#28B463`, texto blanco
- Botón CANCELAR: fondo `#E8E8E8`, texto `#2C3E50`
- Botón ELIMINAR: fondo `#E74C3C`, texto blanco
- Mensajes de éxito: `st.success()` con ícono ✅
- Mensajes de error: `st.error()` con ícono ❌

### Barra de Herramientas de Módulo (como Sisconin)
```
[+ Incluir]  [✏ Modificar]  [🗑 Eliminar]  |  [⬅ Primero] [◀ Ant] [N de TOTAL] [▶ Sig] [⮕ Último]
```
- Estilo de navegación por registros similar al sistema original

---

## Reglas de Diseño

1. **Consistencia:** Todos los módulos usan la misma estructura: header → toolbar → filtros → tabla → panel de ayuda lateral derecho
2. **Panel de ayuda lateral:** Cada módulo incluye en la columna derecha una card con ícono, título del módulo y descripción de qué hace (igual que Sisconin)
3. **Espaciado:** Mínimo 16px entre secciones, 8px entre elementos del mismo grupo
4. **Tipografía:** Sans-serif, títulos de módulo 20px bold, subtítulos 14px semibold, texto tabla 13px
5. **Iconos por módulo:**
   - 🏢 Condominios
   - 🏠 Unidades  
   - 📊 Alícuotas
   - 💰 Fondos
   - 🔧 Servicios
   - 📋 Conceptos
   - 📌 Gastos Fijos
   - ⚡ Conceptos de Consumo
   - 🏦 Cuentas Caja/Bancos
   - 👷 Empleados
   - 👥 Clientes / Propietarios
   - 🔐 Usuarios
   - 📄 Proveedores
   - 🧾 Facturas
   - 📈 Reportes
6. **Responsive:** Mínimo 1024px de ancho, layout de 2 columnas (contenido 75% + ayuda 25%)
7. **Estados vacíos:** Cuando una tabla no tiene datos mostrar mensaje centrado con ícono y texto explicativo
8. **Loading states:** Usar `st.spinner()` durante operaciones con Supabase

---

## CSS Global a inyectar en app.py
```python
st.markdown("""
<style>
    /* Header corporativo */
    .main-header {
        background: #1B4F72;
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    /* Cards */
    .module-card {
        background: white;
        border: 1px solid #D5D8DC;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .module-card:hover {
        border-color: #2E86C1;
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1B4F72 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #AED6F1 !important;
    }
    /* Botones primarios */
    .stButton > button[kind="primary"] {
        background-color: #2E86C1;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }
    /* Tablas */
    .stDataFrame thead tr th {
        background-color: #1B4F72 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)
```
