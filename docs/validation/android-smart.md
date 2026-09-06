# Validación del modo inteligente

La suite JVM usa señales matemáticas y verifica wrap-around, pre-roll, calibración,
detección de voz, silencio de cierre, mínimo consecutivo, máximo de segmento, WAV,
queue limit y similitud coseno. La primera validación física en Pixel 8 detectó falsos
positivos del VAD que no habían aparecido en los tests sintéticos; tras añadir
calibración de 2 s, margen de 12 dB y 10 frames
consecutivos, una sesión de silencio produjo 0 detecciones y 0 `POST /process`.

En una prueba posterior, tres frases del usuario registrado produjeron detección y
envío, aunque una frase se dividió en dos segmentos por una pausa suficientemente
larga. La instrumentación observó scores `1.0000`.

La prueba con otra voz también produjo scores `1.0000` y 0 descartes. Por tanto,
`AcousticSpeakerSimilarity` basado en `[mean, energy, zero-crossing-rate]` más
coseno no discrimina hablantes en condiciones reales observadas. Es un baseline
experimental fallido/no discriminativo, no biometría ni speaker verification.
No se calculan FAR/FRR formales por el tamaño mínimo del conjunto. SMART sigue siendo
experimental y no respalda privacidad basada en identidad del hablante. El umbral
`0.75` no se modifica porque los scores medidos saturan en `1.0000`.
