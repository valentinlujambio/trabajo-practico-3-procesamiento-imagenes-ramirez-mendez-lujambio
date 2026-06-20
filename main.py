"""
TP3 - Cinco dados.

Punto de entrada: procesa cada video de la carpeta `videos/`, detecta el
momento en que los 5 dados quedan quietos, cuenta el valor de cada cara y
genera un video de salida con cada dado recuadrado y rotulado con su número.

Toda la visión por computadora vive en `dados.py`; acá solo se orquesta el
recorrido de los videos y el armado del video de salida.
"""
import os
import cv2

from dados import segmentar_dados, contar_pips, SeguimientoCentroides

# Frames consecutivos sin moverse para dar un dado por "quieto".
FRAMES_ESTABLE = 15


def propiedades_video(video_path):
    """Devuelve FPS, cantidad de frames y resolución del video."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    props = {
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    cap.release()
    return props


def buscar_dados_quietos(video_path, frames_estable=FRAMES_ESTABLE):
    """
    Recorre el video hasta que los 5 dados quedan quietos.
    """
    tracker = SeguimientoCentroides(umbral_px=8, radio_max=40)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video_path}")

    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        _, dados, _ = segmentar_dados(frame)
        dados_con_estado = tracker.actualizar(dados)

        estables = [d for d in dados_con_estado
                    if d['frames_quieto'] >= frames_estable]
        if len(dados_con_estado) == 5 and len(estables) == 5:
            cap.release()
            dados_valor = contar_pips(frame, dados)
            return idx, frame.copy(), dados_valor

        idx += 1

    cap.release()
    return None, None, None


def _dado_presente(dado_ref, dados_actuales, radio_max=40):
    """
    Devuelve el dado del frame actual que coincide con `dado_ref` (mismo lugar),
    o None si en este frame ese dado ya no está (lo levantó la mano).
    """
    cx, cy = dado_ref['centroid']
    mejor, mejor_d = None, radio_max
    for d in dados_actuales:
        ax, ay = d['centroid']
        dist = ((cx - ax) ** 2 + (cy - ay) ** 2) ** 0.5
        if dist < mejor_d:
            mejor_d = dist
            mejor = d
    return mejor


def generar_video_salida(video_path, salida_path, dados_ref):
    """
    Reescribe el video rotulando cada dado mientras está en reposo.
    """
    props = propiedades_video(video_path)
    cap = cv2.VideoCapture(video_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(salida_path, fourcc, props["fps"],
                          (props["width"], props["height"]))

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        _, dados_actuales, _ = segmentar_dados(frame)
        for ref in dados_ref:
            actual = _dado_presente(ref, dados_actuales)
            if actual is None:
                continue                      # dado ausente -> sin recuadro
            x, y, w, h = actual['bbox']
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(frame, f"D{ref['id']}-{ref['valor']}", (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        out.write(frame)

    cap.release()
    out.release()


def procesar_video(video_path, carpeta_salida="salidas"):
    """Pipeline completo para un video: detectar, contar y generar salida."""
    nombre = os.path.splitext(os.path.basename(video_path))[0]

    idx_quieto, _, dados_valor = buscar_dados_quietos(video_path)
    if idx_quieto is None:
        print(f"[{nombre}] No se detectaron los 5 dados quietos.")
        return

    # Id único por dado (D1..D5) en el orden en que se detectaron.
    for i, d in enumerate(dados_valor, start=1):
        d['id'] = i

    etiquetas = [f"D{d['id']}-{d['valor']}" for d in dados_valor]
    print(f"[{nombre}] dados quietos en frame {idx_quieto} -> {etiquetas}")

    os.makedirs(carpeta_salida, exist_ok=True)
    salida = os.path.join(carpeta_salida, f"{nombre}_clasificado.mp4")
    generar_video_salida(video_path, salida, dados_valor)
    print(f"[{nombre}] video de salida: {salida}")


def procesar_videos(directorio_videos="videos"):
    videos = [f for f in os.listdir(directorio_videos) if f.endswith(".mp4")]
    for video in sorted(videos):
        procesar_video(os.path.join(directorio_videos, video))


if __name__ == "__main__":
    procesar_videos()
