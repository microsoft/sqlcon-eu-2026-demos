/*
    Nandiyo Logistics - read-only Azure SQL readiness inventory.
    Run against Operations before remediation. This script changes no data or schema.
*/
SET NOCOUNT ON;

SELECT
    @@SERVERNAME AS ServerName,
    DB_NAME() AS DatabaseName,
    SERVERPROPERTY('ProductVersion') AS ProductVersion,
    SERVERPROPERTY('Edition') AS Edition,
    DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS Collation;

SELECT
    name AS DatabaseName,
    compatibility_level AS CompatibilityLevel,
    containment_desc AS Containment,
    recovery_model_desc AS RecoveryModel
FROM sys.databases
WHERE database_id = DB_ID();

SELECT
    schema_name = schemas.name,
    table_name = tables.name,
    row_count = SUM(partitions.rows)
FROM sys.tables AS tables
INNER JOIN sys.schemas AS schemas ON schemas.schema_id = tables.schema_id
INNER JOIN sys.partitions AS partitions
    ON partitions.object_id = tables.object_id
   AND partitions.index_id IN (0, 1)
GROUP BY schemas.name, tables.name
ORDER BY row_count DESC, schema_name, table_name;

SELECT
    object_type = objects.type_desc,
    schema_name = OBJECT_SCHEMA_NAME(objects.object_id),
    object_name = objects.name
FROM sys.objects AS objects
WHERE objects.is_ms_shipped = 0
  AND objects.type IN ('V', 'P', 'FN', 'IF', 'TF', 'TR')
ORDER BY object_type, schema_name, object_name;

/* DB-001 appears here: vw_OrderRegionalTax references OpsFinance. */
SELECT
    referencing_object = CONCAT(
        OBJECT_SCHEMA_NAME(dependencies.referencing_id),
        '.',
        OBJECT_NAME(dependencies.referencing_id)),
    dependencies.referenced_server_name,
    dependencies.referenced_database_name,
    dependencies.referenced_schema_name,
    dependencies.referenced_entity_name
FROM sys.sql_expression_dependencies AS dependencies
WHERE dependencies.referenced_database_name IS NOT NULL
   OR dependencies.referenced_server_name IS NOT NULL
ORDER BY referencing_object;

SELECT
    schema_name = OBJECT_SCHEMA_NAME(modules.object_id),
    object_name = OBJECT_NAME(modules.object_id),
    finding = CASE
        WHEN modules.definition LIKE '%OPENQUERY%' THEN 'OPENQUERY or linked server usage'
        WHEN modules.definition LIKE '%OPENROWSET%' THEN 'OPENROWSET usage'
        WHEN modules.definition LIKE '%xp[_]%' THEN 'Extended stored procedure usage'
        WHEN modules.definition LIKE '%OpsFinance.%' THEN 'Cross-database three-part name'
        ELSE 'Review required'
    END
FROM sys.sql_modules AS modules
WHERE modules.definition LIKE '%OPENQUERY%'
   OR modules.definition LIKE '%OPENROWSET%'
   OR modules.definition LIKE '%xp[_]%'
    OR modules.definition LIKE '%OpsFinance.%'
ORDER BY schema_name, object_name;

SELECT feature_name
FROM sys.dm_db_persisted_sku_features
ORDER BY feature_name;

SELECT
    orphaned_user = users.name,
    users.type_desc
FROM sys.database_principals AS users
LEFT JOIN sys.server_principals AS logins ON users.sid = logins.sid
WHERE users.authentication_type_desc = 'INSTANCE'
  AND users.principal_id > 4
  AND users.sid IS NOT NULL
  AND logins.sid IS NULL
ORDER BY users.name;