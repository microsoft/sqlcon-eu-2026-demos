#!/usr/bin/env python3
"""Build the UK South small scenario from checksum-verified PMC passages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import random
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

sys.path.insert(0, str(Path(__file__).parents[1] / "source-discovery"))

from pmc_discovery import (  # noqa: E402
    ALLOWED_LICENSES,
    XLINK_HREF,
    metadata_url,
    normalize_text,
    read_json,
    request,
    xml_url_from_metadata,
)

from deploy_common_schema import connect, database_token  # noqa: E402

SERVER = "antho-test-server-uksouth.database.windows.net"
DATABASE = "caldovadb"
AOAI_ENDPOINT = os.getenv("PMC_AOAI_ENDPOINT", "https://antho-openai.openai.azure.com")
AOAI_DEPLOYMENT = os.getenv("PMC_AOAI_DEPLOYMENT", "text-embedding-3-small")
AOAI_API_VERSION = "2024-02-01"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_MODEL_VERSION = "1"
EMBEDDING_DIMENSIONS = 384
EXTRACTION_VERSION = "pmc-paragraph-pilot-v1"
SPACE = re.compile(r"\s+")
SYSTEM_CA_FILE = Path("/etc/ssl/cert.pem")


@dataclass(frozen=True)
class Article:
    article_id: int
    source_object_id: int
    pmcid: str
    version: int
    pmid: int | None
    doi: str | None
    title: str
    journal: str | None
    article_type: str | None
    language: str | None
    license_code: str
    license_url: str | None
    is_retracted: bool
    is_correction: bool
    has_expression_of_concern: bool
    version_family_id: int
    metadata_key: str
    metadata_etag: str
    xml_key: str
    xml_md5: str
    inventory_timestamp: datetime
    source_json_url: str
    source_xml_url: str
    source_record_sha256: bytes


@dataclass(frozen=True)
class Passage:
    passage_id: int
    article_passage_id: int
    article_id: int
    text: str
    content_sha256: bytes
    section_path: str | None
    ordinal: int
    xml_md5: str
    version_family_id: int
    license_code: str
    language: str | None
    safety_state: int
    article_type_code: str | None
    embedding_input: str


def stable_bigint(namespace: str, value: str) -> int:
    digest = hashlib.sha256(f"{namespace}\0{value}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def sha256(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child(element: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in element if local_name(node.tag) == name), None)


def body_passages(root: ET.Element) -> Iterable[tuple[str | None, str]]:
    body = next((node for node in root.iter() if local_name(node.tag) == "body"), None)
    if body is None:
        return

    def walk(container: ET.Element, titles: tuple[str, ...]) -> Iterable[tuple[str | None, str]]:
        for node in container:
            name = local_name(node.tag)
            if name == "sec":
                section_title = normalize_text(child(node, "title"))
                next_titles = titles + ((section_title,) if section_title else ())
                yield from walk(node, next_titles)
            elif name == "p":
                text = normalize_text(node)
                if text and len(text) >= 80:
                    yield " / ".join(titles) or None, text
            elif name not in {"ref-list", "fig", "table-wrap"}:
                yield from walk(node, titles)

    yield from walk(body, ())


def xml_identity(root: ET.Element, id_type: str) -> str | None:
    for node in root.iter():
        if local_name(node.tag) == "article-id" and node.get("pub-id-type") == id_type:
            return normalize_text(node)
    return None


def extract_article(
    inventory_entry: dict,
    remaining: int,
) -> tuple[Article, list[Passage]] | None:
    metadata = read_json(metadata_url(inventory_entry["key"]))
    if not metadata.get("is_pmc_openaccess"):
        return None
    license_code = metadata.get("license_code")
    if license_code not in ALLOWED_LICENSES:
        return None

    xml_url, expected_md5 = xml_url_from_metadata(metadata)
    with request(xml_url) as response:
        xml_bytes = response.read()
    actual_md5 = hashlib.md5(xml_bytes, usedforsecurity=False).hexdigest()
    if not expected_md5 or actual_md5 != expected_md5:
        raise ValueError(f"XML MD5 mismatch for {metadata.get('pmcid')}")

    root = ET.fromstring(xml_bytes)
    pmcid = str(metadata.get("pmcid") or "")
    version = int(metadata.get("version") or 0)
    jats_pmcid = xml_identity(root, "pmc")
    if not pmcid or version <= 0 or (jats_pmcid and jats_pmcid != pmcid.removeprefix("PMC")):
        raise ValueError(f"Identity mismatch for {inventory_entry['key']}")

    title = next(
        (
            value
            for node in root.iter()
            if local_name(node.tag) == "article-title"
            and (value := normalize_text(node))
        ),
        str(metadata.get("title") or pmcid),
    )
    journal = next(
        (
            value
            for node in root.iter()
            if local_name(node.tag) == "journal-title" and (value := normalize_text(node))
        ),
        None,
    )
    license_node = next(
        (node for node in root.iter() if local_name(node.tag) == "license"),
        None,
    )
    license_url = license_node.get(XLINK_HREF) if license_node is not None else None
    article_type = root.get("article-type")
    language = (root.get("{http://www.w3.org/XML/1998/namespace}lang") or "").lower() or None
    is_correction = "correct" in (article_type or "").lower()
    related_types = {
        (node.get("related-article-type") or "").lower()
        for node in root.iter()
        if local_name(node.tag) == "related-article"
    }
    has_eoc = any("expression-of-concern" in value for value in related_types)
    is_retracted = bool(metadata.get("is_retracted"))
    safety_state = 1 if is_retracted else 2 if has_eoc else 3 if is_correction else 0
    article_id = stable_bigint("article-v1", f"{pmcid}\0{version}")
    version_family_id = stable_bigint("version-family-v1", pmcid)
    source_object_id = stable_bigint("source-object-v1", inventory_entry["key"])
    xml_key = urllib.parse.unquote(urllib.parse.urlparse(xml_url).path.lstrip("/"))
    source_record_hash = sha256(
        f"source-record-v1\0{pmcid}\0{version}\0{inventory_entry['etag']}\0{actual_md5}"
    )
    article = Article(
        article_id=article_id,
        source_object_id=source_object_id,
        pmcid=pmcid,
        version=version,
        pmid=int(metadata["pmid"]) if metadata.get("pmid") else None,
        doi=metadata.get("doi"),
        title=title[:2000],
        journal=journal[:512] if journal else None,
        article_type=article_type[:128] if article_type else None,
        language=language[:16] if language else None,
        license_code=license_code,
        license_url=license_url[:1024] if license_url else None,
        is_retracted=is_retracted,
        is_correction=is_correction,
        has_expression_of_concern=has_eoc,
        version_family_id=version_family_id,
        metadata_key=inventory_entry["key"],
        metadata_etag=inventory_entry["etag"][:128],
        xml_key=xml_key,
        xml_md5=actual_md5,
        inventory_timestamp=datetime.fromisoformat(inventory_entry["last_modified"].replace("Z", "+00:00")),
        source_json_url=metadata_url(inventory_entry["key"]),
        source_xml_url=xml_url,
        source_record_sha256=source_record_hash,
    )

    passages: list[Passage] = []
    for ordinal, (section_path, raw_text) in enumerate(body_passages(root), start=1):
        text = SPACE.sub(" ", raw_text).strip()
        content_hash = sha256(f"{EXTRACTION_VERSION}\0{text}")
        passage_id = stable_bigint("passage-v1", content_hash.hex())
        article_passage_id = stable_bigint(
            "article-passage-v1", f"{article_id}\0{ordinal}\0{EXTRACTION_VERSION}"
        )
        context = f"Title: {title}\n"
        if section_path:
            context += f"Section: {section_path}\n"
        context += f"Passage: {text}"
        passages.append(
            Passage(
                passage_id=passage_id,
                article_passage_id=article_passage_id,
                article_id=article_id,
                text=text,
                content_sha256=content_hash,
                section_path=section_path[:1000] if section_path else None,
                ordinal=ordinal,
                xml_md5=actual_md5,
                version_family_id=version_family_id,
                license_code=license_code,
                language=language[:16] if language else None,
                safety_state=safety_state,
                article_type_code=article_type[:64] if article_type else None,
                embedding_input=context,
            )
        )
        if len(passages) >= remaining:
            break
    return article, passages


def azure_token(resource: str) -> str:
    result = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            resource,
            "--query",
            "accessToken",
            "--output",
            "tsv",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def embed_batch(inputs: Sequence[str], token: str) -> tuple[list[list[float]], int]:
    url = (
        f"{AOAI_ENDPOINT}/openai/deployments/{AOAI_DEPLOYMENT}/embeddings"
        f"?api-version={AOAI_API_VERSION}"
    )
    payload = json.dumps(
        {"input": list(inputs), "dimensions": EMBEDDING_DIMENSIONS},
        ensure_ascii=False,
    ).encode("utf-8")
    context = ssl.create_default_context(
        cafile=str(SYSTEM_CA_FILE) if SYSTEM_CA_FILE.exists() else None
    )
    for attempt in range(12):
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "sqlcon-barcelona-small-pilot/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=context) as response:
                body = json.load(response)
            vectors = [item["embedding"] for item in sorted(body["data"], key=lambda item: item["index"])]
            if len(vectors) != len(inputs) or any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
                raise ValueError("Embedding response count or dimensions did not match the contract")
            if body.get("model") != EMBEDDING_MODEL:
                raise ValueError(f"Unexpected embedding model: {body.get('model')}")
            return vectors, int(body.get("usage", {}).get("prompt_tokens", 0))
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504}:
                detail = exc.read().decode("utf-8", errors="replace")[:2048]
                raise RuntimeError(f"Azure OpenAI embeddings HTTP {exc.code}: {detail}") from exc
            if attempt == 11:
                raise
            retry_after_ms = exc.headers.get("retry-after-ms")
            retry_after = exc.headers.get("Retry-After")
            if retry_after_ms:
                delay = float(retry_after_ms) / 1000
            elif retry_after:
                try:
                    delay = float(retry_after)
                except ValueError:
                    delay = min(2**attempt, 120)
            else:
                delay = min(2**attempt, 120)
            time.sleep(max(1.0, delay) + random.uniform(0.25, 1.25))
    raise RuntimeError("Embedding retry loop exhausted")


def chunks(values: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def vector_json(vector: Sequence[float]) -> str:
    return json.dumps(vector, separators=(",", ":"))


def load_database(
    articles: list[Article],
    passages: list[Passage],
    vectors: list[list[float]],
    prompt_tokens: int,
    inventory: dict,
) -> uuid.UUID:
    run_id = uuid.uuid5(uuid.NAMESPACE_URL, f"pmc-small-pilot-v1:{inventory['manifest_sha256']}:{len(passages)}")
    token = database_token()
    with connect(SERVER, DATABASE, token) as connection:
        connection.autocommit = False
        cursor = connection.cursor()
        try:
            cursor.execute("""
                IF EXISTS (SELECT 1 FROM dbo.IngestionRun WHERE IngestionRunId = ?)
                    THROW 51010, 'This deterministic pilot run is already loaded.', 1;
                IF EXISTS (SELECT 1 FROM dbo.PassageVector)
                    THROW 51011, 'The small target is not empty; refusing to mix pilot corpora.', 1;
            """, str(run_id))
            cursor.execute(
                """INSERT INTO dbo.IngestionRun
                   (IngestionRunId, InventoryTimestampUtc, InventoryManifestSha256,
                    ExtractionVersion, EmbeddingModel, EmbeddingModelVersion,
                    EmbeddingDimensions, CorpusRole, RunStatus)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'Anchor', 'Running');""",
                str(run_id),
                datetime.fromtimestamp(int(inventory["creation_timestamp"]) / 1000, timezone.utc).replace(tzinfo=None),
                bytes.fromhex(inventory["manifest_sha256"]),
                EXTRACTION_VERSION,
                EMBEDDING_MODEL,
                EMBEDDING_MODEL_VERSION,
                EMBEDDING_DIMENSIONS,
            )
            cursor.fast_executemany = True
            cursor.executemany(
                """INSERT INTO dbo.SourceObjectLedger
                   (SourceObjectId, IngestionRunId, PmcId, ArticleVersion,
                    MetadataObjectKey, MetadataEtag, XmlObjectKey, XmlMd5,
                    LicenseCode, ProcessingStatus, LastAttemptAtUtc)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Accepted', SYSUTCDATETIME());""",
                [
                    (
                        article.source_object_id, str(run_id), article.pmcid, article.version,
                        article.metadata_key, article.metadata_etag, article.xml_key,
                        article.xml_md5, article.license_code,
                    )
                    for article in articles
                ],
            )
            cursor.executemany(
                """INSERT INTO dbo.Article
                   (ArticleId, PmcId, ArticleVersion, Pmid, Doi, ArticleTitle,
                    JournalTitle, ArticleType, LanguageCode, LicenseCode,
                    LicenseClass, LicenseUrl, AttributionParty, IsRetracted,
                    IsCorrection, HasExpressionOfConcern, VersionFamilyId,
                    SourceJsonUrl, SourceXmlUrl, SourceEtag, XmlMd5,
                    InventoryTimestampUtc, SourceRecordSha256)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                [
                    (
                        a.article_id, a.pmcid, a.version, a.pmid, a.doi, a.title,
                        a.journal, a.article_type, a.language, a.license_code,
                        a.license_code, a.license_url, a.is_retracted, a.is_correction,
                        a.has_expression_of_concern, a.version_family_id,
                        a.source_json_url, a.source_xml_url, a.metadata_etag,
                        a.xml_md5, a.inventory_timestamp.replace(tzinfo=None),
                        a.source_record_sha256,
                    )
                    for a in articles
                ],
            )
            cursor.executemany(
                """INSERT INTO dbo.PassageContent
                   (PassageId, ExtractionVersion, TokenCount, ContentSha256, PassageText)
                   VALUES (?, ?, ?, ?, ?);""",
                [
                    (p.passage_id, EXTRACTION_VERSION, max(1, len(p.embedding_input.split())), p.content_sha256, p.text)
                    for p in passages
                ],
            )
            cursor.executemany(
                """INSERT INTO dbo.ArticlePassage
                   (ArticlePassageId, ArticleId, PassageId, SectionPath,
                    PassageOrdinal, SourceXmlMd5, ExtractionVersion, VersionFamilyId)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
                [
                    (
                        p.article_passage_id, p.article_id, p.passage_id,
                        p.section_path, p.ordinal, p.xml_md5,
                        EXTRACTION_VERSION, p.version_family_id,
                    )
                    for p in passages
                ],
            )
            embedding_hashes = [sha256(f"embedding-v1\0{vector_json(vector)}") for vector in vectors]
            per_passage_tokens = max(1, prompt_tokens // len(passages))
            cursor.executemany(
                """INSERT INTO dbo.EmbeddingLedger
                   (PassageId, ContentSha256, EmbeddingModel, EmbeddingModelVersion,
                    EmbeddingDimensions, EmbeddingSha256, GenerationStatus,
                    PromptTokenCount, AttemptCount, GeneratedAtUtc)
                   VALUES (?, ?, ?, ?, ?, ?, 'Succeeded', ?, 1, SYSUTCDATETIME());""",
                [
                    (
                        p.passage_id, p.content_sha256, EMBEDDING_MODEL,
                        EMBEDDING_MODEL_VERSION, EMBEDDING_DIMENSIONS,
                        embedding_hashes[index], per_passage_tokens,
                    )
                    for index, p in enumerate(passages)
                ],
            )
            cursor.executemany(
                """INSERT INTO dbo.PassageVector
                   (PassageId, CanonicalArticlePassageId, Embedding,
                    EmbeddingSha256, EmbeddingModel, EmbeddingModelVersion,
                    ExtractionVersion, PublicationYear, LicenseClass,
                    SafetyState, LanguageCode, DomainCode, ArticleTypeCode)
                   VALUES (?, ?, CAST(? AS VECTOR(384)), ?, ?, ?, ?, NULL, ?, ?, ?, NULL, ?);""",
                [
                    (
                        p.passage_id, p.article_passage_id, vector_json(vectors[index]),
                        embedding_hashes[index], EMBEDDING_MODEL,
                        EMBEDDING_MODEL_VERSION, EXTRACTION_VERSION,
                        p.license_code, p.safety_state, p.language, p.article_type_code,
                    )
                    for index, p in enumerate(passages)
                ],
            )
            cursor.executemany(
                """INSERT INTO dbo.CorpusSelectionManifest
                   (IngestionRunId, PassageId, ArticlePassageId, IsAnchor,
                    IsCanonical, SelectionRank, ContentSha256, EmbeddingSha256,
                    SourceXmlMd5, ExtractionVersion)
                   VALUES (?, ?, ?, 1, 1, ?, ?, ?, ?, ?);""",
                [
                    (
                        str(run_id), p.passage_id, p.article_passage_id, index + 1,
                        p.content_sha256, embedding_hashes[index], p.xml_md5,
                        EXTRACTION_VERSION,
                    )
                    for index, p in enumerate(passages)
                ],
            )
            cursor.execute(
                """UPDATE dbo.IngestionRun
                   SET RunStatus = 'Succeeded', CompletedAtUtc = SYSUTCDATETIME()
                   WHERE IngestionRunId = ?;""",
                str(run_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return run_id


def create_index_and_validate(query_vector: list[float]) -> dict:
    token = database_token()
    with connect(SERVER, DATABASE, token) as connection:
        index_sql = Path(__file__).with_name("02-create-vector-index.sql.template").read_text(encoding="utf-8")
        connection.execute(index_sql)
        query_sql = """
            DECLARE @QueryVectorJson VARCHAR(MAX) = CAST(? AS VARCHAR(MAX));
            DECLARE @QueryVector VECTOR(384) = CAST(@QueryVectorJson AS VECTOR(384));
            SELECT TOP (5) WITH APPROXIMATE
                   article.PmcId,
                   article.ArticleTitle,
                   passage.PassageText,
                   result.distance
            FROM VECTOR_SEARCH(
                TABLE = dbo.PassageVector AS vector_row,
                COLUMN = Embedding,
                SIMILAR_TO = @QueryVector,
                METRIC = 'COSINE'
            ) AS result WITH (FORCE_ANN_ONLY)
            INNER JOIN dbo.ArticlePassage AS occurrence
                ON occurrence.ArticlePassageId = vector_row.CanonicalArticlePassageId
            INNER JOIN dbo.Article AS article
                ON article.ArticleId = occurrence.ArticleId
            INNER JOIN dbo.PassageContent AS passage
                ON passage.PassageId = vector_row.PassageId
            ORDER BY result.distance;
        """
        results = connection.execute(query_sql, vector_json(query_vector)).fetchall()
        counts = connection.execute("""
            SELECT
                (SELECT COUNT_BIG(*) FROM dbo.Article),
                (SELECT COUNT_BIG(*) FROM dbo.PassageContent),
                (SELECT COUNT_BIG(*) FROM dbo.PassageVector),
                (SELECT COUNT_BIG(*) FROM dbo.CorpusSelectionManifest),
                (SELECT JSON_VALUE(build_parameters, '$.Version')
                 FROM sys.vector_indexes
                 WHERE object_id = OBJECT_ID(N'dbo.PassageVector'));
        """).fetchone()
    return {
        "counts": list(counts),
        "results": [
            {"pmcid": row[0], "title": row[1], "passage": row[2], "distance": row[3]}
            for row in results
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path(__file__).parents[1] / "source-discovery" / "inventory-sample.json",
    )
    parser.add_argument("--passage-limit", type=int, default=1000)
    parser.add_argument("--embedding-batch-size", type=int, default=16)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        parser.error("--apply is required")
    if args.passage_limit < 100:
        parser.error("--passage-limit must be at least 100")

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    articles: list[Article] = []
    passages_by_hash: dict[bytes, Passage] = {}
    for entry in inventory["sample"]:
        if len(passages_by_hash) >= args.passage_limit:
            break
        extracted = extract_article(entry, args.passage_limit - len(passages_by_hash))
        if extracted is None:
            continue
        article, candidate_passages = extracted
        accepted = []
        for passage in candidate_passages:
            if passage.content_sha256 not in passages_by_hash:
                passages_by_hash[passage.content_sha256] = passage
                accepted.append(passage)
        if accepted:
            articles.append(article)

    passages = list(passages_by_hash.values())[: args.passage_limit]
    if len(passages) < 100:
        raise RuntimeError(f"Only {len(passages)} unique passages were extracted")

    ai_token = azure_token("https://cognitiveservices.azure.com/")
    vectors: list[list[float]] = []
    prompt_tokens = 0
    embedding_inputs = [passage.embedding_input for passage in passages]
    for batch in chunks(embedding_inputs, args.embedding_batch_size):
        batch_vectors, batch_tokens = embed_batch(batch, ai_token)
        vectors.extend(batch_vectors)
        prompt_tokens += batch_tokens

    run_id = load_database(articles, passages, vectors, prompt_tokens, inventory)
    query_text = "evidence about cardiovascular disease prevention and treatment"
    query_vectors, query_tokens = embed_batch([query_text], ai_token)
    validation = create_index_and_validate(query_vectors[0])
    output = {
        "run_id": str(run_id),
        "server": SERVER,
        "database": DATABASE,
        "articles": len(articles),
        "passages": len(passages),
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "embedding_prompt_tokens": prompt_tokens,
        "query_prompt_tokens": query_tokens,
        "validation": validation,
    }
    output_path = Path(__file__).parents[1] / "small-pilot-result.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
