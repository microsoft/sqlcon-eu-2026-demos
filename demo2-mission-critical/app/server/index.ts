import { DefaultAzureCredential } from '@azure/identity'
import express from 'express'
import sql from 'mssql'
import type * as MSSQL from 'mssql'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { performance } from 'node:perf_hooks'

type Environment = 'small' | 'large'
type SearchMode = 'vector' | 'keyword' | 'hybrid'

type CorpusStatusRow = { ChunkCount: number; DocumentCount: number }
type IndexStatusRow = { IndexName: string; IndexVersion: string }

type EnvironmentReadiness = {
  environment: Environment
  databaseLabel: string
  configured: boolean
  reachable: boolean
  indexReady: boolean
  keywordReady: boolean
  chunkCount: number | null
  documentCount: number | null
  ready: boolean
  message: string
}

type SearchRow = {
  PmcId: string
  Title: string | null
  ChunkNumber: number
  Distance: number | null
  Score: number
  PreviousPassage: string | null
  Passage: string
  NextPassage: string | null
}

type PoolEntry = { pool: Promise<MSSQL.ConnectionPool>; expiresAt: number }
type DatabaseTarget = { server: string; database: string; poolKey: string }

class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string) {
    super(message)
  }
}

const DATABASE_LABELS: Record<Environment, string> = {
  small: 'Caldova Pilot',
  large: 'Caldova Research',
}

const pools = new Map<string, PoolEntry>()
const credential = new DefaultAzureCredential()
const app = express()
const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const distRoot = path.join(appRoot, 'dist')
const distIndex = path.join(distRoot, 'index.html')
const embeddingServiceUrl = (process.env.EMBEDDING_SERVICE_URL ?? 'http://127.0.0.1:8081').replace(/\/$/, '')

const SEARCH_SQL = `
DECLARE @QueryVector VECTOR(512) = CAST(@queryVectorJson AS VECTOR(512));

WITH VectorRaw AS
(
  SELECT TOP (@candidates) WITH APPROXIMATE
         chunk.document_id, chunk.chunk_number, vector_result.distance AS Distance
  FROM VECTOR_SEARCH
  (
      TABLE = dbo.pmc_chunks AS chunk,
      COLUMN = embedding,
      SIMILAR_TO = @QueryVector,
      METRIC = 'COSINE'
  ) AS vector_result
  WHERE @useVector = 1
    AND chunk.is_boilerplate = 0
  ORDER BY vector_result.distance
),
VectorCandidates AS
(
  SELECT document_id, chunk_number, Distance,
         ROW_NUMBER() OVER (ORDER BY Distance) AS Position
  FROM VectorRaw
),
KeywordCandidates AS
(
  SELECT TOP (@candidates)
         chunk.document_id, chunk.chunk_number,
         ROW_NUMBER() OVER (ORDER BY ranked.[RANK] DESC) AS Position
  FROM FREETEXTTABLE(dbo.pmc_chunks, text_chunk, @queryText, @candidates) AS ranked
  INNER JOIN dbo.pmc_chunks AS chunk ON chunk.chunk_id = ranked.[KEY]
  WHERE @useKeyword = 1
    AND chunk.is_boilerplate = 0
  ORDER BY ranked.[RANK] DESC
),
Fused AS
(
  SELECT candidate.document_id, candidate.chunk_number,
         SUM(1.0 / (60.0 + candidate.Position)) AS Score,
         MIN(candidate.Distance) AS Distance
  FROM
  (
    SELECT document_id, chunk_number, Position, Distance FROM VectorCandidates
    UNION ALL
    SELECT document_id, chunk_number, Position, NULL FROM KeywordCandidates
  ) AS candidate
  GROUP BY candidate.document_id, candidate.chunk_number
),
BestPerDocument AS
(
  SELECT document_id, chunk_number, Score, Distance,
         ROW_NUMBER() OVER (PARTITION BY document_id ORDER BY Score DESC, chunk_number) AS DocumentRank
  FROM Fused
)
SELECT TOP (@top)
       CONCAT('PMC', document.pmcid) AS PmcId,
       document.title AS Title,
       best.chunk_number AS ChunkNumber,
       best.Distance AS Distance,
       best.Score AS Score,
       previous_chunk.text_chunk AS PreviousPassage,
       chunk.text_chunk AS Passage,
       next_chunk.text_chunk AS NextPassage
FROM BestPerDocument AS best
INNER JOIN dbo.pmc_chunks AS chunk
    ON chunk.document_id = best.document_id AND chunk.chunk_number = best.chunk_number
INNER JOIN dbo.pmc_documents AS document
    ON document.document_id = best.document_id
LEFT JOIN dbo.pmc_chunks AS previous_chunk
    ON previous_chunk.document_id = best.document_id AND previous_chunk.chunk_number = best.chunk_number - 1
LEFT JOIN dbo.pmc_chunks AS next_chunk
    ON next_chunk.document_id = best.document_id AND next_chunk.chunk_number = best.chunk_number + 1
WHERE best.DocumentRank = 1
ORDER BY best.Score DESC;`

const CORPUS_STATUS_QUERY = `
SELECT (SELECT COUNT_BIG(*) FROM dbo.pmc_chunks) AS ChunkCount,
       (SELECT COUNT_BIG(*) FROM dbo.pmc_documents) AS DocumentCount;`

const INDEX_STATUS_QUERY = `
SELECT TOP (1)
  index_definition.name AS IndexName,
  JSON_VALUE(vector_index.build_parameters, '$.Version') AS IndexVersion
FROM sys.vector_indexes AS vector_index
INNER JOIN sys.indexes AS index_definition
    ON index_definition.object_id = vector_index.object_id
   AND index_definition.index_id = vector_index.index_id
WHERE vector_index.object_id = OBJECT_ID(N'dbo.pmc_chunks')
  AND vector_index.distance_metric = N'COSINE'
  AND index_definition.is_disabled = 0;`

const KEYWORD_STATUS_QUERY = `
SELECT CAST(OBJECTPROPERTYEX(OBJECT_ID('dbo.pmc_chunks'), 'TableFulltextItemCount') AS INT) AS IndexedRows;`

app.disable('x-powered-by')
app.use(express.json({ limit: '32kb' }))

// Only origins named in CALDOVA_ALLOWED_ORIGINS may call the API cross-origin.
const allowedOrigins = new Set(
  (process.env.CALDOVA_ALLOWED_ORIGINS ?? '')
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean),
)

app.use((request, response, next) => {
  const origin = request.headers.origin
  if (origin && allowedOrigins.has(origin)) {
    response.setHeader('Access-Control-Allow-Origin', origin)
    response.setHeader('Vary', 'Origin')
    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    if (request.method === 'OPTIONS') {
      response.status(204).end()
      return
    }
  }
  next()
})

function getEnvironment(value: unknown): Environment {
  if (value !== 'small' && value !== 'large') {
    throw new ApiError(400, 'INVALID_ENVIRONMENT', 'Environment must be small or large.')
  }
  return value
}

function getSearchMode(value: unknown): SearchMode {
  if (value === undefined || value === null) return 'hybrid'
  if (value !== 'vector' && value !== 'keyword' && value !== 'hybrid') {
    throw new ApiError(400, 'INVALID_MODE', 'Mode must be vector, keyword, or hybrid.')
  }
  return value
}

function getDatabaseTarget(environment: Environment): DatabaseTarget {
  const prefix = environment === 'small' ? 'AZURE_SQL_SMALL' : 'AZURE_SQL_LARGE'
  const database = process.env[`${prefix}_DATABASE`]?.trim()
  if (!database) {
    throw new ApiError(503, 'DATABASE_NOT_CONFIGURED', `${prefix}_DATABASE is not configured.`)
  }
  const server = process.env[`${prefix}_SERVER`]?.trim() || process.env.AZURE_SQL_SERVER?.trim()
  if (!server) {
    throw new ApiError(503, 'SERVER_NOT_CONFIGURED', `${prefix}_SERVER is not configured.`)
  }
  return { server, database, poolKey: `${server}/${database}` }
}

async function embedQuery(query: string): Promise<number[]> {
  let response: Response
  try {
    response = await fetch(`${embeddingServiceUrl}/embed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: query }),
      signal: AbortSignal.timeout(15_000),
    })
  } catch {
    throw new ApiError(503, 'EMBEDDING_UNAVAILABLE', 'The query embedding service is not reachable.')
  }
  if (!response.ok) {
    throw new ApiError(502, 'EMBEDDING_FAILED', `Embedding service returned ${response.status}.`)
  }
  const payload = (await response.json()) as { vector?: number[] }
  if (!Array.isArray(payload.vector) || payload.vector.length !== 512) {
    throw new ApiError(502, 'EMBEDDING_INVALID', 'Embedding service returned an unexpected vector.')
  }
  return payload.vector
}

async function getPool(target: DatabaseTarget): Promise<MSSQL.ConnectionPool> {
  const existing = pools.get(target.poolKey)
  if (existing && existing.expiresAt > Date.now()) return existing.pool

  const accessToken = await credential.getToken('https://database.windows.net/.default')
  if (!accessToken) throw new ApiError(503, 'TOKEN_UNAVAILABLE', 'Could not acquire an Azure SQL token.')

  const config: MSSQL.config = {
    server: target.server,
    database: target.database,
    authentication: {
      type: 'azure-active-directory-access-token',
      options: { token: accessToken.token },
    },
    options: { encrypt: true, trustServerCertificate: false, enableArithAbort: true },
    connectionTimeout: 30_000,
    requestTimeout: 60_000,
    pool: { min: 0, max: 8, idleTimeoutMillis: 60_000 },
  }
  const pool = new sql.ConnectionPool(config).connect()
  pools.set(target.poolKey, { pool, expiresAt: accessToken.expiresOnTimestamp - 120_000 })
  return pool
}

async function inspectEnvironment(environment: Environment): Promise<EnvironmentReadiness> {
  const base: EnvironmentReadiness = {
    environment,
    databaseLabel: DATABASE_LABELS[environment],
    configured: false,
    reachable: false,
    indexReady: false,
    keywordReady: false,
    chunkCount: null,
    documentCount: null,
    ready: false,
    message: '',
  }

  let target: DatabaseTarget
  try {
    target = getDatabaseTarget(environment)
  } catch {
    return { ...base, message: `${DATABASE_LABELS[environment]} is not configured.` }
  }

  let pool: MSSQL.ConnectionPool
  try {
    pool = await getPool(target)
  } catch {
    return { ...base, configured: true, message: `${DATABASE_LABELS[environment]} is not reachable.` }
  }

  try {
    const [corpus, index, keyword] = await Promise.all([
      pool.request().query<CorpusStatusRow>(CORPUS_STATUS_QUERY),
      pool.request().query<IndexStatusRow>(INDEX_STATUS_QUERY),
      pool.request().query<{ IndexedRows: number | null }>(KEYWORD_STATUS_QUERY),
    ])

    // COUNT_BIG arrives as a string, so compare numerically.
    const chunkCount = Number(corpus.recordset[0]?.ChunkCount ?? 0)
    const documentCount = Number(corpus.recordset[0]?.DocumentCount ?? 0)
    const indexReady = index.recordset.length === 1
    const keywordReady = Number(keyword.recordset[0]?.IndexedRows ?? 0) > 0

    return {
      ...base,
      configured: true,
      reachable: true,
      indexReady,
      keywordReady,
      chunkCount,
      documentCount,
      ready: chunkCount > 0 && indexReady,
      message: chunkCount === 0
        ? 'The corpus is empty.'
        : indexReady
          ? `${documentCount.toLocaleString()} articles, ${chunkCount.toLocaleString()} passages.`
          : 'The vector index has not been built on this database yet.',
    }
  } catch (error) {
    return {
      ...base,
      configured: true,
      reachable: true,
      message: error instanceof Error ? error.message : 'Readiness check failed.',
    }
  }
}

app.get('/api/readiness/:environment', async (request, response) => {
  try {
    response.json(await inspectEnvironment(getEnvironment(request.params.environment)))
  } catch (error) {
    const apiError = error as ApiError
    response.status(apiError?.status ?? 500).json({
      code: apiError?.code ?? 'READINESS_FAILED',
      message: apiError?.message ?? 'Readiness could not be determined.',
    })
  }
})

app.post('/api/search', async (request, response) => {
  const started = performance.now()
  try {
    const body = request.body as { environment?: unknown; query?: unknown; mode?: unknown }
    const environment = getEnvironment(body.environment)
    const mode = getSearchMode(body.mode)
    const query = typeof body.query === 'string' ? body.query.trim() : ''
    if (!query || query.length > 500) {
      throw new ApiError(400, 'INVALID_QUERY', 'Provide a question between 1 and 500 characters.')
    }

    const readiness = await inspectEnvironment(environment)
    if (!readiness.ready) {
      throw new ApiError(503, 'DATABASE_NOT_READY', `${readiness.databaseLabel}: ${readiness.message}`)
    }
    if (mode !== 'vector' && !readiness.keywordReady) {
      throw new ApiError(503, 'KEYWORD_NOT_READY', `${readiness.databaseLabel} has no full-text index.`)
    }

    const embedStarted = performance.now()
    const vector = await embedQuery(query)
    const embedMs = performance.now() - embedStarted

    const pool = await getPool(getDatabaseTarget(environment))
    const queryStarted = performance.now()
    const result = await pool.request()
      .input('queryVectorJson', sql.NVarChar(sql.MAX), JSON.stringify(vector))
      .input('queryText', sql.NVarChar(500), query)
      .input('candidates', sql.Int, 50)
      .input('top', sql.Int, 5)
      .input('useVector', sql.Bit, mode === 'vector' || mode === 'hybrid')
      .input('useKeyword', sql.Bit, mode === 'keyword' || mode === 'hybrid')
      .query<SearchRow>(SEARCH_SQL)
    const databaseMs = performance.now() - queryStarted

    response.json({
      environment,
      databaseLabel: readiness.databaseLabel,
      mode,
      chunkCount: readiness.chunkCount,
      documentCount: readiness.documentCount,
      indexStatus: readiness.indexReady ? 'Online · v3' : 'Not built',
      embedMs,
      databaseMs,
      totalMs: performance.now() - started,
      evidence: result.recordset.map((row) => ({
        documentId: row.PmcId,
        title: row.Title ?? row.PmcId,
        chunkNumber: row.ChunkNumber,
        distance: row.Distance,
        passage: row.Passage,
        previousPassage: row.PreviousPassage,
        nextPassage: row.NextPassage,
      })),
    })
  } catch (error) {
    const apiError = error as ApiError
    response.status(apiError?.status ?? 500).json({
      code: apiError?.code ?? 'SEARCH_FAILED',
      message: apiError?.message ?? 'Search failed.',
    })
  }
})

if (existsSync(distIndex)) {
  app.use(express.static(distRoot))
  app.get(/^(?!\/api\/).*/, (_request, response) => {
    response.sendFile(distIndex)
  })
}

const port = Number.parseInt(process.env.PORT ?? '8000', 10)
// Container ingress requires binding all interfaces; local rehearsal stays loopback-only.
const host = process.env.HOST ?? '127.0.0.1'
const server = app.listen(port, host, () => {
  console.log(`Caldova API listening on http://${host}:${port}`)
})

async function shutDown() {
  server.close()
  await Promise.allSettled(
    [...pools.values()].map((entry) => entry.pool.then((pool) => pool.close())),
  )
}

process.on('SIGTERM', shutDown)
process.on('SIGINT', shutDown)

export { app }
