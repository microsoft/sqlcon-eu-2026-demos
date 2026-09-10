/*
    Caldova retrieval.

    One statement covers all three modes. @UseVector and @UseKeyword select which
    retrievers contribute; when both are on, their ranks are fused with reciprocal
    rank fusion, which is the hybrid mode.

    Results are collapsed to the best passage per document so five results mean five
    articles, and each result carries the surrounding chunks for context.
*/

DECLARE @QueryVector VECTOR(512) = CAST(@QueryVectorJson AS VECTOR(512));

WITH VectorRaw AS
(
    -- APPROXIMATE cannot appear alongside a window function, so ranking happens one level up.
    SELECT TOP (@Candidates) WITH APPROXIMATE
           chunk.document_id,
           chunk.chunk_number,
           vector_result.distance AS Distance
    FROM VECTOR_SEARCH
    (
        TABLE = dbo.pmc_chunks AS chunk,
        COLUMN = embedding,
        SIMILAR_TO = @QueryVector,
        METRIC = 'COSINE'
    ) AS vector_result
    WHERE @UseVector = 1
      AND chunk.is_boilerplate = 0
    ORDER BY vector_result.distance
),
VectorCandidates AS
(
    SELECT document_id,
           chunk_number,
           Distance,
           ROW_NUMBER() OVER (ORDER BY Distance) AS Position
    FROM VectorRaw
),
KeywordCandidates AS
(
    SELECT TOP (@Candidates)
           chunk.document_id,
           chunk.chunk_number,
           ROW_NUMBER() OVER (ORDER BY ranked.[RANK] DESC) AS Position
    FROM FREETEXTTABLE(dbo.pmc_chunks, text_chunk, @QueryText, @Candidates) AS ranked
    INNER JOIN dbo.pmc_chunks AS chunk
        ON chunk.chunk_id = ranked.[KEY]
    WHERE @UseKeyword = 1
      AND chunk.is_boilerplate = 0
    ORDER BY ranked.[RANK] DESC
),
Fused AS
(
    SELECT candidate.document_id,
           candidate.chunk_number,
           SUM(1.0 / (60.0 + candidate.Position)) AS Score,
           MIN(candidate.Distance) AS Distance
    FROM
    (
        SELECT document_id, chunk_number, Position, Distance FROM VectorCandidates
        UNION ALL
        SELECT document_id, chunk_number, Position, NULL FROM KeywordCandidates
    ) AS candidate
    GROUP BY candidate.document_id, candidate.chunk_number
),
BestPerDocument AS
(
    SELECT document_id,
           chunk_number,
           Score,
           Distance,
           ROW_NUMBER() OVER (PARTITION BY document_id ORDER BY Score DESC, chunk_number) AS DocumentRank
    FROM Fused
)
SELECT TOP (@Top)
       CONCAT('PMC', document.pmcid) AS PmcId,
       document.title AS Title,
       best.chunk_number AS ChunkNumber,
       best.Distance AS Distance,
       best.Score AS Score,
       previous_chunk.text_chunk AS PreviousPassage,
       chunk.text_chunk AS Passage,
       next_chunk.text_chunk AS NextPassage
FROM BestPerDocument AS best
INNER JOIN dbo.pmc_chunks AS chunk
    ON chunk.document_id = best.document_id
   AND chunk.chunk_number = best.chunk_number
INNER JOIN dbo.pmc_documents AS document
    ON document.document_id = best.document_id
LEFT JOIN dbo.pmc_chunks AS previous_chunk
    ON previous_chunk.document_id = best.document_id
   AND previous_chunk.chunk_number = best.chunk_number - 1
LEFT JOIN dbo.pmc_chunks AS next_chunk
    ON next_chunk.document_id = best.document_id
   AND next_chunk.chunk_number = best.chunk_number + 1
WHERE best.DocumentRank = 1
ORDER BY best.Score DESC;
