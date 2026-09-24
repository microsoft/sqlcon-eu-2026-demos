using System.Reflection;
using Microsoft.Data.SqlClient;

const string query = "SELECT TOP (5) ProductID, Name FROM SalesLT.Product ORDER BY ProductID";

var connectionString = args.Length > 0
    ? args[0]
    : Environment.GetEnvironmentVariable("SQL_CONNECTION_STRING")
        ?? throw new InvalidOperationException(
            "Pass the connection string as the first argument or set SQL_CONNECTION_STRING.");

await using var connection = new SqlConnection(connectionString);
await connection.OpenAsync();
await using var command = connection.CreateCommand();
command.CommandText = query;
await using var reader = await command.ExecuteReaderAsync();

// AssemblyVersion is pinned at 7.0.0.0 for binding stability, so report the package version instead.
var assembly = typeof(SqlConnection).Assembly;
var version = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion.Split('+')[0]
    ?? assembly.GetName().Version?.ToString();

Console.WriteLine($"SqlClient {version}");
Console.WriteLine("Product ID  Name");
Console.WriteLine("----------  ----");
while (await reader.ReadAsync())
{
    Console.WriteLine($"{reader.GetInt32(0),-10}  {reader.GetString(1)}");
}
Console.WriteLine();