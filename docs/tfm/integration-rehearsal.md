# Ensayo de integración

Fecha: 2026-09-06. Se creó una rama temporal desde `origin/main` y se integró,
sin modificar las ramas fuente, en este orden: #5 manual, #7 advanced, #8
hardening y #6 evaluation.

Resultado: cuatro merges automáticos, sin conflictos. El ensayo final incluyó
`51500d4` de #6 y quedó 20 commits por encima de `origin/main`. `git diff --check`
pasó. Se ejecutaron migraciones desde una base PostgreSQL nueva y 64 tests dentro
de la imagen Docker integrada.

El workflow de emulator no pudo dispatcharse porque todavía no está registrado
en la rama por defecto de GitHub; no se hizo merge para habilitarlo.
