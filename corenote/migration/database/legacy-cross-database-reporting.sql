/*
  INTENTIONAL MIGRATION ISSUE DB-001
  Azure SQL Database Hyperscale does not support this SQL Server-style
  three-part-name dependency on another user database.
    Run after the web app has created and seeded Operations locally.
*/
USE master;
GO

IF DB_ID(N'OpsFinance') IS NULL
        CREATE DATABASE OpsFinance;
GO

USE OpsFinance;
GO

IF OBJECT_ID(N'dbo.RegionTaxRates', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.RegionTaxRates
    (
        Region nvarchar(80) NOT NULL CONSTRAINT PK_RegionTaxRates PRIMARY KEY,
        TaxRate decimal(6, 4) NOT NULL
    );

    INSERT dbo.RegionTaxRates (Region, TaxRate)
    VALUES (N'Northeast', 0.0625), (N'Southeast', 0.0575),
           (N'Midwest', 0.0525), (N'Southwest', 0.0475), (N'Pacific', 0.0725);
END;
GO

USE Operations;
GO

CREATE OR ALTER VIEW dbo.vw_OrderRegionalTax
AS
    SELECT orders.Id AS OrderId,
           customers.Region,
           orders.TotalAmount,
           rates.TaxRate,
           orders.TotalAmount * rates.TaxRate AS EstimatedTax
    FROM dbo.Orders AS orders
    INNER JOIN dbo.Customers AS customers ON customers.Id = orders.CustomerId
    INNER JOIN OpsFinance.dbo.RegionTaxRates AS rates
        ON rates.Region = customers.Region;
GO

SELECT TOP (10) * FROM dbo.vw_OrderRegionalTax ORDER BY OrderId DESC;
GO

Create table dbo.porter 
(
    Id int NOT NULL CONSTRAINT PK_porter PRIMARY KEY,
    Name nvarchar(100) NOT NULL,
    Region nvarchar(80) NOT NULL,
    ToRegion nvarchar(80) NOT NULL,
    Next nvarchar(90),
);
GO
