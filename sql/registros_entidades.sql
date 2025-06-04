-- Usar la base de datos
USE FacturAI_DB;
GO

-- Insertar registro de Edesur S.A. si no existe
IF NOT EXISTS (SELECT 1 FROM Entidades WHERE cuit = '30655116512')
BEGIN
    INSERT INTO Entidades (nombre, cuit, condicion_iva)
    VALUES ('Edesur S.A.', '30655116512', 'Responsable Inscripto');
    PRINT 'Registro de Edesur S.A. insertado.';
END
ELSE
BEGIN
    PRINT 'El registro de Edesur S.A. ya existe.';
END

-- Insertar registro de ARBA si no existe
IF NOT EXISTS (SELECT 1 FROM Entidades WHERE cuit = '30657863676')
BEGIN
    INSERT INTO Entidades (nombre, cuit, condicion_iva)
    VALUES ('ARBA', '30657863676', 'Responsable Inscripto');
    PRINT 'Registro de ARBA insertado.';
END
ELSE
BEGIN
    PRINT 'El registro de ARBA ya existe.';
END

-- Insertar registro de Movistar Argentina si no existe
IF NOT EXISTS (SELECT 1 FROM Entidades WHERE cuit = '30678814357')
BEGIN
    INSERT INTO Entidades (nombre, cuit, condicion_iva)
    VALUES ('Movistar Argentina', '30678814357', 'Responsable Inscripto');
    PRINT 'Registro de Movistar Argentina insertado.';
END
ELSE
BEGIN
    PRINT 'El registro de Movistar Argentina ya existe.';
END
GO
