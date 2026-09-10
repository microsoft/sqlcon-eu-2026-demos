#!/usr/bin/env python3
"""Generate the historical 384-dimensional query pack; not used by the Potion lane."""

from __future__ import annotations

import argparse
import hashlib
import json

from deploy_common_schema import connect, database_token
from load_small_pilot import azure_token, embed_batch, vector_json

DEFAULT_SERVER = "antho-test-server-uksouth.database.windows.net"
DATABASE = "caldovadb"

QUERIES = (
    (
        1,
        "Nose-to-brain dexamethasone delivery",
        "How can dry powder formulations deliver dexamethasone through the nose to the brain?",
    ),
    (
        2,
        "Stroke hemorrhagic transformation prediction",
        "Predicting hemorrhagic transformation after intravenous thrombolysis in patients with stroke",
    ),
    (
        3,
        "Colorectal cancer methylation screening",
        "Methylated WIF-1 gene testing for colorectal cancer screening compared with fecal occult blood testing",
    ),
    (
        4,
        "Omicron pneumonia severity",
        "Clinical factors that predict pneumonia severity and outcomes in patients with the Omicron variant",
    ),
    (
        5,
        "Childhood stunting risk factors",
        "Household, maternal, and community risk factors for stunting among children under five in Pakistan",
    ),
    (
        6,
        "Infrared thermography in medicine",
        "Uses of infrared thermography for medical diagnosis, disease screening, and patient monitoring",
    ),
    (
        7,
        "Periodontitis and hypertension",
        "Association between periodontitis severity and hypertension risk",
    ),
    (
        8,
        "Hepatitis C in hemodialysis",
        "Prevalence and risk factors for hepatitis C infection among hemodialysis patients",
    ),
)


def query_hash(query_text: str, vector: list[float]) -> bytes:
    canonical = "\0".join(
        (
            "demo-query-v1",
            "text-embedding-3-small",
            "1",
            "384",
            query_text,
            vector_json(vector),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default=DEFAULT_SERVER)
    args = parser.parse_args()
    token = azure_token("https://cognitiveservices.azure.com/")
    texts = [query[2] for query in QUERIES]
    vectors, prompt_tokens = embed_batch(texts, token)

    with connect(args.server, DATABASE, database_token()) as connection:
        connection.autocommit = False
        try:
            for (query_id, query_name, query_text), vector in zip(QUERIES, vectors):
                vector_text = vector_json(vector)
                vector_digest = query_hash(query_text, vector)
                connection.execute(
                    """
                    IF EXISTS (SELECT 1 FROM dbo.DemoQuery WHERE DemoQueryId = ?)
                    BEGIN
                        UPDATE dbo.DemoQuery
                        SET QueryName = ?,
                            QueryText = ?,
                            QueryVector = CAST(CAST(? AS VARCHAR(MAX)) AS VECTOR(384)),
                            QueryVectorSha256 = ?,
                            EmbeddingModel = 'text-embedding-3-small',
                            EmbeddingModelVersion = '1',
                            IsActive = 1
                        WHERE DemoQueryId = ?;
                    END
                    ELSE
                    BEGIN
                        INSERT INTO dbo.DemoQuery
                        (
                            DemoQueryId, QueryName, QueryText, QueryVector,
                            QueryVectorSha256, EmbeddingModel,
                            EmbeddingModelVersion, IsActive
                        )
                        VALUES
                        (
                            ?, ?, ?, CAST(CAST(? AS VARCHAR(MAX)) AS VECTOR(384)),
                            ?, 'text-embedding-3-small', '1', 1
                        );
                    END;
                    """,
                    query_id,
                    query_name,
                    query_text,
                    vector_text,
                    vector_digest,
                    query_id,
                    query_id,
                    query_name,
                    query_text,
                    vector_text,
                    vector_digest,
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        validation = []
        for query_id, query_name, _ in QUERIES:
            row = connection.execute(
                """
                DECLARE @QueryVector VECTOR(384);
                SELECT @QueryVector = QueryVector
                FROM dbo.DemoQuery
                WHERE DemoQueryId = ?;

                SELECT TOP (1) WITH APPROXIMATE
                       article.PmcId,
                       article.ArticleTitle,
                       result.distance
                FROM VECTOR_SEARCH
                (
                    TABLE = dbo.PassageVector AS vector_row,
                    COLUMN = Embedding,
                    SIMILAR_TO = @QueryVector,
                    METRIC = 'COSINE'
                ) AS result WITH (FORCE_ANN_ONLY)
                INNER JOIN dbo.ArticlePassage AS occurrence
                    ON occurrence.ArticlePassageId = vector_row.CanonicalArticlePassageId
                INNER JOIN dbo.Article AS article
                    ON article.ArticleId = occurrence.ArticleId
                ORDER BY result.distance;
                """,
                query_id,
            ).fetchone()
            validation.append(
                {
                    "query_id": query_id,
                    "query_name": query_name,
                    "top_pmcid": row[0],
                    "top_title": row[1],
                    "distance": row[2],
                }
            )

    print(json.dumps({"prompt_tokens": prompt_tokens, "queries": validation}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
