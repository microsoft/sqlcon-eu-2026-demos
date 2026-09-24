// On Windows, the connection string is handed to SQLDriverConnectW exactly as received.
#if defined(_WIN32)
#include <windows.h>
#endif
#include <sql.h>
#include <sqlext.h>
#if defined(_WIN32)
#include <fcntl.h>
#include <io.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string>

#if defined(_WIN32)
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

    const wchar_t* connectionString = argc > 1 ? argv[1] : _wgetenv(L"SQL_CONNECTION_STRING");
    if (connectionString == nullptr || connectionString[0] == L'\0')
    {
        fwprintf(stderr, L"Pass the connection string as the first argument or set SQL_CONNECTION_STRING.\n");
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

    if (!SQL_SUCCEEDED(SQLDriverConnectW(dbc, nullptr, (SQLWCHAR*)connectionString, SQL_NTS,
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
#else
static std::string TrimVersionPadding(const std::string& version)
{
    std::string result;
    size_t start = 0;

    while (start <= version.size())
    {
        size_t dot = version.find('.', start);
        size_t count = (dot == std::string::npos) ? std::string::npos : dot - start;
        std::string part = version.substr(start, count);
        size_t firstDigit = part.find_first_not_of('0');
        result += (firstDigit == std::string::npos) ? "0" : part.substr(firstDigit);

        if (dot == std::string::npos)
        {
            break;
        }

        result += '.';
        start = dot + 1;
    }

    return result;
}

static void Fail(const char* what, SQLSMALLINT handleType, SQLHANDLE handle)
{
    SQLCHAR state[6] = {};
    SQLINTEGER native = 0;
    SQLCHAR message[1024] = {};
    SQLSMALLINT length = 0;

    if (SQL_SUCCEEDED(SQLGetDiagRec(handleType, handle, 1, state, &native, message,
                                    (SQLSMALLINT)sizeof(message), &length)))
    {
        fprintf(stderr, "%s: [%s] %s\n", what, state, message);
    }
    else
    {
        fprintf(stderr, "%s\n", what);
    }

    exit(1);
}

int main(int argc, char** argv)
{
    const char* connectionString = argc > 1 ? argv[1] : getenv("SQL_CONNECTION_STRING");
    if (connectionString == nullptr || connectionString[0] == '\0')
    {
        fprintf(stderr, "Pass the connection string as the first argument or set SQL_CONNECTION_STRING.\n");
        return 1;
    }

    SQLHENV env = SQL_NULL_HENV;
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &env)))
    {
        fprintf(stderr, "SQLAllocHandle(ENV) failed\n");
        return 1;
    }
    SQLSetEnvAttr(env, SQL_ATTR_ODBC_VERSION, (SQLPOINTER)SQL_OV_ODBC3, 0);

    SQLHDBC dbc = SQL_NULL_HDBC;
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_DBC, env, &dbc)))
    {
        Fail("SQLAllocHandle(DBC) failed", SQL_HANDLE_ENV, env);
    }

    if (!SQL_SUCCEEDED(SQLDriverConnect(dbc, nullptr, (SQLCHAR*)connectionString, SQL_NTS,
                                        nullptr, 0, nullptr, SQL_DRIVER_NOPROMPT)))
    {
        Fail("SQLDriverConnect failed", SQL_HANDLE_DBC, dbc);
    }

    SQLHSTMT stmt = SQL_NULL_HSTMT;
    if (!SQL_SUCCEEDED(SQLAllocHandle(SQL_HANDLE_STMT, dbc, &stmt)))
    {
        Fail("SQLAllocHandle(STMT) failed", SQL_HANDLE_DBC, dbc);
    }

    SQLCHAR query[] = "SELECT TOP (5) ProductID, Name FROM SalesLT.Product ORDER BY ProductID";
    if (!SQL_SUCCEEDED(SQLExecDirect(stmt, query, SQL_NTS)))
    {
        Fail("SQLExecDirect failed", SQL_HANDLE_STMT, stmt);
    }

    SQLCHAR driverVersion[64] = {};
    SQLGetInfo(dbc, SQL_DRIVER_VER, driverVersion, (SQLSMALLINT)sizeof(driverVersion), nullptr);

    printf("ODBC %s\n", TrimVersionPadding((char*)driverVersion).c_str());
    printf("Product ID  Name\n");
    printf("----------  ----\n");

    SQLINTEGER productId = 0;
    SQLCHAR name[128] = {};
    SQLLEN productIdLength = 0;
    SQLLEN nameLength = 0;
    SQLBindCol(stmt, 1, SQL_C_SLONG, &productId, 0, &productIdLength);
    SQLBindCol(stmt, 2, SQL_C_CHAR, name, (SQLLEN)sizeof(name), &nameLength);

    while (SQLFetch(stmt) == SQL_SUCCESS)
    {
        printf("%-10d  %s\n", (int)productId, name);
    }
    printf("\n");

    SQLFreeHandle(SQL_HANDLE_STMT, stmt);
    SQLDisconnect(dbc);
    SQLFreeHandle(SQL_HANDLE_DBC, dbc);
    SQLFreeHandle(SQL_HANDLE_ENV, env);
    return 0;
}
#endif
