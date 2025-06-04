-- Crear la base de datos solo si no existe
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'FacturAI_DB')
BEGIN
    CREATE DATABASE FacturAI_DB;
    PRINT 'Base de datos FacturAI_DB creada correctamente.';
END
ELSE
BEGIN
    PRINT 'La base de datos FacturAI_DB ya existe.';
END
GO

-- Usar la base de datos
USE FacturAI_DB;
GO

-- Crear la tabla Entidades solo si no existe
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Entidades' AND xtype='U')
BEGIN
    CREATE TABLE Entidades (
        ID INT IDENTITY(1,1) PRIMARY KEY,
        nombre NVARCHAR(255) NOT NULL,
        cuit NVARCHAR(20) NOT NULL,
        condicion_iva NVARCHAR(50) NOT NULL
    );
    PRINT 'Tabla Entidades creada correctamente.';
END
ELSE
BEGIN
    PRINT 'La tabla Entidades ya existe.';
END
GO

-- Crear la tabla Facturas solo si no existe
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Facturas' AND xtype='U')
BEGIN
    CREATE TABLE Facturas (
        id INT IDENTITY(1,1) PRIMARY KEY,
        archivo NVARCHAR(255) NOT NULL,
        entidad_id INT NOT NULL,
        cliente NVARCHAR(50),
        cuil CHAR(11),
        monto DECIMAL(18,2),
        vencimiento DATE,
        periodo NVARCHAR(10),
        condicion_iva NVARCHAR(50),
        codigo_barra NVARCHAR(100) UNIQUE,
        fecha_carga DATETIME DEFAULT GETDATE()
    );

    -- Agregar FK entre Facturas.entidad_id y Entidades.ID
    ALTER TABLE Facturas
    ADD CONSTRAINT FK_Facturas_Entidades
    FOREIGN KEY (entidad_id) REFERENCES Entidades(ID);

    PRINT 'Tabla Facturas creada correctamente y FK agregada.';
END
ELSE
BEGIN
    PRINT 'La tabla Facturas ya existe.';
END
GO
