"""
Microservicio HTTP sobre la solucion del repo.

El TP se corre como script y deja los videos en `salidas/`. Esta capa lo deja
consumible desde cualquier cliente: el codigo de vision no se toca (ver
`api/bridge.py`), acá solo se expone como endpoints, se sirven los videos de
ejemplo y se devuelve cada etapa del procesamiento como imagen.

    uvicorn api.main:app --reload --port 8002
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import config
from api.routes.dice import router as dice_router

app = FastAPI(
    title="pdi-tp3-api",
    version="1.0.0",
    description="Deteccion, seguimiento y conteo de dados en video.",
)

# Lista blanca por env (CORS_ORIGINS). Vacia = ningun origen cruzado, que es
# preferible a abrir `*` sin querer en produccion.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dice_router)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "service": "pdi-tp3-api"}


def run() -> None:
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=config.PORT, reload=False)


if __name__ == "__main__":
    run()
