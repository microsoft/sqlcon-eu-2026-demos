#!/usr/bin/env python3
"""Generate the shared Potion query-vector catalog used by the demo API."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np

MODEL_NAME = "minishlab/potion-retrieval-32M"
RUNTIME_NAME = "model2vec"
RUNTIME_VERSION = "0.9.0"
DIMENSIONS = 512
DTYPE = "float32"
STAGE_QUERY = "prognostic and therapeutic biomarkers in type 2 papillary renal cell carcinoma"
DEFAULT_OUTPUT = Path(__file__).parents[1] / "app" / "server" / "data" / "query-vectors.json"


def encode_queries(queries: Sequence[str], model_name: str) -> np.ndarray:
    from model2vec import StaticModel

    installed_version = importlib.metadata.version(RUNTIME_NAME)
    if installed_version != RUNTIME_VERSION:
        raise RuntimeError(
            f"The embedding contract requires {RUNTIME_NAME}=={RUNTIME_VERSION}; "
            f"found {installed_version}"
        )
    model = StaticModel.from_pretrained(model_name)
    embeddings = np.asarray(model.encode(list(queries)), dtype=np.float32)
    expected_shape = (len(queries), DIMENSIONS)
    if embeddings.shape != expected_shape:
        raise ValueError(
            f"Expected embedding shape {expected_shape}, received {embeddings.shape}"
        )
    if not np.isfinite(embeddings).all():
        raise ValueError("The embedding model returned a non-finite component")
    return embeddings


def vector_sha256(vector: np.ndarray) -> str:
    return hashlib.sha256(vector.astype("<f4", copy=False).tobytes()).hexdigest()


def write_catalog(output_path: Path, queries: Sequence[str], embeddings: np.ndarray) -> None:
    catalog = {
        "contractVersion": 1,
        "model": MODEL_NAME,
        "runtime": RUNTIME_NAME,
        "runtimeVersion": RUNTIME_VERSION,
        "dimensions": DIMENSIONS,
        "dtype": DTYPE,
        "distanceMetric": "cosine",
        "generatedAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "queries": [
            {
                "query": query,
                "sha256": vector_sha256(vector),
                "vector": [float(component) for component in vector],
            }
            for query, vector in zip(queries, embeddings, strict=True)
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        json.dump(catalog, temporary_file, ensure_ascii=True, separators=(",", ":"))
        temporary_file.write("\n")
        temporary_path = Path(temporary_file.name)
    os.replace(temporary_path, output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", dest="queries")
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    queries = tuple(query.strip() for query in (args.queries or [STAGE_QUERY]))
    if not queries or any(not query or len(query) > 500 for query in queries):
        parser.error("each query must contain between 1 and 500 characters")
    if len(queries) != len(set(queries)):
        parser.error("queries must be unique")
    if args.model != MODEL_NAME:
        parser.error(f"the demo contract requires {MODEL_NAME}")

    embeddings = encode_queries(queries, args.model)
    write_catalog(args.output.resolve(), queries, embeddings)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "model": MODEL_NAME,
                "dimensions": DIMENSIONS,
                "queries": len(queries),
                "sha256": [vector_sha256(vector) for vector in embeddings],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())