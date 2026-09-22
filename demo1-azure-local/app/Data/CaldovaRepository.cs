using System.Data;
using Caldova.TransferCenter.Models;
using Microsoft.Data.SqlClient;

namespace Caldova.TransferCenter.Data;

public sealed class CaldovaRepository(IConfiguration configuration)
{
    private readonly string _connectionString = configuration.GetConnectionString("Caldova")
        ?? throw new InvalidOperationException("Connection string 'Caldova' is not configured.");

    public async Task<HealthResult> GetHealthAsync(CancellationToken cancellationToken)
    {
        await using var connection = await OpenConnectionAsync(cancellationToken);
        await using var command = new SqlCommand("SELECT DB_NAME(), SYSUTCDATETIME();", connection);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        await reader.ReadAsync(cancellationToken);
        return new HealthResult("Healthy", reader.GetString(0), reader.GetDateTime(1));
    }

    public async Task<IReadOnlyList<TransferQueueItem>> GetTransfersAsync(CancellationToken cancellationToken)
    {
        const string sql = """
            SELECT TransferId, TransferNumber, EncounterNumber, RegionalRecordNumber,
                   GivenName, FamilyName, Age, TransportUnit, DestinationName, ChiefConcern,
                   PriorityCode, TransferStatus, EstimatedArrivalAt, EtaMinutes,
                   DestinationBay, ReceivingTeamNotifiedAt
            FROM app.vTransferQueue
            ORDER BY PriorityCode, EstimatedArrivalAt;
            """;

        await using var connection = await OpenConnectionAsync(cancellationToken);
        await using var command = new SqlCommand(sql, connection);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        var transfers = new List<TransferQueueItem>();
        while (await reader.ReadAsync(cancellationToken))
        {
            transfers.Add(ReadTransfer(reader));
        }

        return transfers;
    }

    public async Task<TransferDetail?> GetTransferDetailAsync(string transferNumber, CancellationToken cancellationToken)
    {
        await using var connection = await OpenConnectionAsync(cancellationToken);
        await using var command = new SqlCommand("app.usp_GetTransferDetail", connection)
        {
            CommandType = CommandType.StoredProcedure
        };
        command.Parameters.Add(new SqlParameter("@TransferNumber", SqlDbType.VarChar, 30) { Value = transferNumber });

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        if (!await reader.ReadAsync(cancellationToken))
        {
            return null;
        }

        var transfer = ReadTransfer(reader);
        var observations = new List<Observation>();
        var narratives = new List<Narrative>();
        var allergies = new List<Allergy>();
        var medications = new List<Medication>();
        var encounters = new List<RecentEncounter>();
        var signals = new List<ExtractedSignal>();

        await reader.NextResultAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            observations.Add(new Observation(
                reader.GetString(0), reader.GetString(1), GetNullable<decimal>(reader, 2),
                GetNullableString(reader, 3), GetNullableString(reader, 4), reader.GetBoolean(5), reader.GetDateTime(6)));
        }

        await reader.NextResultAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            narratives.Add(new Narrative(reader.GetInt64(0), reader.GetString(1), reader.GetString(2), reader.GetDateTime(3)));
        }

        await reader.NextResultAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            allergies.Add(new Allergy(reader.GetString(0), GetNullableString(reader, 1), reader.GetDateTime(2)));
        }

        await reader.NextResultAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            medications.Add(new Medication(
                reader.GetString(0), GetNullableString(reader, 1), GetNullableString(reader, 2), reader.GetDateTime(3)));
        }

        await reader.NextResultAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            encounters.Add(new RecentEncounter(
                reader.GetString(0), reader.GetString(1), reader.GetDateTime(2),
                GetNullable<DateTime>(reader, 3), reader.GetString(4)));
        }

        await reader.NextResultAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            signals.Add(new ExtractedSignal(reader.GetString(0), reader.GetString(1), reader.GetInt64(2)));
        }

        return new TransferDetail(transfer, observations, narratives, allergies, medications, encounters, signals);
    }

    public async Task<BriefingResult> GenerateBriefingAsync(string transferNumber, CancellationToken cancellationToken)
    {
        await using var connection = await OpenConnectionAsync(cancellationToken);

        await ExecuteProcedureAsync(connection, "ai.usp_ExtractSignals", 30, cancellationToken,
            new SqlParameter("@TransferNumber", SqlDbType.VarChar, 30) { Value = transferNumber });

        long packetId;
        await using (var packetCommand = new SqlCommand("ai.usp_CreateTransferPacket", connection)
        {
            CommandType = CommandType.StoredProcedure,
            CommandTimeout = 30
        })
        {
            packetCommand.Parameters.Add(new SqlParameter("@TransferNumber", SqlDbType.VarChar, 30) { Value = transferNumber });
            var packetParameter = packetCommand.Parameters.Add("@TransferPacketId", SqlDbType.BigInt);
            packetParameter.Direction = ParameterDirection.Output;
            await packetCommand.ExecuteNonQueryAsync(cancellationToken);
            packetId = (long)packetParameter.Value;
        }

        long briefingId;
        BriefingResult result;
        await using (var briefingCommand = new SqlCommand("ai.usp_InvokeTransferSkill", connection)
        {
            CommandType = CommandType.StoredProcedure,
            CommandTimeout = 240
        })
        {
            briefingCommand.Parameters.Add(new SqlParameter("@TransferPacketId", SqlDbType.BigInt) { Value = packetId });
            briefingCommand.Parameters.Add(new SqlParameter("@SkillName", SqlDbType.NVarChar, 128) { Value = "ReceivingBriefing" });
            briefingCommand.Parameters.Add(new SqlParameter("@SkillVersion", SqlDbType.VarChar, 30) { Value = "1.0" });
            var briefingParameter = briefingCommand.Parameters.Add("@BriefingId", SqlDbType.BigInt);
            briefingParameter.Direction = ParameterDirection.Output;

            await using var reader = await briefingCommand.ExecuteReaderAsync(cancellationToken);
            await reader.ReadAsync(cancellationToken);
            var summary = reader.GetString(1);
            var reviewStatus = reader.GetString(2);
            var modelId = reader.GetString(3);
            var durationMs = reader.GetInt64(4);
            var httpStatusCode = reader.GetInt32(5);

            var items = new List<BriefingItem>();
            await reader.NextResultAsync(cancellationToken);
            while (await reader.ReadAsync(cancellationToken))
            {
                items.Add(new BriefingItem(reader.GetString(0), reader.GetInt16(1), reader.GetString(2)));
            }

            await reader.CloseAsync();
            briefingId = (long)briefingParameter.Value;
            result = new BriefingResult(
                briefingId, summary, reviewStatus, modelId, durationMs, httpStatusCode, items, []);
        }

        const string sourceSql = """
            SELECT source.SourceType, source.SourceRecordKey, source.SourceSummary
            FROM ai.BriefingSource AS briefingSource
            JOIN ai.PacketSource AS source ON source.PacketSourceId = briefingSource.PacketSourceId
            WHERE briefingSource.BriefingId = @BriefingId
            ORDER BY briefingSource.CitationOrder;
            """;
        await using var sourceCommand = new SqlCommand(sourceSql, connection);
        sourceCommand.Parameters.Add(new SqlParameter("@BriefingId", SqlDbType.BigInt) { Value = briefingId });
        await using var sourceReader = await sourceCommand.ExecuteReaderAsync(cancellationToken);
        var sources = new List<BriefingSource>();
        while (await sourceReader.ReadAsync(cancellationToken))
        {
            sources.Add(new BriefingSource(sourceReader.GetString(0), sourceReader.GetString(1), sourceReader.GetString(2)));
        }

        return result with { Sources = sources };
    }

    private async Task<SqlConnection> OpenConnectionAsync(CancellationToken cancellationToken)
    {
        var connection = new SqlConnection(_connectionString);
        await connection.OpenAsync(cancellationToken);
        return connection;
    }

    private static async Task ExecuteProcedureAsync(
        SqlConnection connection,
        string procedureName,
        int timeout,
        CancellationToken cancellationToken,
        params SqlParameter[] parameters)
    {
        await using var command = new SqlCommand(procedureName, connection)
        {
            CommandType = CommandType.StoredProcedure,
            CommandTimeout = timeout
        };
        command.Parameters.AddRange(parameters);
        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    private static TransferQueueItem ReadTransfer(SqlDataReader reader) => new(
        reader.GetInt64(0), reader.GetString(1), reader.GetString(2), reader.GetString(3),
        reader.GetString(4), reader.GetString(5), reader.GetInt32(6), reader.GetString(7),
        reader.GetString(8), reader.GetString(9), reader.GetByte(10), reader.GetString(11),
        reader.GetDateTime(12), reader.GetInt32(13), GetNullableString(reader, 14),
        GetNullable<DateTime>(reader, 15));

    private static string? GetNullableString(SqlDataReader reader, int ordinal) =>
        reader.IsDBNull(ordinal) ? null : reader.GetString(ordinal);

    private static T? GetNullable<T>(SqlDataReader reader, int ordinal) where T : struct =>
        reader.IsDBNull(ordinal) ? null : reader.GetFieldValue<T>(ordinal);
}