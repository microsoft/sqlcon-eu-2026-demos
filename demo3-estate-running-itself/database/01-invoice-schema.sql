/*
    Demo 3 sample schema: a small operations database with one deliberate anti-pattern.

    InvoiceNumber is VARCHAR. When the application sends an NVARCHAR parameter, SQL
    Server applies CONVERT_IMPLICIT to the column and the index seek becomes a scan.
    The fix is one word in the application; the schema never changes.
*/

SET NOCOUNT ON;
SET XACT_ABORT ON;

IF OBJECT_ID(N'dbo.InvoiceLine', N'U') IS NOT NULL DROP TABLE dbo.InvoiceLine;
IF OBJECT_ID(N'dbo.Invoice', N'U') IS NOT NULL DROP TABLE dbo.Invoice;
IF OBJECT_ID(N'dbo.Customer', N'U') IS NOT NULL DROP TABLE dbo.Customer;

CREATE TABLE dbo.Customer
(
    CustomerId INT NOT NULL,
    CustomerName NVARCHAR(200) NOT NULL,
    Region NVARCHAR(60) NOT NULL,
    CONSTRAINT PK_Customer PRIMARY KEY CLUSTERED (CustomerId)
);

CREATE TABLE dbo.Invoice
(
    InvoiceId INT NOT NULL,
    -- Deliberately VARCHAR. The application parameter must match this type.
    InvoiceNumber VARCHAR(20) NOT NULL,
    CustomerId INT NOT NULL,
    InvoiceDate DATE NOT NULL,
    DueDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL,
    TotalAmount DECIMAL(12, 2) NOT NULL,
    CONSTRAINT PK_Invoice PRIMARY KEY CLUSTERED (InvoiceId),
    CONSTRAINT FK_Invoice_Customer FOREIGN KEY (CustomerId) REFERENCES dbo.Customer (CustomerId),
    CONSTRAINT CK_Invoice_Status CHECK (Status IN ('Draft', 'Sent', 'Paid', 'Overdue', 'Void')),
    CONSTRAINT CK_Invoice_TotalAmount CHECK (TotalAmount >= 0)
);

CREATE UNIQUE NONCLUSTERED INDEX IX_Invoice_InvoiceNumber
    ON dbo.Invoice (InvoiceNumber)
    INCLUDE (CustomerId, InvoiceDate, Status, TotalAmount);

CREATE NONCLUSTERED INDEX IX_Invoice_Status_InvoiceDate
    ON dbo.Invoice (Status, InvoiceDate DESC)
    INCLUDE (InvoiceNumber, CustomerId, TotalAmount);

CREATE TABLE dbo.InvoiceLine
(
    InvoiceLineId INT NOT NULL,
    InvoiceId INT NOT NULL,
    Description NVARCHAR(200) NOT NULL,
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(12, 2) NOT NULL,
    CONSTRAINT PK_InvoiceLine PRIMARY KEY CLUSTERED (InvoiceLineId),
    CONSTRAINT FK_InvoiceLine_Invoice FOREIGN KEY (InvoiceId) REFERENCES dbo.Invoice (InvoiceId),
    CONSTRAINT CK_InvoiceLine_Quantity CHECK (Quantity > 0)
);

CREATE NONCLUSTERED INDEX IX_InvoiceLine_InvoiceId ON dbo.InvoiceLine (InvoiceId);
