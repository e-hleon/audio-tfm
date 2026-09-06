# Checklist para la siguiente sesión

- PR #5: revisar diff y GitHub Actions; mergear solo si procede.
- PR #6: ejecutar ASR GPU base/small y benchmark OpenAI; revisar JSON, tablas y figuras.
- PR avanzado: comprobar que el stacked diff es correcto y revisar CI Android.
- Ejecutar emulador o Pixel: instalar APK, pedir permiso, capturar manual y comprobar `/process`.
- Probar Histórico: vacío, detalle, error, retry y datos reales.
- Probar Día: fecha, interacciones, `missing`, POST generar, `ready`, cambio a `stale`.
- Probar continuo: Activity oculta, notificación persistente, STOP de UI/notificación, chunks consecutivos, `recorded_at`, subida Wi-Fi y archivo pendiente ante fallo.
- Smart físico ya validado de forma limitada en Pixel 8: silencio, voz propia y otra voz; el VAD mejorado funcionó en la prueba y el speaker baseline fue no discriminativo. Queda ampliar, si se necesita para la memoria, un corpus consentido para métricas VAD; no usar SMART como seguridad.
- No calcular FAR/FRR formales a partir de la prueba mínima actual.
- Medir batería en escenarios manual/continuo/smart con duración, brillo y red constantes mediante batterystats/Perfetto.
