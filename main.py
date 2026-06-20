import os
import cv2


def reconocer_dados(frame):
    """
    Reconocemos los dados en el frame.
    """
    pass


def detectar_movimiento(frames_video):
    """
    Comparamos frames y vemos si hay movimiento, 
    en caso que de que no lo haya sabemos que el video es estatico
    y ahí podemos reconocer los dados.
    """
    pass


def fps_and_frames(video_path):
    """
    Vemos los FPS del video
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    return {
        "FPS": cap.get(cv2.CAP_PROP_FPS),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    }


def procesar_videos():
    directorio_videos = "videos"
    videos = [f for f in os.listdir(directorio_videos) if f.endswith(".mp4")]
    for video in videos:
        caracteristicas = fps_and_frames(os.path.join(directorio_videos, video))
        if caracteristicas["FPS"] > 10 and caracteristicas["frames"] > 10:
            # detectar_movimiento(caracteristicas["frames"])
            print(caracteristicas)
        else:
            print("Video no valido")


if __name__ == "__main__":
    procesar_videos()