# Preguntas del tribunal y respuestas

1. **¿Por qué Whisper?** Es multilingüe, reproducible y permite ASR local sin entrenar un modelo propio.
2. **¿Por qué no un LLM local?** El alcance priorizó ASR local; un LLM local grande exige memoria y evaluación adicional.
3. **¿Por qué OpenAI?** Es un proveedor intercambiable detrás de `Analyzer`; se usa por Structured Outputs, no como parte inseparable.
4. **¿Por qué no Kubernetes?** Un TFM personal no necesita orquestación; añadirlo aumentaría complejidad sin requisito.
5. **¿Por qué PostgreSQL?** Transacciones, timestamps y JSONB en una sola base madura.
6. **¿Por qué JSONB?** El análisis es un contrato anidado que evoluciona; se evita crear tablas hijas prematuras.
7. **¿Por qué no MongoDB?** PostgreSQL ya resuelve persistencia relacional y documentos necesarios.
8. **¿Por qué síncrono?** Hace visible el flujo y reduce infraestructura; el coste es bloquear la petición.
9. **¿Por qué 60 s?** Es un límite explícito del backend que acota recursos y encaja con notas cortas.
10. **¿MediaRecorder frente a AudioRecord?** Manual necesita simplicidad; continuo necesita frames PCM y chunking controlado.
11. **¿Por qué VAD energético?** Es local, interpretable y ligero; no se presenta como solución robusta.
12. **¿Es realmente IA?** Whisper y el LLM sí son modelos; VAD y similitud son heurísticas experimentales.
13. **¿Speaker verification es segura?** No. Es un baseline acústico y no biometría robusta.
14. **¿Por qué no diarización?** Identificar todos los interlocutores está fuera de alcance.
15. **¿Qué datos salen del dispositivo?** En manual/continuous sale audio al backend local; al proveedor externo solo texto derivado.
16. **¿Qué sale de casa?** El texto enviado a OpenAI si se configura; no el audio según el pipeline.
17. **¿GDPR?** Consentimiento, minimización y derechos requieren una aplicación legal real; el prototipo no los automatiza.
18. **¿Terceros grabados?** Deben conocerlo y consentir; la evaluación no usa grabaciones de terceros.
19. **¿Qué es WER?** Distancia de edición agregada entre palabras de referencia e hipótesis.
20. **¿Qué es RTF?** Tiempo de inferencia dividido por duración del audio; menor que uno es más rápido que tiempo real.
21. **¿Por qué F1?** Resume precision y recall cuando hay falsos positivos y negativos.
22. **¿Por qué dataset LLM sintético?** Permite ground truth controlado sin exponer conversaciones personales.
23. **¿Cómo evitas hallucinations?** Schema estricto, evidence literal y fixtures negativos; no se garantiza verdad.
24. **¿Qué significa store=false?** No pedir persistencia de estado de la respuesta; no garantiza retención cero.
25. **¿Qué si OpenAI cae?** El endpoint LLM falla con error mapeado; ASR local sigue siendo conceptualmente separable.
26. **¿Concurrencia?** El proceso único serializa inferencia y responde 503 a cargas simultáneas no admitidas.
27. **¿Qué es stale?** Un resumen cuyo fingerprint ya no coincide con las interacciones actuales.
28. **¿Qué es fingerprint?** SHA-256 de IDs/updated_at y timezone para detectar cambios derivados.
29. **¿Por qué no worker queue?** No hay requisito de trabajos persistentes; sería trabajo futuro si aparecen timeouts reales.
30. **¿Cómo se limita la cola?** Tiene capacidad fija; éxito borra, fallo reencola y descarte por capacidad elimina explícitamente.
31. **¿Cómo se evita perder lecturas?** Se acumulan lecturas parciales y se framan sin solapamiento.
32. **¿Qué ocurre al Stop?** Se cancela la captura, se libera AudioRecord y se conserva el último chunk parcial.
33. **¿Qué ocurre con un WAV?** RIFF PCM16 mono, 16 kHz, little-endian y tamaños derivados de muestras.
34. **¿Cómo se prueba Android?** JVM para lógica y workflow separado para instrumentación; hardware sigue pendiente.
35. **¿Por qué notificación?** Android exige visibilidad adecuada para una captura de micrófono en foreground service.
36. **¿Qué mide la evaluación ASR?** FLEURS leído, no conversación espontánea; WER/CER, latencia, RTF y fallos.
37. **¿Una llamada por fixture basta?** Mide esa ejecución, no la varianza del proveedor.
38. **¿Qué limitación principal queda?** La validación física mostró que el VAD mejorado suprime el silencio probado, pero la similitud acústica no distingue voz propia de otra voz: todos los scores observados fueron 1.0000. No se pueden afirmar FAR/FRR formales; también queda medir batería.
39. **¿Qué cambiarías en producción?** Auth, límites de recepción más tempranos, jobs persistentes e idempotencia.
40. **¿Cuál es la contribución?** Un flujo local-first pequeño, trazable y con límites explícitos, no un modelo nuevo.
