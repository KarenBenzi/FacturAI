import sys
import os
import psycopg2
from utils.pdf_utils import convertir_pdf_a_imagen
from utils.ocr import extraer_texto_de_imagen
from utils.barcode_utils import extraer_codigos_barras
from parsers.parser_metrogas import parsear_factura_metrogas
from parsers.parser_edesur import parsear_factura_edesur
from parsers.parser_movistar import parsear_factura_movistar
from datetime import datetime
from utils.db import conectar_postgresql, insertar_entidad_si_no_existe, insertar_factura


# Añadir la ruta del proyecto (FacturAI) al PYTHONPATH
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

def cargar_facturas(carpeta):
    """
    Carga todas las facturas en formato PDF desde la carpeta especificada.
    
    Args:
        carpeta (str): Ruta de la carpeta donde se encuentran las facturas.
    
    Returns:
        list: Lista con las rutas de las facturas PDF encontradas.
    """
    facturas = []
    for archivo in os.listdir(carpeta):
        if archivo.endswith('.pdf'):
            facturas.append(os.path.join(carpeta, archivo))
    return facturas

def procesar_factura(pdf_path):
    """
    Procesa una factura PDF, extrayendo texto, imagen y códigos de barras.
    
    Args:
        pdf_path (str): Ruta del archivo PDF a procesar.
    
    Returns:
        tuple: texto extraído, imagen en OpenCV, códigos de barras extraídos.
    """
    imagen = convertir_pdf_a_imagen(pdf_path)
    texto, imagen_cv = extraer_texto_de_imagen(imagen)
    codigos = extraer_codigos_barras(imagen_cv)

    return texto, imagen_cv, codigos

def despachar_parser(nombre_archivo, texto, codigos_barras):
    """
    Despacha el parser adecuado basado en el nombre del archivo.
    
    Args:
        nombre_archivo (str): Nombre del archivo de la factura.
        texto (str): Texto extraído de la factura.
        codigos_barras (list): Lista de códigos de barras extraídos.
    
    Returns:
        dict: Datos extraídos de la factura (según el tipo de empresa).
    """
    nombre = nombre_archivo.lower()

    if 'metrogas' in nombre:
        return parsear_factura_metrogas(texto, codigos_barras)
    elif 'edesur' in nombre:
        return parsear_factura_edesur(texto, codigos_barras)
    elif 'movistar' in nombre:
        return parsear_factura_movistar(texto, codigos_barras)
    else:
        raise ValueError("No se encontró parser para el tipo de factura.")

def main():
    """
    Función principal para cargar las facturas, procesarlas y mostrar los resultados.
    """
    carpeta_facturas = 'facturas'  # Ruta a la carpeta donde están las facturas
    facturas = cargar_facturas(carpeta_facturas)
    
    for factura in facturas:
        try:
            texto, imagen_cv, codigos = procesar_factura(factura)
            datos = despachar_parser(os.path.basename(factura), texto, codigos)
            
            print(f'\n✅ Factura procesada: {factura}')
            print(f'Datos extraídos: {datos}')

            # 💾 Insertar en base de datos
            nombre_entidad = datos.get("entidad", "EntidadDesconocida")
            cuil_entidad = datos.get("cuil", "00000000000")

            with conectar_postgresql() as conn:
                with conn.cursor() as cur:
                    entidad_id = insertar_entidad_si_no_existe(cur, nombre_entidad, cuil_entidad)
                    insertar_factura(cur, entidad_id, datos)

            print(f'✅ Factura cargada en la base de datos.\n')

        except Exception as e:
            print(f'\n❌ Error procesando la factura {factura}: {e}')


if __name__ == "__main__":
    main()
