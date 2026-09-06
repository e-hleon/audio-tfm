# Threat model ligero

| Activo | Amenaza | Mitigación actual | Riesgo residual |
|---|---|---|---|
| Audio | otra app, pérdida del dispositivo, grabación no intencionada | `cacheDir`, acción explícita, notificación FGS, borrado tras éxito | sin cifrado at-rest ni autenticación completa |
| Transcripción | logs o proveedor externo | no se envía audio; no se registran textos | el texto puede salir al LLM configurado |
| Análisis/resumen | exposición en DB o API | backend local, errores sin contenido | puerto y DB requieren despliegue seguro fuera del prototipo |
| Plantilla acústica | acceso a preferencias privadas | tres rasgos acústicos, almacenamiento privado | no es biometría robusta ni protección criptográfica |
| API key | logs o repositorio | `.env`, no se imprime ni versiona | gestión de secretos del host queda fuera de alcance |
| Propuesta duplicada | retry tras respuesta HTTP perdida | `capture_chunk_id` UNIQUE y devolución del resultado existente | carrera entre procesamiento y respuesta requiere validación física |
| Idea cortada | chunk técnico divide una frase | pausa acústica desde 25 s y hard cap explicable | VAD energético no entiende lenguaje; análisis de sesión pendiente |
| LAN/Internet | interceptación o servicio expuesto | Compose publica loopback por defecto | cambiar el bind sin TLS expone tráfico |

`store=false` reduce el estado de la respuesta, pero no equivale a retención
cero. Los controles de datos del proveedor son una configuración separada.
