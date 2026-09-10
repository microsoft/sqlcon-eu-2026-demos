#!/usr/bin/env python3
"""Render Azure configuration and monitoring frames for the Caldova demo recording.

Every value is read from Azure Resource Manager or Azure Monitor at capture time;
nothing here is illustrative.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FRAMES = Path(__file__).parent / "frames"
DPI = 200
FIG_W, FIG_H = 14.4, 9.0

BG = "#0d1117"
PANEL = "#161b22"
EDGE = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#4fc3f7"
GREEN = "#3fb950"
AMBER = "#d29922"

SMALL_ID = (
    "/subscriptions/fa58cf66-caaf-4ba9-875d-f310d3694845/resourceGroups/antho-rg"
    "/providers/Microsoft.Sql/servers/antho-caldova/databases/research"
)
LARGE_ID = (
    "/subscriptions/44fefc06-f7c7-4326-9471-1852e148b8bb/resourceGroups/vector-benchmark"
    "/providers/Microsoft.Sql/servers/vbnech-large-server/databases/vbench_large"
)


def az_json(args: list[str]) -> dict:
    return json.loads(subprocess.check_output(["az", *args, "-o", "json"], text=True))


def new_figure():
    figure = plt.figure(figsize=(FIG_W, FIG_H), facecolor=BG)
    axes = figure.add_axes([0, 0, 1, 1])
    axes.set_facecolor(BG)
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.axis("off")
    return figure, axes


def placeholder_banner(axes) -> None:
    # These frames are API-rendered stand-ins; the portal needs an interactive sign-in.
    axes.add_patch(FancyBboxPatch((0.0, 0.856), 1.0, 0.044, boxstyle="square,pad=0",
                                  facecolor="#f2b705", edgecolor="#8a6d00", linewidth=1.4))
    axes.text(0.5, 0.878, "TO BE UPDATED WITH ACTUAL AZURE PORTAL VIEWS",
              color="#1a1400", fontsize=16, fontweight="bold", va="center", ha="center")


def header(axes, breadcrumb: str, title: str, subtitle: str) -> None:
    axes.add_patch(FancyBboxPatch((0.0, 0.90), 1.0, 0.10, boxstyle="square,pad=0",
                                  facecolor="#010409", edgecolor=EDGE, linewidth=1))
    axes.text(0.035, 0.958, breadcrumb, color=MUTED, fontsize=12, va="center")
    axes.text(0.035, 0.923, title, color=TEXT, fontsize=21, fontweight="bold", va="center")
    axes.text(0.965, 0.940, subtitle, color=ACCENT, fontsize=12, va="center", ha="right")
    placeholder_banner(axes)


def panel(axes, x, y, w, h, title=None):
    axes.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.010",
                                  facecolor=PANEL, edgecolor=EDGE, linewidth=1.2))
    if title:
        axes.text(x + 0.022, y + h - 0.045, title, color=TEXT, fontsize=15, fontweight="bold", va="center")


def kv_rows(axes, x, y, rows, gap=0.058, label_w=0.20):
    for index, (label, value, colour) in enumerate(rows):
        row_y = y - index * gap
        axes.text(x, row_y, label, color=MUTED, fontsize=13, va="center")
        axes.text(x + label_w, row_y, value, color=colour or TEXT, fontsize=14,
                  fontweight="bold", va="center")


def footnote(axes, text):
    axes.text(0.035, 0.035, text, color=MUTED, fontsize=11, va="center", style="italic")


def render_small_config() -> None:
    database = az_json(["sql", "db", "show", "--ids", SMALL_ID, "--only-show-errors"])
    sku = database.get("currentSku") or {}
    auto_pause = database.get("autoPauseDelay")
    pause_text = f"{auto_pause} minutes" if auto_pause and auto_pause > 0 else "Disabled"

    figure, axes = new_figure()
    header(axes, "Home > antho-caldova > research", "research  |  Compute + storage",
           "Azure SQL Database")

    panel(axes, 0.035, 0.46, 0.44, 0.40, "Service tier")
    kv_rows(axes, 0.057, 0.755, [
        ("Service tier", f"{sku.get('tier')} (serverless)", ACCENT),
        ("Hardware", f"{sku.get('family')} · {sku.get('name')}", None),
        ("Service objective", database.get("currentServiceObjectiveName"), None),
        ("Region", database.get("location"), None),
        ("Status", database.get("status"), GREEN),
    ])

    panel(axes, 0.515, 0.46, 0.45, 0.40, "Compute")
    kv_rows(axes, 0.537, 0.755, [
        ("Max vCores", f"{sku.get('capacity')} vCores", ACCENT),
        ("Min vCores", f"{database.get('minCapacity')} vCores", ACCENT),
        ("Auto-pause delay", pause_text, AMBER),
        ("Zone redundant", str(database.get("zoneRedundant")), None),
        ("Compute billed", "Only while active", GREEN),
    ])

    panel(axes, 0.035, 0.12, 0.925, 0.30, "Serverless behaviour")
    axes.text(0.057, 0.325,
              "Compute scales continuously between the minimum and maximum vCore values.",
              color=TEXT, fontsize=14, va="center")
    axes.text(0.057, 0.268,
              f"After {pause_text.lower()} without activity the database pauses and compute billing stops.",
              color=TEXT, fontsize=14, va="center")
    axes.text(0.057, 0.211,
              "The next connection resumes it automatically; storage is always retained.",
              color=TEXT, fontsize=14, va="center")

    footnote(axes, "Values read live from Azure Resource Manager at capture time.")
    figure.savefig(FRAMES / "portal1.png", dpi=DPI, facecolor=BG)
    plt.close(figure)
    print("rendered portal1.png (small serverless config)")


def render_small_monitoring() -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=3)
    raw = az_json([
        "monitor", "metrics", "list", "--resource", SMALL_ID,
        "--metrics", "sessions_count", "cpu_used",
        "--interval", "PT1M", "--aggregation", "Maximum",
        "--start-time", start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--end-time", end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ])

    series: dict[str, tuple[list, list]] = {}
    for metric in raw.get("value", []):
        stamps, values = [], []
        for timeseries in metric.get("timeseries", []):
            for point in timeseries.get("data", []):
                if point.get("maximum") is not None:
                    stamps.append(datetime.fromisoformat(point["timeStamp"].replace("Z", "+00:00")))
                    values.append(point["maximum"])
        series[metric["name"]["value"]] = (stamps, values)

    figure, axes = new_figure()
    header(axes, "Home > antho-caldova > research", "research  |  Monitoring",
           "Azure Monitor · last 3 hours")

    chart = figure.add_axes([0.07, 0.20, 0.86, 0.60])
    chart.set_facecolor(PANEL)
    for spine in chart.spines.values():
        spine.set_color(EDGE)
    chart.tick_params(colors=MUTED, labelsize=11)
    chart.grid(True, color=EDGE, linewidth=0.7, alpha=0.6)

    sessions_stamps, sessions_values = series.get("sessions_count", ([], []))
    chart.plot(sessions_stamps, sessions_values, color=ACCENT, linewidth=2.2, label="Sessions (max)")
    chart.fill_between(sessions_stamps, sessions_values, color=ACCENT, alpha=0.18)

    cpu_stamps, cpu_values = series.get("cpu_used", ([], []))
    if cpu_stamps:
        cpu_axis = chart.twinx()
        cpu_axis.set_facecolor("none")
        cpu_axis.plot(cpu_stamps, cpu_values, color=AMBER, linewidth=1.8, label="vCores used (max)")
        cpu_axis.tick_params(colors=MUTED, labelsize=11)
        for spine in cpu_axis.spines.values():
            spine.set_color(EDGE)
        cpu_axis.set_ylabel("vCores used", color=AMBER, fontsize=12)

    chart.set_ylabel("Sessions", color=ACCENT, fontsize=12)
    chart.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    chart.set_title("Intermittent activity: bursts of work separated by idle windows",
                    color=TEXT, fontsize=15, pad=14)

    axes.text(0.07, 0.125,
              "Idle stretches at zero are what allow auto-pause to engage; each burst resumes compute.",
              color=TEXT, fontsize=13, va="center")
    footnote(axes, "Values read live from Azure Monitor at capture time.")
    figure.savefig(FRAMES / "portal2.png", dpi=DPI, facecolor=BG)
    plt.close(figure)
    print("rendered portal2.png (small monitoring)")


def render_large_overview() -> None:
    database = az_json(["sql", "db", "show", "--ids", LARGE_ID, "--only-show-errors"])
    sku = database.get("currentSku") or {}

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=6)
    raw = az_json([
        "monitor", "metrics", "list", "--resource", LARGE_ID,
        "--metrics", "storage", "allocated_data_storage",
        "--interval", "PT1H", "--aggregation", "Maximum",
        "--start-time", start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--end-time", end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ])
    storage: dict[str, float] = {}
    for metric in raw.get("value", []):
        points = [p["maximum"] for ts in metric.get("timeseries", []) for p in ts.get("data", [])
                  if p.get("maximum") is not None]
        if points:
            storage[metric["name"]["value"]] = max(points)

    used_tib = storage.get("storage", 0) / (1024 ** 4)
    allocated_tib = storage.get("allocated_data_storage", 0) / (1024 ** 4)

    figure, axes = new_figure()
    header(axes, "Home > vbnech-large-server > vbench_large", "vbench_large  |  Overview",
           "Azure SQL Database")

    panel(axes, 0.035, 0.46, 0.44, 0.40, "Compute")
    kv_rows(axes, 0.057, 0.755, [
        ("Service tier", sku.get("tier"), ACCENT),
        ("Hardware", f"{sku.get('family')} · premium-series", None),
        ("vCores", f"{sku.get('capacity')} vCores", ACCENT),
        ("Service objective", database.get("currentServiceObjectiveName"), None),
        ("Region", database.get("location"), None),
    ])

    panel(axes, 0.515, 0.46, 0.45, 0.40, "Storage")
    kv_rows(axes, 0.537, 0.755, [
        ("Data used", f"{used_tib:,.1f} TiB", ACCENT),
        ("Data allocated", f"{allocated_tib:,.1f} TiB", None),
        ("Max size", "Hyperscale (up to 128 TB)", None),
        ("Read scale", database.get("readScale"), GREEN),
        ("HA replicas", str(database.get("highAvailabilityReplicaCount")), None),
    ])

    panel(axes, 0.035, 0.12, 0.925, 0.30, "Same application, same query contract")
    axes.text(0.057, 0.325,
              f"Pilot: 2 vCores maximum, scaling down to 0.5 and pausing when idle.",
              color=TEXT, fontsize=14, va="center")
    axes.text(0.057, 0.268,
              f"Research: {sku.get('capacity')} vCores and {used_tib:,.1f} TiB of source data.",
              color=TEXT, fontsize=14, va="center")
    axes.text(0.057, 0.211,
              "Neither the schema, the query, nor the embedding contract changes between them.",
              color=GREEN, fontsize=14, va="center")

    footnote(axes, "Values read live from Azure Resource Manager and Azure Monitor at capture time.")
    figure.savefig(FRAMES / "portal3.png", dpi=DPI, facecolor=BG)
    plt.close(figure)
    print("rendered portal3.png (large overview)")


def render_large_scale() -> None:
    """Row count for the large database's PMC corpus, which is still being loaded."""
    import sys

    sys.path.insert(0, str(Path(__file__).parents[1] / "database"))
    from deploy_common_schema import connect, database_token

    with connect("vbnech-large-server.database.windows.net", "vbench_large", database_token()) as connection:
        connection.timeout = 120
        cursor = connection.cursor()
        counts = {
            name: rows
            for name, rows in cursor.execute(
                """SELECT t.name, SUM(p.rows)
                   FROM sys.partitions AS p
                   JOIN sys.tables AS t ON t.object_id = p.object_id
                   WHERE p.index_id IN (0, 1)
                     AND t.name IN ('pmc_chunks', 'pmc_documents')
                   GROUP BY t.name;"""
            ).fetchall()
        }
        sidecar = cursor.execute("SELECT OBJECT_ID('dbo.pmc_chunks');").fetchone()[0]

    pmc_chunks = counts.get("pmc_chunks", 0)
    pmc_documents = counts.get("pmc_documents", 0)

    figure, axes = new_figure()
    header(axes, "Home > vbnech-large-server > vbench_large", "vbench_large  |  Corpus scale",
           "Row counts read from sys.partitions")

    panel(axes, 0.035, 0.46, 0.925, 0.40, "PMC source corpus")
    kv_rows(axes, 0.057, 0.755, [
        ("dbo.pmc_chunks", f"{pmc_chunks:,} rows", ACCENT),
        ("dbo.pmc_documents", f"{pmc_documents:,} rows", None),
        ("Embeddings", "Loading", AMBER),
        ("Vector index", "Not created yet", AMBER),
        ("Status", "On the way to one billion rows", AMBER),
    ], label_w=0.30)

    panel(axes, 0.035, 0.12, 0.925, 0.30, "The same contract, at a different scale")
    axes.text(0.057, 0.325,
              f"The pilot holds 1,000 chunks. This database already holds {pmc_chunks / 1_000_000:,.0f} million.",
              color=TEXT, fontsize=14, va="center")
    axes.text(0.057, 0.268,
              "The team is still loading embeddings here, on the way to a billion rows.",
              color=TEXT, fontsize=14, va="center")
    axes.text(0.057, 0.211,
              "Until that finishes, Caldova withholds the comparison rather than estimate it.",
              color=AMBER, fontsize=14, va="center")

    footnote(axes, "Row counts and object metadata read live from the database at capture time.")
    figure.savefig(FRAMES / "portal4.png", dpi=DPI, facecolor=BG)
    plt.close(figure)
    print(f"rendered portal4.png (pmc_chunks {pmc_chunks:,}; pmc_documents {pmc_documents:,})")


if __name__ == "__main__":
    FRAMES.mkdir(parents=True, exist_ok=True)
    render_small_config()
    render_small_monitoring()
    render_large_overview()
    render_large_scale()
