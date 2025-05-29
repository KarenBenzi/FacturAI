import re
from datetime import datetime

def extraer_datos_codigo_edesur(codigo):
    datos = {
        'cliente': None,
        'monto': None,
        'vencimiento': None,
        'periodo': None
    }

    try:
        cliente = codigo[5:13]
        if cliente.isdigit():
            datos['cliente'] = cliente

        monto_str = codigo[13:24]
        if monto_str.isdigit():
            datos['monto'] = "{:.2f}".format(int(monto_str) / 100)

        fecha_str = codigo[24:30]
        try:
            fecha_venc = datetime.strptime(fecha_str, "%y%m%d")
            datos['vencimiento'] = fecha_venc.strftime("%d/%m/%Y")

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
            pass
    except:
        pass

    return datos

def extraer_condicion_iva(texto):
    texto = texto.lower()

    patrones = {
        "Responsable Inscripto": r"responsable\s+inscripto",
        "Monotributista": r"monotributista",
        "Exento": r"exento",
        "Consumidor Final": r"consumidor\s+final",
        "No Responsable": r"no\s+responsable",
        "Sujeto no Categorizado": r"sujeto\s+no\s+categorizado"
    }

    for condicion, patron in patrones.items():
        if re.search(patron, texto):
            return condicion
    return "Desconocido"

def parsear_factura_edesur(texto, codigos_barras):
    datos = {}

    datos['entidad_id'] = 1

    codigo_largo = next((c for c in codigos_barras if c.isdigit() and len(c) > 40), None)

    if codigo_largo:
        datos_codigo = extraer_datos_codigo_edesur(codigo_largo)
        datos.update({k: v for k, v in datos_codigo.items() if v is not None})
        datos['codigo_barra'] = codigo_largo  

    if not datos.get('cliente'):
        match = re.search(r'(?i)cliente:?\s*(\d+)', texto)
        if match:
            datos['cliente'] = match.group(1).strip()

    if not datos.get('vencimiento'):
        match = re.search(r'1º\s*Vencimiento\s*\(?(\d{2}/\d{2}/\d{4})\)?', texto)
        if match:
            datos['vencimiento'] = match.group(1).strip()

    if not datos.get('monto'):
        match = re.search(r'Total\s*\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))', texto)
        if match:
            monto_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                datos['monto'] = "{:.2f}".format(float(monto_str))
            except:
                pass

    if not datos.get('periodo'):
        match = re.search(r'Periodo.*?(\d{1,2}/\d{4})', texto)
        if match:
            datos['periodo'] = match.group(1)

    # ✅ Extrae la condición frente al IVA desde el texto
    if not datos.get('condicion_iva'):
        # 1. Busca el caso específico "CUIT: Consumidor Final" u otras condiciones después de "CUIT:"
        match = re.search(r'CUIT:\s*([A-Za-z\s\n]+)', texto, re.IGNORECASE)
        if match:
            condicion = match.group(1).strip().split('\n')[0].strip()
            if any(c in condicion.lower() for c in ['consumidor', 'monotributista', 'responsable']):
                datos['condicion_iva'] = condicion

        # 2. Si no se encontró en CUIT, intenta con "Curr" o "Condición IVA"
        if not datos.get('condicion_iva'):
            match = re.search(r'(?i)(?:Curr|Condición\s*IVA):?\s*([A-Za-z\s\n]+)', texto)
            if match:
                condicion = match.group(1).strip().split('\n')[0].strip()
                datos['condicion_iva'] = condicion

    # 3. Como último recurso, usa patrones predefinidos
    if not datos.get('condicion_iva'):
        datos['condicion_iva'] = extraer_condicion_iva(texto)

    return datos
