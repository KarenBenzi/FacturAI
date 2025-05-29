from pdf2image import convert_from_path

def convertir_pdf_a_imagen(pdf_path, dpi=300):
    """
    Convierte la primera página de un PDF en una imagen PIL.

    Args:
        pdf_path (str): Ruta al archivo PDF.
        dpi (int): Resolución para la conversión. Por defecto: 300.

    Returns:
        PIL.Image: Imagen de la primera página del PDF.
    """
    paginas = convert_from_path(pdf_path, dpi=dpi)
    return paginas[0]  # Retornamos solo la primera página
