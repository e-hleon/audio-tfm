# Rendimiento medido

## ASR fallback SLR61

El corpus FLEURS `es_419` quedó bloqueado durante la descarga del dataset. Como
fallback separado se midieron 100 mensajes meteorológicos SLR61, CC BY-SA 4.0,
con RTX 3050 4 GiB, CUDA e `int8_float16`. No representa conversación espontánea
ni sustituye metodológicamente a FLEURS.

| Modelo | N | WER | CER | latencia media | latencia p95 | RTF medio | fallos |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 100 | 0.3315 | 0.2880 | 0.211 s | 0.260 s | 0.0642 | 0 |
| small | 100 | 0.2166 | 0.2540 | 0.388 s | 0.439 s | 0.1187 | 0 |

Warmup y carga se registraron aparte. En 20 muestras fijas y tres pasadas, la
media de latencia de `base` fue 0.209, 0.225 y 0.211 s; para `small`, 0.408,
0.411 y 0.389 s.

Backend: la suite integrada obtuvo 64 tests correctos. E2E ASR/OpenAI real y
latencia `/process` no están medidos en esta sesión. Android y batería tampoco.
