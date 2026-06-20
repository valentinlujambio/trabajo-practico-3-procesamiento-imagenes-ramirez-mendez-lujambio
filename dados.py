"""
TP3 - Cinco dados
Punto A (parte espacial): máscara binaria de los 5 dados en un frame.
"""
import cv2
import numpy as np
import matplotlib.pyplot as plt
from help_show import imshow


def segmentar_dados(frame_bgr, area_min=2000, area_max=15000):
    """
    Devuelve la máscara binaria con los dados de un frame y la lista de
    dados detectados (bbox, área, centroide).

    Los dados son rojos sobre fondo verde/turquesa, así que el color es el
    discriminador (U5). Se limpia con morfología (U6) y se separan los objetos
    con componentes conexas, filtrando por área (U7) para quedarnos solo con
    blobs del tamaño de un dado: descartamos la mano (área > area_max) y el
    ruido (área < area_min).
    """
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    # El rojo "envuelve" el círculo de Hue: se segmenta con dos rangos
    # (cerca de 0 y cerca de 180). S y V mínimos evitan sombras y zonas pálidas.
    rojo_bajo = cv2.inRange(hsv, (0, 80, 60), (10, 255, 255))
    rojo_alto = cv2.inRange(hsv, (170, 80, 60), (179, 255, 255))
    mask_roja = cv2.bitwise_or(rojo_bajo, rojo_alto)

    # Apertura: saca motas. Cierre: rellena los huecos que dejan los pips
    # blancos dentro del dado. Kernel elíptico por la forma redondeada (U6).
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_roja = cv2.morphologyEx(mask_roja, cv2.MORPH_OPEN, k)
    mask_roja = cv2.morphologyEx(mask_roja, cv2.MORPH_CLOSE, k)

    # Componentes conexas + filtrado por área (U7)
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(
        mask_roja, connectivity=8)

    dados = []
    mask_dados = np.zeros_like(mask_roja)
    for i in range(1, num):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < area_min or area > area_max:
            continue
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        dados.append({
            'bbox': (x, y, w, h),
            'area': int(area),
            'centroid': (float(centroids[i, 0]), float(centroids[i, 1])),
        })
        mask_dados[labels == i] = 255

    return mask_dados, dados, mask_roja


def mascaras_por_frame(video_path):
    """
    Recorre el video en streaming y entrega, por cada frame, la máscara
    binaria de los 5 dados (yield). No acumula nada: memoria acotada.

    Devuelve por iteración: (idx, frame_bgr, mask_dados)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video_path}")

    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        mask_dados, _, _ = segmentar_dados(frame)
        yield idx, frame, mask_dados
        idx += 1

    cap.release()



if __name__ == "__main__":
    VIDEO = 'videos/tirada_1.mp4'

    prev = None
    for idx, frame, mask in mascaras_por_frame(VIDEO):
        if prev is not None:
            # Resta entre máscaras consecutivas: píxeles que cambiaron
            diff = cv2.absdiff(mask, prev)
            cambios = int(np.count_nonzero(diff))
        else:
            cambios = -1  # primer frame, no hay anterior

        n_dados = int(np.count_nonzero(mask) > 0)  # placeholder rápido
        print(f"frame {idx:4d} | pixeles_cambiados={cambios:7d}")

        prev = mask