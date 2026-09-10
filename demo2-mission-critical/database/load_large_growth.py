#!/usr/bin/env python3
"""Restartably grow the indexed East US corpus from the frozen PMC sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import pyodbc

from deploy_common_schema import connect, database_token
from load_small_pilot import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EMBEDDING_MODEL_VERSION,
    EXTRACTION_VERSION,
    Article,
    Passage,
    azure_token,
    embed_batch,
    extract_article,
    sha256,
    stable_bigint,
    vector_json,
)

SERVER = "antho-test-server.database.windows.net"
DATABASE = "caldovadb"
DEFAULT_INVENTORY = Path(__file__).parents[1] / "source-discovery" / "inventory-sample-10000.json"
RUN_NAMESPACE = "pmc-large-growth-sample-v1"
MAX_EMBEDDING_INPUT_CHARS = 12000
TRANSIENT_SQL_ERRORS = (
    "08S01",
    "08001",
    "10053",
    "10054",
    "10060",
    "10928",
    "10929",
    "40197",
    "40501",
    "40613",
    "49918",
    "49919",
    "49920",
    "HYT00",
    "HYT01",
)
MAX_SHARD_SQL_ATTEMPTS = 10


def is_transient_sql_error(error: Exception) -> bool:
    message = str(error)
    return isinstance(error, pyodbc.Error) and (
        any(code in message for code in TRANSIENT_SQL_ERRORS)
        or "Token is expired" in message
    )


def chunks(values: Sequence, size: int) -> Iterable[Sequence]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def connect_with_retry(sql_token: bytes, attempts: int = 10):
    for attempt in range(attempts):
        try:
            return connect(SERVER, DATABASE, sql_token)
        except pyodbc.Error as exc:
            message = str(exc)
            if not is_transient_sql_error(exc) or attempt == attempts - 1:
                raise
            delay = min(2**attempt, 60) + random.uniform(0.25, 1.25)
            print(
                json.dumps(
                    {
                        "event": "azure_sql_connection_retry",
                        "attempt": attempt + 1,
                        "delay_seconds": round(delay, 2),
                        "error": message[:500],
                    }
                ),
                flush=True,
            )
            time.sleep(delay)


def existing_ids(connection, table: str, column: str, values: Sequence[int]) -> set[int]:
    found: set[int] = set()
    for group in chunks(values, 500):
        if not group:
            continue
        placeholders = ",".join("?" for _ in group)
        query = f"SELECT {column} FROM dbo.{table} WHERE {column} IN ({placeholders});"
        found.update(int(row[0]) for row in connection.execute(query, *group))
    return found


def initialize_run(run_id: uuid.UUID, inventory: dict, sql_token: bytes) -> None:
    with connect_with_retry(sql_token) as connection:
        index_row = connection.execute(
            """
            SELECT JSON_VALUE(vector_index.build_parameters, '$.Version'),
                   vector_index.distance_metric
            FROM sys.vector_indexes AS vector_index
            INNER JOIN sys.indexes AS index_definition
                ON index_definition.object_id = vector_index.object_id
               AND index_definition.index_id = vector_index.index_id
            WHERE vector_index.object_id = OBJECT_ID(N'dbo.PassageVector')
              AND index_definition.name = N'IX_PassageVector_Embedding';
            """
        ).fetchone()
        vector_count = int(connection.execute("SELECT COUNT_BIG(*) FROM dbo.PassageVector;").fetchone()[0])
        if vector_count < 1000 or index_row is None or tuple(index_row) != ("3", "COSINE"):
            raise RuntimeError("The 1,000-row anchor and version 3 cosine DiskANN index are required")
        connection.execute(
            """
            IF NOT EXISTS (SELECT 1 FROM dbo.IngestionRun WHERE IngestionRunId = ?)
                INSERT INTO dbo.IngestionRun
                (IngestionRunId, InventoryTimestampUtc, InventoryManifestSha256,
                 ExtractionVersion, EmbeddingModel, EmbeddingModelVersion,
                 EmbeddingDimensions, CorpusRole, RunStatus)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'LargeGrowth', 'Running');
            ELSE
                UPDATE dbo.IngestionRun
                SET RunStatus = CASE WHEN RunStatus = 'Succeeded' THEN RunStatus ELSE 'Running' END,
                    CompletedAtUtc = CASE WHEN RunStatus = 'Succeeded' THEN CompletedAtUtc ELSE NULL END
                WHERE IngestionRunId = ?;
            """,
            str(run_id),
            str(run_id),
            datetime.fromtimestamp(int(inventory["creation_timestamp"]) / 1000, timezone.utc).replace(tzinfo=None),
            bytes.fromhex(inventory["manifest_sha256"]),
            EXTRACTION_VERSION,
            EMBEDDING_MODEL,
            EMBEDDING_MODEL_VERSION,
            EMBEDDING_DIMENSIONS,
            str(run_id),
        )
        connection.commit()


def completed_shards(run_id: uuid.UUID, sql_token: bytes) -> set[int]:
    with connect_with_retry(sql_token) as connection:
        return {
            int(row[0])
            for row in connection.execute(
                """SELECT ShardNumber
                   FROM dbo.LoadBatch
                   WHERE IngestionRunId = ?
                     AND BatchStatus = 'Succeeded';""",
                str(run_id),
            )
        }


def mark_batch(run_id: uuid.UUID, shard_number: int, inventory: dict, entries: Sequence[dict], sql_token: bytes) -> tuple[int, bool]:
    load_batch_id = stable_bigint("large-growth-load-batch-v1", f"{run_id}:{shard_number}")
    staged_hash = hashlib.sha256(
        "\n".join(entry["key"] for entry in entries).encode("utf-8")
    ).digest()
    uri = f"pmc-inventory-sample://{inventory['sample_seed']}/shard/{shard_number}"
    with connect_with_retry(sql_token) as connection:
        row = connection.execute(
            "SELECT BatchStatus FROM dbo.LoadBatch WHERE LoadBatchId = ?;", load_batch_id
        ).fetchone()
        if row is not None and row[0] == "Succeeded":
            return load_batch_id, True
        connection.execute(
            """
            IF EXISTS (SELECT 1 FROM dbo.LoadBatch WHERE LoadBatchId = ?)
                UPDATE dbo.LoadBatch
                SET BatchStatus = 'Loading', AttemptCount = AttemptCount + 1,
                    StartedAtUtc = SYSUTCDATETIME(), CompletedAtUtc = NULL, LastError = NULL
                WHERE LoadBatchId = ?;
            ELSE
                INSERT INTO dbo.LoadBatch
                (LoadBatchId, IngestionRunId, EntityName, ShardNumber, StagedObjectUri,
                 StagedObjectSha256, ExpectedRowCount, BatchStatus, AttemptCount, StartedAtUtc)
                VALUES (?, ?, 'ArticleBundle', ?, ?, ?, 0, 'Loading', 1, SYSUTCDATETIME());
            """,
            load_batch_id,
            load_batch_id,
            load_batch_id,
            str(run_id),
            shard_number,
            uri,
            staged_hash,
        )
        connection.commit()
    return load_batch_id, False


def prepare_batch(entries: Sequence[dict]) -> tuple[list[Article], list[Passage]]:
    articles: list[Article] = []
    passages_by_hash: dict[bytes, Passage] = {}
    for entry in entries:
        extracted = extract_article(entry, 1000000)
        if extracted is None:
            continue
        article, candidate_passages = extracted
        accepted = [
            passage
            for passage in candidate_passages
            if len(passage.embedding_input) <= MAX_EMBEDDING_INPUT_CHARS
            and passage.content_sha256 not in passages_by_hash
        ]
        for passage in accepted:
            passages_by_hash[passage.content_sha256] = passage
        if accepted:
            articles.append(article)
    return articles, list(passages_by_hash.values())


def filter_existing(articles: list[Article], passages: list[Passage], sql_token: bytes) -> tuple[list[Article], list[Passage]]:
    with connect_with_retry(sql_token) as connection:
        existing_articles = existing_ids(connection, "Article", "ArticleId", [a.article_id for a in articles])
        passages = [p for p in passages if p.article_id not in existing_articles]
        existing_passages = existing_ids(connection, "PassageContent", "PassageId", [p.passage_id for p in passages])
        passages = [p for p in passages if p.passage_id not in existing_passages]
    passage_article_ids = {p.article_id for p in passages}
    return [a for a in articles if a.article_id in passage_article_ids], passages


def load_batch(
    run_id: uuid.UUID,
    load_batch_id: int,
    articles: list[Article],
    passages: list[Passage],
    vectors: list[list[float]],
    prompt_tokens: int,
    sql_token: bytes,
) -> int:
    if len(passages) != len(vectors):
        raise RuntimeError("Passage and embedding counts differ")
    embedding_hashes = [sha256(f"embedding-v1\0{vector_json(vector)}") for vector in vectors]
    with connect_with_retry(sql_token) as connection:
        connection.autocommit = False
        cursor = connection.cursor()
        cursor.fast_executemany = True
        try:
            selection_rank = int(
                cursor.execute("SELECT ISNULL(MAX(SelectionRank), 0) FROM dbo.CorpusSelectionManifest;").fetchone()[0]
            )
            if articles:
                cursor.executemany(
                    """INSERT INTO dbo.SourceObjectLedger
                       (SourceObjectId, IngestionRunId, PmcId, ArticleVersion, MetadataObjectKey,
                        MetadataEtag, XmlObjectKey, XmlMd5, LicenseCode, ProcessingStatus, LastAttemptAtUtc)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Accepted', SYSUTCDATETIME());""",
                    [(a.source_object_id, str(run_id), a.pmcid, a.version, a.metadata_key, a.metadata_etag, a.xml_key, a.xml_md5, a.license_code) for a in articles],
                )
                cursor.executemany(
                    """INSERT INTO dbo.Article
                       (ArticleId, PmcId, ArticleVersion, Pmid, Doi, ArticleTitle, JournalTitle,
                        ArticleType, LanguageCode, LicenseCode, LicenseClass, LicenseUrl,
                        AttributionParty, IsRetracted, IsCorrection, HasExpressionOfConcern,
                        VersionFamilyId, SourceJsonUrl, SourceXmlUrl, SourceEtag, XmlMd5,
                        InventoryTimestampUtc, SourceRecordSha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                    [(a.article_id, a.pmcid, a.version, a.pmid, a.doi, a.title, a.journal, a.article_type, a.language, a.license_code, a.license_code, a.license_url, a.is_retracted, a.is_correction, a.has_expression_of_concern, a.version_family_id, a.source_json_url, a.source_xml_url, a.metadata_etag, a.xml_md5, a.inventory_timestamp.replace(tzinfo=None), a.source_record_sha256) for a in articles],
                )
            if passages:
                cursor.executemany(
                    "INSERT INTO dbo.PassageContent (PassageId, ExtractionVersion, TokenCount, ContentSha256, PassageText) VALUES (?, ?, ?, ?, ?);",
                    [(p.passage_id, EXTRACTION_VERSION, max(1, len(p.embedding_input.split())), p.content_sha256, p.text) for p in passages],
                )
                cursor.executemany(
                    "INSERT INTO dbo.ArticlePassage (ArticlePassageId, ArticleId, PassageId, SectionPath, PassageOrdinal, SourceXmlMd5, ExtractionVersion, VersionFamilyId) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                    [(p.article_passage_id, p.article_id, p.passage_id, p.section_path, p.ordinal, p.xml_md5, EXTRACTION_VERSION, p.version_family_id) for p in passages],
                )
                per_passage_tokens = max(1, prompt_tokens // len(passages))
                cursor.executemany(
                    """INSERT INTO dbo.EmbeddingLedger
                       (PassageId, ContentSha256, EmbeddingModel, EmbeddingModelVersion,
                        EmbeddingDimensions, EmbeddingSha256, GenerationStatus,
                        PromptTokenCount, AttemptCount, GeneratedAtUtc)
                       VALUES (?, ?, ?, ?, ?, ?, 'Succeeded', ?, 1, SYSUTCDATETIME());""",
                    [(p.passage_id, p.content_sha256, EMBEDDING_MODEL, EMBEDDING_MODEL_VERSION, EMBEDDING_DIMENSIONS, embedding_hashes[i], per_passage_tokens) for i, p in enumerate(passages)],
                )
                cursor.executemany(
                    """INSERT INTO dbo.PassageVector
                       (PassageId, CanonicalArticlePassageId, Embedding, EmbeddingSha256,
                        EmbeddingModel, EmbeddingModelVersion, ExtractionVersion,
                        PublicationYear, LicenseClass, SafetyState, LanguageCode,
                        DomainCode, ArticleTypeCode)
                       VALUES (?, ?, CAST(CAST(? AS VARCHAR(MAX)) AS VECTOR(384)), ?, ?, ?, ?, NULL, ?, ?, ?, NULL, ?);""",
                    [(p.passage_id, p.article_passage_id, vector_json(vectors[i]), embedding_hashes[i], EMBEDDING_MODEL, EMBEDDING_MODEL_VERSION, EXTRACTION_VERSION, p.license_code, p.safety_state, p.language, p.article_type_code) for i, p in enumerate(passages)],
                )
                cursor.executemany(
                    """INSERT INTO dbo.CorpusSelectionManifest
                       (IngestionRunId, PassageId, ArticlePassageId, IsAnchor, IsCanonical,
                        SelectionRank, ContentSha256, EmbeddingSha256, SourceXmlMd5, ExtractionVersion)
                       VALUES (?, ?, ?, 0, 1, ?, ?, ?, ?, ?);""",
                    [(str(run_id), p.passage_id, p.article_passage_id, selection_rank + i + 1, p.content_sha256, embedding_hashes[i], p.xml_md5, EXTRACTION_VERSION) for i, p in enumerate(passages)],
                )
            cursor.execute(
                """UPDATE dbo.LoadBatch
                   SET ExpectedRowCount = CASE
                           WHEN ? = 0 THEN ISNULL(NULLIF(ExpectedRowCount, 0), ISNULL(LoadedRowCount, 0))
                           ELSE ?
                       END,
                       LoadedRowCount = CASE
                           WHEN ? = 0 THEN ISNULL(LoadedRowCount, 0)
                           ELSE ?
                       END,
                       BatchStatus = 'Succeeded',
                       CompletedAtUtc = SYSUTCDATETIME(), LastError = NULL
                   WHERE LoadBatchId = ?;""",
                len(passages), len(passages), len(passages), len(passages), load_batch_id,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.autocommit = True
    return len(passages)


def fail_batch(load_batch_id: int, error: Exception, sql_token: bytes) -> None:
    with connect_with_retry(sql_token, attempts=3) as connection:
        connection.execute(
            """UPDATE dbo.LoadBatch
               SET BatchStatus = 'Failed', CompletedAtUtc = SYSUTCDATETIME(), LastError = ?
               WHERE LoadBatchId = ?;""",
            str(error)[:2048], load_batch_id,
        )
        connection.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--articles-per-shard", type=int, default=10)
    parser.add_argument("--embedding-batch-size", type=int, default=64)
    parser.add_argument("--max-shards", type=int)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    run_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{RUN_NAMESPACE}:{inventory['manifest_sha256']}:{inventory['sample_seed']}")
    sql_token = database_token()
    initialize_run(run_id, inventory, sql_token)

    total_loaded = 0
    sql_token_started = time.monotonic()
    ai_token = azure_token("https://cognitiveservices.azure.com/")
    ai_token_started = time.monotonic()
    shards = list(chunks(inventory["sample"], args.articles_per_shard))
    durable_shards = completed_shards(run_id, sql_token)
    if args.max_shards is not None:
        shards = shards[: args.max_shards]

    for shard_number, entries in enumerate(shards, start=1):
        if shard_number in durable_shards:
            continue
        for shard_attempt in range(MAX_SHARD_SQL_ATTEMPTS):
            if time.monotonic() - sql_token_started > 1200:
                sql_token = database_token()
                sql_token_started = time.monotonic()
            if time.monotonic() - ai_token_started > 1200:
                ai_token = azure_token("https://cognitiveservices.azure.com/")
                ai_token_started = time.monotonic()
            load_batch_id: int | None = None
            try:
                load_batch_id, complete = mark_batch(run_id, shard_number, inventory, entries, sql_token)
                if complete:
                    break
                articles, passages = prepare_batch(entries)
                articles, passages = filter_existing(articles, passages, sql_token)
                vectors: list[list[float]] = []
                prompt_tokens = 0
                for embedding_inputs in chunks([p.embedding_input for p in passages], args.embedding_batch_size):
                    try:
                        batch_vectors, batch_tokens = embed_batch(embedding_inputs, ai_token)
                    except RuntimeError as exc:
                        if "Azure OpenAI embeddings HTTP 401" not in str(exc):
                            raise
                        ai_token = azure_token("https://cognitiveservices.azure.com/")
                        ai_token_started = time.monotonic()
                        batch_vectors, batch_tokens = embed_batch(embedding_inputs, ai_token)
                    vectors.extend(batch_vectors)
                    prompt_tokens += batch_tokens
                loaded = load_batch(run_id, load_batch_id, articles, passages, vectors, prompt_tokens, sql_token)
                total_loaded += loaded
                print(json.dumps({"shard": shard_number, "articles": len(articles), "vectors_loaded": loaded, "session_vectors": total_loaded}), flush=True)
                break
            except Exception as exc:
                if is_transient_sql_error(exc) and shard_attempt < MAX_SHARD_SQL_ATTEMPTS - 1:
                    delay = min(2**shard_attempt, 60) + random.uniform(0.25, 1.25)
                    print(
                        json.dumps(
                            {
                                "event": "azure_sql_shard_retry",
                                "shard": shard_number,
                                "attempt": shard_attempt + 1,
                                "delay_seconds": round(delay, 2),
                                "error": str(exc)[:500],
                            }
                        ),
                        flush=True,
                    )
                    time.sleep(delay)
                    sql_token = database_token()
                    sql_token_started = time.monotonic()
                    continue
                if load_batch_id is not None:
                    try:
                        fail_batch(load_batch_id, exc, sql_token)
                    except Exception as bookkeeping_exc:
                        print(
                            json.dumps(
                                {
                                    "event": "batch_failure_bookkeeping_deferred",
                                    "shard": shard_number,
                                    "original_error": str(exc)[:500],
                                    "bookkeeping_error": str(bookkeeping_exc)[:500],
                                }
                            ),
                            flush=True,
                        )
                raise

    if args.max_shards is None:
        with connect_with_retry(sql_token) as connection:
            connection.execute(
                "UPDATE dbo.IngestionRun SET RunStatus = 'Succeeded', CompletedAtUtc = SYSUTCDATETIME() WHERE IngestionRunId = ?;",
                str(run_id),
            )
            connection.commit()
    print(json.dumps({"run_id": str(run_id), "session_vectors_loaded": total_loaded, "status": "complete"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
