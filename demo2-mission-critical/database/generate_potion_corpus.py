#!/usr/bin/env python3
"""Generate the deterministic Potion sidecar package from a pmc_chunks snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from generate_potion_query_vectors import (
    DIMENSIONS,
    DTYPE,
    MODEL_NAME,
    RUNTIME_NAME,
    RUNTIME_VERSION,
    encode_queries,
    vector_sha256,
)
from generate_potion_rehearsal_fixture import load_passages

ROOT = Path(__file__).parents[1]
DEFAULT_SOURCE = ROOT / "staging" / "pmc-chunks-potion512-source-v1"
DEFAULT_OUTPUT = ROOT / "staging" / "pmc-chunks-potion512-sidecar-v1"
SOURCE_FILES = ("manifest.json", "PmcChunkSource.jsonl")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def output_rows(source: Path) -> Iterable[dict[str, Any]]:
    passages = load_passages(source)
    vectors = encode_queries([passage["passage"] for passage in passages], MODEL_NAME)
    if vectors.shape != (len(passages), DIMENSIONS):
        raise ValueError(f"Unexpected corpus-vector shape: {vectors.shape}")
    if np.any(np.linalg.norm(vectors, axis=1) == 0):
        raise ValueError("Potion generated a zero-length corpus embedding")

    vector_hashes: set[str] = set()
    for passage, vector in zip(passages, vectors, strict=True):
        vector_hash = vector_sha256(vector)
        if vector_hash in vector_hashes:
            raise ValueError(f"Duplicate Potion vector hash: {vector_hash}")
        vector_hashes.add(vector_hash)
        yield {
            "DocumentId": str(passage["sourceDocumentId"]),
            "ChunkNumber": passage["chunkNumber"],
            "SourceContentSha256": {"$binary_hex": passage["sourceContentSha256"]},
            "Embedding": [float(component) for component in vector],
            "EmbeddingSha256": {"$binary_hex": vector_hash},
        }


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    row_count = 0
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        for row in rows:
            temporary_file.write(json.dumps(row, ensure_ascii=True, separators=(",", ":")))
            temporary_file.write("\n")
            row_count += 1
        temporary_path = Path(temporary_file.name)
    os.replace(temporary_path, path)
    return row_count


def write_json(path: Path, value: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        json.dump(value, temporary_file, ensure_ascii=True, indent=2)
        temporary_file.write("\n")
        temporary_path = Path(temporary_file.name)
    os.replace(temporary_path, path)


def generate(source: Path, output: Path) -> dict[str, Any]:
    try:
        source_relative_path = source.relative_to(ROOT).as_posix()
    except ValueError as error:
        raise ValueError("The source snapshot must be inside the project root") from error
    output.mkdir(parents=True, exist_ok=True)
    payload_path = output / "CaldovaPotionEmbedding.jsonl"
    row_count = write_jsonl(payload_path, output_rows(source))
    if row_count != 1000:
        raise ValueError(f"The Potion anchor must contain exactly 1,000 rows; received {row_count}")

    manifest = {
        "format": "caldova-pmc-potion512-v1",
        "embedding": {
            "model": MODEL_NAME,
            "runtime": RUNTIME_NAME,
            "runtimeVersion": RUNTIME_VERSION,
            "dimensions": DIMENSIONS,
            "dtype": DTYPE,
            "distanceMetric": "cosine",
            "vectorHashEncoding": "little-endian-float32",
        },
        "source": {
            "path": source_relative_path,
            "table": "dbo.pmc_chunks",
            "identityColumns": ["document_id", "chunk_number"],
            "textColumn": "text_chunk",
            "historicalVectorFilesUsed": False,
            "files": [
                {
                    "path": name,
                    "sha256": file_sha256(source / name),
                }
                for name in SOURCE_FILES
            ],
        },
        "payload": {
            "path": payload_path.name,
            "rows": row_count,
            "bytes": payload_path.stat().st_size,
            "sha256": file_sha256(payload_path),
        },
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    manifest = generate(args.source.resolve(), args.output.resolve())
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
