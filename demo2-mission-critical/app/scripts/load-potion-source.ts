import { AzureCliCredential } from '@azure/identity'
import { createHash } from 'node:crypto'
import { readFile, stat } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import sql from 'mssql'
import type * as MSSQL from 'mssql'

type SourceRow = {
  DocumentId: number
  PmcId: string
  ChunkNumber: number
  ArticleTitle: string
  PassageText: string
  SourceContentSha256: string
}

type SourceDocument = {
  DocumentId: number
  PmcNumericId: number
  ArticleTitle: string
}

type Manifest = {
  format: string
  source: {
    server: string
    database: string
    chunkTable: string
    documentTable: string
    stagePmcId: string
    selection: string
  }
  payload: {
    path: string
    rows: number
    stageArticleRows: number
    bytes: number
    sha256: string
  }
}

type Target = { environment: 'small'; server: string; database: string }

type TargetStatus = {
  DatabaseName: string
  CompatibilityLevel: number
  DocumentCount: number
  ChunkCount: number
}

type StoredRow = {
  DocumentId: number
  PmcNumericId: number
  ChunkNumber: number
  ArticleTitle: string | null
  SourceContentSha256: string
}

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(scriptDirectory, '..', '..')
const defaultPackage = path.join(projectRoot, 'staging', 'pmc-chunks-potion512-source-v1')
const approvedServer = 'antho-caldova.database.windows.net'
const approvedDatabase = 'research'
const sqlScope = 'https://database.windows.net/.default'
const batchSize = 50

const targetStatusSql = `
IF OBJECT_ID(N'dbo.pmc_documents', N'U') IS NULL
   OR OBJECT_ID(N'dbo.pmc_chunks', N'U') IS NULL
    THROW 51233, 'The minimal PMC source schema has not been applied.', 1;

SELECT DB_NAME() AS DatabaseName,
       database_definition.compatibility_level AS CompatibilityLevel,
       (SELECT COUNT_BIG(*) FROM dbo.pmc_documents) AS DocumentCount,
       (SELECT COUNT_BIG(*) FROM dbo.pmc_chunks) AS ChunkCount
FROM sys.databases AS database_definition
WHERE database_definition.database_id = DB_ID();`

const insertDocumentsSql = `
SET NOCOUNT ON;

INSERT dbo.pmc_documents
(
  document_id,
  pmcid,
  title
)
SELECT input.DocumentId,
       input.PmcNumericId,
       input.ArticleTitle
FROM OPENJSON(@DocumentsJson)
WITH
(
  DocumentId INT '$.DocumentId',
  PmcNumericId INT '$.PmcNumericId',
  ArticleTitle NVARCHAR(2000) '$.ArticleTitle'
) AS input;

IF @@ROWCOUNT <> (SELECT COUNT_BIG(*) FROM OPENJSON(@DocumentsJson))
    THROW 51234, 'Not every source document was inserted.', 1;`

const insertChunksSql = `
SET NOCOUNT ON;

WITH InputRows AS
(
  SELECT input.DocumentId,
         input.ChunkNumber,
         input.PassageText,
         input.SourceContentSha256Hex
  FROM OPENJSON(@BatchJson)
  WITH
  (
    DocumentId INT '$.DocumentId',
    ChunkNumber INT '$.ChunkNumber',
    PassageText NVARCHAR(MAX) '$.PassageText',
    SourceContentSha256Hex VARCHAR(64) '$.SourceContentSha256'
  ) AS input
)
INSERT dbo.pmc_chunks
(
  document_id,
  chunk_number,
  text_chunk
)
SELECT input.DocumentId,
       input.ChunkNumber,
       input.PassageText
FROM InputRows AS input
WHERE HASHBYTES('SHA2_256', CONVERT(VARBINARY(MAX), input.PassageText))
    = CONVERT(BINARY(32), input.SourceContentSha256Hex, 2);

IF @@ROWCOUNT <> (SELECT COUNT_BIG(*) FROM OPENJSON(@BatchJson))
    THROW 51235, 'A source passage does not match its declared UTF-16LE hash.', 1;`

const readBackSql = `
SELECT chunk.document_id AS DocumentId,
       document.pmcid AS PmcNumericId,
       chunk.chunk_number AS ChunkNumber,
       document.title AS ArticleTitle,
       CONVERT(VARCHAR(64), HASHBYTES('SHA2_256', CONVERT(VARBINARY(MAX), chunk.text_chunk)), 2)
           AS SourceContentSha256
FROM dbo.pmc_chunks AS chunk
INNER JOIN dbo.pmc_documents AS document
    ON document.document_id = chunk.document_id
ORDER BY chunk.document_id, chunk.chunk_number;`

function option(name: string): string | undefined {
  const index = process.argv.indexOf(name)
  if (index < 0) return undefined
  const value = process.argv[index + 1]
  if (!value || value.startsWith('--')) throw new Error(`${name} requires a value`)
  return value
}

function requireSmallEnvironment(): void {
  if (option('--environment') !== 'small') {
    throw new Error('--environment must be small; the source loader cannot target the large database')
  }
}

function targetFor(required: boolean): Target | null {
  const server = option('--server') ?? process.env.AZURE_SQL_SMALL_SERVER
  const database = option('--database') ?? process.env.AZURE_SQL_SMALL_DATABASE
  if (!server || !database) {
    if (required) {
      throw new Error('Configure AZURE_SQL_SMALL_SERVER and AZURE_SQL_SMALL_DATABASE, or pass --server and --database')
    }
    return null
  }

  const normalizedServer = server.trim().toLowerCase()
  const normalizedDatabase = database.trim().toLowerCase()
  if (normalizedServer !== approvedServer || normalizedDatabase !== approvedDatabase) {
    throw new Error(`Source mutation is restricted to ${approvedServer}/${approvedDatabase}`)
  }
  return { environment: 'small', server: normalizedServer, database: normalizedDatabase }
}

async function sha256(pathname: string): Promise<string> {
  return createHash('sha256').update(await readFile(pathname)).digest('hex')
}

function textSha256(value: string): string {
  return createHash('sha256').update(Buffer.from(value, 'utf16le')).digest('hex')
}

async function validatePackage(packagePath: string): Promise<{
  manifest: Manifest
  rows: SourceRow[]
  documents: SourceDocument[]
}> {
  const manifest = JSON.parse(await readFile(path.join(packagePath, 'manifest.json'), 'utf8')) as Manifest
  if (
    manifest.format !== 'caldova-pmc-chunk-source-v1' ||
    manifest.source.server !== 'vbnech-large-server.database.windows.net' ||
    manifest.source.database !== 'vbench_large' ||
    manifest.source.chunkTable !== 'dbo.pmc_chunks' ||
    manifest.source.documentTable !== 'dbo.pmc_documents' ||
    manifest.source.stagePmcId !== 'PMC10022194' ||
    manifest.source.selection !== 'all-stage-article-chunks-then-lowest-source-keys'
  ) {
    throw new Error('The source package contract is incompatible with the approved Potion snapshot')
  }

  const payloadPath = path.join(packagePath, manifest.payload.path)
  const payloadStats = await stat(payloadPath)
  if (payloadStats.size !== manifest.payload.bytes || (await sha256(payloadPath)) !== manifest.payload.sha256) {
    throw new Error('Source payload bytes do not match the manifest')
  }
  if (manifest.payload.rows !== 1000 || manifest.payload.stageArticleRows !== 88) {
    throw new Error('The source manifest must declare 1,000 rows and 88 stage-article rows')
  }

  const rows = (await readFile(payloadPath, 'utf8'))
    .split('\n')
    .filter(Boolean)
    .map((line) => JSON.parse(line) as SourceRow)
  if (rows.length !== manifest.payload.rows) {
    throw new Error(`Expected ${manifest.payload.rows} source rows; received ${rows.length}`)
  }

  const sourceKeys = new Set<string>()
  const documentsById = new Map<number, SourceDocument>()
  const documentIdByPmcId = new Map<number, number>()
  let stageArticleRows = 0
  for (const [index, row] of rows.entries()) {
    const rowNumber = index + 1
    const pmcMatch = /^PMC([1-9][0-9]*)$/.exec(row.PmcId)
    const pmcNumericId = pmcMatch ? Number(pmcMatch[1]) : Number.NaN
    const sourceKey = `${row.DocumentId}/${row.ChunkNumber}`
    if (
      !Number.isInteger(row.DocumentId) ||
      row.DocumentId <= 0 ||
      !Number.isSafeInteger(pmcNumericId) ||
      pmcNumericId <= 0 ||
      pmcNumericId > 2_147_483_647 ||
      !Number.isInteger(row.ChunkNumber) ||
      row.ChunkNumber < 0 ||
      typeof row.ArticleTitle !== 'string' ||
      row.ArticleTitle.length === 0 ||
      row.ArticleTitle.length > 2000 ||
      typeof row.PassageText !== 'string' ||
      row.PassageText.length === 0 ||
      !/^[0-9a-f]{64}$/.test(row.SourceContentSha256) ||
      textSha256(row.PassageText) !== row.SourceContentSha256
    ) {
      throw new Error(`Invalid source content at payload row ${rowNumber}`)
    }
    if (sourceKeys.has(sourceKey)) throw new Error(`Duplicate source key at payload row ${rowNumber}`)
    sourceKeys.add(sourceKey)

    const document = { DocumentId: row.DocumentId, PmcNumericId: pmcNumericId, ArticleTitle: row.ArticleTitle }
    const existingDocument = documentsById.get(row.DocumentId)
    if (
      existingDocument &&
      (existingDocument.PmcNumericId !== document.PmcNumericId ||
        existingDocument.ArticleTitle !== document.ArticleTitle)
    ) {
      throw new Error(`Inconsistent document metadata at payload row ${rowNumber}`)
    }
    const existingDocumentId = documentIdByPmcId.get(pmcNumericId)
    if (existingDocumentId !== undefined && existingDocumentId !== row.DocumentId) {
      throw new Error(`PMCID maps to multiple documents at payload row ${rowNumber}`)
    }
    documentsById.set(row.DocumentId, document)
    documentIdByPmcId.set(pmcNumericId, row.DocumentId)
    if (row.PmcId === manifest.source.stagePmcId) stageArticleRows += 1
  }

  if (stageArticleRows !== manifest.payload.stageArticleRows) {
    throw new Error(`Expected ${manifest.payload.stageArticleRows} stage-article rows; received ${stageArticleRows}`)
  }

  return {
    manifest,
    rows,
    documents: [...documentsById.values()].sort((left, right) => left.DocumentId - right.DocumentId),
  }
}

function expectedApproval(target: Target, manifest: Manifest): string {
  return `LOAD SOURCE ${target.environment} ${target.server}/${target.database} ${manifest.payload.rows} ${manifest.payload.sha256}`
}

async function connect(target: Target): Promise<MSSQL.ConnectionPool> {
  const accessToken = await new AzureCliCredential().getToken(sqlScope)
  if (!accessToken) throw new Error('Azure CLI did not return an Azure SQL access token')
  const config: MSSQL.config = {
    server: target.server,
    database: target.database,
    authentication: {
      type: 'azure-active-directory-access-token',
      options: { token: accessToken.token },
    },
    options: { encrypt: true, trustServerCertificate: false, enableArithAbort: true },
    connectionTimeout: 15_000,
    requestTimeout: 120_000,
    pool: { min: 0, max: 1, idleTimeoutMillis: 30_000 },
  }
  return new sql.ConnectionPool(config).connect()
}

async function requireEmptyTarget(pool: MSSQL.ConnectionPool, target: Target): Promise<void> {
  const result = await pool.request().query<TargetStatus>(targetStatusSql)
  const status = result.recordset[0]
  if (
    !status ||
    status.DatabaseName.toLowerCase() !== target.database ||
    status.CompatibilityLevel < 170 ||
    Number(status.DocumentCount) !== 0 ||
    Number(status.ChunkCount) !== 0
  ) {
    throw new Error('The target must have compatibility level 170 and empty minimal PMC source tables')
  }
}

function compareStoredRows(expected: SourceRow[], actual: StoredRow[]): void {
  if (actual.length !== expected.length) {
    throw new Error(`Read-back row count mismatch: expected ${expected.length}, received ${actual.length}`)
  }
  const expectedByKey = new Map(expected.map((row) => [`${row.DocumentId}/${row.ChunkNumber}`, row]))
  for (const row of actual) {
    const sourceKey = `${row.DocumentId}/${row.ChunkNumber}`
    const expectedRow = expectedByKey.get(sourceKey)
    if (
      !expectedRow ||
      row.PmcNumericId !== Number(expectedRow.PmcId.slice(3)) ||
      row.ArticleTitle !== expectedRow.ArticleTitle ||
      row.SourceContentSha256.toLowerCase() !== expectedRow.SourceContentSha256
    ) {
      throw new Error(`Read-back mismatch for source key ${sourceKey}`)
    }
    expectedByKey.delete(sourceKey)
  }
  if (expectedByKey.size > 0) throw new Error('Read-back did not contain every source key')
}

async function applyPackage(
  pool: MSSQL.ConnectionPool,
  documents: SourceDocument[],
  rows: SourceRow[],
): Promise<void> {
  const transaction = new sql.Transaction(pool)
  await transaction.begin(sql.ISOLATION_LEVEL.SERIALIZABLE)
  try {
    await new sql.Request(transaction)
      .input('DocumentsJson', sql.NVarChar(sql.MAX), JSON.stringify(documents))
      .query(insertDocumentsSql)
    for (let start = 0; start < rows.length; start += batchSize) {
      await new sql.Request(transaction)
        .input('BatchJson', sql.NVarChar(sql.MAX), JSON.stringify(rows.slice(start, start + batchSize)))
        .query(insertChunksSql)
    }
    const readBack = await new sql.Request(transaction).query<StoredRow>(readBackSql)
    compareStoredRows(rows, readBack.recordset)
    await transaction.commit()
  } catch (error) {
    await transaction.rollback().catch(() => undefined)
    throw error
  }
}

async function main(): Promise<void> {
  requireSmallEnvironment()
  const apply = process.argv.includes('--apply')
  const target = targetFor(apply)
  const packagePath = path.resolve(option('--package') ?? defaultPackage)
  const { manifest, rows, documents } = await validatePackage(packagePath)

  if (!apply) {
    const approval = target ? expectedApproval(target, manifest) : null
    console.log(JSON.stringify({
      mode: 'validation-only',
      networkConnectionOpened: false,
      targetConfigured: target !== null,
      target,
      packagePath,
      payload: manifest.payload,
      documentRows: documents.length,
      applyCommand: approval
        ? `npm run load:potion-source -- --environment small --apply --confirm "${approval}"`
        : null,
    }, null, 2))
    return
  }

  if (!target) throw new Error('Mutation requires a configured target')
  const approval = expectedApproval(target, manifest)
  if (option('--confirm') !== approval) {
    throw new Error(`Mutation blocked. Exact confirmation required:\n${approval}`)
  }

  const pool = await connect(target)
  try {
    await requireEmptyTarget(pool, target)
    await applyPackage(pool, documents, rows)
    console.log(JSON.stringify({
      status: 'loaded-and-verified',
      target,
      documentRows: documents.length,
      chunkRows: rows.length,
      payloadSha256: manifest.payload.sha256,
    }, null, 2))
  } finally {
    await pool.close()
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})