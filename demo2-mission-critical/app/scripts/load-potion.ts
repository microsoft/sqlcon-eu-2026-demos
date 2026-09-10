import { AzureCliCredential } from '@azure/identity'
import { createHash } from 'node:crypto'
import { readFile, stat } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import sql from 'mssql'
import type * as MSSQL from 'mssql'

type Environment = 'small' | 'large'

type HashValue = { $binary_hex: string }

type PayloadRow = {
  DocumentId: string
  ChunkNumber: number
  SourceContentSha256: HashValue
  Embedding: number[]
  EmbeddingSha256: HashValue
}

type Manifest = {
  format: string
  embedding: {
    model: string
    runtime: string
    runtimeVersion: string
    dimensions: number
    dtype: string
    distanceMetric: string
    vectorHashEncoding: string
  }
  source: {
    path: string
    table: string
    identityColumns: string[]
    textColumn: string
    historicalVectorFilesUsed: boolean
    files: Array<{ path: string; sha256: string }>
  }
  payload: { path: string; rows: number; bytes: number; sha256: string }
}

type Target = { environment: Environment; server: string; database: string }

type ContractRow = {
  DatabaseName: string
  CompatibilityLevel: number
  SchemaVersion: string
  EmbeddingModel: string
  EmbeddingRuntime: string
  EmbeddingRuntimeVersion: string
  EmbeddingDimensions: number
  EmbeddingDataType: string
  DistanceMetric: string
}

type StoredRow = {
  DocumentId: number
  ChunkNumber: number
  SourceContentSha256: string
  EmbeddingSha256: string
}

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(scriptDirectory, '..', '..')
const defaultPackage = path.join(projectRoot, 'staging', 'pmc-chunks-potion512-sidecar-v1')
const sqlScope = 'https://database.windows.net/.default'
const batchSize = 25

const insertBatchSql = `
SET NOCOUNT ON;

WITH InputRows AS
(
  SELECT input.DocumentId,
       input.ChunkNumber,
       input.SourceContentSha256Hex,
           input.EmbeddingJson,
           input.EmbeddingSha256Hex
    FROM OPENJSON(@BatchJson)
    WITH
    (
    DocumentId INT '$.DocumentId',
    ChunkNumber INT '$.ChunkNumber',
    SourceContentSha256Hex VARCHAR(64) '$.SourceContentSha256',
        EmbeddingJson NVARCHAR(MAX) '$.Embedding' AS JSON,
        EmbeddingSha256Hex VARCHAR(64) '$.EmbeddingSha256'
    ) AS input
)
INSERT dbo.CaldovaPotionEmbedding
(
  DocumentId,
  ChunkNumber,
  SourceContentSha256,
    Embedding,
    EmbeddingSha256
)
SELECT input.DocumentId,
     input.ChunkNumber,
     CONVERT(BINARY(32), input.SourceContentSha256Hex, 2),
       CAST(input.EmbeddingJson AS VECTOR(512)),
       CONVERT(BINARY(32), input.EmbeddingSha256Hex, 2)
FROM InputRows AS input
INNER JOIN dbo.pmc_chunks AS chunk
  ON chunk.document_id = input.DocumentId
   AND chunk.chunk_number = input.ChunkNumber
WHERE HASHBYTES('SHA2_256', CONVERT(VARBINARY(MAX), chunk.text_chunk))
  = CONVERT(BINARY(32), input.SourceContentSha256Hex, 2);

IF @@ROWCOUNT <> (SELECT COUNT_BIG(*) FROM OPENJSON(@BatchJson))
  THROW 51220, 'A sidecar row does not match the current dbo.pmc_chunks key and text hash.', 1;

-- VECTOR to NVARCHAR conversion is lossy, so equality is proven in-engine.
IF EXISTS
(
  SELECT 1
  FROM OPENJSON(@BatchJson)
  WITH
  (
    DocumentId INT '$.DocumentId',
    ChunkNumber INT '$.ChunkNumber',
    EmbeddingJson NVARCHAR(MAX) '$.Embedding' AS JSON
  ) AS input
  INNER JOIN dbo.CaldovaPotionEmbedding AS potion
    ON potion.DocumentId = input.DocumentId
   AND potion.ChunkNumber = input.ChunkNumber
  WHERE VECTOR_DISTANCE('euclidean', potion.Embedding, CAST(input.EmbeddingJson AS VECTOR(512))) <> 0
)
  THROW 51221, 'A stored Potion vector does not exactly match the packaged vector.', 1;`

const contractSql = `
SELECT DB_NAME() AS DatabaseName,
       database_definition.compatibility_level AS CompatibilityLevel,
       contract.SchemaVersion,
       contract.EmbeddingModel,
       contract.EmbeddingRuntime,
       contract.EmbeddingRuntimeVersion,
       contract.EmbeddingDimensions,
       contract.EmbeddingDataType,
       contract.DistanceMetric
FROM sys.databases AS database_definition
CROSS JOIN dbo.CaldovaVectorContract AS contract
WHERE database_definition.database_id = DB_ID()
  AND contract.ContractId = 1
  AND OBJECT_ID(N'dbo.CaldovaPotionEmbedding', N'U') IS NOT NULL
  AND OBJECT_ID(N'dbo.pmc_chunks', N'U') IS NOT NULL;`

const readBackSql = `
SELECT potion.DocumentId,
       potion.ChunkNumber,
       CONVERT(VARCHAR(64), potion.SourceContentSha256, 2) AS SourceContentSha256,
       CONVERT(VARCHAR(64), potion.EmbeddingSha256, 2) AS EmbeddingSha256
FROM dbo.CaldovaPotionEmbedding AS potion
ORDER BY potion.DocumentId, potion.ChunkNumber;`

function option(name: string): string | undefined {
  const index = process.argv.indexOf(name)
  if (index < 0) return undefined
  const value = process.argv[index + 1]
  if (!value || value.startsWith('--')) throw new Error(`${name} requires a value`)
  return value
}

function environmentOption(): Environment {
  const value = option('--environment')
  if (value !== 'small' && value !== 'large') {
    throw new Error('--environment must be small or large')
  }
  return value
}

function targetFor(environment: Environment, required: boolean): Target | null {
  const prefix = environment === 'small' ? 'AZURE_SQL_SMALL' : 'AZURE_SQL_LARGE'
  const server = option('--server') ?? process.env[`${prefix}_SERVER`] ?? process.env.AZURE_SQL_SERVER
  const database = option('--database') ?? process.env[`${prefix}_DATABASE`]
  if (!server || !database) {
    if (required) {
      throw new Error(`Configure ${prefix}_SERVER and ${prefix}_DATABASE, or pass --server and --database`)
    }
    return null
  }
  return { environment, server: server.trim(), database: database.trim() }
}

async function sha256(pathname: string): Promise<string> {
  return createHash('sha256').update(await readFile(pathname)).digest('hex')
}

function vectorSha256(vector: number[]): string {
  const bytes = Buffer.alloc(vector.length * 4)
  vector.forEach((component, index) => bytes.writeFloatLE(component, index * 4))
  return createHash('sha256').update(bytes).digest('hex')
}

async function validatePackage(packagePath: string): Promise<{ manifest: Manifest; rows: PayloadRow[] }> {
  const manifest = JSON.parse(await readFile(path.join(packagePath, 'manifest.json'), 'utf8')) as Manifest
  const contract = manifest.embedding
  if (
    manifest.format !== 'caldova-pmc-potion512-v1' ||
    contract.model !== 'minishlab/potion-retrieval-32M' ||
    contract.runtime !== 'model2vec' ||
    contract.runtimeVersion !== '0.9.0' ||
    contract.dimensions !== 512 ||
    contract.dtype !== 'float32' ||
    contract.distanceMetric !== 'cosine' ||
    contract.vectorHashEncoding !== 'little-endian-float32' ||
    manifest.source.table !== 'dbo.pmc_chunks' ||
    manifest.source.identityColumns.join(',') !== 'document_id,chunk_number' ||
    manifest.source.textColumn !== 'text_chunk' ||
    manifest.source.historicalVectorFilesUsed !== false
  ) {
    throw new Error('The load package contract is incompatible with caldova-pmc-potion512-v1')
  }

  for (const source of manifest.source.files) {
    const sourcePath = path.join(projectRoot, manifest.source.path, source.path)
    if ((await sha256(sourcePath)) !== source.sha256) {
      throw new Error(`Source checksum mismatch: ${source.path}`)
    }
  }

  const payloadPath = path.join(packagePath, manifest.payload.path)
  const payloadStats = await stat(payloadPath)
  if (payloadStats.size !== manifest.payload.bytes || (await sha256(payloadPath)) !== manifest.payload.sha256) {
    throw new Error('Payload bytes do not match the manifest')
  }

  const payloadText = await readFile(payloadPath, 'utf8')
  const rows = payloadText
    .split('\n')
    .filter(Boolean)
    .map((line) => JSON.parse(line) as PayloadRow)
  if (rows.length !== manifest.payload.rows || rows.length !== 1000) {
    throw new Error(`Expected exactly 1,000 payload rows; received ${rows.length}`)
  }

  const sourceKeys = new Set<string>()
  const vectorHashes = new Set<string>()
  for (const [index, row] of rows.entries()) {
    const rowNumber = index + 1
    const documentId = Number(row.DocumentId)
    const sourceKey = `${row.DocumentId}/${row.ChunkNumber}`
    const vectorHash = vectorSha256(row.Embedding)
    if (
      !Number.isInteger(documentId) ||
      documentId <= 0 ||
      documentId > 2_147_483_647 ||
      row.DocumentId !== String(documentId) ||
      !Number.isInteger(row.ChunkNumber) ||
      row.ChunkNumber < 0 ||
      row.Embedding.length !== 512 ||
      row.Embedding.some((component) => !Number.isFinite(component)) ||
      !/^[0-9a-f]{64}$/.test(row.SourceContentSha256.$binary_hex) ||
      vectorHash !== row.EmbeddingSha256.$binary_hex
    ) {
      throw new Error(`Invalid content at payload row ${rowNumber}`)
    }
    if (sourceKeys.has(sourceKey) || vectorHashes.has(vectorHash)) {
      throw new Error(`Duplicate identity or vector at payload row ${rowNumber}`)
    }
    sourceKeys.add(sourceKey)
    vectorHashes.add(vectorHash)
  }
  return { manifest, rows }
}

function expectedApproval(target: Target, manifest: Manifest): string {
  return `LOAD ${target.environment} ${target.server}/${target.database} ${manifest.payload.rows} ${manifest.payload.sha256}`
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

async function requireTargetContract(pool: MSSQL.ConnectionPool, target: Target): Promise<void> {
  const result = await pool.request().query<ContractRow>(contractSql)
  const contract = result.recordset[0]
  if (
    !contract ||
    contract.DatabaseName.toLowerCase() !== target.database.toLowerCase() ||
    contract.CompatibilityLevel < 170 ||
    contract.SchemaVersion !== 'caldova-pmc-potion512-v1' ||
    contract.EmbeddingModel !== 'minishlab/potion-retrieval-32M' ||
    contract.EmbeddingRuntime !== 'model2vec' ||
    contract.EmbeddingRuntimeVersion !== '0.9.0' ||
    contract.EmbeddingDimensions !== 512 ||
    contract.EmbeddingDataType !== 'float32' ||
    contract.DistanceMetric !== 'COSINE'
  ) {
    throw new Error('The connected database does not have the required Potion schema contract')
  }
}

function compareStoredRows(expected: PayloadRow[], actual: StoredRow[]): void {
  if (actual.length !== expected.length) {
    throw new Error(`Read-back row count mismatch: expected ${expected.length}, received ${actual.length}`)
  }
  const expectedByKey = new Map(expected.map((row) => [`${row.DocumentId}/${row.ChunkNumber}`, row]))
  for (const row of actual) {
    const sourceKey = `${row.DocumentId}/${row.ChunkNumber}`
    const expectedRow = expectedByKey.get(sourceKey)
    if (
      !expectedRow ||
      row.SourceContentSha256.toLowerCase() !== expectedRow.SourceContentSha256.$binary_hex ||
      row.EmbeddingSha256.toLowerCase() !== expectedRow.EmbeddingSha256.$binary_hex
    ) {
      throw new Error(`Read-back mismatch for source key ${sourceKey}`)
    }
    expectedByKey.delete(sourceKey)
  }
  if (expectedByKey.size > 0) throw new Error('Read-back did not contain every payload source key')
}

async function applyPackage(pool: MSSQL.ConnectionPool, rows: PayloadRow[]): Promise<void> {
  const transaction = new sql.Transaction(pool)
  await transaction.begin(sql.ISOLATION_LEVEL.SERIALIZABLE)
  try {
    await new sql.Request(transaction).query('SET XACT_ABORT ON; DELETE FROM dbo.CaldovaPotionEmbedding;')
    for (let start = 0; start < rows.length; start += batchSize) {
      const batch = rows.slice(start, start + batchSize).map((row) => ({
        DocumentId: row.DocumentId,
        ChunkNumber: row.ChunkNumber,
        SourceContentSha256: row.SourceContentSha256.$binary_hex,
        Embedding: row.Embedding,
        EmbeddingSha256: row.EmbeddingSha256.$binary_hex,
      }))
      await new sql.Request(transaction)
        .input('BatchJson', sql.NVarChar(sql.MAX), JSON.stringify(batch))
        .query(insertBatchSql)
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
  const environment = environmentOption()
  const apply = process.argv.includes('--apply')
  const target = targetFor(environment, apply)
  const packagePath = path.resolve(option('--package') ?? defaultPackage)
  const { manifest, rows } = await validatePackage(packagePath)

  if (!apply) {
    const approval = target ? expectedApproval(target, manifest) : null
    console.log(JSON.stringify({
      mode: 'validation-only',
      networkConnectionOpened: false,
      targetConfigured: target !== null,
      target,
      packagePath,
      payload: manifest.payload,
      applyCommand: approval
        ? `npm run load:potion -- --environment ${environment} --apply --confirm "${approval}"`
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
    await requireTargetContract(pool, target)
    await applyPackage(pool, rows)
    console.log(JSON.stringify({
      status: 'loaded-and-verified',
      target,
      rows: rows.length,
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
