def insertar_factura(cursor, datos):
    """
    Inserta una factura en la base de datos si no existe ya una con el mismo código de barras.
    
    Args:
        cursor: Cursor de la base de datos.
        datos: Diccionario con los datos extraídos de la factura.
    
    Returns:
        bool: True si se insertó, False si ya existía.
    """
    # Buscar entidad_id
    cursor.execute("SELECT id FROM Entidades WHERE cuit = %s", (datos['cuit'],))
    entidad = cursor.fetchone()

    if not entidad:
        print(f"Entidad con CUIT {datos['cuit']} no encontrada.")
        return False

    entidad_id = entidad[0]

    # Verificar si ya existe la factura por código de barras
    cursor.execute("SELECT 1 FROM Facturas WHERE codigo_barra = %s", (datos['codigo_barra'],))
    if cursor.fetchone():
        return False

    # Insertar factura
    cursor.execute("""
        INSERT INTO Facturas (
            archivo, entidad_id, cliente, monto, vencimiento, periodo,
            condicion_iva, codigo_barra, fecha_carga
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, GETDATE())
    """, (
        datos['archivo'],
        entidad_id,
        datos.get('cliente'),
        datos.get('monto'),
        datos.get('vencimiento'),
        datos.get('periodo'),
        datos.get('condicion_iva'),
        datos.get('codigo_barra')
    ))

    return True
