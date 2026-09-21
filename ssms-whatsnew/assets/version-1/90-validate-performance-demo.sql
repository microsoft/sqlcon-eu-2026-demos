/*
Validation only. Compare the execution plans and confirm both queries return
the same five rows before rehearsing the demo.
*/

USE [WideWorldImporters];
GO

SET NOCOUNT ON;
SET STATISTICS IO ON;
SET STATISTICS TIME ON;

-- Demo query: the function on OrderDate makes the predicate non-SARGable.
SELECT TOP 5
    o.CustomerID,
    SUM(ol.Quantity * ol.UnitPrice) AS SalesValue
FROM Sales.Orders AS o
JOIN Sales.OrderLines AS ol
    ON o.OrderID = ol.OrderID
WHERE YEAR(o.OrderDate) = 2015
GROUP BY o.CustomerID
ORDER BY SalesValue DESC;

-- Reference query: the date range can use an index seek.
SELECT TOP 5
    o.CustomerID,
    SUM(ol.Quantity * ol.UnitPrice) AS SalesValue
FROM Sales.Orders AS o
JOIN Sales.OrderLines AS ol
    ON o.OrderID = ol.OrderID
WHERE o.OrderDate >= '20150101'
  AND o.OrderDate < '20160101'
GROUP BY o.CustomerID
ORDER BY SalesValue DESC;

SET STATISTICS TIME OFF;
SET STATISTICS IO OFF;
GO
