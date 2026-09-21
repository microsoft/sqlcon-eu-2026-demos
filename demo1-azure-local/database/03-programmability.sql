/* ============================================================================
   Caldova Regional Care Transfer Center
   03-programmability.sql : app queries, regex extraction, grounded packet build
   ============================================================================ */

USE [CaldovaRegionalCare];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER VIEW app.vTransferQueue
AS
SELECT
    t.TransferId,
    t.TransferNumber,
    e.EncounterNumber,
    p.RegionalRecordNumber,
    p.GivenName,
    p.FamilyName,
    DATEDIFF(year, p.DateOfBirth, CAST(SYSUTCDATETIME() AS date))
        - CASE WHEN DATEADD(year, DATEDIFF(year, p.DateOfBirth, CAST(SYSUTCDATETIME() AS date)), p.DateOfBirth)
                    > CAST(SYSUTCDATETIME() AS date) THEN 1 ELSE 0 END AS Age,
    t.TransportUnit,
    destination.FacilityName AS DestinationName,
    t.ChiefConcern,
    t.PriorityCode,
    t.TransferStatus,
    t.EstimatedArrivalAt,
    CASE
        WHEN DATEDIFF(minute, SYSUTCDATETIME(), t.EstimatedArrivalAt) < 0 THEN 0
        ELSE DATEDIFF(minute, SYSUTCDATETIME(), t.EstimatedArrivalAt)
    END AS EtaMinutes,
    t.DestinationBay,
    t.ReceivingTeamNotifiedAt
FROM ops.Transfer AS t
JOIN care.Encounter AS e ON e.EncounterId = t.EncounterId
JOIN care.Person AS p ON p.PersonId = e.PersonId
JOIN ops.Facility AS destination ON destination.FacilityId = t.DestinationFacilityId
WHERE t.TransferStatus IN ('Requested', 'Accepted', 'InTransit');
GO

CREATE OR ALTER PROCEDURE app.usp_GetTransferDetail
    @TransferNumber varchar(30)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @EncounterId bigint;
    DECLARE @PersonId bigint;

    SELECT
        @EncounterId = t.EncounterId,
        @PersonId = e.PersonId
    FROM ops.Transfer AS t
    JOIN care.Encounter AS e ON e.EncounterId = t.EncounterId
    WHERE t.TransferNumber = @TransferNumber;

    IF @EncounterId IS NULL
        THROW 50010, 'Transfer not found.', 1;

    SELECT *
    FROM app.vTransferQueue
    WHERE TransferNumber = @TransferNumber;

    SELECT ObservationCode, ObservationName, NumericValue, TextValue, Unit, IsAlert, ObservedAt
    FROM care.Observation
    WHERE EncounterId = @EncounterId
    ORDER BY ObservedAt DESC, ObservationId;

    SELECT n.NarrativeId, n.NarrativeText, n.AuthoredBy, n.RecordedAt
    FROM ops.FieldNarrative AS n
    WHERE n.EncounterId = @EncounterId
    ORDER BY n.RecordedAt DESC;

    SELECT a.AllergyName, pa.Reaction, pa.RecordedAt
    FROM care.PersonAllergy AS pa
    JOIN care.Allergy AS a ON a.AllergyId = pa.AllergyId
    WHERE pa.PersonId = @PersonId
      AND pa.AllergyStatus = 'Active'
    ORDER BY a.AllergyName;

    SELECT m.MedicationName, pm.Dose, pm.Frequency, pm.StartedAt
    FROM care.PersonMedication AS pm
    JOIN care.Medication AS m ON m.MedicationId = pm.MedicationId
    WHERE pm.PersonId = @PersonId
      AND pm.MedicationStatus = 'Active'
    ORDER BY m.MedicationName;

    SELECT TOP (5)
        e.EncounterNumber, e.EncounterType, e.StartedAt, e.EndedAt, f.FacilityName
    FROM care.Encounter AS e
    JOIN ops.Facility AS f ON f.FacilityId = e.FacilityId
    WHERE e.PersonId = @PersonId
      AND e.EncounterId <> @EncounterId
    ORDER BY e.StartedAt DESC;

        SELECT s.SignalType, s.SignalValue, s.MatchOrdinal
        FROM ai.ExtractedSignal AS s
        JOIN ops.FieldNarrative AS n ON n.NarrativeId = s.NarrativeId
        WHERE n.EncounterId = @EncounterId
        ORDER BY s.SignalType, s.MatchOrdinal;
END;
GO

CREATE OR ALTER PROCEDURE ai.usp_ExtractSignals
    @TransferNumber varchar(30)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @NarrativeId bigint;

    SELECT TOP (1) @NarrativeId = n.NarrativeId
    FROM ops.Transfer AS t
    JOIN ops.FieldNarrative AS n ON n.EncounterId = t.EncounterId
    WHERE t.TransferNumber = @TransferNumber
    ORDER BY n.RecordedAt DESC;

    IF @NarrativeId IS NULL
        THROW 50011, 'No field narrative was found for the transfer.', 1;

    BEGIN TRANSACTION;

    DELETE FROM ai.ExtractedSignal
    WHERE NarrativeId = @NarrativeId;

    INSERT ai.ExtractedSignal
        (NarrativeId, SignalRuleId, MatchOrdinal, SignalType, SignalValue,
         StartPosition, EndPosition)
    SELECT
        n.NarrativeId,
        r.SignalRuleId,
        matches.match_id,
        r.SignalType,
        CONVERT(nvarchar(1000), COALESCE(
            JSON_VALUE(CONVERT(nvarchar(max), matches.substring_matches), '$[0].value'),
            matches.match_value)),
        matches.start_position,
        matches.end_position
    FROM ops.FieldNarrative AS n
    CROSS JOIN ai.SignalRule AS r
    CROSS APPLY REGEXP_MATCHES(n.NarrativeText, r.Pattern, r.Flags) AS matches
    WHERE n.NarrativeId = @NarrativeId
      AND r.IsActive = 1;

    COMMIT TRANSACTION;

    SELECT SignalType, SignalValue, MatchOrdinal, StartPosition, EndPosition
    FROM ai.ExtractedSignal
    WHERE NarrativeId = @NarrativeId
    ORDER BY SignalType, MatchOrdinal;
END;
GO

CREATE OR ALTER PROCEDURE ai.usp_CreateTransferPacket
    @TransferNumber varchar(30),
    @TransferPacketId bigint OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TransferId bigint;
    DECLARE @EncounterId bigint;
    DECLARE @PersonId bigint;
    DECLARE @PacketVersion int;
    DECLARE @TransferJson nvarchar(max);
    DECLARE @PersonJson nvarchar(max);
    DECLARE @ObservationsJson nvarchar(max);
    DECLARE @AllergiesJson nvarchar(max);
    DECLARE @MedicationsJson nvarchar(max);
    DECLARE @RecentEncountersJson nvarchar(max);
    DECLARE @NarrativeJson nvarchar(max);
    DECLARE @SignalsJson nvarchar(max);
    DECLARE @PacketJson nvarchar(max);

    SELECT
        @TransferId = t.TransferId,
        @EncounterId = t.EncounterId,
        @PersonId = e.PersonId
    FROM ops.Transfer AS t
    JOIN care.Encounter AS e ON e.EncounterId = t.EncounterId
    WHERE t.TransferNumber = @TransferNumber;

    IF @TransferId IS NULL
        THROW 50012, 'Transfer not found.', 1;

    IF NOT EXISTS
    (
        SELECT 1
        FROM ai.ExtractedSignal AS s
        JOIN ops.FieldNarrative AS n ON n.NarrativeId = s.NarrativeId
        WHERE n.EncounterId = @EncounterId
    )
        EXEC ai.usp_ExtractSignals @TransferNumber = @TransferNumber;

    SET @TransferJson =
    (
        SELECT
            t.TransferNumber AS transferNumber,
            e.EncounterNumber AS encounterNumber,
            origin.FacilityName AS origin,
            destination.FacilityName AS destination,
            t.TransportUnit AS transportUnit,
            t.ChiefConcern AS chiefConcern,
            t.PriorityCode AS priority,
            t.TransferStatus AS [status],
            t.EstimatedArrivalAt AS estimatedArrivalAt,
            t.DestinationBay AS destinationBay,
            t.ReceivingTeamNotifiedAt AS receivingTeamNotifiedAt
        FROM ops.Transfer AS t
        JOIN care.Encounter AS e ON e.EncounterId = t.EncounterId
        JOIN ops.Facility AS origin ON origin.FacilityId = t.OriginFacilityId
        JOIN ops.Facility AS destination ON destination.FacilityId = t.DestinationFacilityId
        WHERE t.TransferId = @TransferId
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    );

    SET @PersonJson =
    (
        SELECT
            p.RegionalRecordNumber AS regionalRecordNumber,
            p.GivenName AS givenName,
            p.FamilyName AS familyName,
            p.DateOfBirth AS dateOfBirth,
            p.AdministrativeSex AS administrativeSex
        FROM care.Person AS p
        WHERE p.PersonId = @PersonId
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    );

    SET @ObservationsJson =
    (
        SELECT ObservationCode AS code, ObservationName AS [name], NumericValue AS numericValue,
               TextValue AS textValue, Unit AS unit, IsAlert AS isAlert, ObservedAt AS observedAt
        FROM care.Observation
        WHERE EncounterId = @EncounterId
        ORDER BY ObservedAt, ObservationId
        FOR JSON PATH
    );

    SET @AllergiesJson =
    (
        SELECT a.AllergyName AS [name], pa.Reaction AS reaction, pa.RecordedAt AS recordedAt
        FROM care.PersonAllergy AS pa
        JOIN care.Allergy AS a ON a.AllergyId = pa.AllergyId
        WHERE pa.PersonId = @PersonId AND pa.AllergyStatus = 'Active'
        ORDER BY a.AllergyName
        FOR JSON PATH
    );

    SET @MedicationsJson =
    (
        SELECT m.MedicationName AS [name], pm.Dose AS dose, pm.Frequency AS frequency
        FROM care.PersonMedication AS pm
        JOIN care.Medication AS m ON m.MedicationId = pm.MedicationId
        WHERE pm.PersonId = @PersonId AND pm.MedicationStatus = 'Active'
        ORDER BY m.MedicationName
        FOR JSON PATH
    );

    SET @RecentEncountersJson =
    (
        SELECT TOP (5)
            e.EncounterNumber AS encounterNumber, e.EncounterType AS encounterType,
            e.StartedAt AS startedAt, f.FacilityName AS facilityName
        FROM care.Encounter AS e
        JOIN ops.Facility AS f ON f.FacilityId = e.FacilityId
        WHERE e.PersonId = @PersonId AND e.EncounterId <> @EncounterId
        ORDER BY e.StartedAt DESC
        FOR JSON PATH
    );

    SET @NarrativeJson =
    (
        SELECT TOP (1)
            n.NarrativeText AS narrative, n.AuthoredBy AS authoredBy, n.RecordedAt AS recordedAt
        FROM ops.FieldNarrative AS n
        WHERE n.EncounterId = @EncounterId
        ORDER BY n.RecordedAt DESC
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    );

    SET @SignalsJson =
    (
        SELECT s.SignalType AS [type], s.SignalValue AS [value], s.MatchOrdinal AS matchOrdinal
        FROM ai.ExtractedSignal AS s
        JOIN ops.FieldNarrative AS n ON n.NarrativeId = s.NarrativeId
        WHERE n.EncounterId = @EncounterId
        ORDER BY s.SignalType, s.MatchOrdinal
        FOR JSON PATH
    );

    SET @PacketJson =
    (
        SELECT
            JSON_QUERY(@TransferJson) AS transfer,
            JSON_QUERY(@PersonJson) AS person,
            JSON_QUERY(@ObservationsJson) AS observations,
            JSON_QUERY(@AllergiesJson) AS allergies,
            JSON_QUERY(@MedicationsJson) AS medications,
            JSON_QUERY(@RecentEncountersJson) AS recentEncounters,
            JSON_QUERY(@NarrativeJson) AS fieldNarrative,
            JSON_QUERY(@SignalsJson) AS extractedSignals
        FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
    );

    IF ISJSON(@PacketJson) <> 1
        THROW 50013, 'Transfer packet construction did not produce valid JSON.', 1;

    BEGIN TRANSACTION;

    SELECT @PacketVersion = ISNULL(MAX(PacketVersion), 0) + 1
    FROM ai.TransferPacket WITH (UPDLOCK, HOLDLOCK)
    WHERE TransferId = @TransferId;

    INSERT ai.TransferPacket
        (TransferId, PacketVersion, PacketJson, PacketHash)
    VALUES
        (@TransferId, @PacketVersion, CAST(@PacketJson AS json),
         HASHBYTES('SHA2_256', CONVERT(varbinary(max), @PacketJson)));

    SET @TransferPacketId = SCOPE_IDENTITY();

    INSERT ai.PacketSource
        (TransferPacketId, SourceType, SourceRecordKey, SourceVersion, SourceSummary, SourceHash)
    SELECT
        @TransferPacketId,
        source.SourceType,
        source.SourceRecordKey,
        CONVERT(nvarchar(50), @PacketVersion),
        source.SourceSummary,
        HASHBYTES('SHA2_256', CONVERT(varbinary(max), source.SourceSummary))
    FROM (VALUES
        ('Transfer', @TransferNumber, @TransferJson),
        ('Person', CONVERT(nvarchar(100), @PersonId), @PersonJson),
        ('Observations', CONVERT(nvarchar(100), @EncounterId), @ObservationsJson),
        ('Allergies', CONVERT(nvarchar(100), @PersonId), @AllergiesJson),
        ('Medications', CONVERT(nvarchar(100), @PersonId), @MedicationsJson),
        ('RecentEncounters', CONVERT(nvarchar(100), @PersonId), @RecentEncountersJson),
        ('FieldNarrative', CONVERT(nvarchar(100), @EncounterId), @NarrativeJson)
    ) AS source(SourceType, SourceRecordKey, SourceSummary);

    COMMIT TRANSACTION;

    SELECT @TransferPacketId AS TransferPacketId, @PacketVersion AS PacketVersion,
           PacketHash, PacketJson
    FROM ai.TransferPacket
    WHERE TransferPacketId = @TransferPacketId;
END;
GO