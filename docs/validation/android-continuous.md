# Validación de captura continua

`SmartAudioTest` cubre ring buffer, header WAV, VAD, plantilla, cola y segmentación
con PCM sintético. `BackendTest` cubre health, histórico, día, generación explícita
y errores HTTP. CI compila `testDebugUnitTest`, `lintDebug`, `assembleDebug` y
`compileDebugAndroidTestKotlin`.

No se afirma prueba de micrófono, duración real, notificación, stop desde
notificación, continuidad con Activity oculta ni subida por Wi-Fi. Requiere emulador
o dispositivo Android y queda en `docs/tfm/remaining-validation.md`.
