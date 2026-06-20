"""
TP3 - Cinco dados
Punto A (parte espacial): máscara binaria de los 5 dados en un frame.
"""
import cv2
import numpy as np
import matplotlib.pyplot as plt
from help_show import imshow


def mascara_roja(frame_bgr, cerrar=True):
    """
    Segmenta el rojo del dado en HSV (U5) y lo limpia con morfología.
    """
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    rojo_bajo = cv2.inRange(hsv, (0, 80, 60), (10, 255, 255))
    rojo_alto = cv2.inRange(hsv, (170, 80, 60), (179, 255, 255))
    mask_roja = cv2.bitwise_or(rojo_bajo, rojo_alto)

    # Kernel elíptico por la forma redondeada del dado (U6).
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_roja = cv2.morphologyEx(mask_roja, cv2.MORPH_OPEN, k)   # saca motas
    if cerrar:
        mask_roja = cv2.morphologyEx(mask_roja, cv2.MORPH_CLOSE, k)  # rellena pips
    return mask_roja


def segmentar_dados(frame_bgr, area_min=2000, area_max=15000):
    """
    Devuelve la máscara binaria con los dados de un frame y la lista de
    dados detectados (bbox, área, centroide).
    """
    mask_roja = mascara_roja(frame_bgr, cerrar=True)

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



def _distancia(c1, c2):
    """Distancia euclidiana entre dos centroides (cx, cy)."""
    return ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2) ** 0.5


def emparejar_dados(prev_dados, curr_dados, radio_max=40):
    """
    Empareja cada dado del frame actual con el más cercano del frame anterior,
    siempre que estén a menos de `radio_max` píxeles.
    """
    emparejados = []
    usados = set()
    for dado in curr_dados:
        mejor_dist = None
        mejor_idx = None
        for j, prev in enumerate(prev_dados):
            if j in usados:
                continue
            d = _distancia(dado['centroid'], prev['centroid'])
            if d < radio_max and (mejor_dist is None or d < mejor_dist):
                mejor_dist = d
                mejor_idx = j
        if mejor_idx is not None:
            usados.add(mejor_idx)
            emparejados.append((dado, mejor_dist))
        else:
            emparejados.append((dado, None))   # dado nuevo / no encontrado
    return emparejados


class SeguimientoCentroides:
    """
    Acumula cuántos frames consecutivos lleva cada dado sin moverse.

    Internamente mantiene una lista de 'tracks': cada uno guarda el
    centroide del dado y su contador de frames quieto.
    """

    def __init__(self, umbral_px=8, radio_max=40):
        self.umbral_px = umbral_px   # movimiento máximo para considerarlo quieto
        self.radio_max = radio_max   # radio de emparejamiento entre frames
        self._tracks = []            # [{centroid, frames_quieto}]

    def actualizar(self, dados_actuales):
        """
        Recibe la lista de dados del frame actual y actualiza los tracks.
        Devuelve la misma lista con el campo 'frames_quieto' añadido a cada dado.
        """
        emparejados = emparejar_dados(self._tracks, dados_actuales, self.radio_max)

        nuevos_tracks = []
        resultado = []
        for dado, dist in emparejados:
            if dist is None:
                # Dado nuevo: arranca en 0 frames quieto
                frames_quieto = 0
            elif dist <= self.umbral_px:
                # Se movió poco: buscar el track correspondiente y sumarle 1
                # (reusar el centroide viejo para no acumular drift)
                track = self._encontrar_track(dado['centroid'])
                frames_quieto = (track['frames_quieto'] + 1) if track else 1
            else:
                # Se movió más del umbral: reiniciar contador
                frames_quieto = 0

            nuevos_tracks.append({
                'centroid': dado['centroid'],
                'frames_quieto': frames_quieto,
            })
            resultado.append({**dado, 'frames_quieto': frames_quieto})

        self._tracks = nuevos_tracks
        return resultado

    def _encontrar_track(self, centroid):
        mejor, mejor_d = None, float('inf')
        for t in self._tracks:
            d = _distancia(t['centroid'], centroid)
            if d < mejor_d:
                mejor_d = d
                mejor = t
        return mejor if mejor_d < self.radio_max else None


def contar_pips(frame_bgr, dados, pip_area_min=20):
    """
    Cuenta los puntos (pips) de la cara de cada dado y devuelve la lista de
    dados con el campo 'valor' agregado.
    """
    # Apertura SIN cierre: así los pips siguen siendo huecos en el rojo.
    rojo = mascara_roja(frame_bgr, cerrar=False)
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    resultado = []
    for d in dados:
        x, y, w, h = d['bbox']
        roi = rojo[y:y + h, x:x + w]

        # Relleno la cara del dado (contorno externo) para luego restar el rojo.
        contornos, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        cara_llena = np.zeros_like(roi)
        cv2.drawContours(cara_llena, contornos, -1, 255, thickness=-1)

        pips = cv2.subtract(cara_llena, roi)            # huecos = pips
        pips = cv2.morphologyEx(pips, cv2.MORPH_OPEN, k3)

        num, _, stats, _ = cv2.connectedComponentsWithStats(pips, connectivity=8)
        valor = sum(1 for i in range(1, num)
                    if stats[i, cv2.CC_STAT_AREA] >= pip_area_min)
        resultado.append({**d, 'valor': valor})
    return resultado


if __name__ == "__main__":
    VIDEO = 'videos/tirada_1.mp4'

    FRAMES_ESTABLE = 15 # cuantos frames esperamos que el dado no se mueva

    tracker = SeguimientoCentroides(umbral_px=8, radio_max=40)
    prev_dados = []

    cap = cv2.VideoCapture(VIDEO)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir {VIDEO}")

    frame_quieto = None       # primer frame con los 5 dados quietos
    dados_quietos = None
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        mask_dados, dados, _ = segmentar_dados(frame)
        dados_con_estado = tracker.actualizar(dados)

        # Los 5 dados quietos = hay 5 dados y todos superan el umbral de frames
        estables = [d for d in dados_con_estado
                    if d['frames_quieto'] >= FRAMES_ESTABLE]
        if len(dados_con_estado) == 5 and len(estables) == 5:
            frame_quieto = frame.copy()       # me guardo el frame para la cara
            dados_quietos = dados
            print(f"Dados quietos en el frame {idx}")
            break                             # ya tengo el frame, corto la búsqueda

        prev_dados = dados
        idx += 1

    cap.release()

    if frame_quieto is None:
        print("No se detectaron los 5 dados quietos en el video.")
    else:
        # Cuento los pips de cada dado sobre el frame quieto
        dados_valor = contar_pips(frame_quieto, dados_quietos)

        # Dibujo el bounding box y el valor de cada dado
        anotado = frame_quieto.copy()
        for d in dados_valor:
            x, y, w, h = d['bbox']
            print(f"dado en ({x},{y}) -> valor {d['valor']}")
            cv2.rectangle(anotado, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(anotado, str(d['valor']), (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)

        imshow(cv2.cvtColor(anotado, cv2.COLOR_BGR2RGB),
               title=f"Dados clasificados (frame {idx})",
               color_img=True, blocking=True)