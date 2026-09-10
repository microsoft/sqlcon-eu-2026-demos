#!/usr/bin/env python3
"""Generate a Potion-backed rehearsal fixture from a dbo.pmc_chunks snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from model2vec import StaticModel

from generate_potion_query_vectors import (
    DIMENSIONS,
    DTYPE,
    MODEL_NAME,
    RUNTIME_NAME,
    RUNTIME_VERSION,
    STAGE_QUERY,
    vector_sha256,
)

ROOT = Path(__file__).parents[1]
DEFAULT_SOURCE = ROOT / "staging" / "pmc-chunks-potion512-source-v1"
DEFAULT_OUTPUT = ROOT / "app" / "src" / "data" / "rehearsal-fixture.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def corpus_sha256(passages: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for passage in passages:
        digest.update(str(passage["sourceDocumentId"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(passage["chunkNumber"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(passage["sourceContentSha256"].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def load_passages(source: Path) -> list[dict[str, Any]]:
    source_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if source_manifest.get("format") != "caldova-pmc-chunk-source-v1":
        raise ValueError("The source snapshot manifest is invalid")
    payload = source_manifest.get("payload", {})
    source_path = source / str(payload.get("path", ""))
    if not source_path.is_file() or source_path.stat().st_size != payload.get("bytes"):
        raise ValueError("The source snapshot payload is missing or has the wrong size")
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != payload.get("sha256"):
        raise ValueError("The source snapshot payload hash is invalid")

    passages = []
    source_keys: set[tuple[int, int]] = set()
    for row in read_jsonl(source_path):
        document_id = int(row["DocumentId"])
        chunk_number = int(row["ChunkNumber"])
        source_key = (document_id, chunk_number)
        title = str(row["ArticleTitle"])
        passage = str(row["PassageText"])
        source_content_hash = str(row["SourceContentSha256"])
        if source_key in source_keys:
            raise ValueError(f"Duplicate source key: {document_id}/{chunk_number}")
        if (
            document_id <= 0
            or chunk_number < 0
            or not title
            or not passage
            or hashlib.sha256(passage.encode("utf-16-le")).hexdigest() != source_content_hash
        ):
            raise ValueError(f"Invalid source row: {document_id}/{chunk_number}")
        source_keys.add(source_key)
        passages.append(
            {
                "sourceDocumentId": document_id,
                "documentId": str(row["PmcId"]),
                "chunkNumber": chunk_number,
                "title": title,
                "passage": passage,
                "sourceContentSha256": source_content_hash,
            }
        )
    if len(passages) != payload.get("rows"):
        raise ValueError("The source snapshot row count is invalid")
    return passages


def generate(source: Path, query: str) -> dict[str, Any]:
    passages = load_passages(source)
    if not passages:
        raise ValueError("The staged source contains no passages")

    model = StaticModel.from_pretrained(MODEL_NAME)
    passage_vectors = np.asarray(
        model.encode([passage["passage"] for passage in passages]),
        dtype=np.float32,
    )
    query_vector = np.asarray(model.encode([query])[0], dtype=np.float32)
    if passage_vectors.shape != (len(passages), DIMENSIONS):
        raise ValueError(f"Unexpected passage-vector shape: {passage_vectors.shape}")
    if query_vector.shape != (DIMENSIONS,):
        raise ValueError(f"Unexpected query-vector shape: {query_vector.shape}")

    passage_norms = np.linalg.norm(passage_vectors, axis=1)
    query_norm = np.linalg.norm(query_vector)
    if query_norm == 0 or np.any(passage_norms == 0):
        raise ValueError("Potion generated a zero-length embedding")
    distances = 1.0 - (passage_vectors @ query_vector) / (passage_norms * query_norm)
    top_indices = np.argsort(distances)[:5]

    return {
        "contractVersion": 1,
        "mode": "offline-rehearsal",
        "model": MODEL_NAME,
        "runtime": RUNTIME_NAME,
        "runtimeVersion": RUNTIME_VERSION,
        "dimensions": DIMENSIONS,
        "dtype": DTYPE,
        "distanceMetric": "cosine",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "path": "staging/pmc-chunks-potion512-source-v1",
            "table": "dbo.pmc_chunks",
            "identityColumns": ["document_id", "chunk_number"],
            "textColumn": "text_chunk",
            "textFiles": ["PmcChunkSource.jsonl"],
            "historicalVectorFilesUsed": False,
            "corpusCount": len(passages),
            "corpusSha256": corpus_sha256(passages),
        },
        "query": query,
        "queryVectorSha256": vector_sha256(query_vector),
        "evidence": [
            {
                "documentId": passages[index]["documentId"],
                "chunkNumber": passages[index]["chunkNumber"],
                "title": passages[index]["title"],
                "passage": passages[index]["passage"],
                "distance": float(distances[index]),
            }
            for index in top_indices
        ],
    }


def write_fixture(output: Path, fixture: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        json.dump(fixture, temporary_file, ensure_ascii=True, indent=2)
        temporary_file.write("\n")
        temporary_path = Path(temporary_file.name)
    os.replace(temporary_path, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--query", default=STAGE_QUERY)
    args = parser.parse_args()
    if not args.query.strip() or len(args.query) > 500:
        parser.error("--query must contain between 1 and 500 characters")

    fixture = generate(args.source.resolve(), args.query.strip())
    write_fixture(args.output.resolve(), fixture)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "model": fixture["model"],
                "corpusCount": fixture["source"]["corpusCount"],
                "queryVectorSha256": fixture["queryVectorSha256"],
                "topDocumentIds": [row["documentId"] for row in fixture["evidence"]],
                "distances": [row["distance"] for row in fixture["evidence"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())