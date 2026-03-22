# Git workflow — proyecto Condominio

## Regla para el asistente
Tras **cambios de código o docs** que el usuario acepte o que cierren una tarea:

1. `git add` de los archivos tocados (o `git add -u` si aplica).
2. `git commit -m "tipo: mensaje breve en español"` (feat / fix / docs / chore).
3. `git push origin main`.

**Excepción:** si el usuario pide explícitamente no commitear, no hacer push, o usar otra rama.

No pedir confirmación para commit/push salvo que el usuario lo indique.
