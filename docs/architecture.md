# Arquitectura inicial

## Principios

La arquitectura debe ser:

- sencilla;
- modular;
- reproducible;
- local-first;
- fácil de probar;
- comprensible para el autor del TFM.

No se introducirán componentes cuya utilidad no esté justificada por un requisito
real del proyecto.

## Componentes previstos

### Cliente Android

Responsable de:

- capturar audio;
- seleccionar el modo de captura;
- enviar grabaciones;
- consultar resultados.

El procesamiento del modo inteligente deberá realizarse localmente en el
dispositivo antes de enviar audio al backend.

### API

Backend HTTP desarrollado inicialmente con FastAPI.

Responsable de:

- recibir grabaciones;
- crear trabajos de procesamiento;
- consultar su estado;
- devolver transcripciones y análisis;
- consultar la información diaria.

### Worker

Proceso separado encargado de operaciones costosas:

- procesamiento de audio;
- transcripción;
- análisis mediante LLM.

Separarlo de la API evita mantener peticiones HTTP abiertas durante procesos
largos.

### Cola

Se estudiará inicialmente Redis + RQ por su simplicidad.

Su función será desacoplar la recepción de una grabación de su procesamiento.

No se utilizará una tecnología más compleja salvo que aparezca un requisito que
la justifique.

### Base de datos

PostgreSQL almacenará los metadatos, transcripciones y resultados del análisis.

Los archivos de audio se almacenarán inicialmente en un volumen/directorio local.
No se utilizará almacenamiento de objetos mientras no exista una necesidad real.

### ASR

Se utilizará inicialmente faster-whisper para realizar transcripción local.

El modelo concreto se elegirá mediante pruebas teniendo en cuenta calidad,
velocidad y los recursos disponibles.

### LLM

El análisis semántico se realizará mediante una interfaz de proveedor.

Ejemplo conceptual:

LLMProvider
  - OpenAIProvider
  - LocalProvider (opcional)

El proveedor externo podrá utilizarse inicialmente para obtener buenos resultados
sin exigir la ejecución local de un modelo grande.

## Despliegue

La infraestructura del backend se definirá mediante Docker Compose.

Configuración prevista:

- API;
- worker;
- Redis;
- PostgreSQL.

No se utilizará Kubernetes en el alcance inicial.

## Flujo

Android
  |
  | audio
  v
API
  |
  | job
  v
Redis/RQ
  |
  v
Worker
  |
  +--> ASR local
  |
  +--> LLM provider
  |
  v
PostgreSQL
  |
  v
API
  |
  v
Android / interfaz de consulta

## Evolución

Esta arquitectura es inicial.

Las decisiones podrán cambiar si las pruebas muestran que una alternativa es
claramente más sencilla o adecuada.

Todo cambio arquitectónico significativo deberá documentar:

1. problema encontrado;
2. alternativas consideradas;
3. decisión adoptada;
4. consecuencias.
