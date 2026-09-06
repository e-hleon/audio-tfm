# Guion de defensa (10–15 minutos)

1. **Apertura (1 min).** El problema es convertir voz personal en diario sin enviar audio bruto por defecto.
2. **Objetivos (1 min).** Captura, ASR local, extracción estructurada, persistencia, consulta y evaluación reproducible.
3. **Arquitectura (2 min).** Android → FastAPI → faster-whisper local → Analyzer externo opcional → PostgreSQL; mostrar el diagrama y la frontera de privacidad.
4. **Demo (3 min).** Health, envío de audio, interacción, día y resumen explícito; después captura manual. No prometer resultados no ejecutados.
5. **Android avanzado (2 min).** FGS visible para continuous, PCM16/chunks/cola y smart como baseline VAD/speaker experimental.
6. **Evaluación (2 min).** FLEURS para WER/CER/RTF; 36 fixtures sintéticos para PRF; tests de límites. Presentar tablas solo si contienen artefactos MEDIDOS.
7. **Privacidad (1 min).** Audio local al ASR; solo texto derivado al proveedor; claves en entorno; `store=false` no es garantía de retención cero.
8. **Limitaciones y cierre (1–2 min).** La prueba física en Pixel 8 confirmó que la calibración y el mínimo consecutivo eliminan los falsos positivos de silencio observados, pero el baseline de speaker dio 1.0000 tanto para la voz registrada como para otra voz. SMART sigue siendo experimental, no biométrico ni una base de privacidad por identidad; batería y métricas formales FAR/FRR siguen pendientes.
