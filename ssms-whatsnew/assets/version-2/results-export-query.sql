USE [WideWorldImporters];
GO

SELECT TOP 5
    c.CustomerName,
    COUNT(DISTINCT o.OrderID) AS OrderCount,
    CAST(SUM(ol.Quantity * ol.UnitPrice) AS decimal(18, 2)) AS SalesValue
FROM Sales.Customers AS c
JOIN Sales.Orders AS o
    ON c.CustomerID = o.CustomerID
JOIN Sales.OrderLines AS ol
    ON o.OrderID = ol.OrderID
WHERE o.OrderDate >= '20150101'
  AND o.OrderDate < '20160101'
GROUP BY c.CustomerName
ORDER BY SalesValue DESC;
