import sys
import os
from datetime import datetime

import pyodbc
from utils.pdf_utils import convertir_pdf_a_imagen
from utils.ocr import extraer_texto_de_imagen
from utils.barcode_utils import extraer_codigos_barras
from parsers.parser_metrogas import parsear_factura_metrogas
from parsers.parser_edesur import parsear_factura_edesur
from parsers.parser_movistar import parsear_factura_movistar

# Añadir la ruta del proyecto (FacturAI) al PYTHONPATH
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def conectar_sqlserver():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-UOLF2LM;'
        'DATABASE=FacturAI_DB;'
        'Trusted_Connection=yes;'
        'TrustServerCertificate=yes;'
    )
    return conn

def insertar_factura(cursor, datos):
    # Verificar si ya existe
    cursor.execute("SELECT COUNT(1) FROM Facturas WHERE codigo_barra = ?", datos['codigo_barra'])
    if cursor.fetchone()[0] > 0:
        return False

    # Convertir vencimiento de str a datetime
    try:
        fecha_vencimiento = datetime.strptime(datos['vencimiento'], '%d/%m/%Y')
    except ValueError:
        raise ValueError(f"Formato de vencimiento inválido: {datos['vencimiento']}")

    # Convertir periodo de str a datetime (usamos día 1 del mes por convención)
    try:
        periodo_dt = datetime.strptime(datos['periodo'], '%m/%Y')
    except ValueError:
        raise ValueError(f"Formato de periodo inválido: {datos['periodo']}")

    sql = """
    INSERT INTO Facturas (archivo, entidad_id, cliente, monto, vencimiento, periodo, condicion_iva, codigo_barra, cuil)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        datos.get('archivo'),
        datos.get('entidad_id'),
        datos.get('cliente'),
        datos.get('monto'),
        fecha_vencimiento,
        periodo_dt,
        datos.get('condicion_iva'),
        datos.get('codigo_barra'),
        datos.get('cuil'),   # <-- Nuevo campo CUIL
    )
    cursor.execute(sql, params)
    return True

def cargar_facturas(carpeta):
    facturas = []
    for archivo in os.listdir(carpeta):
        if archivo.endswith('.pdf'):
            facturas.append(os.path.join(carpeta, archivo))
    return facturas

def procesar_factura(pdf_path):
    imagen = convertir_pdf_a_imagen(pdf_path)
    texto, imagen_cv = extraer_texto_de_imagen(imagen)
    codigos = extraer_codigos_barras(imagen_cv)
    return texto, imagen_cv, codigos

def despachar_parser(nombre_archivo, texto, codigos_barras):
    nombre = nombre_archivo.lower()
    if 'metrogas' in nombre:
        return parsear_factura_metrogas(texto, codigos_barras)
    elif 'edesur' in nombre:
        return parsear_factura_edesur(texto, codigos_barras)
    elif 'movistar' in nombre:
        return parsear_factura_movistar(texto, codigos_barras)
    else:
        raise ValueError("No se encontró módulo para el tipo de factura.")

def main():
    carpeta_facturas = 'facturas'
    facturas = cargar_facturas(carpeta_facturas)

    conn = conectar_sqlserver()
    try:
        for factura in facturas:
            try:
                texto, imagen_cv, codigos = procesar_factura(factura)
                datos = despachar_parser(os.path.basename(factura), texto, codigos)
                datos['archivo'] = os.path.basename(factura)

                print(f'\nFactura procesada: {factura}')
                print(f'Datos extraídos: {datos}')

                with conn.cursor() as cursor:
                    inserted = insertar_factura(cursor, datos)
                    if inserted:
                        conn.commit()
                        print('Factura cargada en la base de datos.\n')
                    else:
                        print(f'La factura con código de barra {datos["codigo_barra"]} ya fue cargada previamente.\n')

            except Exception as e:
                print(f'Error procesando la factura {factura}: {e}')
    finally:
        conn.close()

if __name__ == "__main__":
    main()