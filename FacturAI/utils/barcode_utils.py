from pyzbar.pyzbar import decode
from PIL import Image
import numpy as np
import cv2


def extraer_codigos_barras(imagen_cv):
    """
    Extrae códigos de barras y QR desde una imagen OpenCV.

    Args:
        imagen_cv (np.ndarray): Imagen en formato OpenCV (BGR).

    Returns:
        list: Lista de textos decodificados desde los códigos.
    """
    # Convertir imagen de OpenCV a PIL
    imagen_pil = Image.fromarray(cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2RGB))

    # Decodificar códigos
    decodificados = decode(imagen_pil)

    # Obtener los datos en texto
    codigos = [d.data.decode('utf-8') for d in decodificados]

    return codigos
