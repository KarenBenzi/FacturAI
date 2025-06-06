import os
import csv
from flask import (
    Flask, request, render_template, redirect,
    url_for, flash, session, send_file
)
from werkzeug.utils import secure_filename
from io import StringIO, BytesIO

# ✅ NUEVO: importar la función de búsqueda
from main import (
    procesar_factura, despachar_parser,
    conectar_sqlserver, insertar_factura,
    buscar_facturas_por_cuil  # ✅ NUEVO
)

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

    cuil = request.form.get('cuil')
    files = request.files.getlist('files[]')
    resultados = []
    primer_cuil_extraido = None

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
                        datos['cuil'] = cuil

                        if not primer_cuil_extraido and datos.get('cuil'):
                            primer_cuil_extraido = datos['cuil']

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
    session['cuil'] = primer_cuil_extraido or cuil

    return redirect(url_for('resultados'))

@app.route('/resultados', methods=['GET'])
def resultados():
    resultados = session.get('resultados')
    cuil = session.get('cuil')
    if not resultados:
        flash("No hay resultados disponibles.")
        return redirect(url_for('index'))
    return render_template('resultados.html', resultados=resultados, cuil=cuil)

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

# ✅ NUEVO: ruta para buscar facturas por CUIL
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


# 🔚 FIN DEL BLOQUE NUEVO

if __name__ == "__main__":
    app.run(debug=True)
