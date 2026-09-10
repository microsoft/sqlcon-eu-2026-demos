import { DefaultAzureCredential } from '@azure/identity'
import express from 'express'
import sql from 'mssql'
import type * as MSSQL from 'mssql'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { performance } from 'node:perf_hooks'

type ParameterMode = 'nvarchar' | 'varchar'

type InvoiceRow = {
  InvoiceId: number
  InvoiceNumber: string
  CustomerName: string
  Region: string
  InvoiceDate: Date
  DueDate: Date
  Status: string
  TotalAmount: number
}

const app = express()
const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const distRoot = path.join(appRoot, 'dist')
const distIndex = path.join(distRoot, 'index.html')
const credential = new DefaultAzureCredential()

/*
 * The demo switch. 'nvarchar' reproduces the production anti-pattern: an NVARCHAR
 * parameter compared against a VARCHAR column, which forces CONVERT_IMPLICIT on
 * every row and turns the index seek into a scan. 'varchar' is the one-word fix.
 */
const defaultParameterMode: ParameterMode =
  process.env.INVOICE_PARAMETER_MODE === 'varchar' ? 'varchar' : 'nvarchar'

const LOOKUP_SQL = `
SELECT invoice.InvoiceId,
       invoice.InvoiceNumber,
       customer.CustomerName,
       customer.Region,
       invoice.InvoiceDate,
       invoice.DueDate,
       invoice.Status,
       invoice.TotalAmount
FROM dbo.Invoice AS invoice
INNER JOIN dbo.Customer AS customer
    ON customer.CustomerId = invoice.CustomerId
WHERE invoice.InvoiceNumber = @invoiceNumber;`

const RECENT_SQL = `
SELECT invoice.InvoiceId,
       invoice.InvoiceNumber,
       customer.CustomerName,
       customer.Region,
       invoice.InvoiceDate,
       invoice.DueDate,
       invoice.Status,
       invoice.TotalAmount
FROM dbo.Invoice AS invoice
INNER JOIN dbo.Customer AS customer
    ON customer.CustomerId = invoice.CustomerId
WHERE invoice.Status = @status
ORDER BY invoice.InvoiceDate DESC
OFFSET @offset ROWS FETCH NEXT @pageSize ROWS ONLY;`

let poolPromise: Promise<MSSQL.ConnectionPool> | null = null
let poolExpiry = 0

async function getPool(): Promise<MSSQL.ConnectionPool> {
  if (poolPromise && poolExpiry > Date.now()) return poolPromise

  const server = process.env.AZURE_SQL_SERVER?.trim()
  const database = process.env.AZURE_SQL_DATABASE?.trim()
  if (!server || !database) throw new Error('AZURE_SQL_SERVER and AZURE_SQL_DATABASE are required')

  const token = await credential.getToken('https://database.windows.net/.default')
  if (!token) throw new Error('Could not acquire an Azure SQL access token')

  const config: MSSQL.config = {
    server,
    database,
    authentication: { type: 'azure-active-directory-access-token', options: { token: token.token } },
    options: { encrypt: true, trustServerCertificate: false, enableArithAbort: true },
    connectionTimeout: 30_000,
    requestTimeout: 120_000,
    pool: { min: 0, max: 8, idleTimeoutMillis: 60_000 },
  }
  poolPromise = new sql.ConnectionPool(config).connect()
  poolExpiry = token.expiresOnTimestamp - 120_000
  return poolPromise
}

app.disable('x-powered-by')
app.use(express.json({ limit: '32kb' }))

app.get('/api/invoices/:invoiceNumber', async (request, response) => {
  const started = performance.now()
  const invoiceNumber = String(request.params.invoiceNumber).slice(0, 20)
  const mode: ParameterMode = request.query.mode === 'varchar' ? 'varchar'
    : request.query.mode === 'nvarchar' ? 'nvarchar'
      : defaultParameterMode

  try {
    const pool = await getPool()
    const result = await pool.request()
      .input('invoiceNumber',
        mode === 'varchar' ? sql.VarChar(20) : sql.NVarChar(20),
        invoiceNumber)
      .query<InvoiceRow>(LOOKUP_SQL)

    response.json({
      parameterMode: mode,
      databaseMs: performance.now() - started,
      found: result.recordset.length,
      invoices: result.recordset,
    })
  } catch (error) {
    response.status(500).json({ message: error instanceof Error ? error.message : 'Lookup failed' })
  }
})

app.get('/api/invoices', async (request, response) => {
  const started = performance.now()
  const status = typeof request.query.status === 'string' ? request.query.status : 'Overdue'
  const page = Math.max(1, Number.parseInt(String(request.query.page ?? '1'), 10) || 1)
  const pageSize = Math.min(100, Math.max(10, Number.parseInt(String(request.query.pageSize ?? '25'), 10) || 25))

  try {
    const pool = await getPool()
    const result = await pool.request()
      .input('status', sql.VarChar(20), status)
      .input('offset', sql.Int, (page - 1) * pageSize)
      .input('pageSize', sql.Int, pageSize)
      .query<InvoiceRow>(RECENT_SQL)

    response.json({
      page,
      pageSize,
      databaseMs: performance.now() - started,
      invoices: result.recordset,
    })
  } catch (error) {
    response.status(500).json({ message: error instanceof Error ? error.message : 'Query failed' })
  }
})

app.get('/api/config', (_request, response) => {
  response.json({ parameterMode: defaultParameterMode })
})

if (existsSync(distIndex)) {
  app.use(express.static(distRoot))
  app.get(/^(?!\/api\/).*/, (_request, response) => response.sendFile(distIndex))
}

const port = Number.parseInt(process.env.PORT ?? '8010', 10)
const host = process.env.HOST ?? '127.0.0.1'
app.listen(port, host, () => {
  console.log(`Caldova Operations listening on http://${host}:${port} (parameter mode: ${defaultParameterMode})`)
})

export { app }
