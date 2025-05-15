# Parsers/parser_edesur.py
import re
from datetime import datetime

def parsear_factura_edesur(texto, codigos_barras):
    datos = {}

    # Cliente y domicilio
    datos['cliente'] = re.search(r'(?i)cliente:?\s*(.*)', texto)
    datos['domicilio'] = re.search(r'(?i)domicilio:?\s*(.*)', texto)

    # Número de cliente y medidor
    datos['nro_cliente'] = re.search(r'N\u00ba\s*Cliente:?\s*(\d+)', texto)
    datos['medidor'] = re.search(r'Medidor:?\s*(\d+)', texto)

    # Consumo
    datos['consumo'] = re.search(r'(\d+)\s*kWh', texto)

    # Vencimiento (usamos el primer vencimiento si está disponible)
    datos['vencimiento'] = re.search(r'1\u00ba\s*Vencimiento\s*(\d{2}/\d{2}/\d{4})', texto)

    # Total facturado
    datos['total'] = re.search(r'Total\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))', texto)

    # Empresa fija
    datos['empresa'] = "EDESUR"

    # Periodo de facturación (usamos formato Mes/Año desde la fecha final)
    match_periodo = re.search(r'Periodo:?\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})', texto)
    if match_periodo:
        try:
            fecha_final = datetime.strptime(match_periodo.group(2), "%d/%m/%Y")
            datos['periodo'] = fecha_final.strftime("%m/%Y")
        except:
            datos['periodo'] = None
    else:
        datos['periodo'] = None

    # Provincia desde QR (si se puede)
    qr_texto = next((c for c in codigos_barras if c.startswith("000201")), None)
    if qr_texto and "Buenos Aires" in qr_texto:
        datos['provincia'] = "Buenos Aires"
    else:
        datos['provincia'] = None

    # Convertir valores extraídos (limpieza)
    for clave in ['cliente', 'domicilio', 'nro_cliente', 'medidor', 'consumo', 'vencimiento', 'total']:
        datos[clave] = datos[clave].group(1).strip() if datos[clave] else None

    # Extra: obtener total desde barra si no se extrajo
    barra_importe = next((c for c in codigos_barras if c.startswith("30000")), None)
    if barra_importe and not datos['total']:
        try:
            total_centavos = int(barra_importe[5:12])
            datos['total'] = "{:.2f}".format(total_centavos / 100).replace('.', ',')
        except:
            pass

    return datos