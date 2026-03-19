# Ejecutar migración en Supabase

1. Abre tu proyecto en [Supabase Dashboard](https://supabase.com/dashboard).
2. Ve a **SQL Editor** → **New query**.
3. Copia y pega **todo** el contenido del archivo `supabase_migration.sql` (en la raíz del proyecto).
4. Pulsa **Run**. Debe aparecer "Success" (puede decir "No rows returned").

Con eso quedan creadas la tabla `unidad_propietarios`, los índices y los cambios que permiten crear unidades sin propietario ni alícuota.
