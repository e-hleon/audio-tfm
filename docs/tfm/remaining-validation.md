# Checklist para la siguiente sesión

- PR #5: revisar diff y GitHub Actions; mergear solo si procede.
- PR #6: ejecutar ASR GPU base/small y benchmark OpenAI; revisar JSON, tablas y figuras.
- PR avanzado: comprobar que el stacked diff es correcto y revisar CI Android.
- Ejecutar emulador o Pixel: instalar APK, pedir permiso, capturar manual y comprobar `/process`.
- Probar Histórico: vacío, detalle, error, retry y datos reales.
- Probar Día: fecha, interacciones, `missing`, POST generar, `ready`, cambio a `stale`.
- Probar continuo: Activity oculta, notificación persistente, STOP de UI/notificación, chunks consecutivos, `recorded_at`, subida Wi-Fi y archivo pendiente ante fallo.
- Probar smart: enrollment, reemplazo/eliminación, silencio, voz, pre-roll, rechazo/aceptación y fallback sin plantilla.
- Medir con audios consentidos VAD precision/recall/F1 y speaker FAR/FRR; no usarlo como seguridad.
- Medir batería en escenarios manual/continuo/smart con duración, brillo y red constantes mediante batterystats/Perfetto.
