# parsers/parser_metrogas.py
import re
from datetime import datetime

# Función que extrae datos estructurados desde un código de barras largo de una factura de Metrogas
def extraer_datos_codigo_metrogas(codigo):
    datos = {
        'cliente': None,
        'monto': None,
        'vencimiento': None,
        'periodo': None
    }

    try:
        # Extrae el número de cliente desde la posición 34 a la 44 (10 dígitos)
        cliente = codigo[33:44]
        if cliente.isdigit():
            datos['cliente'] = cliente

        # Extrae el monto desde la posición 20 a la 28, lo divide por 100 para obtener el valor real
        monto_str = codigo[20:28]
        if monto_str.isdigit():
            datos['monto'] = "{:.2f}".format(int(monto_str) / 100)

    except:
        pass

    return datos


# Funciones auxiliares para mejorar la extracción desde texto

def extraer_vencimiento(texto):
    patrones = [
        r'Vencimiento:? (\d{2}/\d{2}/\d{4})',
        r'Fecha de Vencimiento:? (\d{2}/\d{2}/\d{4})',
        r'Fecha vencimiento:? (\d{2}-\d{2}-\d{4})',
        r'Fecha de pago hasta:? (\d{2}/\d{2}/\d{4})',
        r'Vencimiento factura:? (\d{2}/\d{2}/\d{4})',
        r'1º\s*Vencimiento\s*\(?(\d{2}/\d{2}/\d{4})\)?'  # tu patrón original agregado aquí
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            fecha_str = match.group(1).replace('-', '/')
            try:
                datetime.strptime(fecha_str, "%d/%m/%Y")
                return fecha_str
            except:
                continue
    return None

def calcular_periodo_desde_vencimiento(fecha_vencimiento_str):
    try:
        fecha_venc = datetime.strptime(fecha_vencimiento_str, "%d/%m/%Y")
        mes = fecha_venc.month
        anio = fecha_venc.year
        # Periodo es mes anterior al vencimiento
        if mes == 1:
            mes_periodo = 12
            anio -= 1
        else:
            mes_periodo = mes - 1
        return f"{mes_periodo:02d}/{anio}"
    except:
        return None

def extraer_periodo(texto):
    # Buscar "PERIODO DE LIQUIDACIÓN: ... A ..."
    match = re.search(r'PERIODO DE LIQUIDACIÓN:\s*\d{2}/\d{2}/\d{4} A (\d{2})/(\d{2})/(\d{4})', texto, re.IGNORECASE)
    if match:
        mes = match.group(1)
        anio = match.group(3)
        return f"{mes}/{anio}"
    # Buscar "Periodo: MM/YYYY"
    match2 = re.search(r'Periodo:? (\d{2}/\d{4})', texto, re.IGNORECASE)
    if match2:
        return match2.group(1)
    # También usar patrón simple para MM/YYYY
    match3 = re.search(r'(\d{2}/\d{4})', texto)
    if match3:
        return match3.group(1)
    return None

def extraer_condicion_iva(texto):
    patrones = [
        r'Condición frente al IVA[:\s]*([^\n\.]+)',  # hasta salto de línea o punto
        r'Condicion frente al IVA[:\s]*([^\n\.]+)',
        r'Condición frente al I\.V\.A\.[:\s]*([^\n\.]+)',
        r'Condicion frente al I\.V\.A\.[:\s]*([^\n\.]+)',
        r'Condición IVA[:\s]*([^\n\.]+)',  # Variante común y corta
        r'Condicion IVA[:\s]*([^\n\.]+)'
    ]

    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            cond = match.group(1).strip()
            cond_lower = cond.lower()
            if "cons final" in cond_lower or "consumidor final" in cond_lower:
                return "Cons Final"
            elif "responsable inscripto" in cond_lower:
                return "Resp Inscripto"
            elif "exento" in cond_lower:
                return "Exento"
            else:
                cond_limpia = re.sub(r'[^a-zA-Z\s]', '', cond).strip()
                return cond_limpia.title()
    return None


# Función principal que parsea el texto completo de la factura y los códigos de barras detectados por OCR
def parsear_factura_metrogas(texto, codigos_barras):
    datos = {}

    # ID fijo que representa a la empresa Metrogas
    datos['entidad_id'] = 2

    # Busca el primer código de barras largo (más de 40 dígitos seguidos)
    codigo_largo = next((c for c in codigos_barras if c.isdigit() and len(c) > 40), None)

    if codigo_largo:
        datos_codigo = extraer_datos_codigo_metrogas(codigo_largo)
        datos.update({k: v for k, v in datos_codigo.items() if v is not None})

    # Si no se pudo obtener el número de cliente del código, intenta extraerlo desde el texto OCR
    if not datos.get('cliente'):
        match = re.search(r'(?i)cliente:?\s*(\d+)', texto)
        if match:
            datos['cliente'] = match.group(1).strip()

    # Mejor extracción de vencimiento
    if not datos.get('vencimiento'):
        venc = extraer_vencimiento(texto)
        if venc:
            datos['vencimiento'] = venc

    # Mejor extracción de periodo
    if not datos.get('periodo'):
        # Si tenemos vencimiento, intentamos calcular periodo desde vencimiento
        if datos.get('vencimiento'):
            periodo = calcular_periodo_desde_vencimiento(datos['vencimiento'])
            if periodo:
                datos['periodo'] = periodo
        # Si no, extraemos periodo directamente del texto
        if not datos.get('periodo'):
            periodo = extraer_periodo(texto)
            if periodo:
                datos['periodo'] = periodo

    # Si no se pudo extraer el monto desde el código, se intenta encontrar el total desde el texto OCR
    if not datos.get('monto'):
        match = re.search(r'Total\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))', texto)
        if match:
            monto_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                datos['monto'] = "{:.2f}".format(float(monto_str))
            except:
                pass

    # Mejor extracción condición IVA
    if not datos.get('condicion_iva'):
        cond_iva = extraer_condicion_iva(texto)
        if cond_iva:
            datos['condicion_iva'] = cond_iva

    return datos
