using Caldova.TransferCenter.Data;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddProblemDetails();
builder.Services.AddScoped<CaldovaRepository>();

var app = builder.Build();

app.UseExceptionHandler();
app.UseDefaultFiles();
app.UseStaticFiles();

app.MapGet("/api/health", async (CaldovaRepository repository, CancellationToken cancellationToken) =>
	Results.Ok(await repository.GetHealthAsync(cancellationToken)));

app.MapGet("/api/transfers", async (CaldovaRepository repository, CancellationToken cancellationToken) =>
	Results.Ok(await repository.GetTransfersAsync(cancellationToken)));

app.MapGet("/api/transfers/{transferNumber}", async (
	string transferNumber,
	CaldovaRepository repository,
	CancellationToken cancellationToken) =>
{
	var detail = await repository.GetTransferDetailAsync(transferNumber, cancellationToken);
	return detail is null ? Results.NotFound() : Results.Ok(detail);
});

app.MapPost("/api/transfers/{transferNumber}/briefings", async (
	string transferNumber,
	CaldovaRepository repository,
	CancellationToken cancellationToken) =>
	Results.Ok(await repository.GenerateBriefingAsync(transferNumber, cancellationToken)));

app.MapFallbackToFile("index.html");

app.Run();
