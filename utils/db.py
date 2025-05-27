# utils/db.py

import psycopg2
from datetime import datetime

def conectar_postgresql():
    return psycopg2.connect(
        host="localhost",
        port="5432",
        dbname="facturas_db",
        user="tu_usuario",
        password="Argentina5_"
    )

def insertar_entidad_si_no_existe(cursor, nombre, cuil):
    cursor.execute("""
        SELECT id FROM entidad WHERE nombre = %s AND cuil = %s
    """, (nombre, cuil))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute("""
            INSERT INTO entidad (nombre, cuil) VALUES (%s, %s) RETURNING id
        """, (nombre, cuil))
        return cursor.fetchone()[0]

def insertar_factura(cur, datos):
    from datetime import datetime
    vencimiento_date = datetime.strptime(datos['vencimiento'], '%d/%m/%Y').date()

    # Verificar si el codigo_barra ya existe
    cur.execute("SELECT 1 FROM facturas WHERE codigo_barra = %s", (datos['codigo_barra'],))
    if cur.fetchone():
        return False  # Ya existe

    query = """
    INSERT INTO facturas (entidad_id, cliente, monto, codigo_barra, vencimiento, periodo)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    valores = (
        datos['entidad_id'],
        datos['cliente'],
        float(datos['monto']),
        datos['codigo_barra'],
        vencimiento_date,
        datos['periodo'],
        datos.get('condicion_iva')  # Puede ser None si no viene
)
    cur.execute(query, valores)
    return True
