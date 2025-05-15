def parsear_factura_movistar(texto, codigos_barras):
    """
    Parsea una factura de Movistar, extrayendo información útil.

    Parámetros:
    - texto: string con el texto extraído de la factura.
    - codigos_barras: lista de strings con los códigos de barra detectados.

    Retorna:
    - dict con los campos clave extraídos.
    """
    datos = {
        "empresa": "Movistar",
        "cliente": None,
        "domicilio": None,
        "periodo": None,
        "vencimiento": None,
        "importe": None,
        "codigo_barras": codigos_barras[0] if codigos_barras else None
    }

    # Extracciones por patrones simples (adaptar según tu factura escaneada)
    for linea in texto.split("\n"):
        linea = linea.strip()

        if "cliente" in linea.lower():
            datos["cliente"] = linea
        elif "domicilio" in linea.lower():
            datos["domicilio"] = linea
        elif "periodo" in linea.lower():
            datos["periodo"] = linea
        elif "vencimiento" in linea.lower():
            datos["vencimiento"] = linea
        elif "$" in linea or "importe" in linea.lower():
            datos["importe"] = linea

    return datos
