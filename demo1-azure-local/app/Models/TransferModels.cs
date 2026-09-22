namespace Caldova.TransferCenter.Models;

public sealed record TransferQueueItem(
    long TransferId,
    string TransferNumber,
    string EncounterNumber,
    string RegionalRecordNumber,
    string GivenName,
    string FamilyName,
    int Age,
    string TransportUnit,
    string DestinationName,
    string ChiefConcern,
    byte PriorityCode,
    string TransferStatus,
    DateTime EstimatedArrivalAt,
    int EtaMinutes,
    string? DestinationBay,
    DateTime? ReceivingTeamNotifiedAt);

public sealed record Observation(
    string Code,
    string Name,
    decimal? NumericValue,
    string? TextValue,
    string? Unit,
    bool IsAlert,
    DateTime ObservedAt);

public sealed record Narrative(long Id, string Text, string AuthoredBy, DateTime RecordedAt);
public sealed record Allergy(string Name, string? Reaction, DateTime RecordedAt);
public sealed record Medication(string Name, string? Dose, string? Frequency, DateTime StartedAt);
public sealed record RecentEncounter(string Number, string Type, DateTime StartedAt, DateTime? EndedAt, string FacilityName);
public sealed record ExtractedSignal(string Type, string Value, long MatchOrdinal);

public sealed record TransferDetail(
    TransferQueueItem Transfer,
    IReadOnlyList<Observation> Observations,
    IReadOnlyList<Narrative> Narratives,
    IReadOnlyList<Allergy> Allergies,
    IReadOnlyList<Medication> Medications,
    IReadOnlyList<RecentEncounter> RecentEncounters,
    IReadOnlyList<ExtractedSignal> Signals);

public sealed record BriefingItem(string SectionName, short DisplayOrder, string Text);
public sealed record BriefingSource(string Type, string RecordKey, string Summary);

public sealed record BriefingResult(
    long BriefingId,
    string Summary,
    string ReviewStatus,
    string ModelId,
    long DurationMs,
    int HttpStatusCode,
    IReadOnlyList<BriefingItem> Items,
    IReadOnlyList<BriefingSource> Sources);

public sealed record HealthResult(string Status, string Database, DateTime CheckedAtUtc);