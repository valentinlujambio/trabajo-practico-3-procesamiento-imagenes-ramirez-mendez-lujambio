# 🎲 Cinco dados — detección y conteo en video

> Tirás cinco dados, el programa espera a que se queden quietos, **encuentra cada
> uno y lee su valor**, y te devuelve el mismo video con cada dado recuadrado y
> rotulado con su número.

<p align="center">
  <img src="assets/demo.gif" alt="Demo: dados recuadrados y rotulados en el video de salida" width="320">
</p>

Todo está hecho con **procesamiento de imágenes clásico** (OpenCV + NumPy): nada
de redes neuronales ni modelos entrenados. Solo color, morfología y componentes
conexas.

---

## La idea en 3 pasos

<p align="center">
  <img src="assets/pipeline.jpg" alt="Pipeline: frame original, máscara roja y detección con valores" width="900">
</p>

1. **Buscar el rojo.** Pasamos el frame a HSV y nos quedamos solo con los píxeles
   rojos del dado. Una limpieza morfológica (apertura + cierre) borra el ruido y
   tapa los puntitos para obtener una mancha sólida por dado.
2. **Separar los dados.** Con *componentes conexas* aislamos cada mancha y la
   filtramos por área, así descartamos reflejos o manchas que no son dados.
   Cuando aparecen 5 manchas válidas, tenemos los 5 dados.
3. **Leer cada cara.** Recortamos cada dado y contamos sus **pips** (los puntos).

## ¿Cuándo están "quietos"?

Los dados se cuentan recién cuando dejan de rodar. Para eso seguimos el
**centroide** de cada dado frame a frame: si un dado se mueve menos de unos pocos
píxeles, le sumamos uno a su contador de "frames quieto"; si se mueve, se
reinicia. Cuando **los 5** llevan varios frames sin moverse, recién ahí leemos
los valores.

> Es un seguimiento por cercanía: cada dado del frame nuevo se empareja con el
> más próximo del frame anterior. Simple y suficiente para esta escena.

## Contar los puntos

<p align="center">
  <img src="assets/pips.jpg" alt="Conteo de pips: cara del dado y puntos detectados" width="420">
</p>

Acá hay un truco lindo: si rellenamos el contorno de la cara del dado y le
**restamos** la máscara roja, lo único que queda son los huecos… que son
justamente los pips. Contamos esos huecos y ese es el valor del dado.

---

## Cómo correrlo

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

El programa recorre todos los `.mp4` de la carpeta [`videos/`](videos/) y deja
los videos clasificados en [`salidas/`](salidas/), uno por tirada.

## API HTTP (`api/`)

La solución también está expuesta como **microservicio FastAPI**, para poder
consumirla desde otra aplicación en vez de correr el script.

El código de visión **no se modificó**: `api/bridge.py` agrega la raíz al
`sys.path`, fija el backend `Agg` de matplotlib (en un servidor no hay display)
y reexporta las funciones de `dados.py` y `main.py`. Los endpoints solo orquestan
y serializan.

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8002
# docs interactivas en http://localhost:8002/docs
```

| Método | Endpoint | Qué hace |
|---|---|---|
| `GET` | `/health` | Health check. |
| `GET` | `/dice/samples` | Videos de tirada disponibles. |
| `GET` | `/dice/samples/{id}/video` | El video de entrada. |
| `GET` | `/dice/samples/{id}/result-video` | El video ya rotulado, si fue generado. |
| `POST` | `/dice/samples/{id}/analyze` | Busca el reposo, cuenta los pips y devuelve el paso a paso. |
| `POST` | `/dice/samples/{id}/render` | Genera el video de salida rotulado (caro: reescribe el video entero). |

Analizar recorre el video frame a frame hasta encontrar el reposo, así que la
primera llamada tarda unos segundos; como las muestras son archivos fijos, el
resultado queda cacheado en memoria (`"cached": true` en la respuesta).

```jsonc
{
  "sample": { "id": "tirada_4", "label": "Tirada 4" },
  "ms": 5696,
  "steps": [{ "id": "pips", "title": "…", "caption": "…", "image": "data:image/png;base64,…" }],
  "result": {
    "settled": true, "frame": 61, "second": 2.03, "total": 13,
    "dice": [{ "id": 1, "value": 2, "bbox": [136, 427, 80, 84] }]
  }
}
```

### Variables de entorno

Ver `.env.example`. La relevante es **`CORS_ORIGINS`**: lista de orígenes
autorizados a consumir la API desde el navegador, separada por comas o en JSON.
Se normaliza sin barra final (el navegador manda el header `Origin` sin barra).
Si queda vacía, no se habilita ningún origen cruzado.

## Estructura

| Archivo | Qué hace |
|---|---|
| [`dados.py`](dados.py) | Toda la visión: máscara roja, componentes conexas, seguimiento de centroides y conteo de pips. |
| [`main.py`](main.py) | Orquesta el recorrido de los videos y arma el video de salida. |
| `api/` | Microservicio FastAPI sobre lo anterior: `main.py` (app y CORS), `bridge.py` (reexporta sin tocar el código), `imaging.py`, `routes/dice.py`. |
| `videos/` · `salidas/` | Entradas y resultados. |

---

<sub>Trabajo Práctico 3 — Procesamiento de Imágenes I · TUIA (UNR / FCEIA). El
informe completo está en <code>Informe TP3.pdf</code>.</sub>
