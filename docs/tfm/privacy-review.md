# Revisión de privacidad

- El permiso usado es `RECORD_AUDIO`; el servicio declara únicamente tipo
  `microphone` y solo arranca por acción explícita.
- La captura continua/inteligente muestra notificación persistente y acción STOP.
- Manual conserva M4A temporal; continuo escribe WAV en `cacheDir` y borra tras
  éxito. Los segmentos rechazados del selector no se guardan.
- El enrollment guarda solo tres características en preferencias privadas. La
  plantilla no sale del dispositivo, no se usa para identificar terceros y no es
  autenticación.
- `/process` envía audio al backend; el backend envía únicamente la transcripción
  al proveedor LLM, con `store=false`. Las notificaciones no incluyen texto privado.
- El backend sigue ligado a loopback por defecto; LAN es una configuración explícita
  para red confiable y no se ha añadido autenticación.
- No hay claves, grabaciones personales ni modelos grandes versionados.
