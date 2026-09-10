# Caldova

Caldova is the stage application for the Demo 2 thesis:

> Start small. Scale without re-architecting.

It is a biomedical evidence explorer. A natural-language question is embedded at request
time, and one parameterized statement runs against whichever Azure SQL Hyperscale target is
selected. The statement does not change between targets; only the connection does.

## How a search works

1. The question is sent to the embedding service, which returns 512 L2-normalized
   `float32` values.
2. That vector and the raw question are passed to [search.sql](../database/search.sql).
3. The statement runs up to two retrievals and fuses them:
   - **Vector** — approximate nearest neighbour over the DiskANN cosine index.
   - **Keyword** — `FREETEXTTABLE` over the full-text index.
   - **Hybrid** — both, combined with reciprocal rank fusion (k = 60).
4. Results are deduplicated to the best passage per article, boilerplate is excluded, and
   the neighbouring passages are attached so each quote reads in context.

`VectorSearchMs` is measured inside the engine around the ANN retrieval only, so it
excludes the round trip and the embedding call. The UI reports it separately from total
time.

## Fail-closed behaviour

Every target is checked before it is queried. If the database is unreachable, or the vector
or full-text index is missing, the app reports why and leaves the timings as `--`. It never
displays a number it cannot back up.

## Environments

| Key | Database | Purpose |
|---|---|---|
| `small` | `research` on `antho-caldova` | Hyperscale serverless pilot, auto-pauses |
| `large` | `vbench_large` | The full corpus, still loading embeddings |
| `replica` | `research-replica` | Serverless named replica of `vbench_large` |

The named replica shares the primary's storage but has its own compute, so reading through
it does not compete with the loading job on the primary.

## Configuration

The API reads these at startup and does not load `.env` files automatically:

```bash
export AZURE_SQL_SMALL_SERVER='antho-caldova.database.windows.net'
export AZURE_SQL_SMALL_DATABASE='research'
export AZURE_SQL_LARGE_SERVER='vbnech-large-server.database.windows.net'
export AZURE_SQL_LARGE_DATABASE='vbench_large'
export AZURE_SQL_REPLICA_SERVER='vbnech-large-server.database.windows.net'
export AZURE_SQL_REPLICA_DATABASE='research-replica'
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
