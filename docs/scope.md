# Alcance del TFM

## Idea

El proyecto consiste en una plataforma local-first para generar un diario personal
a partir de grabaciones de interacciones de voz.

El usuario podrá registrar conversaciones o notas de voz desde un dispositivo
Android. Las grabaciones se enviarán a un backend que realizará la transcripción
automática y el análisis semántico para generar información estructurada del día.

El resultado podrá incluir:

- transcripción;
- resumen de la interacción;
- temas tratados;
- decisiones;
- tareas;
- recordatorios;
- cronología y resumen diario.

## Objetivo principal

Diseñar, implementar y evaluar una plataforma modular para la captura y
procesamiento de interacciones de voz utilizando reconocimiento automático del
habla y modelos de lenguaje, prestando especial atención a la privacidad,
minimización de datos y reproducibilidad del sistema.

## Modos de captura

La aplicación Android se diseñará para soportar tres políticas de captura.

### Manual

El usuario inicia y detiene explícitamente una grabación.

Es el modo prioritario y debe funcionar en el MVP.

### Continuo

El usuario inicia explícitamente una sesión durante la que se conserva todo el
audio hasta que la detiene.

La interfaz deberá advertir claramente de las implicaciones de privacidad.

### Inteligente / selectivo

Modo experimental.

El dispositivo mantiene un pequeño buffer circular de audio y utiliza
procesamiento local para detectar actividad de voz y determinar si aparece la voz
del usuario.

Los segmentos que no sean relevantes deberán descartarse localmente.

Este modo no debe bloquear la finalización del TFM si su precisión o coste
computacional no resultan adecuados.

## Procesamiento

Pipeline previsto:

1. captura de audio;
2. envío al backend;
3. almacenamiento temporal;
4. procesamiento asíncrono;
5. transcripción local mediante ASR;
6. análisis de la transcripción mediante un proveedor LLM;
7. extracción de información estructurada;
8. persistencia;
9. generación de la cronología diaria.

## Privacidad

El diseño seguirá un enfoque local-first.

La transcripción de audio se realizará localmente siempre que sea posible.

El análisis mediante LLM podrá utilizar un proveedor externo. Si se utiliza,
la aplicación deberá informar de que el contenido textual será enviado a dicho
proveedor.

El proveedor de LLM deberá estar desacoplado del resto del sistema para permitir
sustituirlo en el futuro por un modelo local.

No se utilizarán grabaciones de terceros sin conocimiento de los participantes
para evaluar el TFM.

## Fuera del alcance obligatorio

No son requisitos para finalizar el TFM:

- Kubernetes;
- despliegue distribuido;
- alta disponibilidad;
- múltiples usuarios;
- reconocimiento de identidad de todos los interlocutores;
- entrenamiento de modelos propios;
- almacenamiento S3/MinIO;
- Traefik;
- RabbitMQ.

Pueden estudiarse como trabajo futuro si aportan valor.

## Prioridades

### MVP

- recibir una grabación;
- transcribirla;
- analizar la transcripción;
- guardar el resultado;
- consultar el resultado.

### Segunda fase

- procesamiento asíncrono;
- cronología y resumen diario;
- aplicación Android con captura manual;
- pruebas automatizadas.

### Tercera fase

- captura continua;
- modo inteligente con VAD y verificación de hablante;
- evaluación de consumo energético y precisión;
- alternativas de procesamiento local del LLM.
