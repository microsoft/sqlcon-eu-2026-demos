package main

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"runtime/debug"

	_ "github.com/microsoft/go-mssqldb"
)

const driverModule = "github.com/microsoft/go-mssqldb"

func driverVersion() string {
	info, ok := debug.ReadBuildInfo()
	if !ok {
		return "unknown"
	}
	for _, dep := range info.Deps {
		if dep.Path != driverModule {
			continue
		}
		if dep.Replace != nil {
			return "local replace"
		}
		return dep.Version
	}
	return "unknown"
}

func main() {
	connectionString := os.Getenv("SQL_CONNECTION_STRING")
	if len(os.Args) > 1 {
		connectionString = os.Args[1]
	}
	if connectionString == "" {
		panic("pass the connection string as the first argument or set SQL_CONNECTION_STRING")
	}
	database, err := sql.Open("sqlserver", connectionString)
	check(err)
	defer database.Close()

	rows, err := database.QueryContext(context.Background(), `
		SELECT TOP (5) ProductID, Name
		FROM SalesLT.Product
		ORDER BY ProductID`)
	check(err)
	defer rows.Close()

	fmt.Printf("go-mssqldb %s\n", driverVersion())
	fmt.Println("Product ID  Name")
	fmt.Println("----------  ----")
	for rows.Next() {
		var productID int
		var name string
		check(rows.Scan(&productID, &name))
		fmt.Printf("%-10d  %s\n", productID, name)
	}
	check(rows.Err())
	fmt.Println()
}

func check(err error) {
	if err != nil {
		panic(err)
	}
}
