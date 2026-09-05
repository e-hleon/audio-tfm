# 001 — Transcripción síncrona para el primer incremento

Estado: aceptada; transcripción real por HTTP en CUDA verificada.

## Problema

Demostrar audio → HTTP → transcripción local CUDA → JSON con una GPU de 4 GB.
La arquitectura inicialmente prevista exige servicios que no son necesarios para
este flujo y dificultan aislar los fallos de inferencia.

## Alternativas consideradas

1. API, Redis/RQ, worker y PostgreSQL: trabajos persistentes y consultas posteriores,
   a cambio de varios procesos y estados que este incremento no necesita.
2. Ejecutar ASR directamente en un script: sencillo, pero no verifica HTTP.
3. API con inferencia en el mismo proceso: satisface el flujo con un solo servicio.

## Decisión

Elegir la tercera opción: FastAPI/Uvicorn, faster-whisper, un proceso, una instancia
CUDA y respuesta síncrona. Usar un hilo interno para no bloquear la atención de
salud y un bloqueo para rechazar inferencias simultáneas. No introducir cola.

Empezar con `base` multilingüe e `int8_float16`, buscando margen de memoria.
Docker con CUDA/cuDNN permite empaquetar las bibliotecas requeridas. La selección
se ha ratificado con transcripciones reales en la RTX 3050. No constituye una
comparación exhaustiva de modelos ni una evaluación de calidad en español.

## Consecuencias

Menos servicios y una ruta de ejecución fácil de explicar y probar. Los archivos
son temporales; no hay persistencia de resultados ni recuperación tras un fallo.
El cliente espera durante la inferencia y debe reintentar si recibe 503.

Los audios de prueba se limitan a 10 MiB y 60 segundos; no se ofrece una API pública
ni procesamiento concurrente. Si aparecen necesidades de mayor duración,
concurrencia o recuperación, se evaluará entonces procesamiento asíncrono.

Se fija Hugging Face Hub 0.34.4: la resolución inicial a Hub 1.x dejó sin instalar
`requests`, que faster-whisper 1.2.0 importa. El puerto es configurable para
evitar colisiones con servicios existentes.

Se añaden pruebas desde el principio. El alcance general de `docs/scope.md` no se
modifica. No se declara el incremento funcional hasta completar la prueba CUDA
real de extremo a extremo.
