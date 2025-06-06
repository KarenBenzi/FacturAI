import sys
import os
from datetime import datetime
import re

# Librerías propias del proyecto
import pyodbc
from utils.pdf_utils import convertir_pdf_a_imagen
from utils.ocr import extraer_texto_de_imagen
from utils.barcode_utils import extraer_codigos_barras
from parsers.parser_metrogas import parsear_factura_metrogas
from parsers.parser_edesur import parsear_factura_edesur
from parsers.parser_movistar import parsear_factura_movistar

# Añadimos la ruta del proyecto al PYTHONPATH para asegurarnos de que se pueden importar los módulos correctamente
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Esta función se conecta a la base de datos SQL Server
def conectar_sqlserver():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-UOLF2LM;'
        'DATABASE=FacturAI_DB;'
        'Trusted_Connection=yes;'
        'TrustServerCertificate=yes;'
    )
    return conn

# Esta función inserta una factura en la base de datos
def insertar_factura(cursor, datos):
    # Primero revisamos si la factura ya fue cargada, basándonos en el código de barras
    cursor.execute("SELECT COUNT(1) FROM Facturas WHERE codigo_barra = ?", datos['codigo_barra'])
    if cursor.fetchone()[0] > 0:
        return False  # Si ya existe, no la insertamos de nuevo

    # Convertimos el vencimiento de texto a objeto datetime
    try:
        fecha_vencimiento = datetime.strptime(datos['vencimiento'], '%d/%m/%Y')
    except ValueError:
        raise ValueError(f"Formato de vencimiento inválido: {datos['vencimiento']}")

    # Convertimos el periodo también a datetime, usando el día 1 por convención
    try:
        periodo_dt = datetime.strptime(datos['periodo'], '%m/%Y')
    except ValueError:
        raise ValueError(f"Formato de periodo inválido: {datos['periodo']}")

    # Sentencia SQL para insertar los datos en la tabla Facturas
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
        datos.get('cuil'),  # Campo nuevo: CUIL del cliente
    )
    cursor.execute(sql, params)
    return True

# Esta función recorre una carpeta y devuelve todos los archivos PDF que encuentre
def cargar_facturas(carpeta):
    facturas = []
    for archivo in os.listdir(carpeta):
        if archivo.endswith('.pdf'):
            facturas.append(os.path.join(carpeta, archivo))
    return facturas

# Esta función convierte el PDF en imagen, le aplica OCR y lee los códigos de barras
def procesar_factura(pdf_path):
    imagen = convertir_pdf_a_imagen(pdf_path)
    texto, imagen_cv = extraer_texto_de_imagen(imagen)
    codigos = extraer_codigos_barras(imagen_cv)
    # Devuelve el texto reconocido, la imagen procesada y los códigos encontrados
    return texto, imagen_cv, codigos

# Esta función elige qué parser usar según el nombre del archivo
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

# Esta función busca facturas en la base de datos filtrando por CUIL y, opcionalmente, por entidad
def buscar_facturas_por_cuil(cursor, cuil, entidad_id=None):
    query = """
        SELECT Archivo, Entidad_id, Codigo_Barra, Cliente, Monto, Vencimiento,
               Periodo, Condicion_IVA, CUIL
        FROM Facturas
        WHERE CUIL = ?
    """
    params = [cuil]

    if entidad_id:
        query += " AND Entidad_id = ?"
        params.append(entidad_id)

    cursor.execute(query, params)
    columnas = [column[0] for column in cursor.description]
    resultados = cursor.fetchall()
    # Convertimos cada fila en un diccionario con nombres de columnas
    return [dict(zip(columnas, fila)) for fila in resultados]

# Función principal que coordina todo el flujo
def main():
    carpeta_facturas = 'facturas'  # Carpeta donde están los archivos PDF
    facturas = cargar_facturas(carpeta_facturas)  # Cargamos todos los PDFs

    conn = conectar_sqlserver()  # Nos conectamos a la base de datos
    try:
        for factura in facturas:
            try:
                # Procesamos la factura: OCR, códigos de barras, etc.
                texto, imagen_cv, codigos = procesar_factura(factura)

                # Usamos el parser adecuado según el tipo de factura
                datos = despachar_parser(os.path.basename(factura), texto, codigos)

                # Agregamos el nombre del archivo al diccionario de datos
                datos['archivo'] = os.path.basename(factura)

                print(f'\nFactura procesada: {factura}')
                print(f'Datos extraídos: {datos}')

                # Intentamos insertar los datos en la base
                with conn.cursor() as cursor:
                    inserted = insertar_factura(cursor, datos)
                    if inserted:
                        conn.commit()  # Confirmamos si fue insertada
                        print('Factura cargada en la base de datos.\n')
                    else:
                        print(f'La factura con código de barra {datos["codigo_barra"]} ya fue cargada previamente.\n')

            except Exception as e:
                # Si hubo algún error procesando la factura, lo mostramos
                print(f'Error procesando la factura {factura}: {e}')
    finally:
        conn.close()  # Cerramos la conexión a la base de datos

# Este bloque se ejecuta si el script se corre directamente
if __name__ == "__main__":
    main()
