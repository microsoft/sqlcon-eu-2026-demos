/* ============================================================================
   Caldova Regional Care Transfer Center
   02a-native-json-upgrade.sql : upgrade persisted AI documents to native JSON
   ============================================================================ */

USE [CaldovaRegionalCare];
GO

SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;

IF EXISTS
(
        SELECT 1
        FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'ai.Skill')
            AND c.name = N'SkillJson'
            AND t.name = N'nvarchar'
)
BEGIN
    IF OBJECT_ID(N'ai.CK_Skill_Json', N'C') IS NOT NULL
        ALTER TABLE ai.Skill DROP CONSTRAINT CK_Skill_Json;

    ALTER TABLE ai.Skill ALTER COLUMN SkillJson json NOT NULL;
END;

IF EXISTS
(
        SELECT 1
        FROM sys.columns AS c
        JOIN sys.types AS t ON t.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(N'ai.TransferPacket')
            AND c.name = N'PacketJson'
            AND t.name = N'nvarchar'
)
BEGIN
    IF OBJECT_ID(N'ai.CK_TransferPacket_Json', N'C') IS NOT NULL
        ALTER TABLE ai.TransferPacket DROP CONSTRAINT CK_TransferPacket_Json;

    ALTER TABLE ai.TransferPacket ALTER COLUMN PacketJson json NOT NULL;
END;

IF NOT EXISTS
(
    SELECT 1
    FROM sys.columns AS c
    JOIN sys.types AS t ON t.user_type_id = c.user_type_id
    WHERE c.object_id = OBJECT_ID(N'ai.Skill')
      AND c.name = N'SkillJson'
      AND t.name = N'json'
)
    THROW 50030, 'ai.Skill.SkillJson is not the native json type.', 1;

IF NOT EXISTS
(
    SELECT 1
    FROM sys.columns AS c
    JOIN sys.types AS t ON t.user_type_id = c.user_type_id
    WHERE c.object_id = OBJECT_ID(N'ai.TransferPacket')
      AND c.name = N'PacketJson'
      AND t.name = N'json'
)
    THROW 50031, 'ai.TransferPacket.PacketJson is not the native json type.', 1;

COMMIT TRANSACTION;
GO

SELECT
    OBJECT_SCHEMA_NAME(c.object_id) AS SchemaName,
    OBJECT_NAME(c.object_id) AS TableName,
    c.name AS ColumnName,
    TYPE_NAME(c.user_type_id) AS DataType
FROM sys.columns AS c
WHERE (c.object_id = OBJECT_ID(N'ai.Skill') AND c.name = N'SkillJson')
   OR (c.object_id = OBJECT_ID(N'ai.TransferPacket') AND c.name = N'PacketJson')
ORDER BY TableName, ColumnName;
GO