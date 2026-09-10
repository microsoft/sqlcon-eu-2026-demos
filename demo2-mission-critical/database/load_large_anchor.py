#!/usr/bin/env python3
"""Replay the checksummed 1,000-vector small anchor into the East US database."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from deploy_common_schema import connect, database_token

SERVER = "antho-test-server.database.windows.net"
DATABASE = "caldovadb"
DEFAULT_STAGING = Path(__file__).parents[1] / "staging" / "small-pilot-v1"

INSERTS = {
    "IngestionRun": (
        ("IngestionRunId", "InventoryTimestampUtc", "InventoryManifestSha256", "ExtractionVersion", "EmbeddingModel", "EmbeddingModelVersion", "EmbeddingDimensions", "CorpusRole", "RunStatus", "StartedAtUtc", "CompletedAtUtc"),
        "INSERT INTO dbo.IngestionRun (IngestionRunId, InventoryTimestampUtc, InventoryManifestSha256, ExtractionVersion, EmbeddingModel, EmbeddingModelVersion, EmbeddingDimensions, CorpusRole, RunStatus, StartedAtUtc, CompletedAtUtc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
    ),
    "SourceObjectLedger": (
        ("SourceObjectId", "IngestionRunId", "PmcId", "ArticleVersion", "MetadataObjectKey", "MetadataEtag", "XmlObjectKey", "XmlMd5", "LicenseCode", "ProcessingStatus", "RejectionReasonCode", "LastAttemptAtUtc"),
        "INSERT INTO dbo.SourceObjectLedger (SourceObjectId, IngestionRunId, PmcId, ArticleVersion, MetadataObjectKey, MetadataEtag, XmlObjectKey, XmlMd5, LicenseCode, ProcessingStatus, RejectionReasonCode, LastAttemptAtUtc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
    ),
    "Article": (
        ("ArticleId", "PmcId", "ArticleVersion", "Pmid", "Doi", "ArticleTitle", "JournalTitle", "PublicationDate", "PublicationYear", "ArticleType", "LanguageCode", "LicenseCode", "LicenseClass", "LicenseUrl", "AttributionParty", "IsRetracted", "IsCorrection", "HasExpressionOfConcern", "VersionFamilyId", "SourceJsonUrl", "SourceXmlUrl", "SourceEtag", "XmlMd5", "InventoryTimestampUtc", "SourceRecordSha256", "CreatedAtUtc", "UpdatedAtUtc"),
        "INSERT INTO dbo.Article (ArticleId, PmcId, ArticleVersion, Pmid, Doi, ArticleTitle, JournalTitle, PublicationDate, PublicationYear, ArticleType, LanguageCode, LicenseCode, LicenseClass, LicenseUrl, AttributionParty, IsRetracted, IsCorrection, HasExpressionOfConcern, VersionFamilyId, SourceJsonUrl, SourceXmlUrl, SourceEtag, XmlMd5, InventoryTimestampUtc, SourceRecordSha256, CreatedAtUtc, UpdatedAtUtc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
    ),
    "PassageContent": (
        ("PassageId", "ExtractionVersion", "TokenCount", "ContentSha256", "PassageText", "CreatedAtUtc"),
        "INSERT INTO dbo.PassageContent (PassageId, ExtractionVersion, TokenCount, ContentSha256, PassageText, CreatedAtUtc) VALUES (?, ?, ?, ?, ?, ?);",
    ),
    "ArticlePassage": (
        ("ArticlePassageId", "ArticleId", "PassageId", "SectionPath", "PassageOrdinal", "SourceXmlMd5", "ExtractionVersion", "VersionFamilyId"),
        "INSERT INTO dbo.ArticlePassage (ArticlePassageId, ArticleId, PassageId, SectionPath, PassageOrdinal, SourceXmlMd5, ExtractionVersion, VersionFamilyId) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
    ),
    "EmbeddingLedger": (
        ("PassageId", "ContentSha256", "EmbeddingModel", "EmbeddingModelVersion", "EmbeddingDimensions", "EmbeddingSha256", "GenerationStatus", "PromptTokenCount", "AttemptCount", "GeneratedAtUtc", "LastError"),
        "INSERT INTO dbo.EmbeddingLedger (PassageId, ContentSha256, EmbeddingModel, EmbeddingModelVersion, EmbeddingDimensions, EmbeddingSha256, GenerationStatus, PromptTokenCount, AttemptCount, GeneratedAtUtc, LastError) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
    ),
    "PassageVector": (
        ("PassageId", "CanonicalArticlePassageId", "Embedding", "EmbeddingSha256", "EmbeddingModel", "EmbeddingModelVersion", "ExtractionVersion", "PublicationYear", "LicenseClass", "SafetyState", "LanguageCode", "DomainCode", "ArticleTypeCode"),
        "INSERT INTO dbo.PassageVector (PassageId, CanonicalArticlePassageId, Embedding, EmbeddingSha256, EmbeddingModel, EmbeddingModelVersion, ExtractionVersion, PublicationYear, LicenseClass, SafetyState, LanguageCode, DomainCode, ArticleTypeCode) VALUES (?, ?, CAST(CAST(? AS VARCHAR(MAX)) AS VECTOR(384)), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
    ),
    "CorpusSelectionManifest": (
        ("IngestionRunId", "PassageId", "ArticlePassageId", "IsAnchor", "IsCanonical", "SelectionRank", "ContentSha256", "EmbeddingSha256", "SourceXmlMd5", "ExtractionVersion"),
        "INSERT INTO dbo.CorpusSelectionManifest (IngestionRunId, PassageId, ArticlePassageId, IsAnchor, IsCanonical, SelectionRank, ContentSha256, EmbeddingSha256, SourceXmlMd5, ExtractionVersion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
    ),
}


def decode(value: Any) -> Any:
    if isinstance(value, dict) and "$binary_hex" in value:
        return bytes.fromhex(value["$binary_hex"])
    if isinstance(value, dict) and "$iso8601" in value:
        return datetime.fromisoformat(value["$iso8601"])
    if isinstance(value, dict) and "$decimal" in value:
        return value["$decimal"]
    return value


def read_verified(staging: Path, file_info: dict[str, Any]) -> list[dict[str, Any]]:
    path = staging / file_info["path"]
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != file_info["sha256"]:
        raise RuntimeError(f"Checksum mismatch: {path}")
    records = [json.loads(line) for line in payload.splitlines() if line]
    if len(records) != file_info["rows"]:
        raise RuntimeError(f"Row-count mismatch: {path}")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    args = parser.parse_args()
    manifest = json.loads((args.staging / "manifest.json").read_text(encoding="utf-8"))
    if manifest["embedding_dimensions"] != 384:
        raise RuntimeError("The staged anchor does not use 384 dimensions")

    files = {item["entity"]: item for item in manifest["files"]}
    records = {entity: read_verified(args.staging, files[entity]) for entity in INSERTS}
    if len(records["PassageVector"]) != 1000:
        raise RuntimeError("The anchor must contain exactly 1,000 passage vectors")

    with connect(SERVER, DATABASE, database_token()) as connection:
        current = connection.execute("SELECT COUNT_BIG(*) FROM dbo.PassageVector;").fetchone()[0]
        if current not in {0, 1000}:
            raise RuntimeError(f"Large target contains {current} vectors; expected 0 or 1,000")

        if current == 0:
            connection.autocommit = False
            try:
                cursor = connection.cursor()
                cursor.fast_executemany = True
                for entity, (columns, statement) in INSERTS.items():
                    values = [tuple(decode(record[column]) for column in columns) for record in records[entity]]
                    for start in range(0, len(values), 100):
                        cursor.executemany(statement, values[start : start + 100])
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.autocommit = True

        counts = connection.execute(
            """
            SELECT (SELECT COUNT_BIG(*) FROM dbo.Article),
                   (SELECT COUNT_BIG(*) FROM dbo.PassageContent),
                   (SELECT COUNT_BIG(*) FROM dbo.PassageVector),
                   (SELECT COUNT_BIG(*) FROM dbo.CorpusSelectionManifest);
            """
        ).fetchone()
        if tuple(counts) != (32, 1000, 1000, 1000):
            raise RuntimeError(f"Unexpected anchor counts: {tuple(counts)}")
        index_sql = Path(__file__).with_name("02-create-vector-index.sql.template").read_text(encoding="utf-8")
        connection.execute(index_sql)
        version = connection.execute(
            """
            SELECT JSON_VALUE(vector_index.build_parameters, '$.Version')
            FROM sys.vector_indexes AS vector_index
            INNER JOIN sys.indexes AS index_definition
                ON index_definition.object_id = vector_index.object_id
               AND index_definition.index_id = vector_index.index_id
            WHERE vector_index.object_id = OBJECT_ID(N'dbo.PassageVector')
              AND index_definition.name = N'IX_PassageVector_Embedding';
            """
        ).fetchone()[0]
        if version != "3":
            raise RuntimeError(f"Unexpected DiskANN version: {version}")

    print(json.dumps({"status": "ready", "articles": 32, "vectors": 1000, "diskann_version": version}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
