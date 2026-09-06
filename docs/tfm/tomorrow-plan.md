# Plan operativo actual

Estado tras la validación automatizada del 2026-09-06: integración de #5, #7,
#8 y #6 ensayada sin conflictos; PostgreSQL fresco, migraciones y 64 tests
correctos; CI de los cuatro PRs verde; APK debug publicado en #8. FLEURS sigue
bloqueado por la descarga del dataset, pero el fallback SLR61 tiene benchmark
real medido y documentado. No se ha hecho ningún merge.

## P0 — bloqueantes

1. Revisar los cuatro PRs y ejecutar el orden de merge recomendado (humano).
2. Instalar el APK debug y validar backend LAN + migrations (30–60 min).
3. Ejecutar manual completo y conservar interaction id y logs sanitizados (15–30 min).
4. Ejecutar continuous y smart en el dispositivo, sin afirmar batería ni precisión (30–60 min).

## P1 — importantes

5. Medir batería idle/continuous/smart, 15–30 min por modo.
6. Si se necesita FLEURS estrictamente, repetir su descarga en un entorno con acceso estable.
7. Revisar claims de memoria y resultados fallback frente al corpus elegido.

## P2 — opcionales

8. Threshold sweep VAD/speaker con audios consentidos.
9. Habilitar el workflow de emulator en una rama reconocida por GitHub, sin hacerlo en `main` automáticamente.
10. Revisión humana final y orden de integración de PRs.

No hacer merge durante la validación; anotar cada estado como MEDIDO, NO MEDIDO o NO DISPONIBLE.
