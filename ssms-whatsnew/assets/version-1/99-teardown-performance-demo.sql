/*
Removes the demo-only index created by 00-setup-performance-demo.sql.
Run only when the demo environment is no longer needed.
*/

USE [WideWorldImporters];
GO

IF EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'Sales.Orders')
      AND name = N'IX_SQLCon_Orders_OrderDate'
)
BEGIN
    DROP INDEX IX_SQLCon_Orders_OrderDate ON Sales.Orders;
END;
GO
