# Validación del modo inteligente

La implementación y los tests usan señales matemáticas, no conversaciones reales.
Se verifican wrap-around, pre-roll, detección de voz, silencio de cierre, máximo de
segmento, WAV, queue limit y similitud coseno. No se han medido VAD precision/recall,
FAR, FRR, batería ni accuracy de speaker: no hay audios consentidos ni dispositivo
disponible en este entorno. El selector debe considerarse experimental.
