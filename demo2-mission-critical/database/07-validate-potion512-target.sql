/* Read-only acceptance query. Run independently on each Caldova target. */

SET NOCOUNT ON;
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;

SELECT contract.SchemaVersion,
       contract.EmbeddingModel,
       contract.EmbeddingRuntime,
       contract.EmbeddingRuntimeVersion,
       contract.EmbeddingDimensions,
       contract.EmbeddingDataType,
       contract.DistanceMetric,
       contract.AppliedAtUtc
FROM dbo.CaldovaVectorContract AS contract
WHERE contract.ContractId = 1;

SELECT COUNT_BIG(*) AS CorpusCount,
       MIN(potion.DocumentId) AS MinimumDocumentId,
       MAX(potion.DocumentId) AS MaximumDocumentId,
       COUNT_BIG(DISTINCT potion.SourceContentSha256) AS DistinctContentHashes,
       COUNT_BIG(DISTINCT potion.EmbeddingSha256) AS DistinctEmbeddingHashes,
       SUM(CASE WHEN chunk.document_id IS NULL THEN 1 ELSE 0 END) AS MissingSourceRows,
       SUM
       (
           CASE
               WHEN chunk.document_id IS NOT NULL
                AND HASHBYTES('SHA2_256', CONVERT(VARBINARY(MAX), chunk.text_chunk))
                    <> potion.SourceContentSha256
                   THEN 1
               ELSE 0
           END
       ) AS SourceContentHashMismatches
FROM dbo.CaldovaPotionEmbedding AS potion
LEFT JOIN dbo.pmc_chunks AS chunk
    ON chunk.document_id = potion.DocumentId
   AND chunk.chunk_number = potion.ChunkNumber;

SELECT index_definition.name AS IndexName,
       vector_index.distance_metric AS DistanceMetric,
       JSON_VALUE(vector_index.build_parameters, '$.Version') AS IndexVersion,
       index_definition.is_disabled AS IsDisabled,
       index_definition.is_hypothetical AS IsHypothetical
FROM sys.vector_indexes AS vector_index
INNER JOIN sys.indexes AS index_definition
    ON index_definition.object_id = vector_index.object_id
   AND index_definition.index_id = vector_index.index_id
WHERE vector_index.object_id = OBJECT_ID(N'dbo.CaldovaPotionEmbedding');

DECLARE @QueryVector VECTOR(512) = CAST(@QueryVectorJson AS VECTOR(512));

SELECT TOP (5) WITH APPROXIMATE
       CONCAT('PMC', document.pmcid) AS PmcId,
       potion.ChunkNumber,
       COALESCE(document.title, CONCAT('PMC', document.pmcid)) AS ArticleTitle,
       chunk.text_chunk AS PassageText,
       vector_result.distance AS Distance
FROM VECTOR_SEARCH
(
    TABLE = dbo.CaldovaPotionEmbedding AS potion,
    COLUMN = Embedding,
    SIMILAR_TO = @QueryVector,
    METRIC = 'COSINE'
) AS vector_result
WITH (FORCE_ANN_ONLY)
INNER JOIN dbo.pmc_chunks AS chunk
    ON chunk.document_id = potion.DocumentId
   AND chunk.chunk_number = potion.ChunkNumber
INNER JOIN dbo.pmc_documents AS document
    ON document.document_id = potion.DocumentId
WHERE HASHBYTES('SHA2_256', CONVERT(VARBINARY(MAX), chunk.text_chunk))
    = potion.SourceContentSha256
ORDER BY vector_result.distance;
