import os
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from main import procesar_factura, despachar_parser

UPLOAD_FOLDER = 'uploads'  # carpeta temporal para guardar PDFs subidos
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'tu_clave_secreta'  # para mensajes flash

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')  # formulario para subir PDFs

@app.route('/procesar', methods=['POST'])
def procesar():
    if 'files[]' not in request.files:
        flash('No se seleccionaron archivos')
        return redirect(request.url)

    files = request.files.getlist('files[]')
    resultados = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                texto, imagen_cv, codigos = procesar_factura(filepath)
                datos = despachar_parser(filename, texto, codigos)
                resultados.append({'archivo': filename, 'datos': datos})
            except Exception as e:
                resultados.append({'archivo': filename, 'error': str(e)})

    return render_template('resultados.html', resultados=resultados)

if __name__ == "__main__":
    app.run(debug=True)
