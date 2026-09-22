/*
Removes the demo-only index created by 00-setup-performance-demo.sql.
Run only when the demo environment is no longer needed.
*/

USE [WideWorldImporters];
GO

DECLARE @IndexName sysname = N'IX_SQLCon_Orders_OrderDate';
DECLARE @OwnershipMarker sysname = N'SQLConDemoOwns_IX_SQLCon_Orders_OrderDate';

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
    THROW 50001, 'The index is not marked as demo-owned and will not be removed.', 1;

IF EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'Sales.Orders')
      AND name = @IndexName
)
BEGIN
    DROP INDEX IX_SQLCon_Orders_OrderDate ON Sales.Orders;
END;
GO
