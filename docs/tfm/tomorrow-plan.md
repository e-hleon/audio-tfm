# Plan operativo de mañana

## P0 — bloqueantes

1. Instalar/obtener APK debug y verificar backend LAN + migrations (30–60 min).
2. Ejecutar manual completo y conservar interaction id, logs sanitizados y fila (15–30 min).
3. Ejecutar continuous con Stop, notification, background, chunk y fallo/reanudación (30–60 min).
4. Ejecutar smart con enrollment y anotar aceptaciones/rechazos sin llamarlas precisión (30–60 min).

## P1 — importantes

5. Medir batería idle/continuous/smart, 15–30 min por modo.
6. Ejecutar ASR base/small 50 y ampliar a 100 si estable; guardar agregados reales.
7. Ejecutar 36 casos LLM si la clave autorizada está configurada; revisar tokens/coste.
8. Actualizar resultados y revisar claims de memoria.

## P2 — opcionales

9. Threshold sweep VAD/speaker con audios consentidos.
10. Dispatch del workflow de emulador y revisión de artifact.
11. Revisión humana final y orden de integración de PRs.

No hacer merge durante la validación; anotar cada estado como MEDIDO, NO MEDIDO o NO DISPONIBLE.
