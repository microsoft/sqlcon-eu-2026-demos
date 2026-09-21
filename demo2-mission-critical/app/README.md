# Caldova

Caldova is the stage application for the Demo 2 thesis:

> Start small. Scale without re-architecting.

It is a biomedical evidence explorer. A natural-language question is embedded at request
time and sent to the selected Azure SQL Hyperscale target. The target contract stays fixed,
while a server-side allowlist chooses the compatible table and query profile.

## How a search works

1. The question is sent to the embedding service, which returns 512 L2-normalized
   `float32` values.
2. That vector and the raw question are passed to the selected retrieval query.
3. The 4K target runs up to two retrievals and fuses them:
   - **Vector** — approximate nearest neighbour over the DiskANN cosine index.
   - **Keyword** — `FREETEXTTABLE` over the full-text index.
   - **Hybrid** — both, combined with reciprocal rank fusion (k = 60).
4. The scale targets run vector-only retrieval because their source table has no full-text
   index or hybrid-query metadata columns.
5. Results are deduplicated to the best passage per article and neighbouring passages are
   attached so each quote reads in context.

`VectorSearchMs` is measured inside the engine around the ANN retrieval only, so it
excludes the round trip and the embedding call. The UI reports it separately from total
time.

## Readiness and recording scale

Every target is checked before it is queried. If the database is unreachable or the index
required by that target is missing, the app reports why and leaves the timings as `--`. It
does not invent a timing. Unsupported modes and filters are also rejected instead of silently
changing their meaning.

`CALDOVA_LARGE_SCALE_MODE` makes the review-recording setup explicit:

- `1M` (default) queries the indexed `dbo.pmc_chunks_1M` table for both visible large targets
   and presents `1,000,000,014` as **Rows searched**. This is a stage projection for recording,
   not a measured scan cardinality or a 1B latency benchmark.
- `1B` queries `dbo.pmc_chunks` for both large targets, reports its measured row count, and
   requires a real vector index on that table. Readiness fails closed until that index exists.

Restart the API after changing the value. The standalone `1M` API key remains available for
diagnostics, but the UI hides it so the recording flow is `4K` → `1B` → `Named Replica`.

## Environments

| Key | UI label | Database table | Search profile | Verified state |
|---|---|---|---|---|
| `small` | `4K` | `research.dbo.pmc_chunks` | Hybrid | 4,076 passages, ready |
| `million` | Hidden | `vbench_large.dbo.pmc_chunks_1M` | Vector | Diagnostic API target |
| `billion` | `1B` | Selected by `CALDOVA_LARGE_SCALE_MODE` | Vector | 1M recording projection or real 1B |
| `replica` | `Named Replica` | Selected by `CALDOVA_LARGE_SCALE_MODE` | Vector | 1M recording projection or real 1B |

The named replica shares the primary's storage and 1M vector index but has its own compute,
so reading through it does not compete with work on the primary. Table identifiers are not
accepted from API input; they come only from the fixed mapping in `server/index.ts`.

## Configuration

The API reads these at startup and does not load `.env` files automatically:

```bash
export AZURE_SQL_SMALL_SERVER='antho-caldova.database.windows.net'
export AZURE_SQL_SMALL_DATABASE='research'
export AZURE_SQL_LARGE_SERVER='vbnech-large-server.database.windows.net'
export AZURE_SQL_LARGE_DATABASE='vbench_large'
export AZURE_SQL_REPLICA_SERVER='vbnech-large-server.database.windows.net'
export AZURE_SQL_REPLICA_DATABASE='research-replica'
export CALDOVA_LARGE_SCALE_MODE='1M' # recording projection; use 1B for the real table
export EMBEDDING_SERVICE_URL='http://127.0.0.1:8081'
```

An environment with no server or database configured reports "not configured" rather than
failing at query time. Local runs use the Azure CLI credential; the deployment uses the
`caldova-workload-id` managed identity via `AZURE_CLIENT_ID`.

## Run locally

The API needs the embedding service running, since query vectors are computed per request:

```bash
cd ../embedding && uvicorn main:app --port 8081
```

Then, from this directory:

```bash
npm install
npm run build
npm start
```

Open `http://127.0.0.1:8000`. For development with hot reload, run `npm run dev:api` and
`npm run dev` in separate terminals and open the Vite URL.

## API

| Route | Purpose |
|---|---|
| `GET /api/readiness/:environment` | Whether a target is configured, reachable, and indexed |
| `POST /api/search` | `{ environment, mode, query }` returns evidence and timings |

## Commands

| Command | Purpose |
|---|---|
| `npm run build` | Typecheck server and client, build static assets |
| `npm run lint` | Run repository lint rules |
| `npm start` | Serve the built app and API on `127.0.0.1:8000` |

## Deployment

The app and the embedding service run as two containers in one Azure Container Apps
replica, so they communicate over loopback. See
[caldova-app.yaml](../deploy/caldova-app.yaml).
