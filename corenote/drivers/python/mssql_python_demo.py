"""Demo for mssql-python using a connection string passed as the first argument."""

import sys
from importlib.metadata import version

import mssql_python

if len(sys.argv) < 2:
    raise SystemExit("Pass the connection string as the first argument.")

connection = mssql_python.connect(sys.argv[1])
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
