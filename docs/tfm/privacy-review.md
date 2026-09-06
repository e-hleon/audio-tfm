# Revisión de privacidad

| Permiso | Motivo | Modo | Consecuencia |
|---|---|---|---|
| `RECORD_AUDIO` | Capturar voz | manual, continuous, smart, enrollment | Puede registrar a quien esté cerca; requiere consentimiento. |
| `FOREGROUND_SERVICE` | Ejecutar captura visible | continuous, smart | La sesión puede continuar al salir de Activity; hay notificación y STOP. |
| `FOREGROUND_SERVICE_MICROPHONE` | Tipo específico Android 14+ | continuous, smart | Android controla el acceso al micrófono del servicio. |
| `POST_NOTIFICATIONS` | Mostrar notificación Android 13+ | continuous, smart | Si se deniega, la UI no inicia esos modos. |

No se solicitan permisos de almacenamiento. M4A/WAV y plantilla quedan en almacenamiento privado/cache; el éxito elimina audio manual y los segmentos enviados. ASR procesa localmente. Solo texto/proyección derivada puede salir al proveedor LLM; no se envían audio, filename ni template speaker. `store=false` reduce estado persistido de la respuesta, pero no promete retención cero. La revisión física debe comprobar ficheros y consentimiento de terceros.
