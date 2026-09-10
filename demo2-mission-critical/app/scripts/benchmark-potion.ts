import { AzureCliCredential } from '@azure/identity'
import { createHash } from 'node:crypto'
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { performance } from 'node:perf_hooks'
import sql from 'mssql'
import type * as MSSQL from 'mssql'

type Environment = 'small' | 'large'
type Target = { environment: Environment; server: string; database: string }
type HashRow = {
  DocumentId: number
  ChunkNumber: number
  SourceContentSha256: string
  EmbeddingSha256: string
}
type SearchRow = {
  DocumentId: string
  ChunkNumber: number
  Title: string
  Passage: string
  Distance: number
}
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
type CorpusRow = {
  CorpusCount: number
  DistinctContentHashes: number
  DistinctEmbeddingHashes: number
  MissingSourceRows: number
  SourceContentHashMismatches: number
}
type IndexRow = { IndexName: string; DistanceMetric: string; IndexVersion: string }
type Sample = { sequence: number; sqlMs: number; totalMs: number }
type Evidence = Array<{
  documentId: string
  chunkNumber: number
  title: string
  passage: string
  distance: number
}>
type EnvironmentResult = {
  target: Target
  readiness: {
    schemaVersion: string
    compatibilityLevel: number
    corpusCount: number
    corpusFingerprintSha256: string
    indexName: string
    indexVersion: string
    distanceMetric: string
  }
  warmup: Sample[]
  measured: Sample[]
  summary: {
    sqlMs: { median: number; p95: number }
    totalMs: { median: number; p95: number }
  }
  evidence: Evidence
}

type QueryCatalog = {
  contractVersion: number
  model: string
  runtime: string
  runtimeVersion: string
  dimensions: number
  dtype: string
  distanceMetric: string
  queries: Array<{ query: string; sha256: string; vector: number[] }>
}

type Manifest = {
  format: string
  payload: { path: string; rows: number; bytes: number; sha256: string }
}

type PayloadIdentity = {
  DocumentId: string
  ChunkNumber: number
  SourceContentSha256: { $binary_hex: string }
  EmbeddingSha256: { $binary_hex: string }
}

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const appRoot = path.resolve(scriptDirectory, '..')
const projectRoot = path.resolve(appRoot, '..')
const catalogPath = path.join(appRoot, 'server', 'data', 'query-vectors.json')
const packagePath = path.join(projectRoot, 'staging', 'pmc-chunks-potion512-sidecar-v1')
const stageQuery = 'prognostic and therapeutic biomarkers in type 2 papillary renal cell carcinoma'
const sqlScope = 'https://database.windows.net/.default'

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
  AND OBJECT_ID(N'dbo.pmc_chunks', N'U') IS NOT NULL
  AND OBJECT_ID(N'dbo.pmc_documents', N'U') IS NOT NULL;`

const corpusSql = `
SELECT COUNT_BIG(*) AS CorpusCount,
     COUNT_BIG(DISTINCT potion.SourceContentSha256) AS DistinctContentHashes,
     COUNT_BIG(DISTINCT potion.EmbeddingSha256) AS DistinctEmbeddingHashes,
     SUM(CASE WHEN chunk.document_id IS NULL THEN 1 ELSE 0 END) AS MissingSourceRows,
     SUM
     (
       CASE
         WHEN chunk.document_id IS NOT NULL
        AND HASHBYTES('SHA2_256', CONVERT(VARBINARY(MAX), chunk.text_chunk))
          <> potion.SourceContentSha256
           THEN 1
         ELSE 0
       END
     ) AS SourceContentHashMismatches
FROM dbo.CaldovaPotionEmbedding AS potion
LEFT JOIN dbo.pmc_chunks AS chunk
  ON chunk.document_id = potion.DocumentId
   AND chunk.chunk_number = potion.ChunkNumber;`

const indexSql = `
SELECT index_definition.name AS IndexName,
       vector_index.distance_metric AS DistanceMetric,
       JSON_VALUE(vector_index.build_parameters, '$.Version') AS IndexVersion
FROM sys.vector_indexes AS vector_index
INNER JOIN sys.indexes AS index_definition
    ON index_definition.object_id = vector_index.object_id
   AND index_definition.index_id = vector_index.index_id
INNER JOIN sys.index_columns AS index_column
    ON index_column.object_id = vector_index.object_id
   AND index_column.index_id = vector_index.index_id
INNER JOIN sys.columns AS column_definition
    ON column_definition.object_id = index_column.object_id
   AND column_definition.column_id = index_column.column_id
WHERE vector_index.object_id = OBJECT_ID(N'dbo.CaldovaPotionEmbedding')
  AND column_definition.name = N'Embedding'
  AND vector_index.distance_metric = N'COSINE'
  AND JSON_VALUE(vector_index.build_parameters, '$.Version') = N'3'
  AND index_definition.is_disabled = 0
  AND index_definition.is_hypothetical = 0;`

const hashRowsSql = `
SELECT potion.DocumentId,
       potion.ChunkNumber,
       CONVERT(VARCHAR(64), potion.SourceContentSha256, 2) AS SourceContentSha256,
       CONVERT(VARCHAR(64), potion.EmbeddingSha256, 2) AS EmbeddingSha256
FROM dbo.CaldovaPotionEmbedding AS potion
ORDER BY potion.DocumentId, potion.ChunkNumber;`

const searchSql = `
SET NOCOUNT ON;
DECLARE @QueryVector VECTOR(512) = CAST(@QueryVectorJson AS VECTOR(512));
DECLARE @StartedAt DATETIME2(7) = SYSUTCDATETIME();
DECLARE @Result TABLE
(
    ResultRank TINYINT IDENTITY(1, 1) NOT NULL,
    DocumentId VARCHAR(20) NOT NULL,
    ChunkNumber INT NOT NULL,
    Title NVARCHAR(1000) NOT NULL,
    Passage NVARCHAR(MAX) NOT NULL,
    Distance FLOAT NOT NULL
);

INSERT @Result (DocumentId, ChunkNumber, Title, Passage, Distance)
SELECT TOP (5) WITH APPROXIMATE
  CONCAT('PMC', document.pmcid),
  potion.ChunkNumber,
  COALESCE(document.title, CONCAT('PMC', document.pmcid)),
  chunk.text_chunk,
       vector_result.distance
FROM VECTOR_SEARCH
(
    TABLE = dbo.CaldovaPotionEmbedding AS potion,
    COLUMN = Embedding,
    SIMILAR_TO = @QueryVector,
    METRIC = 'COSINE'
) AS vector_result
WITH (FORCE_ANN_ONLY)
INNER JOIN dbo.pmc_chunks AS chunk
  ON chunk.document_id = potion.DocumentId
   AND chunk.chunk_number = potion.ChunkNumber
INNER JOIN dbo.pmc_documents AS document
  ON document.document_id = potion.DocumentId
WHERE HASHBYTES('SHA2_256', CONVERT(VARBINARY(MAX), chunk.text_chunk))
  = potion.SourceContentSha256
ORDER BY vector_result.distance;

DECLARE @SqlMicroseconds BIGINT = DATEDIFF_BIG(MICROSECOND, @StartedAt, SYSUTCDATETIME());

SELECT result.DocumentId,
       result.ChunkNumber,
       result.Title,
       result.Passage,
       result.Distance
FROM @Result AS result
ORDER BY result.ResultRank;

SELECT CAST(@SqlMicroseconds / 1000.0 AS DECIMAL(18, 3)) AS SqlMs;`

function option(name: string): string | undefined {
  const index = process.argv.indexOf(name)
  if (index < 0) return undefined
  const value = process.argv[index + 1]
  if (!value || value.startsWith('--')) throw new Error(`${name} requires a value`)
  return value
}

function integerOption(name: string, defaultValue: number, minimum: number, maximum: number): number {
  const raw = option(name)
  const value = raw === undefined ? defaultValue : Number(raw)
  if (!Number.isInteger(value) || value < minimum || value > maximum) {
    throw new Error(`${name} must be an integer from ${minimum} through ${maximum}`)
  }
  return value
}

function requestedEnvironments(): Environment[] {
  const value = option('--environment') ?? 'both'
  if (value === 'both') return ['small', 'large']
  if (value === 'small' || value === 'large') return [value]
  throw new Error('--environment must be small, large, or both')
}

function targetFor(environment: Environment): Target {
  const prefix = environment === 'small' ? 'AZURE_SQL_SMALL' : 'AZURE_SQL_LARGE'
  const server = process.env[`${prefix}_SERVER`] ?? process.env.AZURE_SQL_SERVER
  const database = process.env[`${prefix}_DATABASE`]
  if (!server || !database) throw new Error(`${prefix}_SERVER and ${prefix}_DATABASE must be configured`)
  return { environment, server: server.trim(), database: database.trim() }
}

function sha256(value: Buffer | string): string {
  return createHash('sha256').update(value).digest('hex')
}

function vectorSha256(vector: number[]): string {
  const bytes = Buffer.alloc(vector.length * 4)
  vector.forEach((component, index) => bytes.writeFloatLE(component, index * 4))
  return sha256(bytes)
}

function fingerprint(rows: HashRow[]): string {
  const digest = createHash('sha256')
  for (const row of rows) {
    digest.update(
      `${row.DocumentId}\0${row.ChunkNumber}\0${row.SourceContentSha256.toLowerCase()}\0${row.EmbeddingSha256.toLowerCase()}\n`,
    )
  }
  return digest.digest('hex')
}

async function localBenchmarkInputs(): Promise<{
  vector: number[]
  vectorHash: string
  payloadHash: string
  payloadRows: number
  corpusFingerprint: string
}> {
  const catalog = JSON.parse(await readFile(catalogPath, 'utf8')) as QueryCatalog
  const query = catalog.queries.find((candidate) => candidate.query === stageQuery)
  if (
    catalog.contractVersion !== 1 ||
    catalog.model !== 'minishlab/potion-retrieval-32M' ||
    catalog.runtime !== 'model2vec' ||
    catalog.runtimeVersion !== '0.9.0' ||
    catalog.dimensions !== 512 ||
    catalog.dtype !== 'float32' ||
    catalog.distanceMetric !== 'cosine' ||
    !query ||
    query.vector.length !== 512 ||
    query.vector.some((component) => !Number.isFinite(component)) ||
    vectorSha256(query.vector) !== query.sha256
  ) {
    throw new Error('The stage query-vector catalog is invalid')
  }

  const manifest = JSON.parse(await readFile(path.join(packagePath, 'manifest.json'), 'utf8')) as Manifest
  const payloadFile = path.join(packagePath, manifest.payload.path)
  const payloadBuffer = await readFile(payloadFile)
  if (
    manifest.format !== 'caldova-pmc-potion512-v1' ||
    manifest.payload.rows !== 1000 ||
    (await stat(payloadFile)).size !== manifest.payload.bytes ||
    sha256(payloadBuffer) !== manifest.payload.sha256
  ) {
    throw new Error('The local Potion payload does not match its manifest')
  }
  const identities = payloadBuffer
    .toString('utf8')
    .split('\n')
    .filter(Boolean)
    .map((line) => JSON.parse(line) as PayloadIdentity)
    .sort((left, right) => {
      const documentDifference = Number(left.DocumentId) - Number(right.DocumentId)
      return documentDifference || left.ChunkNumber - right.ChunkNumber
    })
    .map((row) => ({
      DocumentId: Number(row.DocumentId),
      ChunkNumber: row.ChunkNumber,
      SourceContentSha256: row.SourceContentSha256.$binary_hex,
      EmbeddingSha256: row.EmbeddingSha256.$binary_hex,
    }))
  if (identities.length !== manifest.payload.rows) throw new Error('Payload row count is invalid')
  return {
    vector: query.vector,
    vectorHash: query.sha256,
    payloadHash: manifest.payload.sha256,
    payloadRows: manifest.payload.rows,
    corpusFingerprint: fingerprint(identities),
  }
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
    requestTimeout: 60_000,
    pool: { min: 0, max: 1, idleTimeoutMillis: 30_000 },
  }
  return new sql.ConnectionPool(config).connect()
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000
}

function percentile(values: number[], percentileValue: number): number {
  const sorted = [...values].sort((left, right) => left - right)
  const rank = Math.max(0, Math.ceil(percentileValue * sorted.length) - 1)
  return round(sorted[rank])
}

function median(values: number[]): number {
  const sorted = [...values].sort((left, right) => left - right)
  const midpoint = Math.floor(sorted.length / 2)
  return round(sorted.length % 2 === 0 ? (sorted[midpoint - 1] + sorted[midpoint]) / 2 : sorted[midpoint])
}

async function inspectTarget(
  pool: MSSQL.ConnectionPool,
  target: Target,
  expectedRows: number,
  expectedFingerprint: string,
): Promise<EnvironmentResult['readiness']> {
  const contract = (await pool.request().query<ContractRow>(contractSql)).recordset[0]
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
    throw new Error(`${target.environment} target failed the Potion schema contract`)
  }

  const corpus = (await pool.request().query<CorpusRow>(corpusSql)).recordset[0]
  if (
    !corpus ||
    corpus.CorpusCount !== expectedRows ||
    corpus.DistinctContentHashes !== expectedRows ||
    corpus.DistinctEmbeddingHashes !== expectedRows ||
    corpus.MissingSourceRows !== 0 ||
    corpus.SourceContentHashMismatches !== 0
  ) {
    throw new Error(`${target.environment} target does not contain the exact ${expectedRows}-row anchor shape`)
  }

  const indexes = (await pool.request().query<IndexRow>(indexSql)).recordset
  if (indexes.length !== 1) throw new Error(`${target.environment} target lacks one online version 3 cosine index`)

  const hashRows = (await pool.request().query<HashRow>(hashRowsSql)).recordset
  const actualFingerprint = fingerprint(hashRows)
  if (actualFingerprint !== expectedFingerprint) {
    throw new Error(`${target.environment} target corpus fingerprint differs from the canonical payload`)
  }

  return {
    schemaVersion: contract.SchemaVersion,
    compatibilityLevel: contract.CompatibilityLevel,
    corpusCount: corpus.CorpusCount,
    corpusFingerprintSha256: actualFingerprint,
    indexName: indexes[0].IndexName,
    indexVersion: indexes[0].IndexVersion,
    distanceMetric: indexes[0].DistanceMetric,
  }
}

async function sample(pool: MSSQL.ConnectionPool, vectorJson: string, sequence: number): Promise<{
  sample: Sample
  evidence: Evidence
}> {
  const startedAt = performance.now()
  const result = await pool
    .request()
    .input('QueryVectorJson', sql.NVarChar(16_000), vectorJson)
    .query<SearchRow>(searchSql)
  const totalMs = performance.now() - startedAt
  const timingRows = result.recordsets[1] as unknown as Array<{ SqlMs: number | string }>
  const sqlMs = Number(timingRows[0]?.SqlMs)
  if (result.recordsets[0].length !== 5 || !Number.isFinite(sqlMs)) {
    throw new Error('Forced-ANN query did not return five rows and a valid server timing')
  }
  return {
    sample: { sequence, sqlMs: round(sqlMs), totalMs: round(totalMs) },
    evidence: result.recordsets[0].map((row) => ({
      documentId: row.DocumentId,
      chunkNumber: row.ChunkNumber,
      title: row.Title,
      passage: row.Passage,
      distance: row.Distance,
    })),
  }
}

async function benchmarkTarget(
  target: Target,
  vector: number[],
  expectedRows: number,
  expectedFingerprint: string,
  warmupRuns: number,
  measuredRuns: number,
): Promise<EnvironmentResult> {
  const pool = await connect(target)
  try {
    const readiness = await inspectTarget(pool, target, expectedRows, expectedFingerprint)
    const vectorJson = JSON.stringify(vector)
    const warmup: Sample[] = []
    const measured: Sample[] = []
    let evidence: Evidence = []
    for (let sequence = 1; sequence <= warmupRuns; sequence += 1) {
      const result = await sample(pool, vectorJson, sequence)
      warmup.push(result.sample)
    }
    for (let sequence = 1; sequence <= measuredRuns; sequence += 1) {
      const result = await sample(pool, vectorJson, sequence)
      measured.push(result.sample)
      if (sequence === 1) evidence = result.evidence
    }
    const sqlValues = measured.map((item) => item.sqlMs)
    const totalValues = measured.map((item) => item.totalMs)
    return {
      target,
      readiness,
      warmup,
      measured,
      summary: {
        sqlMs: { median: median(sqlValues), p95: percentile(sqlValues, 0.95) },
        totalMs: { median: median(totalValues), p95: percentile(totalValues, 0.95) },
      },
      evidence,
    }
  } finally {
    await pool.close()
  }
}

async function main(): Promise<void> {
  const environments = requestedEnvironments()
  const warmupRuns = integerOption('--warmup', 3, 0, 50)
  const measuredRuns = integerOption('--runs', 20, 5, 500)
  const targets = environments.map(targetFor)
  if (
    targets.length === 2 &&
    targets[0].server.toLowerCase() === targets[1].server.toLowerCase() &&
    targets[0].database.toLowerCase() === targets[1].database.toLowerCase()
  ) {
    throw new Error('Small and large benchmarks must use independent server/database targets')
  }

  const inputs = await localBenchmarkInputs()
  const results: EnvironmentResult[] = []
  for (const target of targets) {
    results.push(await benchmarkTarget(
      target,
      inputs.vector,
      inputs.payloadRows,
      inputs.corpusFingerprint,
      warmupRuns,
      measuredRuns,
    ))
  }

  const small = results.find((result) => result.target.environment === 'small')
  const large = results.find((result) => result.target.environment === 'large')
  const comparison = small && large ? {
    medianSqlMsLargeMinusSmall: round(large.summary.sqlMs.median - small.summary.sqlMs.median),
    medianSqlMsLargeToSmallRatio: round(large.summary.sqlMs.median / small.summary.sqlMs.median),
    p95SqlMsLargeMinusSmall: round(large.summary.sqlMs.p95 - small.summary.sqlMs.p95),
    medianTotalMsLargeMinusSmall: round(large.summary.totalMs.median - small.summary.totalMs.median),
    medianTotalMsLargeToSmallRatio: round(large.summary.totalMs.median / small.summary.totalMs.median),
    p95TotalMsLargeMinusSmall: round(large.summary.totalMs.p95 - small.summary.totalMs.p95),
  } : null
  const report = {
    reportVersion: 1,
    measuredAtUtc: new Date().toISOString(),
    query: stageQuery,
    queryVectorSha256: inputs.vectorHash,
    payloadSha256: inputs.payloadHash,
    corpusFingerprintSha256: inputs.corpusFingerprint,
    warmupRuns,
    measuredRuns,
    results,
    comparison,
  }
  const reportJson = `${JSON.stringify(report, null, 2)}\n`
  const output = option('--output')
  if (output) {
    const outputPath = path.resolve(output)
    await mkdir(path.dirname(outputPath), { recursive: true })
    await writeFile(outputPath, reportJson, { encoding: 'utf8', flag: 'wx' })
    console.log(JSON.stringify({ status: 'benchmark-complete', outputPath, comparison }, null, 2))
  } else {
    console.log(reportJson)
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error)
  process.exitCode = 1
})
