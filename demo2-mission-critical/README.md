# Demo 2: Mission-Critical, at Any Scale

**Slide title:** Start small. Scale without re-architecting.

An evidence search application over a PMC corpus in Azure SQL Hyperscale. It runs the
same application contract against a 4K serverless pilot, a 1M indexed table on the
primary, and that same 1M index through a named replica. A 1B table is also visible, but
the app correctly withholds search until its own vector index exists.

## How search works

The corpus was ingested with **`minishlab/potion-base-32M`** through model2vec, producing
512-dimension float32 vectors that are L2-normalized and stored in
`dbo.pmc_chunks.embedding`. Queries are embedded with the same model at request time,
which is what makes the similarity meaningful.

> Verified, not assumed: re-encoding known chunks with `potion-base-32M` reproduces the
> stored vectors exactly (cosine 1.000000). `potion-retrieval-32M` scores 0.48–0.67 against
> the same rows, so it is a different vector space and must not be used for queries.

Three retrieval modes ship for the 4K pilot:

| Mode | What it does |
|---|---|
| **Vector** | Cosine ANN over the DiskANN index. Best for natural-language questions. |
| **Keyword** | `FREETEXTTABLE` full-text ranking. Best for rare or exact domain terms. |
| **Hybrid** | Reciprocal rank fusion of both. The default. |

The larger tables have the same vector shape but not the pilot's full-text index or
filtering metadata, so their compatible query profile is vector-only.

Two design decisions came out of testing and matter more than they look:

- **One result per article.** Ranking raw chunks returned five passages from the same
  paper, which looked repetitive. Results are collapsed to the best passage per document.
- **Context expansion.** Each result carries the preceding and following chunk, so a
  passage that starts mid-sentence still reads. Journal front matter and reference lists
  are excluded through a persisted `is_boilerplate` flag.

## What the timer measures

The app shows **vector search** time, not the round trip. The ANN step is materialised into
a table variable on its own and timed inside the engine with `SYSUTCDATETIME()`, so the
number excludes rank fusion, the document joins, and context expansion.

On the pilot it runs around 5 ms warm and about 25 ms on the first call after a resume.
In keyword mode there is no vector search, so the field reads `--` rather than borrowing
the round-trip number.

## Four targets

| UI label | Environment key | What it is | Current state |
|---|---|---|---|
| `4K` | `small` | Serverless Hyperscale pilot | 4,076 passages, hybrid ready |
| `1M` | `million` | `dbo.pmc_chunks_1M` on the primary | 1,000,113 passages, vector ready |
| `1B` | `billion` | `dbo.pmc_chunks` on the primary | 1,000,000,014 passages, index not built |
| `Named Replica` | `replica` | The 1M table through a named replica | 1,000,113 passages, vector ready |

A named replica shares the primary's storage, so no data is copied and the corpus stays in
one place. It is read-only and sized independently, which is exactly what a search workload
wants. The application keeps one result contract while selecting a compatible query and
table from a fixed server-side allowlist.

### Replica status

`research-replica` **exists and is Online**: `HS_S_Gen5_8` serverless named replica of
`vbench_large`, min 1 vCore, on `vbnech-large-server` in East US 2. The app is configured to
use it. A live local API validation returned five results from the 1M vector index on both
the primary and named replica.

`autoPauseDelay` reads `-1` because East US 2 does not persist auto-pause. That is expected
and does not matter here; auto-pause is demonstrated on the pilot.

The deployed managed identity still needs these prerequisites if they have not already
been completed by the owner of `vbnech-large-server`:

1. **A network path from the app.** The Container Apps environment has around 160 rotating
   outbound addresses, so per-IP firewall rules are not workable. Either enable
   *Allow Azure services* on the server, or put the Container Apps environment on a VNet
   behind a NAT gateway and allow that single address. The second is narrower and is the
   better answer if there is time.

2. **A database user for the app identity.** A named replica is read-only, so the user
   cannot be created on the replica. It has to be created on the **primary**, where it then
   replicates:

   ```sql
   -- On vbench_large, by the server's Entra administrator
   CREATE USER [caldova-workload-id] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [caldova-workload-id];
   ```

The `vidx_embedding` cosine vector index on `dbo.pmc_chunks_1M` is already enabled on the
primary and visible through shared storage on the replica. The 1B table remains unindexed.

[deploy/create-named-replica.sh](deploy/create-named-replica.sh) records how the replica was
created. Note that `az sql db replica create` cannot make a serverless named replica: it
demands `-e` for a serverless SKU and then rejects `-e` as unrecognised, so the script uses
an ARM REST call.

## Layout

```
app/            React client + Express API (search, readiness)
embedding/      FastAPI service running the corpus embedding model
database/       Schema, corpus export and load, search SQL, retrieval evaluation
workload/       Scheduled job that exercises auto-pause and resume
staging/        Curated corpus package with its original embeddings
deploy/         Container Apps definition (API + embedding in one replica)
fabric-app/     Rayfin static hosting configuration
docs/           Demo plan, stage script, recording script
```

## Deployed state

| | |
|---|---|
| Server | `antho-caldova.database.windows.net`, West Central US |
| Database | `research`, `HS_S_Gen5_2` serverless, 0.5–2 vCores, 60-minute auto-pause |
| Auth | Microsoft Entra only |
| Corpus | 44 articles, 4,076 passages |
| Vector index | `IX_pmc_chunks_embedding`, cosine DiskANN version 3 |
| Full-text | `CaldovaCatalog` on `text_chunk` |
| App | https://caldova-app.whitemeadow-b4119f0c.westcentralus.azurecontainerapps.io |
| Workload | Container Apps job `caldova-workload`, every 3 hours |

The large database (`vbnech-large-server` / `vbench_large`) is **read-only** for this work.
The existing 1M vector index is used as-is. No index has been built on the 1B table, so the
application reports that target as not ready rather than inventing a comparison.

## Rebuild from scratch

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Curate a corpus from the large database (read-only) and keep its embeddings
python database/export_curated_corpus.py --docs-per-topic 3

# 2. Check retrieval quality offline before touching a database
python database/inspect_retrieval.py

# 3. Apply schema, load, and build the indexes
python database/apply_schema.py 10-research-schema.sql.template
python database/load_curated_corpus.py --apply
python database/create_fulltext_index.py

# 4. Run it
cd embedding && uvicorn main:app --port 8081 &
cd ../app && npm install && npm run build
AZURE_SQL_SMALL_SERVER=antho-caldova.database.windows.net \
AZURE_SQL_SMALL_DATABASE=research npm start
```

## Ground rules

- No latency or scale number is spoken unless it appears in a retained report.
- The app shows `--` and an explanation when a database is not ready.
- The existing 1M index is read-only for this demo; the 1B table gets no index or writes.
