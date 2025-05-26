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

def insertar_factura(cursor, entidad_id, datos):
    # Convertir vencimiento a formato fecha
    vencimiento = None
    if datos.get("vencimiento"):
        try:
            vencimiento = datetime.strptime(datos["vencimiento"], "%d/%m/%Y").date()
        except:
            vencimiento = None

    cursor.execute("""
        INSERT INTO facturas (entidad_id, monto, cliente, domicilio, medidor, vencimiento, periodo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        entidad_id,
        float(datos.get("monto", 0)) if datos.get("monto") else None,
        datos.get("cliente"),
        datos.get("domicilio"),
        datos.get("medidor"),
        vencimiento,
        datos.get("periodo")
    ))
