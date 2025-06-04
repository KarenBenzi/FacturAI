import os
import csv
from flask import (
    Flask, request, render_template, redirect,
    url_for, flash, session, send_file
)
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO

from main import procesar_factura, despachar_parser, conectar_sqlserver, insertar_factura

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'tu_clave_secreta'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/procesar', methods=['POST'])
def procesar():
    if 'files[]' not in request.files:
        flash('No se seleccionaron archivos')
        return redirect(url_for('index'))

    files = request.files.getlist('files[]')
    resultados = []

    try:
        with conectar_sqlserver() as conn:
            cursor = conn.cursor()

            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    try:
                        texto, imagen_cv, codigos = procesar_factura(filepath)
                        datos = despachar_parser(filename, texto, codigos)
                        datos['archivo'] = filename

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

                    # Borrar archivo aquí, fuera del try-except interno
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        print(f"Error al eliminar el archivo {filepath}: {e}")
                else:
                    resultados.append({'archivo': file.filename, 'error': 'Formato no permitido'})

    except Exception as e:
        flash(f'Error al conectar con la base de datos: {e}')
        return redirect(url_for('index'))

    session['resultados'] = resultados
    return redirect(url_for('resultados'))

@app.route('/resultados', methods=['GET'])
def resultados():
    resultados = session.get('resultados')
    if not resultados:
        flash("No hay resultados disponibles.")
        return redirect(url_for('index'))
    return render_template('resultados.html', resultados=resultados)

@app.route('/descargar_csv')
def descargar_csv():
    resultados = session.get('resultados')
    if not resultados:
        flash("No hay resultados para descargar.")
        return redirect(url_for('index'))

    si = StringIO()
    writer = csv.writer(si)

    writer.writerow([
        'Archivo', 'Entidad', 'Código de barra', 'Cliente', 'Monto',
        'Vencimiento', 'Periodo', 'Condición IVA', 'Estado'
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
            'Procesado'
        ])

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

if __name__ == "__main__":
    app.run(debug=True)
