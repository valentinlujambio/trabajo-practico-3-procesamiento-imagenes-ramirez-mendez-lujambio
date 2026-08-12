"""
Lectura automatica de una tirada de dados en video.

El problema no es "reconocer un dado": es decidir *cuando* mirar. Mientras los
dados ruedan, cualquier lectura es basura. El pipeline sigue el centroide de
cada dado frame a frame y recien cuando los cinco llevan varios frames sin
moverse congela ese frame y cuenta los pips de cada cara.

La vision es la de `dados.py` y `main.py` en la raiz del repo; acá se orquesta,
se cachea y se devuelve cada etapa como imagen.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api import bridge, config, imaging

router = APIRouter(prefix="/dice", tags=["dados"])

# Analizar un video implica recorrerlo frame a frame hasta encontrar el reposo:
# segundos de CPU. Como las muestras son archivos fijos, el resultado se cachea
# en memoria y la segunda visita es instantanea.
_cache: dict[str, dict] = {}
_lock = threading.Lock()


def _sample_path(sample_id: str) -> Path:
    path = bridge.VIDEOS_DIR / f"{sample_id}.mp4"
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Muestra desconocida: {sample_id}")
    return path


def _roi_strip(mask: np.ndarray, dados: list[dict]) -> np.ndarray:
    """
    Pega el recorte de cada dado sobre la mascara roja *sin cierre*, que es
    donde los pips todavia son huecos. Es la explicacion visual del conteo.
    """
    size = 150
    gap = 10
    crops = []
    for dado in dados:
        x, y, w, h = dado["bbox"]
        crop = mask[max(0, y) : y + h, max(0, x) : x + w]
        if crop.size == 0:
            continue
        crops.append(cv2.resize(crop, (size, size), interpolation=cv2.INTER_NEAREST))

    if not crops:
        return mask

    total = len(crops) * size + gap * (len(crops) + 1)
    strip = np.zeros((size + 2 * gap, total), dtype=np.uint8)
    offset = gap
    for crop in crops:
        strip[gap : gap + size, offset : offset + size] = crop
        offset += size + gap
    return strip


def _annotate(frame: np.ndarray, dados: list[dict]) -> np.ndarray:
    out = frame.copy()
    for index, dado in enumerate(dados, start=1):
        x, y, w, h = dado["bbox"]
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 3)
        cv2.putText(
            out,
            f"D{index}-{dado['valor']}",
            (x, max(16, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    return out


def _run(video_path: Path) -> dict:
    started = time.perf_counter()

    props = bridge.propiedades_video(str(video_path)) or {}
    frame_index, frame, dados_valor = bridge.buscar_dados_quietos(
        str(video_path), frames_estable=config.FRAMES_ESTABLE
    )

    if frame_index is None:
        return {
            "ms": int((time.perf_counter() - started) * 1000),
            "steps": [],
            "result": {
                "settled": False,
                "frame": None,
                "dice": [],
                "total": 0,
                "video": props,
            },
        }

    mask_dados, dados, mask_roja = bridge.segmentar_dados(frame)
    mask_abierta = bridge.mascara_roja(frame, cerrar=False)

    fps = props.get("fps") or 0
    segundo = round(frame_index / fps, 2) if fps else None

    steps = [
        imaging.step(
            "frame",
            f"Frame en reposo (#{frame_index})",
            "Ningun frame anterior sirve: mientras los dados ruedan la lectura es ruido. El seguimiento de centroides decide cuando mirar.",
            frame,
        ),
        imaging.step(
            "red-open",
            "Rojo segmentado (sin cierre)",
            "En HSV se aisla el rojo del dado con dos rangos (el matiz rojo esta partido en los extremos de la rueda) y una apertura saca las motas. Los pips quedan como huecos.",
            mask_abierta,
            fmt=".png",
        ),
        imaging.step(
            "red-closed",
            "Rojo cerrado",
            "Un cierre morfologico con nucleo eliptico tapa los pips y deja una mancha solida por dado: asi cada dado es un unico componente.",
            mask_roja,
            fmt=".png",
        ),
        imaging.step(
            "dice-mask",
            f"{len(dados)} dados aislados",
            "Componentes conexas filtradas por area: los reflejos y las manchas que no son dados quedan afuera.",
            mask_dados,
            fmt=".png",
        ),
        imaging.step(
            "pips",
            "Conteo de pips",
            "Se rellena el contorno de la cara y se le resta la mascara roja: lo unico que sobrevive son los huecos, que son los puntos. Contarlos es el valor del dado.",
            _roi_strip(mask_abierta, dados_valor),
            fmt=".png",
        ),
        imaging.step(
            "result",
            "Tirada leida",
            "Cada dado recuadrado con su valor. El video de salida arrastra estas etiquetas mientras el dado sigue en la mesa.",
            _annotate(frame, dados_valor),
        ),
    ]

    dice = [
        {
            "id": index,
            "value": int(dado["valor"]),
            "bbox": [int(v) for v in dado["bbox"]],
            "area": int(dado["area"]),
        }
        for index, dado in enumerate(dados_valor, start=1)
    ]

    return {
        "ms": int((time.perf_counter() - started) * 1000),
        "steps": steps,
        "result": {
            "settled": True,
            "frame": int(frame_index),
            "second": segundo,
            "dice": dice,
            "total": sum(item["value"] for item in dice),
            "video": props,
        },
    }


@router.get("/samples")
def list_samples() -> dict:
    """Videos de tirada disponibles, con su video ya clasificado si existe."""
    if not bridge.VIDEOS_DIR.exists():
        return {"samples": []}

    samples = []
    for path in sorted(bridge.VIDEOS_DIR.glob("*.mp4")):
        sample_id = path.stem
        rendered = bridge.SALIDAS_DIR / f"{sample_id}_clasificado.mp4"
        samples.append(
            {
                "id": sample_id,
                "label": sample_id.replace("_", " ").capitalize(),
                "note": "Tirada de cinco dados sobre la mesa.",
                "url": f"/dice/samples/{sample_id}/video",
                "resultUrl": f"/dice/samples/{sample_id}/result-video" if rendered.exists() else None,
            }
        )
    return {"samples": samples}


@router.get("/samples/{sample_id}/video")
def sample_video(sample_id: str) -> FileResponse:
    return FileResponse(_sample_path(sample_id), media_type="video/mp4")


@router.get("/samples/{sample_id}/result-video")
def result_video(sample_id: str) -> FileResponse:
    path = bridge.SALIDAS_DIR / f"{sample_id}_clasificado.mp4"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Todavia no se genero el video clasificado de {sample_id}. Usa POST /dice/samples/{sample_id}/render.",
        )
    return FileResponse(path, media_type="video/mp4")


@router.post("/samples/{sample_id}/analyze")
def analyze_sample(sample_id: str) -> dict:
    path = _sample_path(sample_id)

    with _lock:
        cached = _cache.get(sample_id)
    if cached is not None:
        return {**cached, "cached": True}

    try:
        payload = _run(path)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - se traduce a 500 con el motivo
        raise HTTPException(status_code=500, detail=f"Error en el pipeline: {exc}") from exc

    payload["sample"] = {"id": sample_id, "label": sample_id.replace("_", " ").capitalize()}
    with _lock:
        _cache[sample_id] = payload
    return {**payload, "cached": False}


@router.post("/samples/{sample_id}/render")
def render_sample(sample_id: str) -> dict:
    """
    Genera el video de salida rotulado (reusa `generar_video_salida` de main.py).
    Es caro: reescribe el video entero. Si ya existe, no lo rehace.
    """
    path = _sample_path(sample_id)
    bridge.SALIDAS_DIR.mkdir(parents=True, exist_ok=True)
    salida = bridge.SALIDAS_DIR / f"{sample_id}_clasificado.mp4"

    if salida.exists():
        return {"generated": False, "url": f"/dice/samples/{sample_id}/result-video"}

    _, _, dados_valor = bridge.buscar_dados_quietos(
        str(path), frames_estable=config.FRAMES_ESTABLE
    )
    if not dados_valor:
        raise HTTPException(status_code=422, detail="No se detectaron los 5 dados quietos")

    for index, dado in enumerate(dados_valor, start=1):
        dado["id"] = index

    bridge.generar_video_salida(str(path), str(salida), dados_valor)
    return {"generated": True, "url": f"/dice/samples/{sample_id}/result-video"}
