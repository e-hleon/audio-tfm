# 003 — Fundación de persistencia con PostgreSQL

## Problema

El MVP procesa audio y devuelve JSON, pero pierde el resultado al terminar la
petición. El siguiente paso necesita conservar interacciones y preparar resúmenes
diarios sin introducir todavía colas ni trabajadores.

## Decisión

Usar PostgreSQL 16 en Docker Compose, SQLAlchemy 2.x síncrono, psycopg 3 y Alembic.
Las tablas iniciales son `interactions` y `daily_summaries`. El `AnalysisResult`
completo se almacena en JSONB porque mantiene el contrato y permite evolucionarlo sin
crear tablas hijas para decisiones, tareas y recordatorios.

Los timestamps se guardan como `TIMESTAMP WITH TIME ZONE` y se normalizan a UTC.
`recorded_at` representa cuándo ocurrió la interacción; `created_at` cuándo se
persistió. `APP_TIMEZONE` (UTC por defecto) solo determina el día local y no cambia
el instante almacenado.

Alembic gestiona las migraciones desde una base vacía. El volumen `postgres_data`
persiste los datos aunque el contenedor PostgreSQL se elimine y se cree de nuevo; el
contenedor es efímero, el volumen no lo es.

## Alternativas descartadas

- SQLite: no representa el PostgreSQL real ni sus tipos JSONB y timestamptz.
- Crear tablas con `Base.metadata.create_all()`: no ofrece historial reproducible de
  cambios.
- Redis, RQ o workers: el bloque aún no procesa trabajos en segundo plano.
- Normalizar cada elemento del análisis: añade relaciones y migraciones sin una
  consulta que lo justifique.

## Consecuencias

La persistencia requiere PostgreSQL disponible y una migración aplicada. Los
repositorios no contienen lógica HTTP y dejan la transacción bajo control del
servicio que los invoque. Este bloque no integra todavía `/process`, no guarda audio
y no genera resúmenes mediante un LLM.
