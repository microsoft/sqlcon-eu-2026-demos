/*
    The two statements the demo compares.

    Run both with "Include Actual Execution Plan" on. The only difference is the
    declared type of @InvoiceNumber. The schema, the index, and the data are identical.
*/

SET STATISTICS IO ON;
SET STATISTICS TIME ON;

-- 1. What the application sends today.
--    NVARCHAR against a VARCHAR column forces CONVERT_IMPLICIT on every row,
--    so IX_Invoice_InvoiceNumber cannot be seeked and the plan shows an Index Scan.
DECLARE @SlowInvoiceNumber NVARCHAR(20) = N'INV-0004821993';

SELECT invoice.InvoiceId,
       invoice.InvoiceNumber,
       invoice.InvoiceDate,
       invoice.Status,
       invoice.TotalAmount,
       customer.CustomerName
FROM dbo.Invoice AS invoice
INNER JOIN dbo.Customer AS customer
    ON customer.CustomerId = invoice.CustomerId
WHERE invoice.InvoiceNumber = @SlowInvoiceNumber;

-- 2. The fix. One word in the application, nothing in the database.
DECLARE @FastInvoiceNumber VARCHAR(20) = 'INV-0004821993';

SELECT invoice.InvoiceId,
       invoice.InvoiceNumber,
       invoice.InvoiceDate,
       invoice.Status,
       invoice.TotalAmount,
       customer.CustomerName
FROM dbo.Invoice AS invoice
INNER JOIN dbo.Customer AS customer
    ON customer.CustomerId = invoice.CustomerId
WHERE invoice.InvoiceNumber = @FastInvoiceNumber;

/*
    Confirming the cause from the plan cache, which is what the diagnostic hand-off
    into SSMS shows.
*/
SELECT TOP (20)
       query_stats.execution_count,
       query_stats.total_logical_reads / query_stats.execution_count AS AvgLogicalReads,
       query_stats.total_elapsed_time / query_stats.execution_count / 1000 AS AvgElapsedMs,
       SUBSTRING(sql_text.text,
                 (query_stats.statement_start_offset / 2) + 1,
                 ((CASE query_stats.statement_end_offset
                       WHEN -1 THEN DATALENGTH(sql_text.text)
                       ELSE query_stats.statement_end_offset
                   END - query_stats.statement_start_offset) / 2) + 1) AS StatementText
FROM sys.dm_exec_query_stats AS query_stats
CROSS APPLY sys.dm_exec_sql_text(query_stats.sql_handle) AS sql_text
WHERE sql_text.text LIKE '%dbo.Invoice%'
ORDER BY AvgLogicalReads DESC;
