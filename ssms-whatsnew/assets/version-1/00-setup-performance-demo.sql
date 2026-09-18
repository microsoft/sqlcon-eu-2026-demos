/*
Sets up the repeatable performance comparison for Demo Version 1.
Run once against a disposable or approved WideWorldImporters demo database.
*/

USE [WideWorldImporters];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

IF OBJECT_ID(N'Sales.Orders', N'U') IS NULL
    THROW 50001, 'Sales.Orders was not found. Restore WideWorldImporters before continuing.', 1;

IF OBJECT_ID(N'Sales.OrderLines', N'U') IS NULL
    THROW 50002, 'Sales.OrderLines was not found. Restore WideWorldImporters before continuing.', 1;

IF NOT EXISTS
(
    SELECT 1
    FROM Sales.Orders
    WHERE OrderDate >= '20150101'
      AND OrderDate < '20160101'
)
    THROW 50003, 'The database does not contain the 2015 order data required by the demo.', 1;

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'Sales.Orders')
      AND name = N'IX_SQLCon_Orders_OrderDate'
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_SQLCon_Orders_OrderDate
        ON Sales.Orders (OrderDate)
        INCLUDE (CustomerID);
END;

UPDATE STATISTICS Sales.Orders WITH FULLSCAN;
UPDATE STATISTICS Sales.OrderLines WITH FULLSCAN;

SELECT
    N'Demo setup complete' AS Status,
    DB_NAME() AS DatabaseName,
    COUNT_BIG(*) AS OrdersIn2015
FROM Sales.Orders
WHERE OrderDate >= '20150101'
  AND OrderDate < '20160101';
GO
