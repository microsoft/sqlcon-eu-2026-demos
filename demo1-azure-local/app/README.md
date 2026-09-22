# Caldova Regional Care Transfer Center

ASP.NET Core 10 application backed by the `CaldovaRegionalCare` SQL Server 2025
database. The browser uses live database records; generating a receiving briefing
executes the approved `ReceivingBriefing` skill through SQL Server and persists its
output and seven grounding sources.

## Run locally

From the public demo package root, after database setup succeeds:

```powershell
.\app\run.ps1
```

Open `http://localhost:5099` in a browser.

The default connection uses Windows integrated authentication:

```text
Server=localhost;Database=CaldovaRegionalCare;Integrated Security=true
```

Override it without editing source:

```powershell
$env:ConnectionStrings__Caldova = '<SQL Server connection string>'
.\app\run.ps1
```

## HTTP surface

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Verify database connectivity |
| `GET` | `/api/transfers` | Read the active transfer queue |
| `GET` | `/api/transfers/{transferNumber}` | Read transfer detail and extracted signals |
| `POST` | `/api/transfers/{transferNumber}/briefings` | Build a packet, run the approved skill, and return persisted output |

## Build

```powershell
dotnet build .\app\Caldova.TransferCenter.csproj
```

No model endpoint, prompt, skill instructions, or patient facts are embedded in
the browser. Those remain database-owned contracts.
