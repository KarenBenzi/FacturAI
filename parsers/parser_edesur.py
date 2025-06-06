import re
from datetime import datetime

# Función que extrae datos del código de barras largo de una factura de Edesur
def extraer_datos_codigo_edesur(codigo):
    # Diccionario inicial con campos vacíos
    datos = {
        'cliente': None,
        'monto': None,
        'vencimiento': None,
        'periodo': None
    }

    try:
        # Extrae el número de cliente (posiciones 6 a 13 del código)
        cliente = codigo[5:13]
        if cliente.isdigit():
            datos['cliente'] = cliente

        # Extrae el monto de la factura (posiciones 14 a 24 del código)
        monto_str = codigo[13:24]
        if monto_str.isdigit():
            datos['monto'] = "{:.2f}".format(int(monto_str) / 100)  # Convierte a decimal con 2 decimales

        # Extrae la fecha de vencimiento (posiciones 25 a 30 del código)
        fecha_str = codigo[24:30]
        try:
            fecha_venc = datetime.strptime(fecha_str, "%y%m%d")
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
            pass  # Ignora errores en la conversión de fecha
    except:
        pass  # Ignora errores generales

    return datos

# Función auxiliar para identificar la condición frente al IVA a partir de texto
def extraer_condicion_iva(texto):
    texto = texto.lower()

    # Diccionario de patrones de texto que se corresponden con condiciones fiscales
    patrones = {
        "Responsable Inscripto": r"responsable\s+inscripto",
        "Monotributista": r"monotributista",
        "Exento": r"exento",
        "Consumidor Final": r"consumidor\s+final",
        "No Responsable": r"no\s+responsable",
        "Sujeto no Categorizado": r"sujeto\s+no\s+categorizado"
    }

    # Recorre los patrones y devuelve la condición encontrada
    for condicion, patron in patrones.items():
        if re.search(patron, texto):
            return condicion
    return "Desconocido"  # Si no encuentra coincidencias

# Función principal que parsea una factura de Edesur a partir del texto extraído y códigos de barra
def parsear_factura_edesur(texto, codigos_barras):
    datos = {}

    datos['entidad_id'] = 1  # ID fijo para Edesur

    # Busca un código de barras largo (más de 40 dígitos)
    codigo_largo = next((c for c in codigos_barras if c.isdigit() and len(c) > 40), None)

    # Si se encuentra un código válido, se extraen los datos
    if codigo_largo:
        datos_codigo = extraer_datos_codigo_edesur(codigo_largo)
        datos.update({k: v for k, v in datos_codigo.items() if v is not None})
        datos['codigo_barra'] = codigo_largo  

    # Si no se pudo extraer el número de cliente desde el código, se intenta desde el texto
    if not datos.get('cliente'):
        match = re.search(r'(?i)cliente:?\s*(\d+)', texto)
        if match:
            datos['cliente'] = match.group(1).strip()

    # Si no se pudo extraer la fecha de vencimiento, se intenta buscarla en el texto
    if not datos.get('vencimiento'):
        match = re.search(r'1º\s*Vencimiento\s*\(?(\d{2}/\d{2}/\d{4})\)?', texto)
        if match:
            datos['vencimiento'] = match.group(1).strip()

    # Si no se pudo extraer el monto, se intenta buscarlo en el texto
    if not datos.get('monto'):
        match = re.search(r'Total\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))', texto)
        if match:
            monto_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                datos['monto'] = "{:.2f}".format(float(monto_str))
            except:
                pass  # Ignora errores de conversión

    # Si no se pudo extraer el período, se intenta buscarlo en el texto
    if not datos.get('periodo'):
        match = re.search(r'Periodo.*?(\d{1,2}/\d{4})', texto)
        if match:
            datos['periodo'] = match.group(1)

    # Si no se pudo extraer la condición frente al IVA, se intenta encontrar en el texto
    if not datos.get('condicion_iva'):
        condiciones_validas = [
            "consumidor final",
            "monotributista",
            "responsable inscripto",
            "exento",
            "no responsable",
            "sujeto no categorizado"
        ]

        # Busca texto como "CUIT: Consumidor Final"
        match = re.search(r'CUIT:\s*([A-Za-z\s]+)', texto, re.IGNORECASE)
        if match:
            posible_condicion = match.group(1).strip().lower().split('\n')[0]
            for condicion in condiciones_validas:
                if condicion in posible_condicion:
                    datos['condicion_iva'] = condicion.title()
                    break

        # Si no se encontró, intenta con "Curr" o "Condición IVA"
        if not datos.get('condicion_iva'):
            match = re.search(r'(?i)(?:Curr|Condición\s*IVA):?\s*([A-Za-z\s\n]+)', texto)
            if match:
                posible_condicion = match.group(1).strip().lower().split('\n')[0]
                for condicion in condiciones_validas:
                    if condicion in posible_condicion:
                        datos['condicion_iva'] = condicion.title()
                        break

    # Último intento genérico para obtener la condición IVA
    if not datos.get('condicion_iva'):
        datos['condicion_iva'] = extraer_condicion_iva(texto)

    return datos  # Devuelve todos los datos extraídos en forma de diccionario
