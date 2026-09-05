# ADR 007: selector inteligente experimental

El modo inteligente aplica primero un VAD energético adaptativo a frames de 20 ms,
con hysteresis, mínimo de voz, cierre tras silencio, pre-roll de 1 s y máximo de
45 s. Solo a segmentos con voz se aplica una plantilla acústica local de tres
características y similitud coseno. La regla de envío es `voz AND score >= 0.75`.

La plantilla se obtiene mediante enrollment explícito de cuatro segundos y se guarda
como tres valores en preferencias privadas. No se conserva el audio de enrollment,
no se envía a OpenAI y no es autenticación ni identificación de terceros. Es una
baseline integrable y defendible, pero sensible a ruido y micrófonos; el umbral
necesita calibración con audios consentidos.
