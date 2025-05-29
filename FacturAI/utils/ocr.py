import cv2
import numpy as np
import pytesseract

def extraer_texto_de_imagen(imagen_pil):
    """
    Extrae texto de una imagen usando Tesseract OCR.

    Args:
        imagen_pil (PIL.Image): Imagen en formato PIL.

    Returns:
        tuple:
            - texto extraído (str)
            - imagen en formato OpenCV (np.ndarray)
    """
    # Convertir imagen de PIL a OpenCV
    imagen_cv = cv2.cvtColor(np.array(imagen_pil), cv2.COLOR_RGB2BGR)
    
    # Aplicar OCR con Tesseract
    texto = pytesseract.image_to_string(imagen_cv, lang='spa')

    return texto, imagen_cv
