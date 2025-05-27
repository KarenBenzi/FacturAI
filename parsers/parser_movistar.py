import re
from datetime import datetime

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

def extraer_datos_codigo_movistar(codigo):
    datos = {
        'cliente': None,
        'monto': None,
        'vencimiento': None,
        'periodo': None,
    }
    try:
        # Monto: dígitos de la posición 14 a 20 (6 dígitos)
        monto_str = codigo[14:20].lstrip('0')
        if monto_str.isdigit():
            datos['monto'] = "{:.2f}".format(int(monto_str))

        # Vencimiento: dígitos posición 20 a 28 (DDMMYYYY)
        venc_str = codigo[20:28]
        if len(venc_str) == 8 and venc_str.isdigit():
            dia = venc_str[0:2]
            mes = venc_str[2:4]
            anio = venc_str[4:8]
            try:
                datetime.strptime(f"{dia}/{mes}/{anio}", "%d/%m/%Y")
                datos['vencimiento'] = f"{dia}/{mes}/{anio}"
                datos['periodo'] = calcular_periodo_desde_vencimiento(datos['vencimiento'])
            except:
                pass
    except:
        pass
    return datos

def extraer_vencimiento(texto):
    patrones = [
        r'Vencimiento[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Fecha de Vencimiento[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Fecha vencimiento[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Fecha de pago hasta[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
        r'Vencimiento factura[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{4})',
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

def extraer_nombre_cliente(texto):
    patrones = [
        r'Cliente\s*N[\*°º:”“"\'’`]*\s*[:\-]?\s*(\d{5,15})',   # incluye comillas tipográficas
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

def extraer_monto(texto):
    match = re.search(r'Monto\s*(Total)?[:\s]*\$?\s*([\d.,]+)', texto, re.IGNORECASE)
    if match:
        monto_str = match.group(2).replace('.', '').replace(',', '.')
        try:
            return "{:.2f}".format(float(monto_str))
        except:
            return None
    return None

def parsear_factura_movistar(texto, codigos_barras):
    datos = {}
    datos['entidad_id'] = 3

    # Buscar el código de barras válido
    codigo_movistar = next((c for c in codigos_barras if c.isdigit() and len(c) >= 30), None)

    if codigo_movistar:
        datos['codigo_barra'] = codigo_movistar  # ← Se agrega el código de barras
        datos_codigo = extraer_datos_codigo_movistar(codigo_movistar)
        datos.update({k: v for k, v in datos_codigo.items() if v is not None})

    if not datos.get('cliente'):
        cliente = extraer_nombre_cliente(texto)
        if cliente:
            datos['cliente'] = cliente

    if not datos.get('vencimiento'):
        venc = extraer_vencimiento(texto)
        if venc:
            datos['vencimiento'] = venc
            if 'periodo' not in datos or not datos['periodo']:
                datos['periodo'] = calcular_periodo_desde_vencimiento(venc)

    if not datos.get('monto'):
        monto = extraer_monto(texto)
        if monto:
            datos['monto'] = monto

    return datos
