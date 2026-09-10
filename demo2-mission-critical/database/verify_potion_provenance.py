#!/usr/bin/env python3
"""Verify that one Azure SQL document contains Potion float32 embeddings."""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
from model2vec import StaticModel

from deploy_common_schema import connect, database_token
from generate_potion_query_vectors import (
    DEFAULT_OUTPUT,
    DIMENSIONS,
    MODEL_NAME,
    STAGE_QUERY,
    vector_sha256,
)

DEFAULT_SERVER = "vbnech-large-server.database.windows.net"
DEFAULT_DATABASE = "vbench_large"
DEFAULT_DOCUMENT_ID = 1
QUERY_TIMEOUT_SECONDS = 20

DOCUMENT_QUERY = """
SELECT document_id,
       chunk_number,
       text_chunk,
       CAST(embedding AS NVARCHAR(MAX)) AS embedding_json
FROM dbo.pmc_chunks
WHERE document_id = ?
ORDER BY chunk_number;
"""


def parse_vector(value: str) -> np.ndarray:
    vector = np.asarray(json.loads(value), dtype=np.float32)
    if vector.shape != (DIMENSIONS,):
        raise ValueError(f"Expected {DIMENSIONS} components, received {vector.shape}")
    if not np.isfinite(vector).all():
        raise ValueError("Stored embedding contains a non-finite component")
    return vector


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    numerator = np.sum(left * right, axis=1)
    denominator = np.linalg.norm(left, axis=1) * np.linalg.norm(right, axis=1)
    if np.any(denominator == 0):
        raise ValueError("Cannot compare a zero-length embedding")
    return numerator / denominator


def load_catalog_hash(catalog_path: Path, query: str) -> str:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("model") != MODEL_NAME or catalog.get("dimensions") != DIMENSIONS:
        raise ValueError("Query-vector catalog does not match the Potion contract")
    matches = [entry for entry in catalog.get("queries", []) if entry.get("query") == query]
    if len(matches) != 1:
        raise ValueError(f"Expected one catalog entry for the stage query, found {len(matches)}")
    return str(matches[0]["sha256"])


def verify(args: argparse.Namespace) -> dict[str, Any]:
    with connect(args.server, args.database, database_token()) as connection:
        connection.timeout = args.timeout
        cursor = connection.cursor()
        rows = cursor.execute(DOCUMENT_QUERY, args.document_id).fetchall()

    if not rows:
        raise ValueError(f"Document {args.document_id} returned no chunks")

    stored = np.stack([parse_vector(str(row.embedding_json)) for row in rows])
    texts = [str(row.text_chunk) for row in rows]
    model = StaticModel.from_pretrained(MODEL_NAME)
    fresh = np.asarray(model.encode(texts), dtype=np.float32)
    if fresh.shape != stored.shape:
        raise ValueError(f"Fresh shape {fresh.shape} does not match stored shape {stored.shape}")

    component_differences = np.abs(stored - fresh)
    row_max_differences = np.max(component_differences, axis=1)
    similarities = cosine_similarity(stored, fresh)
    exact_matches = np.all(stored == fresh, axis=1)

    query_vector = np.asarray(model.encode([args.query])[0], dtype=np.float32)
    query_hash = vector_sha256(query_vector)
    catalog_hash = load_catalog_hash(args.catalog, args.query)
    query_matrix = np.repeat(query_vector[np.newaxis, :], fresh.shape[0], axis=0)
    distances = 1.0 - cosine_similarity(fresh, query_matrix)
    top_indices = np.argsort(distances)[:5]

    all_rows_match = bool(np.all(exact_matches))
    query_matches_catalog = query_hash == catalog_hash
    return {
        "contract": {
            "model": MODEL_NAME,
            "model2vecVersion": version("model2vec"),
            "dimensions": DIMENSIONS,
            "dtype": "float32",
        },
        "sample": {
            "server": args.server,
            "database": args.database,
            "documentId": args.document_id,
            "chunkCount": len(rows),
        },
        "comparison": {
            "allRowsExactFloat32Match": all_rows_match,
            "exactMatchCount": int(np.sum(exact_matches)),
            "globalMaxAbsoluteDifference": float(np.max(component_differences)),
            "meanRowMaxAbsoluteDifference": float(np.mean(row_max_differences)),
            "cosineSimilarityMinimum": float(np.min(similarities)),
            "cosineSimilarityMaximum": float(np.max(similarities)),
        },
        "stageQuery": {
            "text": args.query,
            "generatedSha256": query_hash,
            "catalogSha256": catalog_hash,
            "matchesCatalog": query_matches_catalog,
            "topFiveSampleChunks": [
                {
                    "chunkNumber": int(rows[index].chunk_number),
                    "cosineDistance": float(distances[index]),
                    "excerpt": texts[index][:240],
                }
                for index in top_indices
            ],
        },
        "provenanceVerified": all_rows_match and query_matches_catalog,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--document-id", type=int, default=DEFAULT_DOCUMENT_ID)
    parser.add_argument("--query", default=STAGE_QUERY)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=int, default=QUERY_TIMEOUT_SECONDS)
    args = parser.parse_args()
    if args.timeout < 1 or args.timeout > 120:
        parser.error("--timeout must be between 1 and 120 seconds")

    result = verify(args)
    print(json.dumps(result, indent=2))
    return 0 if result["provenanceVerified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())