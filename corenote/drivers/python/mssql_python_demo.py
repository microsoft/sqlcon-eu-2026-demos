"""Demo for mssql-python using a connection string passed as the first argument."""

import sys
from importlib.metadata import version

import mssql_python

import os

connection_string = (
    sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SQL_CONNECTION_STRING")
)
if not connection_string:
    raise SystemExit(
        "Pass the connection string as the first argument or set SQL_CONNECTION_STRING."
    )

connection = mssql_python.connect(connection_string)
try:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT TOP (5) ProductID, Name FROM SalesLT.Product ORDER BY ProductID"
    )
    rows = cursor.fetchall()
finally:
    connection.close()

print(f"mssql-python {version('mssql-python')}")
print("Product ID  Name")
print("----------  ----")
for row in rows:
    print(f"{row[0]:<10}  {row[1]}")
print()
