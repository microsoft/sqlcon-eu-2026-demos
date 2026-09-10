#!/usr/bin/env python3
"""Validate the local Potion catalog, rehearsal fixture, and load package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from generate_potion_query_vectors import (
    DEFAULT_OUTPUT as DEFAULT_CATALOG,
    DIMENSIONS,
    DTYPE,
    MODEL_NAME,
    RUNTIME_NAME,
    RUNTIME_VERSION,
    STAGE_QUERY,
    vector_sha256,
)

ROOT = Path(__file__).parents[1]
DEFAULT_FIXTURE = ROOT / "app" / "src" / "data" / "rehearsal-fixture.json"
DEFAULT_PACKAGE = ROOT / "staging" / "pmc-chunks-potion512-sidecar-v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_contract(value: dict[str, Any], *, distance_key: str) -> None:
    expected = {
        "model": MODEL_NAME,
        "runtime": RUNTIME_NAME,
        "runtimeVersion": RUNTIME_VERSION,
        "dimensions": DIMENSIONS,
        "dtype": DTYPE,
        distance_key: "cosine",
    }
    actual = {key: value.get(key) for key in expected}
    if actual != expected:
        raise ValueError(f"Potion contract mismatch: expected {expected}, received {actual}")


def validate_catalog(path: Path) -> tuple[dict[str, Any], str]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    require_contract(catalog, distance_key="distanceMetric")
    if catalog.get("contractVersion") != 1:
        raise ValueError("Query catalog contractVersion must be 1")
    matches = [entry for entry in catalog.get("queries", []) if entry.get("query") == STAGE_QUERY]
    if len(matches) != 1:
        raise ValueError("Query catalog must contain the stage query exactly once")
    entry = matches[0]
    vector = np.asarray(entry.get("vector"), dtype=np.float32)
    if vector.shape != (DIMENSIONS,) or not np.isfinite(vector).all():
        raise ValueError("Stage query must contain exactly 512 finite float32 components")
    actual_hash = vector_sha256(vector)
    if entry.get("sha256") != actual_hash:
        raise ValueError("Stage-query vector hash does not match its float32 bytes")
    return catalog, actual_hash


def validate_fixture(path: Path, query_hash: str) -> dict[str, Any]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    require_contract(fixture, distance_key="distanceMetric")
    if fixture.get("contractVersion") != 1 or fixture.get("mode") != "offline-rehearsal":
        raise ValueError("Rehearsal fixture identity is invalid")
    if fixture.get("query") != STAGE_QUERY or fixture.get("queryVectorSha256") != query_hash:
        raise ValueError("Rehearsal fixture query does not match the query catalog")
    if fixture.get("source", {}).get("historicalVectorFilesUsed") is not False:
        raise ValueError("Rehearsal fixture must not use historical vector files")
    evidence = fixture.get("evidence", [])
    distances = [float(item["distance"]) for item in evidence]
    if len(evidence) != 5 or distances != sorted(distances):
        raise ValueError("Rehearsal fixture must contain five ascending cosine distances")
    return fixture


def validate_package(path: Path) -> dict[str, Any]:
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "caldova-pmc-potion512-v1":
        raise ValueError("Load package format is invalid")
    require_contract(manifest.get("embedding", {}), distance_key="distanceMetric")
    source_contract = manifest.get("source", {})
    if (
        source_contract.get("historicalVectorFilesUsed") is not False
        or source_contract.get("table") != "dbo.pmc_chunks"
        or source_contract.get("identityColumns") != ["document_id", "chunk_number"]
        or source_contract.get("textColumn") != "text_chunk"
    ):
        raise ValueError("Load package must not use historical vector files")

    source_root = ROOT / source_contract["path"]
    for source_file in source_contract["files"]:
        source_path = source_root / source_file["path"]
        if file_sha256(source_path) != source_file["sha256"]:
            raise ValueError(f"Source checksum mismatch: {source_path}")
    source_rows = {
        (int(row["DocumentId"]), int(row["ChunkNumber"])): row
        for row in (
            json.loads(line)
            for line in (source_root / "PmcChunkSource.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        )
    }

    payload = manifest["payload"]
    payload_path = path / payload["path"]
    if payload_path.stat().st_size != payload["bytes"]:
        raise ValueError("Payload byte count does not match the manifest")
    if file_sha256(payload_path) != payload["sha256"]:
        raise ValueError("Payload checksum does not match the manifest")

    source_keys: set[tuple[int, int]] = set()
    vector_hashes: set[str] = set()
    row_count = 0
    with payload_path.open(encoding="utf-8") as payload_file:
        for line in payload_file:
            row_count += 1
            row = json.loads(line)
            document_id = int(row["DocumentId"])
            source_key = (document_id, int(row["ChunkNumber"]))
            content_hash = str(row["SourceContentSha256"]["$binary_hex"])
            source_row = source_rows.get(source_key)
            if document_id <= 0 or source_key[1] < 0:
                raise ValueError(f"Invalid source identity at payload row {row_count}")
            if not source_row or source_row.get("SourceContentSha256") != content_hash:
                raise ValueError(f"Content hash mismatch at payload row {row_count}")
            vector = np.asarray(row["Embedding"], dtype=np.float32)
            if vector.shape != (DIMENSIONS,) or not np.isfinite(vector).all():
                raise ValueError(f"Invalid vector at payload row {row_count}")
            actual_vector_hash = vector_sha256(vector)
            declared_vector_hash = row["EmbeddingSha256"]["$binary_hex"]
            if actual_vector_hash != declared_vector_hash:
                raise ValueError(f"Vector hash mismatch at payload row {row_count}")
            if source_key in source_keys:
                raise ValueError(f"Duplicate source identity at payload row {row_count}")
            if actual_vector_hash in vector_hashes:
                raise ValueError(f"Duplicate embedding at payload row {row_count}")
            source_keys.add(source_key)
            vector_hashes.add(actual_vector_hash)

    if row_count != payload["rows"] or row_count != 1000:
        raise ValueError(f"Expected exactly 1,000 payload rows, received {row_count}")
    return manifest


def validate(catalog_path: Path, fixture_path: Path, package_path: Path) -> dict[str, Any]:
    _, query_hash = validate_catalog(catalog_path)
    fixture = validate_fixture(fixture_path, query_hash)
    manifest = validate_package(package_path)
    if fixture["source"]["corpusCount"] != manifest["payload"]["rows"]:
        raise ValueError("Fixture and load package corpus counts differ")
    return {
        "valid": True,
        "contract": "caldova-pmc-potion512-v1",
        "runtime": f"{RUNTIME_NAME}=={RUNTIME_VERSION}",
        "queryVectorSha256": query_hash,
        "payloadRows": manifest["payload"]["rows"],
        "payloadBytes": manifest["payload"]["bytes"],
        "payloadSha256": manifest["payload"]["sha256"],
        "rehearsalEvidenceRows": len(fixture["evidence"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    args = parser.parse_args()
    result = validate(args.catalog.resolve(), args.fixture.resolve(), args.package.resolve())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
