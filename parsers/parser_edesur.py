# parsers/parser_edesur.py
import re
from datetime import datetime

# Función que extrae datos estructurados desde un código de barras largo de una factura de Edesur
def extraer_datos_codigo_edesur(codigo):
    datos = {
        'cliente': None,
        'monto': None,
        'vencimiento': None,
        'periodo': None
    }

    try:
        # Extrae el número de cliente desde la posición 5 a la 13 (8 dígitos)
        cliente = codigo[5:13]
        if cliente.isdigit():
            datos['cliente'] = cliente

        # Extrae el monto desde la posición 13 a la 24, lo divide por 100 para obtener el valor real con decimales
        monto_str = codigo[13:24]
        if monto_str.isdigit():
            datos['monto'] = "{:.2f}".format(int(monto_str) / 100)

        # Extrae la fecha de vencimiento desde la posición 24 a la 30 en formato YYMMDD
        fecha_str = codigo[24:30]
        try:
            fecha_venc = datetime.strptime(fecha_str, "%y%m%d")
            # Convierte la fecha al formato DD/MM/YYYY
            datos['vencimiento'] = fecha_venc.strftime("%d/%m/%Y")

            # Calcula el período como el mes anterior al vencimiento
            año = fecha_venc.year
            mes = fecha_venc.month
            if mes == 1:
                mes_periodo = 12
                año_periodo = año - 1
            else:
                mes_periodo = mes - 1
                año_periodo = año
            datos['periodo'] = f"{mes_periodo:02d}/{año_periodo}"
        except:
            # Ignora errores si la fecha no puede ser interpretada
            pass

    except:
        # Ignora errores en general del procesamiento del código
        pass

    return datos


# Función principal que parsea el texto completo de la factura y los códigos de barras detectados por OCR
def parsear_factura_edesur(texto, codigos_barras):
    datos = {}

    # ID fijo que representa a la empresa Edesur
    datos['entidad_id'] = 1

    # Busca el primer código de barras largo (más de 40 dígitos seguidos)
    codigo_largo = next((c for c in codigos_barras if c.isdigit() and len(c) > 40), None)

    # Si se encuentra un código largo, se extraen los datos desde él
    if codigo_largo:
        datos_codigo = extraer_datos_codigo_edesur(codigo_largo)
        datos.update({k: v for k, v in datos_codigo.items() if v is not None})

    # Si no se pudo obtener el número de cliente del código, intenta extraerlo desde el texto OCR
    if not datos.get('cliente'):
        match = re.search(r'(?i)cliente:?\s*(\d+)', texto)
        if match:
            datos['cliente'] = match.group(1).strip()

    # Si no se obtuvo la fecha de vencimiento, se busca una fecha que siga al texto "1º Vencimiento"
    if not datos.get('vencimiento'):
        match = re.search(r'1º\s*Vencimiento\s*\(?(\d{2}/\d{2}/\d{4})\)?', texto)
        if match:
            datos['vencimiento'] = match.group(1).strip()

    # Si no se pudo extraer el monto desde el código, se intenta encontrar el total desde el texto OCR
    if not datos.get('monto'):
        match = re.search(r'Total\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))', texto)
        if match:
            monto_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                datos['monto'] = "{:.2f}".format(float(monto_str))
            except:
                pass

    # Si todavía no se pudo determinar el período, se intenta extraer desde una línea que contenga "Periodo"
    if not datos.get('periodo'):
        match = re.search(r'Periodo.*?(\d{1,2}/\d{4})', texto)
        if match:
            datos['periodo'] = match.group(1)

    # Extrae la condición frente al IVA desde el texto (ej: "Curr: Consumidor Final")
# Extrae la condición frente al IVA desde el texto (ej: "Curr: Consumidor Final" o "Condición IVA: Monotributista")
    if not datos.get('condicion_iva'):
        match = re.search(r'(?i)(?:Curr|Condición\s*IVA):?\s*([A-Za-z\s]+)', texto)
        if match:
            datos['condicion_iva'] = match.group(1).strip()


    return datos
