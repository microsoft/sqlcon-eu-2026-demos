// The connection string is handed to SQLDriverConnectW exactly as received, with no parsing in between.
#include <windows.h>
#include <sql.h>
#include <sqlext.h>
#include <fcntl.h>
#include <io.h>
#include <stdio.h>
#include <stdlib.h>
#include <string>

// SQL_DRIVER_VER is a fixed-width "##.##.####" field, so 18.7.1 arrives as "18.07.0001".
static std::wstring TrimVersionPadding(const std::wstring& version)
{
    std::wstring result;
    size_t start = 0;

    while (start <= version.size())
    {
        size_t dot = version.find(L'.', start);
        size_t count = (dot == std::wstring::npos) ? std::wstring::npos : dot - start;
        std::wstring part = version.substr(start, count);

        size_t firstDigit = part.find_first_not_of(L'0');
        result += (firstDigit == std::wstring::npos) ? L"0" : part.substr(firstDigit);

        if (dot == std::wstring::npos)
        {
            break;
        }

        result += L'.';
        start = dot + 1;
    }

    return result;
}

static void Fail(const wchar_t* what, SQLSMALLINT handleType, SQLHANDLE handle)
{
    SQLWCHAR state[6] = {};
    SQLINTEGER native = 0;
    SQLWCHAR message[1024] = {};
    SQLSMALLINT length = 0;

    if (SQL_SUCCEEDED(SQLGetDiagRecW(handleType, handle, 1, state, &native, message,
                                     (SQLSMALLINT)(sizeof(message) / sizeof(SQLWCHAR)), &length)))
    {
        fwprintf(stderr, L"%ls: [%ls] %ls\n", what, state, message);
    }
    else
    {
        fwprintf(stderr, L"%ls\n", what);
    }

    exit(1);
}

int wmain(int argc, wchar_t** argv)
{
    _setmode(_fileno(stdout), _O_U8TEXT);
    _setmode(_fileno(stderr), _O_U8TEXT);

    if (argc < 2)
    {
        fwprintf(stderr, L"Pass the connection string as the first argument.\n");
        return 1;
    }

    SQLHENV env = SQL_NULL_HENV;
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &env)))
    {
        fwprintf(stderr, L"SQLAllocHandle(ENV) failed\n");
        return 1;
    }
    SQLSetEnvAttr(env, SQL_ATTR_ODBC_VERSION, (SQLPOINTER)SQL_OV_ODBC3, 0);

    SQLHDBC dbc = SQL_NULL_HDBC;
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_DBC, env, &dbc)))
    {
        Fail(L"SQLAllocHandle(DBC) failed", SQL_HANDLE_ENV, env);
    }

    if (!SQL_SUCCEEDED(SQLDriverConnectW(dbc, nullptr, argv[1], SQL_NTS,
                                         nullptr, 0, nullptr, SQL_DRIVER_NOPROMPT)))
    {
        Fail(L"SQLDriverConnect failed", SQL_HANDLE_DBC, dbc);
    }

    SQLHSTMT stmt = SQL_NULL_HSTMT;
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_STMT, dbc, &stmt)))
    {
        Fail(L"SQLAllocHandle(STMT) failed", SQL_HANDLE_DBC, dbc);
    }

    SQLWCHAR query[] = L"SELECT TOP (5) ProductID, Name FROM SalesLT.Product ORDER BY ProductID";
    if (!SQL_SUCCEEDED(SQLExecDirectW(stmt, query, SQL_NTS)))
    {
        Fail(L"SQLExecDirect failed", SQL_HANDLE_STMT, stmt);
    }

    SQLWCHAR driverVersion[64] = {};
    SQLGetInfoW(dbc, SQL_DRIVER_VER, driverVersion, (SQLSMALLINT)sizeof(driverVersion), nullptr);

    wprintf(L"ODBC %ls\n", TrimVersionPadding(driverVersion).c_str());
    wprintf(L"Product ID  Name\n");
    wprintf(L"----------  ----\n");

    SQLINTEGER productId = 0;
    SQLWCHAR name[128] = {};
    SQLLEN productIdLength = 0;
    SQLLEN nameLength = 0;
    SQLBindCol(stmt, 1, SQL_C_SLONG, &productId, 0, &productIdLength);
    SQLBindCol(stmt, 2, SQL_C_WCHAR, name, (SQLLEN)sizeof(name), &nameLength);

    while (SQLFetch(stmt) == SQL_SUCCESS)
    {
        wprintf(L"%-10d  %ls\n", (int)productId, name);
    }
    wprintf(L"\n");

    SQLFreeHandle(SQL_HANDLE_STMT, stmt);
    SQLDisconnect(dbc);
    SQLFreeHandle(SQL_HANDLE_DBC, dbc);
    SQLFreeHandle(SQL_HANDLE_ENV, env);
    return 0;
}
