/*
Sets up the repeatable performance comparison for Demo Version 1.
Run once against a disposable or approved WideWorldImporters demo database.
*/

USE [WideWorldImporters];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @IndexName sysname = N'IX_SQLCon_Orders_OrderDate';
DECLARE @OwnershipMarker sysname = N'SQLConDemoOwns_IX_SQLCon_Orders_OrderDate';

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

IF EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'Sales.Orders')
      AND name = @IndexName
)
AND NOT EXISTS
(
    SELECT 1
        FROM sys.extended_properties AS ep
        JOIN sys.indexes AS i
            ON i.object_id = ep.major_id
         AND i.index_id = ep.minor_id
        WHERE ep.class = 7
            AND i.object_id = OBJECT_ID(N'Sales.Orders')
            AND i.name = @IndexName
            AND ep.name = @OwnershipMarker
)
    THROW 50004, 'The demo index name is already in use and is not marked as demo-owned. Review it manually.', 1;

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'Sales.Orders')
      AND name = @IndexName
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_SQLCon_Orders_OrderDate
        ON Sales.Orders (OrderDate)
        INCLUDE (CustomerID);
END;

IF NOT EXISTS
(
    SELECT 1
        FROM sys.extended_properties AS ep
        JOIN sys.indexes AS i
            ON i.object_id = ep.major_id
         AND i.index_id = ep.minor_id
        WHERE ep.class = 7
            AND i.object_id = OBJECT_ID(N'Sales.Orders')
            AND i.name = @IndexName
            AND ep.name = @OwnershipMarker
)
BEGIN
    EXEC sys.sp_addextendedproperty
        @name = @OwnershipMarker,
        @value = N'Created by the SQLCon SSMS demo setup.',
        @level0type = N'SCHEMA',
        @level0name = N'Sales',
        @level1type = N'TABLE',
        @level1name = N'Orders',
        @level2type = N'INDEX',
        @level2name = @IndexName;
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
