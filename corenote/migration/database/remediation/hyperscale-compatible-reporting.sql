/*
  Azure SQL Database remediation for the Operations demo database.
  Run this against the source SQL Server before BACPAC export.
  Stop the application before running this script. The script is idempotent.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

USE master;
GO

IF DB_ID(N'Operations') IS NULL
    THROW 50001, 'The Operations database does not exist.', 1;

IF DB_ID(N'OpsFinance') IS NULL
    THROW 50002, 'The OpsFinance database does not exist.', 1;

IF OBJECT_ID(N'OpsFinance.dbo.RegionTaxRates', N'U') IS NULL
    THROW 50003, 'OpsFinance.dbo.RegionTaxRates does not exist.', 1;

IF (SELECT COUNT(*) FROM OpsFinance.dbo.RegionTaxRates) <> 5
    THROW 50004, 'OpsFinance.dbo.RegionTaxRates must contain exactly five rows.', 1;
GO

IF EXISTS (SELECT 1 FROM sys.databases WHERE name = N'Operations' AND is_broker_enabled = 1)
    ALTER DATABASE Operations SET DISABLE_BROKER WITH ROLLBACK IMMEDIATE;
GO

USE Operations;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.porter', N'U') IS NULL
        THROW 50005, 'Operations.dbo.porter does not exist.', 1;

    IF COL_LENGTH(N'dbo.porter', N'Next') IS NOT NULL
       AND COL_LENGTH(N'dbo.porter', N'NextStep') IS NULL
        EXEC sys.sp_rename N'dbo.porter.Next', N'NextStep', N'COLUMN';

    IF COL_LENGTH(N'dbo.porter', N'Next') IS NOT NULL
       OR COL_LENGTH(N'dbo.porter', N'NextStep') IS NULL
        THROW 50006, 'The dbo.porter column could not be remediated to NextStep.', 1;

    IF OBJECT_ID(N'dbo.RegionTaxRates', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.RegionTaxRates
        (
            Region nvarchar(80) NOT NULL CONSTRAINT PK_RegionTaxRates PRIMARY KEY,
            TaxRate decimal(6, 4) NOT NULL
        );
    END;

    UPDATE target
    SET target.TaxRate = source.TaxRate
    FROM dbo.RegionTaxRates AS target
    INNER JOIN OpsFinance.dbo.RegionTaxRates AS source
        ON source.Region = target.Region;

    INSERT dbo.RegionTaxRates (Region, TaxRate)
    SELECT source.Region, source.TaxRate
    FROM OpsFinance.dbo.RegionTaxRates AS source
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM dbo.RegionTaxRates AS target
        WHERE target.Region = source.Region
    );

    EXEC(N'
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
    ');

    IF (SELECT COUNT(*) FROM dbo.RegionTaxRates) <> 5
        THROW 50007, 'Operations.dbo.RegionTaxRates must contain exactly five rows.', 1;

    IF NOT EXISTS (SELECT 1 FROM dbo.vw_OrderRegionalTax)
        THROW 50008, 'dbo.vw_OrderRegionalTax returned no rows.', 1;

    IF EXISTS
    (
        SELECT 1
        FROM sys.sql_expression_dependencies
        WHERE referenced_database_name IS NOT NULL
    )
        THROW 50009, 'A cross-database dependency remains in Operations.', 1;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

SELECT
    TaxRateCount = (SELECT COUNT(*) FROM dbo.RegionTaxRates),
    ViewRowCount = (SELECT COUNT(*) FROM dbo.vw_OrderRegionalTax),
    CrossDatabaseDependencyCount =
    (
        SELECT COUNT(*)
        FROM sys.sql_expression_dependencies
        WHERE referenced_database_name IS NOT NULL
    ),
    ServiceBrokerEnabled =
    (
        SELECT is_broker_enabled
        FROM sys.databases
        WHERE name = N'Operations'
    ),
    NextColumnCount =
    (
        SELECT COUNT(*)
        FROM sys.columns
        WHERE object_id = OBJECT_ID(N'dbo.porter')
          AND name = N'Next'
    ),
    NextStepColumnCount =
    (
        SELECT COUNT(*)
        FROM sys.columns
        WHERE object_id = OBJECT_ID(N'dbo.porter')
          AND name = N'NextStep'
    );
GO