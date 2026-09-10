#!/usr/bin/env python3
"""Export the exact loaded small pilot as checksummed deterministic JSONL shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from deploy_common_schema import connect, database_token

SERVER = "antho-test-server-uksouth.database.windows.net"
DATABASE = "caldovadb"

EXPORTS = {
    "IngestionRun": """
        SELECT IngestionRunId, InventoryTimestampUtc, InventoryManifestSha256,
               ExtractionVersion, EmbeddingModel, EmbeddingModelVersion,
               EmbeddingDimensions, CorpusRole, RunStatus, StartedAtUtc, CompletedAtUtc
        FROM dbo.IngestionRun ORDER BY IngestionRunId;
    """,
    "SourceObjectLedger": """
        SELECT SourceObjectId, IngestionRunId, PmcId, ArticleVersion,
               MetadataObjectKey, MetadataEtag, XmlObjectKey, XmlMd5,
               LicenseCode, ProcessingStatus, RejectionReasonCode, LastAttemptAtUtc
        FROM dbo.SourceObjectLedger ORDER BY SourceObjectId;
    """,
    "Article": """
        SELECT ArticleId, PmcId, ArticleVersion, Pmid, Doi, ArticleTitle,
               JournalTitle, PublicationDate, PublicationYear, ArticleType,
               LanguageCode, LicenseCode, LicenseClass, LicenseUrl,
               AttributionParty, IsRetracted, IsCorrection, HasExpressionOfConcern,
               VersionFamilyId, SourceJsonUrl, SourceXmlUrl, SourceEtag, XmlMd5,
               InventoryTimestampUtc, SourceRecordSha256, CreatedAtUtc, UpdatedAtUtc
        FROM dbo.Article ORDER BY ArticleId;
    """,
    "PassageContent": """
        SELECT PassageId, ExtractionVersion, TokenCount, ContentSha256,
               PassageText, CreatedAtUtc
        FROM dbo.PassageContent ORDER BY PassageId;
    """,
    "ArticlePassage": """
        SELECT ArticlePassageId, ArticleId, PassageId, SectionPath,
               PassageOrdinal, SourceXmlMd5, ExtractionVersion, VersionFamilyId
        FROM dbo.ArticlePassage ORDER BY ArticlePassageId;
    """,
    "EmbeddingLedger": """
        SELECT PassageId, ContentSha256, EmbeddingModel, EmbeddingModelVersion,
               EmbeddingDimensions, EmbeddingSha256, GenerationStatus,
               PromptTokenCount, AttemptCount, GeneratedAtUtc, LastError
        FROM dbo.EmbeddingLedger ORDER BY PassageId;
    """,
    "PassageVector": """
        SELECT PassageId, CanonicalArticlePassageId,
               CAST(Embedding AS VARCHAR(MAX)) AS Embedding,
               EmbeddingSha256, EmbeddingModel, EmbeddingModelVersion,
               ExtractionVersion, PublicationYear, LicenseClass, SafetyState,
               LanguageCode, DomainCode, ArticleTypeCode
        FROM dbo.PassageVector ORDER BY PassageId;
    """,
    "CorpusSelectionManifest": """
        SELECT IngestionRunId, PassageId, ArticlePassageId, IsAnchor,
               IsCanonical, SelectionRank, ContentSha256, EmbeddingSha256,
               SourceXmlMd5, ExtractionVersion
        FROM dbo.CorpusSelectionManifest
        ORDER BY IngestionRunId, PassageId, ArticlePassageId;
    """,
}


def encode(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"$binary_hex": value.hex()}
    if isinstance(value, (datetime, date)):
        return {"$iso8601": value.isoformat()}
    if isinstance(value, Decimal):
        return {"$decimal": str(value)}
    return value


def export(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": "pmc-small-anchor-jsonl-v1",
        "source_server": SERVER,
        "database": DATABASE,
        "embedding_dimensions": 384,
        "files": [],
    }
    with connect(SERVER, DATABASE, database_token()) as connection:
        for entity, query in EXPORTS.items():
            cursor = connection.execute(query)
            columns = [description[0] for description in cursor.description]
            path = output / f"{entity}.jsonl"
            digest = hashlib.sha256()
            count = 0
            with path.open("wb") as stream:
                for row in cursor:
                    record = {column: encode(value) for column, value in zip(columns, row)}
                    line = (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                    stream.write(line)
                    digest.update(line)
                    count += 1
            manifest["files"].append(
                {
                    "entity": entity,
                    "path": path.name,
                    "rows": count,
                    "bytes": path.stat().st_size,
                    "sha256": digest.hexdigest(),
                }
            )
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
