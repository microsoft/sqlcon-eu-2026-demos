SET NOCOUNT ON;

SELECT HASHBYTES
(
    'SHA2_256',
    STRING_AGG
    (
        CONVERT
        (
            NVARCHAR(MAX),
            CONCAT
            (
                schema_definition.name, N'.', table_definition.name, N'|',
                column_definition.column_id, N'|', column_definition.name, N'|',
                type_definition.name, N'|', column_definition.max_length, N'|',
                column_definition.precision, N'|', column_definition.scale, N'|',
                column_definition.is_nullable, N'|', column_definition.is_identity
            )
        ),
        NCHAR(10)
    ) WITHIN GROUP
    (
        ORDER BY schema_definition.name, table_definition.name, column_definition.column_id
    )
) AS ColumnFingerprint
FROM sys.tables AS table_definition
INNER JOIN sys.schemas AS schema_definition
    ON schema_definition.schema_id = table_definition.schema_id
INNER JOIN sys.columns AS column_definition
    ON column_definition.object_id = table_definition.object_id
INNER JOIN sys.types AS type_definition
    ON type_definition.user_type_id = column_definition.user_type_id
WHERE schema_definition.name = N'dbo'
  AND table_definition.name IN
  (
      N'SchemaVersion',
      N'IngestionRun',
      N'LoadBatch',
      N'SourceObjectLedger',
      N'Article',
      N'PassageContent',
      N'ArticlePassage',
      N'EmbeddingLedger',
      N'PassageVector',
      N'CorpusSelectionManifest',
      N'DemoQuery',
      N'DemoMeasurement'
  );
