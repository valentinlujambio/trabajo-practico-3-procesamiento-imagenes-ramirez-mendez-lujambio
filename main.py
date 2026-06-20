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


def obtener_frames(video_path, nombre_video, propiedades):
    """
    Obtenemos los frames del video.
    """
    frame_number = 0
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    carpeta_destino = os.path.join("frames", nombre_video)
    os.makedirs(carpeta_destino, exist_ok = True)
    while (cap.isOpened()):
        ret, frame = cap.read()

        if ret == True:  
            frame = cv2.resize(frame, dsize=(int(propiedades['width']/3), int(propiedades['height']/3)))
            cv2.imshow('Frame', frame)

            ruta = os.path.join(carpeta_destino, f"frame_{frame_number}.jpg")
            if not cv2.imwrite(ruta, frame):
                print(f"No se pudo guardar {ruta}")

            frame_number += 1
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
        else:  
            break  

    cap.release()
    cv2.destroyAllWindows()
    

def propiedades_video(video_path):
    """
    Vemos los FPS del video
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    return {
        "FPS": cap.get(cv2.CAP_PROP_FPS),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }


def procesar_videos():
    directorio_videos = "videos"
    videos = [f for f in os.listdir(directorio_videos) if f.endswith(".mp4")]
    for video in videos:
        path_video = os.path.join(directorio_videos, video)
        nombre_video = video.split(".")[0]
        propiedades = propiedades_video(path_video)
        obtener_frames(path_video, nombre_video, propiedades)


if __name__ == "__main__":
    procesar_videos()