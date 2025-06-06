# Importación de librerías necesarias
import os
import csv
from flask import (
    Flask, request, render_template, redirect,
    url_for, flash, session, send_file
)
from flask import make_response
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO

# Se importan funciones desde el archivo principal (main.py)
from main import (
    procesar_factura, despachar_parser,
    conectar_sqlserver, insertar_factura,
    buscar_facturas_por_cuil  # Nueva función para búsqueda por CUIL
)

# Se define la carpeta donde se van a guardar los archivos subidos
UPLOAD_FOLDER = 'uploads'
# Se permite únicamente archivos con extensión .pdf
ALLOWED_EXTENSIONS = {'pdf'}

# Se configura la aplicación Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'tu_clave_secreta'  # Clave para mantener la sesión

# Si no existe la carpeta de uploads, se crea
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Función auxiliar para validar que el archivo tenga una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta principal: muestra el formulario de carga
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Ruta para procesar los archivos subidos
@app.route('/procesar', methods=['POST'])
def procesar():
    # Se valida que se hayan subido archivos
    if 'files[]' not in request.files:
        flash('No se seleccionaron archivos')
        return redirect(url_for('index'))

    # Se obtiene el CUIL ingresado por el usuario
    cuil = request.form.get('cuil')
    files = request.files.getlist('files[]')  # Lista de archivos subidos
    resultados = []
    primer_cuil_extraido = None  # Para guardar el primer CUIL extraído desde el archivo

    try:
        with conectar_sqlserver() as conn:
            cursor = conn.cursor()

            for file in files:
                # Validación del archivo y guardado temporal
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    try:
                        # Se extrae el texto del PDF y se analiza el contenido
                        texto, imagen_cv, codigos = procesar_factura(filepath)
                        datos = despachar_parser(filename, texto, codigos)
                        datos['archivo'] = filename
                        datos['cuil'] = cuil

                        # Se guarda el primer CUIL extraído, si no estaba definido aún
                        if not primer_cuil_extraido and datos.get('cuil'):
                            primer_cuil_extraido = datos['cuil']

                        # Inserta los datos en la base de datos si no existe previamente
                        inserted = insertar_factura(cursor, datos)
                        if inserted:
                            conn.commit()
                            resultados.append({'archivo': filename, 'datos': datos})
                        else:
                            resultados.append({
                                'archivo': filename,
                                'error': f"La factura con código {datos['codigo_barra']} ya fue cargada previamente."
                            })
                    except Exception as e:
                        resultados.append({'archivo': filename, 'error': str(e)})

                    # Borra el archivo después de procesarlo
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        print(f"Error al eliminar el archivo {filepath}: {e}")
                else:
                    resultados.append({'archivo': file.filename, 'error': 'Formato no permitido'})

    except Exception as e:
        flash(f'Error al conectar con la base de datos: {e}')
        return redirect(url_for('index'))

    # Se guardan los resultados y el CUIL extraído en la sesión
    session['resultados'] = resultados
    session['cuil'] = primer_cuil_extraido or cuil

    # Redirecciona a la vista de resultados
    return redirect(url_for('resultados'))

# Ruta para mostrar los resultados luego del procesamiento
@app.route('/resultados', methods=['GET'])
def resultados():
    resultados = session.get('resultados')
    cuil = session.get('cuil')
    if not resultados:
        flash("No hay resultados disponibles.")
        return redirect(url_for('index'))
    return render_template('resultados.html', resultados=resultados, cuil=cuil)

# Ruta para descargar los resultados procesados en formato CSV
@app.route('/descargar_csv')
def descargar_csv():
    resultados = session.get('resultados')
    if not resultados:
        flash("No hay resultados para descargar.")
        return redirect(url_for('index'))

    # Se crea un CSV en memoria con los datos procesados
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow([
        'Archivo', 'Entidad', 'Código de barra', 'Cliente', 'Monto',
        'Vencimiento', 'Periodo', 'Condición IVA', 'CUIL', 'Estado'
    ])

    for r in resultados:
        if 'error' in r:
            continue
        datos = r['datos']
        entidad = {
            1: 'Edesur',
            2: 'Metrogas',
            3: 'Movistar'
        }.get(datos.get('entidad_id'), 'Desconocida')

        writer.writerow([
            r['archivo'],
            entidad,
            datos.get('codigo_barra', ''),
            datos.get('cliente', ''),
            datos.get('monto', ''),
            datos.get('vencimiento', ''),
            datos.get('periodo', ''),
            datos.get('condicion_iva', ''),
            datos.get('cuil', ''),
            'Procesado'
        ])

    # Se convierte el CSV a un archivo descargable
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    si.close()

    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='facturas_procesadas.csv'
    )

# Ruta para buscar facturas previamente procesadas, filtrando por CUIL (y opcionalmente por entidad)
@app.route('/buscar_facturas', methods=['GET'])
def buscar_facturas():
    cuil = request.args.get('cuil')
    entidad_id = request.args.get('entidad_id')
    
    if not cuil:
        flash("Debe ingresar un CUIL para buscar.")
        return redirect(url_for('index'))

    try:
        with conectar_sqlserver() as conn:
            cursor = conn.cursor()
            facturas = buscar_facturas_por_cuil(cursor, cuil, entidad_id if entidad_id else None)
            if not facturas:
                flash(f"No se encontraron facturas para el CUIL: {cuil}")
                return redirect(url_for('index'))
            return render_template('buscar_facturas.html', facturas=facturas, cuil=cuil)
    except Exception as e:
        flash(f"Error al buscar facturas: {e}")
        return redirect(url_for('index'))

# Ruta para descargar las facturas previamente consultadas desde la base de datos
@app.route('/descargar_facturas', methods=['GET'])
def descargar_facturas():
    cuil = request.args.get('cuil')
    entidad_id = request.args.get('entidad_id')

    if not cuil:
        flash("Debe ingresar un CUIL para buscar.")
        return redirect(url_for('index'))

    try:
        with conectar_sqlserver() as conn:
            cursor = conn.cursor()
            facturas = buscar_facturas_por_cuil(cursor, cuil, entidad_id if entidad_id else None)
            if not facturas:
                flash(f"No se encontraron facturas para el CUIL: {cuil}")
                return redirect(url_for('index'))
            
            # Se genera el CSV directamente desde los datos obtenidos
            si = StringIO()
            writer = csv.DictWriter(si, fieldnames=facturas[0].keys())
            writer.writeheader()
            writer.writerows(facturas)
            output = si.getvalue()
            
            # Se devuelve como archivo descargable
            response = make_response(output)
            response.headers["Content-Disposition"] = f"attachment; filename=facturas_{cuil}.csv"
            response.headers["Content-type"] = "text/csv; charset=utf-8"
            return response

    except Exception as e:
        flash(f"Error al descargar facturas: {e}")
        return redirect(url_for('index'))

# Punto de entrada principal para ejecutar la aplicación Flask
if __name__ == "__main__":
    app.run(debug=True)
