# Demo 2: Mission-Critical, at Any Scale

**Slide title:** Start small. Scale without re-architecting.

An evidence search application over a PMC corpus in Azure SQL Hyperscale. It runs the
same statement against a small serverless database and, once its embeddings finish
loading, a very large one. Nothing about the application changes in between.

## How search works

The corpus was ingested with **`minishlab/potion-base-32M`** through model2vec, producing
512-dimension float32 vectors that are L2-normalized and stored in
`dbo.pmc_chunks.embedding`. Queries are embedded with the same model at request time,
which is what makes the similarity meaningful.

> Verified, not assumed: re-encoding known chunks with `potion-base-32M` reproduces the
> stored vectors exactly (cosine 1.000000). `potion-retrieval-32M` scores 0.48–0.67 against
> the same rows, so it is a different vector space and must not be used for queries.

Three retrieval modes ship in one statement:

| Mode | What it does |
|---|---|
| **Vector** | Cosine ANN over the DiskANN index. Best for natural-language questions. |
| **Keyword** | `FREETEXTTABLE` full-text ranking. Best for rare or exact domain terms. |
| **Hybrid** | Reciprocal rank fusion of both. The default. |

Two design decisions came out of testing and matter more than they look:

- **One result per article.** Ranking raw chunks returned five passages from the same
  paper, which looked repetitive. Results are collapsed to the best passage per document.
- **Context expansion.** Each result carries the preceding and following chunk, so a
  passage that starts mid-sentence still reads. Journal front matter and reference lists
  are excluded through a persisted `is_boilerplate` flag.

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
Its embeddings are still loading, so no vector index has been built on it and the
application reports it as not ready rather than inventing a comparison.

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
- The large database gets no index and no writes until its load finishes.
