USE master;
GO

IF DB_ID(N'AdventureWorksLT') IS NULL
BEGIN
    CREATE DATABASE AdventureWorksLT;
END;
GO

USE AdventureWorksLT;
GO

IF SCHEMA_ID(N'SalesLT') IS NULL
BEGIN
    EXEC(N'CREATE SCHEMA SalesLT AUTHORIZATION dbo;');
END;
GO

IF OBJECT_ID(N'SalesLT.Product', N'U') IS NULL
BEGIN
    CREATE TABLE SalesLT.Product
    (
        ProductID INT NOT NULL,
        Name NVARCHAR(100) NOT NULL,
        CONSTRAINT PK_Product PRIMARY KEY (ProductID)
    );
END;
GO

WITH SeedProducts AS
(
    SELECT ProductID, Name
    FROM (VALUES
        (680, N'HL Road Frame - Black, 58'),
        (706, N'HL Road Frame - Red, 58'),
        (707, N'Sport-100 Helmet, Red'),
        (708, N'Sport-100 Helmet, Black'),
        (709, N'Mountain Bike Socks, M')
    ) AS Products(ProductID, Name)
)
INSERT SalesLT.Product (ProductID, Name)
SELECT SeedProducts.ProductID, SeedProducts.Name
FROM SeedProducts
WHERE NOT EXISTS
(
    SELECT 1
    FROM SalesLT.Product
    WHERE SalesLT.Product.ProductID = SeedProducts.ProductID
);
GO