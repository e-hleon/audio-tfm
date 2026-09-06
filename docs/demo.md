# Demo reproducible

1. Instalar Docker/Compose, Python para utilidades y Android Studio/SDK si se prueba Android.
2. Copiar `.env.example` a `.env` y completar valores localmente; nunca versionar la clave.
3. Ejecutar `docker compose up -d`, luego `docker compose exec api alembic upgrade head`.
4. Comprobar `curl http://127.0.0.1:8000/health`.
5. Enviar un audio público de prueba: `curl -F file=@sample.wav -F recorded_at=2026-09-05T10:00:00Z http://127.0.0.1:8000/process`.
6. Consultar el `interaction_id` con `curl http://127.0.0.1:8000/interactions/<id>`.
7. Consultar el día: `curl http://127.0.0.1:8000/days/2026-09-05`.
8. Generar resumen solo explícitamente: `curl -X POST http://127.0.0.1:8000/days/2026-09-05/summary`.
9. Para Android, usar la IP LAN, instalar el APK debug, conceder micrófono/notificaciones y seguir el plan físico.
10. Al terminar, borrar el audio de prueba local y apagar Compose con `docker compose down`.
