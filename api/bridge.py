"""
Puente hacia el codigo original del TP.

`dados.py` y `main.py` viven en la raiz del repo y se escribieron como scripts:
importan `help_show`, que a su vez hace `import matplotlib.pyplot` a nivel de
modulo. En un servidor sin display el backend interactivo por defecto falla al
importar, asi que acá se fija `Agg` *antes* de tocarlos, se agrega la raiz al
`sys.path` y se reexporta lo que necesita la API. El codigo de vision no se
modifica.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dados import (  # noqa: E402
    SeguimientoCentroides,
    contar_pips,
    mascara_roja,
    segmentar_dados,
)
from main import (  # noqa: E402
    buscar_dados_quietos,
    generar_video_salida,
    propiedades_video,
)

VIDEOS_DIR = ROOT / "videos"
SALIDAS_DIR = ROOT / "salidas"

__all__ = [
    "ROOT",
    "VIDEOS_DIR",
    "SALIDAS_DIR",
    "SeguimientoCentroides",
    "contar_pips",
    "mascara_roja",
    "segmentar_dados",
    "buscar_dados_quietos",
    "generar_video_salida",
    "propiedades_video",
]
