import re
from datetime import datetime

# Función que calcula el periodo (mes/año) correspondiente al mes anterior al vencimiento
def calcular_periodo_desde_vencimiento(fecha_vencimiento_str):
    try:
        # Convierte la fecha de vencimiento de string a objeto datetime
        fecha_venc = datetime.strptime(fecha_vencimiento_str, "%d/%m/%Y")
        mes = fecha_venc.month
        anio = fecha_venc.year
        # Si el vencimiento es en enero, el periodo será diciembre del año anterior
        if mes == 1:
            mes_periodo = 12
            anio -= 1
        else:
            mes_periodo = mes - 1
        # Devuelve el periodo en formato MM/YYYY
        return f"{mes_periodo:02d}/{anio}"
    except:
        # En caso de error (por ejemplo, formato inválido), devuelve None
        return None

# Función que extrae datos estructurados desde el código de barras de una factura Movistar
def extraer_datos_codigo_movistar(codigo):
    datos = {
        'cliente': None,
        'monto': None,
        'vencimiento': None,
        'periodo': None,
    }
    try:
        # Extrae el monto del código de barras: posiciones 14 a 20 (6 dígitos), quitando ceros a la izquierda
        monto_str = codigo[14:20].lstrip('0')
        if monto_str.isdigit():
            datos['monto'] = "{:.2f}".format(int(monto_str))

        # Extrae la fecha de vencimiento: posiciones 20 a 28 (formato DDMMYYYY)
        venc_str = codigo[20:28]
        if len(venc_str) == 8 and venc_str.isdigit():
            dia = venc_str[0:2]
            mes = venc_str[2:4]
            anio = venc_str[4:8]
            try:
                # Verifica si la fecha es válida
                datetime.strptime(f"{dia}/{mes}/{anio}", "%d/%m/%Y")
                datos['vencimiento'] = f"{dia}/{mes}/{anio}"
                # Calcula el periodo a partir de la fecha de vencimiento
                datos['periodo'] = calcular_periodo_desde_vencimiento(datos['vencimiento'])
            except:
                pass
    except:
        pass
    return datos

# Función que extrae la fecha de vencimiento desde texto libre
def extraer_vencimiento(texto):
    patrones = [
        r'Vencimiento[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Fecha de Vencimiento[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Fecha vencimiento[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Fecha de pago hasta[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Vencimiento factura[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Próximo Vencimiento Estimado\s*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',  # especial para Movistar
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            # Normaliza el formato de la fecha (usa / en lugar de -)
            fecha_str = match.group(1).replace('-', '/')
            try:
                # Verifica si la fecha es válida
                datetime.strptime(fecha_str, "%d/%m/%Y")
                return fecha_str
            except:
                continue
    return None

# Función que busca el número de cliente dentro del texto
def extraer_nombre_cliente(texto):
    patrones = [
        r'Cliente\s*N[\*°º:”“"\'’`]*\s*[:\-]?\s*(\d{5,15})',  # permite símbolos tipográficos
        r'N[úu]mero de Cliente\s*[:\-]?\s*(\d{5,15})',
        r'N[°º] Cliente\s*[:\-]?\s*(\d{5,15})',
        r'N° de cliente\s*[:\-]?\s*(\d{5,15})',
        r'Cliente\s*[:\-]?\s*(\d{5,15})',
        r'Cliente\s*\n\s*(\d{5,15})'
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

# Función que extrae el monto total a pagar desde el texto
def extraer_monto(texto):
    match = re.search(r'Monto\s*(Total)?[:\s]*\$?\s*([\d.,]+)', texto, re.IGNORECASE)
    if match:
        # Normaliza el número: quita puntos de miles y cambia coma decimal por punto
        monto_str = match.group(2).replace('.', '').replace(',', '.')
        try:
            return "{:.2f}".format(float(monto_str))
        except:
            return None
    return None

# Función que detecta la condición frente al IVA en el texto y la normaliza
def extraer_condicion_iva_movistar(texto):
    patrones = [
        r'IVA\s*-\s*Cons\.? Final',
        r'Condición frente al IVA[:\s]*([^\n\.]+)',
        r'Condicion frente al IVA[:\s]*([^\n\.]+)',
        r'Condición IVA[:\s]*([^\n\.]+)',
        r'Condicion IVA[:\s]*([^\n\.]+)'
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            # Si el patrón coincide directamente con "IVA - Cons. Final"
            if patron == r'IVA\s*-\s*Cons\.? Final':
                return "Consumidor Final"
            else:
                cond = match.group(1).strip()
                cond_lower = cond.lower()
                # Normalización de las condiciones más comunes
                if "cons final" in cond_lower or "consumidor final" in cond_lower:
                    return "Consumidor Final"
                elif "responsable inscripto" in cond_lower:
                    return "Resp Inscripto"
                elif "exento" in cond_lower:
                    return "Exento"
                else:
                    # Limpia caracteres no alfabéticos y capitaliza
                    cond_limpia = re.sub(r'[^a-zA-Z\s]', '', cond).strip()
                    return cond_limpia.title()
    return None

# Función principal que agrupa todas las extracciones anteriores para una factura Movistar
def parsear_factura_movistar(texto, codigos_barras):
    datos = {}
    datos['entidad_id'] = 3  # ID fijo que representa a Movistar

    # Busca el primer código de barras válido: al menos 30 dígitos numéricos
    codigo_movistar = next((c for c in codigos_barras if c.isdigit() and len(c) >= 30), None)

    if codigo_movistar:
        datos['codigo_barra'] = codigo_movistar  # guarda el código
        # Extrae los datos embebidos en el código de barras
        datos_codigo = extraer_datos_codigo_movistar(codigo_movistar)
        # Agrega solo los datos no vacíos
        datos.update({k: v for k, v in datos_codigo.items() if v is not None})

    # Si no se extrajo el cliente desde el código, busca en el texto
    if not datos.get('cliente'):
        cliente = extraer_nombre_cliente(texto)
        if cliente:
            datos['cliente'] = cliente

    # Si no se extrajo vencimiento del código, intenta buscarlo en el texto
    if not datos.get('vencimiento'):
        venc = extraer_vencimiento(texto)
        if venc:
            datos['vencimiento'] = venc
            # Si no hay periodo calculado, se calcula desde esta fecha
            if 'periodo' not in datos or not datos['periodo']:
                datos['periodo'] = calcular_periodo_desde_vencimiento(venc)

    # Si no se extrajo el monto del código, intenta buscarlo en el texto
    if not datos.get('monto'):
        monto = extraer_monto(texto)
        if monto:
            datos['monto'] = monto

    # Intenta extraer y agregar la condición frente al IVA
    condicion_iva = extraer_condicion_iva_movistar(texto)
    if condicion_iva:
        datos['condicion_iva'] = condicion_iva

    return datos
