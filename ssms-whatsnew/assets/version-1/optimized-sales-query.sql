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
