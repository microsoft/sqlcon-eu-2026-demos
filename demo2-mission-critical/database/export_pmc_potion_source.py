#!/usr/bin/env python3
"""Export a deterministic, read-only Potion source snapshot from dbo.pmc_chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from deploy_common_schema import connect, database_token

ROOT = Path(__file__).parents[1]
DEFAULT_OUTPUT = ROOT / "staging" / "pmc-chunks-potion512-source-v1"
DEFAULT_SERVER = "vbnech-large-server.database.windows.net"
DEFAULT_DATABASE = "vbench_large"
DEFAULT_ROWS = 1000
DEFAULT_STAGE_PMCID = 10022194
QUERY_TIMEOUT_SECONDS = 60

SOURCE_QUERY = """
WITH StageDocument AS
(
    SELECT document.document_id
    FROM dbo.pmc_documents AS document
    WHERE document.pmcid = ?
),
StageRows AS
(
    SELECT 0 AS SelectionGroup,
           chunk.document_id,
           document.pmcid,
           chunk.chunk_number,
           document.title,
           chunk.text_chunk
    FROM dbo.pmc_chunks AS chunk
    INNER JOIN dbo.pmc_documents AS document
        ON document.document_id = chunk.document_id
    INNER JOIN StageDocument AS stage
        ON stage.document_id = chunk.document_id
    WHERE chunk.text_chunk IS NOT NULL
      AND DATALENGTH(chunk.text_chunk) > 0
),
FillerRows AS
(
    SELECT TOP (?)
           1 AS SelectionGroup,
           chunk.document_id,
           document.pmcid,
           chunk.chunk_number,
           document.title,
           chunk.text_chunk
    FROM dbo.pmc_chunks AS chunk
    INNER JOIN dbo.pmc_documents AS document
        ON document.document_id = chunk.document_id
    WHERE NOT EXISTS
    (
        SELECT 1
        FROM StageDocument AS stage
        WHERE stage.document_id = chunk.document_id
    )
      AND chunk.text_chunk IS NOT NULL
      AND DATALENGTH(chunk.text_chunk) > 0
    ORDER BY chunk.document_id, chunk.chunk_number
),
SelectedRows AS
(
    SELECT stage.SelectionGroup,
           stage.document_id,
           stage.pmcid,
           stage.chunk_number,
           stage.title,
           stage.text_chunk
    FROM StageRows AS stage

    UNION ALL

    SELECT filler.SelectionGroup,
           filler.document_id,
           filler.pmcid,
           filler.chunk_number,
           filler.title,
           filler.text_chunk
    FROM FillerRows AS filler
)
SELECT TOP (?)
       selected.document_id,
       selected.pmcid,
       selected.chunk_number,
       selected.title,
       selected.text_chunk
FROM SelectedRows AS selected
ORDER BY selected.SelectionGroup,
         selected.document_id,
         selected.chunk_number;
"""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_immutable(path: Path, value: bytes) -> None:
    if path.exists():
        if path.read_bytes() == value:
            return
        raise FileExistsError(f"Refusing to replace existing source snapshot: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as output:
        output.write(value)
        temporary_path = Path(output.name)
    os.replace(temporary_path, path)


def export(args: argparse.Namespace) -> dict[str, Any]:
    with connect(args.server, args.database, database_token()) as connection:
        connection.timeout = args.timeout
        rows = connection.cursor().execute(
            SOURCE_QUERY,
            args.stage_pmcid,
            args.rows,
            args.rows,
        ).fetchall()

    if len(rows) != args.rows:
        raise ValueError(f"Expected {args.rows} source rows; received {len(rows)}")

    source_keys: set[tuple[int, int]] = set()
    stage_rows = 0
    payload_lines: list[bytes] = []
    for row in rows:
        document_id = int(row.document_id)
        chunk_number = int(row.chunk_number)
        pmcid = int(row.pmcid)
        text = str(row.text_chunk)
        source_key = (document_id, chunk_number)
        if source_key in source_keys:
            raise ValueError(f"Duplicate source key: {document_id}/{chunk_number}")
        if not text:
            raise ValueError(f"Empty source text: {document_id}/{chunk_number}")
        source_keys.add(source_key)
        if pmcid == args.stage_pmcid:
            stage_rows += 1

        payload = {
            "DocumentId": document_id,
            "PmcId": f"PMC{pmcid}",
            "ChunkNumber": chunk_number,
            "ArticleTitle": str(row.title) if row.title else f"PMC{pmcid}",
            "PassageText": text,
            "SourceContentSha256": sha256_bytes(text.encode("utf-16-le")),
        }
        payload_lines.append(
            json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8") + b"\n"
        )

    if stage_rows == 0:
        raise ValueError(f"Stage article PMC{args.stage_pmcid} returned no source chunks")

    payload_bytes = b"".join(payload_lines)
    manifest = {
        "format": "caldova-pmc-chunk-source-v1",
        "source": {
            "server": args.server,
            "database": args.database,
            "chunkTable": "dbo.pmc_chunks",
            "documentTable": "dbo.pmc_documents",
            "stagePmcId": f"PMC{args.stage_pmcid}",
            "selection": "all-stage-article-chunks-then-lowest-source-keys",
        },
        "payload": {
            "path": "PmcChunkSource.jsonl",
            "rows": len(rows),
            "stageArticleRows": stage_rows,
            "bytes": len(payload_bytes),
            "sha256": sha256_bytes(payload_bytes),
        },
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
    write_immutable(args.output / "PmcChunkSource.jsonl", payload_bytes)
    write_immutable(args.output / "manifest.json", manifest_bytes)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--stage-pmcid", type=int, default=DEFAULT_STAGE_PMCID)
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=int, default=QUERY_TIMEOUT_SECONDS)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.rows < 1000 or args.rows > 100_000:
        parser.error("--rows must be between 1,000 and 100,000")
    if args.stage_pmcid < 1:
        parser.error("--stage-pmcid must be positive")
    if args.timeout < 1 or args.timeout > 300:
        parser.error("--timeout must be between 1 and 300 seconds")

    print(json.dumps(export(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())