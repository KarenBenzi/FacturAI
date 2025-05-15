import re
from datetime import datetime

def parsear_factura_metrogas(texto, codigos_barras):
    """
    Parsea los datos relevantes de una factura de Metrogas.

    Args:
        texto (str): Texto extraído con OCR.
        codigos_barras (list): Lista de códigos extraídos de la imagen.

    Returns:
        dict: Diccionario con los datos estructurados.
    """
    datos = {}

    # Datos desde texto
    datos['cliente'] = extraer_regex(texto, r'(?i)cliente:\s*(.*)')
    datos['domicilio'] = extraer_regex(texto, r'(?i)domicilio\s*[:\-]?\s*(.*)')
    datos['nro_cliente'] = extraer_regex(texto, r'Cliente N\*\s*(\d+)')
    datos['medidor'] = extraer_regex(texto, r'Medidor\s*:?\s*(\d+)')
    datos['consumo'] = extraer_regex(texto, r'(\d+)\s*kWh')
    datos['vencimiento'] = extraer_regex(texto, r'1º Vencimiento\s*\((.*?)\)')
    datos['total'] = extraer_regex(texto, r'TOTAL\s*[A-Za-z]*\s*[\$:]\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))')
    datos['empresa'] = extraer_regex(texto, r'(METROGAS S\.A\.)')

    # Periodo
    match_periodo = re.search(r'PERIODO DE LIQUIDACIÓN:\s*(\d{2}/\d{2}/\d{4})\s*A\s*(\d{2}/\d{2}/\d{4})', texto)
    if match_periodo:
        fecha_final = match_periodo.group(2).strip()
        try:
            fecha_obj = datetime.strptime(fecha_final, "%d/%m/%Y")
            datos['periodo'] = fecha_obj.strftime("%m/%Y")
        except:
            datos['periodo'] = None
    else:
        datos['periodo'] = None

    # Provincia desde QR
    qr_texto = next((c for c in codigos_barras if c.startswith("000201")), None)
    datos['provincia'] = "Buenos Aires" if qr_texto and "Buenos Aires" in qr_texto else None

    # Si falta número de cliente, intentar desde barra 2507
    barra_numerica = next((c for c in codigos_barras if c.startswith("2507")), None)
    if barra_numerica and not datos['nro_cliente']:
        datos['nro_cliente'] = barra_numerica[12:22].lstrip("0")

    # Si falta total, intentar desde barra 30000
    barra_importe = next((c for c in codigos_barras if c.startswith("30000")), None)
    if barra_importe and not datos['total']:
        try:
            total_centavos = int(barra_importe[5:12])
            datos['total'] = "{:.2f}".format(total_centavos / 100).replace('.', ',')
        except:
            pass

    return datos

def extraer_regex(texto, patron):
    """
    Aplica una expresión regular y retorna el primer grupo encontrado o None.
    """
    match = re.search(patron, texto)
    return match.group(1).strip() if match else None
