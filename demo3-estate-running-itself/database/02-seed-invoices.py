#!/usr/bin/env python3
"""Seed the demo 3 invoice database.

Volume matters: the scan has to be slow enough for the application to feel slow.
Two million invoices makes the difference between a seek and a scan obvious without
making the seed step take all afternoon.
"""

from __future__ import annotations

import argparse
import random
import struct
import subprocess
from datetime import date, timedelta

import pyodbc

SQL_COPT_SS_ACCESS_TOKEN = 1256
REGIONS = ["North", "South", "East", "West", "Central"]
STATUSES = ["Draft", "Sent", "Paid", "Overdue", "Void"]
STATUS_WEIGHTS = [5, 25, 55, 12, 3]
DESCRIPTIONS = [
    "Consulting hours", "Platform subscription", "Support retainer", "Implementation services",
    "Training workshop", "Data migration", "Licence renewal", "Managed service",
]


def database_token() -> bytes:
    result = subprocess.run(
        ["az", "account", "get-access-token", "--resource", "https://database.windows.net/",
         "--query", "accessToken", "--output", "tsv"],
        check=True, capture_output=True, text=True,
    )
    encoded = result.stdout.strip().encode("utf-16-le")
    return struct.pack("<I", len(encoded)) + encoded


def connect(server: str, database: str) -> pyodbc.Connection:
    connection_string = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server=tcp:{server},1433;Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return pyodbc.connect(connection_string,
                          attrs_before={SQL_COPT_SS_ACCESS_TOKEN: database_token()},
                          autocommit=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--customers", type=int, default=5_000)
    parser.add_argument("--invoices", type=int, default=2_000_000)
    parser.add_argument("--batch", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=20260909)
    args = parser.parse_args()

    random.seed(args.seed)
    start = date(2022, 1, 1)

    with connect(args.server, args.database) as connection:
        connection.timeout = 1800
        cursor = connection.cursor()
        cursor.fast_executemany = True

        print(f"seeding {args.customers:,} customers")
        cursor.executemany(
            "INSERT dbo.Customer (CustomerId, CustomerName, Region) VALUES (?, ?, ?);",
            [(i, f"Customer {i:06d}", random.choice(REGIONS)) for i in range(1, args.customers + 1)],
        )
        connection.commit()

        print(f"seeding {args.invoices:,} invoices")
        for start_id in range(1, args.invoices + 1, args.batch):
            rows = []
            for invoice_id in range(start_id, min(start_id + args.batch, args.invoices + 1)):
                issued = start + timedelta(days=random.randint(0, 1200))
                rows.append((
                    invoice_id,
                    f"INV-{invoice_id:010d}",
                    random.randint(1, args.customers),
                    issued,
                    issued + timedelta(days=30),
                    random.choices(STATUSES, STATUS_WEIGHTS)[0],
                    round(random.uniform(120.0, 48_000.0), 2),
                ))
            cursor.executemany(
                """INSERT dbo.Invoice
                   (InvoiceId, InvoiceNumber, CustomerId, InvoiceDate, DueDate, Status, TotalAmount)
                   VALUES (?, ?, ?, ?, ?, ?, ?);""",
                rows,
            )
            connection.commit()
            if start_id % 100_000 == 1:
                print(f"  {start_id - 1:,} invoices")

        print("seeding invoice lines for a sample of invoices")
        line_id = 1
        for start_id in range(1, min(args.invoices, 200_000) + 1, args.batch):
            rows = []
            for invoice_id in range(start_id, min(start_id + args.batch, 200_001)):
                for _ in range(random.randint(1, 4)):
                    rows.append((line_id, invoice_id, random.choice(DESCRIPTIONS),
                                 random.randint(1, 40), round(random.uniform(25.0, 900.0), 2)))
                    line_id += 1
            cursor.executemany(
                """INSERT dbo.InvoiceLine (InvoiceLineId, InvoiceId, Description, Quantity, UnitPrice)
                   VALUES (?, ?, ?, ?, ?);""",
                rows,
            )
            connection.commit()

        counts = cursor.execute(
            "SELECT (SELECT COUNT_BIG(*) FROM dbo.Customer), (SELECT COUNT_BIG(*) FROM dbo.Invoice),"
            " (SELECT COUNT_BIG(*) FROM dbo.InvoiceLine);"
        ).fetchone()
        print(f"customers={counts[0]:,} invoices={counts[1]:,} lines={counts[2]:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
