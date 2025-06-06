# parsers/parser_metrogas.py
import re
from datetime import datetime

# Extrae datos básicos desde el código de barras largo de una factura de Metrogas
def extraer_datos_codigo_metrogas(codigo):
    datos = {
        'cliente': None,
        'monto': None,
        'vencimiento': None,
        'periodo': None
    }

    try:
        # Extrae el número de cliente desde una posición fija del código
        cliente = codigo[33:44]
        if cliente.isdigit():
            datos['cliente'] = cliente

        # Extrae el monto (en centavos) y lo convierte a formato decimal
        monto_str = codigo[20:28]
        if monto_str.isdigit():
            datos['monto'] = "{:.2f}".format(int(monto_str) / 100)

    except:
        # Si hay un error en el parseo, ignora y sigue
        pass

    return datos


# Busca la fecha de vencimiento en el texto de la factura usando patrones comunes
def extraer_vencimiento(texto):
    patrones = [
        r'Vencimiento:? (\d{2}/\d{2}/\d{4})',
        r'Fecha de Vencimiento:? (\d{2}/\d{2}/\d{4})',
        r'Fecha vencimiento:? (\d{2}-\d{2}-\d{4})',
        r'Fecha de pago hasta:? (\d{2}/\d{2}/\d{4})',
        r'Vencimiento factura:? (\d{2}/\d{2}/\d{4})',
        r'1º\s*Vencimiento\s*\(?(\d{2}/\d{2}/\d{4})\)?'
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            fecha_str = match.group(1).replace('-', '/')
            try:
                # Valida si es una fecha válida
                datetime.strptime(fecha_str, "%d/%m/%Y")
                return fecha_str
            except:
                continue
    return None

# Calcula el período de facturación anterior al vencimiento (ej: vencimiento en 03/2025 → periodo 02/2025)
def calcular_periodo_desde_vencimiento(fecha_vencimiento_str):
    try:
        fecha_venc = datetime.strptime(fecha_vencimiento_str, "%d/%m/%Y")
        mes = fecha_venc.month
        anio = fecha_venc.year
        if mes == 1:
            mes_periodo = 12
            anio -= 1
        else:
            mes_periodo = mes - 1
        return f"{mes_periodo:02d}/{anio}"
    except:
        return None

# Extrae el período de facturación desde el texto si está explícitamente indicado
def extraer_periodo(texto):
    # Busca expresiones comunes que contengan el período
    match = re.search(r'PERIODO DE LIQUIDACIÓN:\s*\d{2}/\d{2}/\d{4} A (\d{2})/(\d{2})/(\d{4})', texto, re.IGNORECASE)
    if match:
        mes = match.group(1)
        anio = match.group(3)
        return f"{mes}/{anio}"
    
    match2 = re.search(r'Periodo:? (\d{2}/\d{4})', texto, re.IGNORECASE)
    if match2:
        return match2.group(1)

    match3 = re.search(r'(\d{2}/\d{4})', texto)
    if match3:
        return match3.group(1)
    
    return None

# Extrae la condición frente al IVA desde el texto (mapea a una versión estandarizada)
def extraer_condicion_iva(texto):
    mapping = {
        "cons final": "Consumidor Final",
        "consumidor final": "Consumidor Final",
        "responsable inscripto": "Responsable Inscripto",
        "exento": "Exento",
        "no responsable": "No Responsable",
        "monotributista": "Monotributista",
        "sujeto no categorizado": "Sujeto no Categorizado"
    }
    
    # Patrones para distintas variantes del texto que contiene la condición frente al IVA
    patrones = [
        r'Condición frente al IVA[:\s]*([^\n\.]+)',
        r'Condicion frente al IVA[:\s]*([^\n\.]+)',
        r'Condición frente al I\.V\.A\.[:\s]*([^\n\.]+)',
        r'Condicion frente al I\.V\.A\.[:\s]*([^\n\.]+)',
        r'Condición IVA[:\s]*([^\n\.]+)',
        r'Condicion IVA[:\s]*([^\n\.]+)'
    ]

    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            cond = match.group(1).strip().lower()
            for key in mapping:
                if key in cond:
                    return mapping[key]
            # Si no se encuentra mapeo, se limpia y capitaliza la cadena
            cond_limpia = re.sub(r'[^a-zA-Z\s]', '', cond).strip()
            return cond_limpia.title()

    # Fallback: si no se encontró con regex, buscar directamente
    for key in mapping:
        if key in texto.lower():
            return mapping[key]

    return None


# Función principal: procesa el texto y códigos de barras de una factura Metrogas
def parsear_factura_metrogas(texto, codigos_barras):
    datos = {}

    # ID que representa a Metrogas como entidad
    datos['entidad_id'] = 2

    # Busca un código de barras largo (mayor a 40 caracteres y numérico)
    codigo_largo = next((c for c in codigos_barras if c.isdigit() and len(c) > 40), None)

    if codigo_largo:
        # Extrae datos del código y los agrega si existen
        datos_codigo = extraer_datos_codigo_metrogas(codigo_largo)
        datos.update({k: v for k, v in datos_codigo.items() if v is not None})
        datos['codigo_barra'] = codigo_largo

    # Si no se extrajo cliente, buscar en el texto explícitamente
    if not datos.get('cliente'):
        match = re.search(r'(?i)cliente:?\s*(\d+)', texto)
        if match:
            datos['cliente'] = match.group(1).strip()

    # Si no se extrajo vencimiento del código, buscarlo en el texto
    if not datos.get('vencimiento'):
        venc = extraer_vencimiento(texto)
        if venc:
            datos['vencimiento'] = venc

    # Si no se extrajo período, intentar calcularlo desde el vencimiento o extraerlo del texto
    if not datos.get('periodo'):
        if datos.get('vencimiento'):
            periodo = calcular_periodo_desde_vencimiento(datos['vencimiento'])
            if periodo:
                datos['periodo'] = periodo
        if not datos.get('periodo'):
            periodo = extraer_periodo(texto)
            if periodo:
                datos['periodo'] = periodo

    # Si no se extrajo monto del código, buscar en el texto usando patrón de Total $
    if not datos.get('monto'):
        match = re.search(r'Total\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))', texto)
        if match:
            monto_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                datos['monto'] = "{:.2f}".format(float(monto_str))
            except:
                pass

    # Si no se extrajo la condición IVA, intentar extraerla del texto
    if not datos.get('condicion_iva'):
        cond_iva = extraer_condicion_iva(texto)
        if cond_iva:
            datos['condicion_iva'] = cond_iva

    return datos
