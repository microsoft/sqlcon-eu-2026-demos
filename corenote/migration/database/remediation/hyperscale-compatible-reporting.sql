/* DB-001 remediation: colocate the small reference table in the target database. */
CREATE TABLE dbo.RegionTaxRates
(
    Region nvarchar(80) NOT NULL CONSTRAINT PK_RegionTaxRates PRIMARY KEY,
    TaxRate decimal(6, 4) NOT NULL
);
GO

INSERT dbo.RegionTaxRates (Region, TaxRate)
VALUES (N'Northeast', 0.0625), (N'Southeast', 0.0575),
       (N'Midwest', 0.0525), (N'Southwest', 0.0475), (N'Pacific', 0.0725);
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
    INNER JOIN dbo.RegionTaxRates AS rates ON rates.Region = customers.Region;
GO