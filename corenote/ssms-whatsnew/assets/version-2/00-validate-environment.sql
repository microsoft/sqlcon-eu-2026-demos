/*
Validates the WideWorldImporters objects and data used by Demo Version 2.
This script does not modify the database.
*/

USE [WideWorldImporters];
GO

SET NOCOUNT ON;

IF OBJECT_ID(N'Sales.Customers', N'U') IS NULL
    THROW 50011, 'Sales.Customers was not found. Restore WideWorldImporters before continuing.', 1;

IF OBJECT_ID(N'Sales.Orders', N'U') IS NULL
    THROW 50012, 'Sales.Orders was not found. Restore WideWorldImporters before continuing.', 1;

IF OBJECT_ID(N'Sales.OrderLines', N'U') IS NULL
    THROW 50013, 'Sales.OrderLines was not found. Restore WideWorldImporters before continuing.', 1;

IF NOT EXISTS
(
    SELECT 1
    FROM Sales.Orders
    WHERE OrderDate >= '20150101'
      AND OrderDate < '20160101'
)
    THROW 50014, 'The database does not contain the 2015 order data required by the demo.', 1;

SELECT
    N'Demo environment ready' AS Status,
    DB_NAME() AS DatabaseName,
    COUNT_BIG(*) AS OrdersIn2015
FROM Sales.Orders
WHERE OrderDate >= '20150101'
  AND OrderDate < '20160101';
GO
