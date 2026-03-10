# .NET ORM Benchmarks

Visual Studio projects containing unit and benchmark tests for 3 different .NET ORMs.

Visual Studio Test Explorer window can be used to run unit tests.

To run performance benchmarks, set `BenchmarkMain` as a startup project. Configuration must be set to `Release`. Then start the project without debugging (CTRL + F5). A console window will appear. It contains instructions on how to target specific benchmarks. To run all, type in an asterisk (\*) and press enter. This will trigger a full run, which takes approximately one hour to finish. You can switch to the test configuration which does only a few numbers of iterations in `BenchmarkMain/Program.cs` file.

Console command for running benchmarks is `dotnet run --configuration Release --project BenchmarkMain\BenchmarkMain.csproj`. To run with a shorter test configuration, append `-- --testb` at the end of the command.

Tests will not execute without a database running locally. The instructions to start an instance are below.

## Mocking mechanism

**Common/Mock** contains files for mocking the functionality of EFCore, NHibernate, and Dapper.

**EFCorePerformance/EFCoreBenchmarks.cs**, **NHibernatePerformance/NHibernateBenchmarks.cs**, and **DapperPerformance/DapperBenchmark.cs** contain updated benchmark code that uses the mocking mechanism to extract full SQL query command, query plan's estimated row count and query output schema information, namely column names, ordinals, and data types.

Then, during query benchmarking Query execution the DBMS was removed by mocking/intercepting the command, and then constructing the underlying DbDataReader directly. The idea is to measure each ORM's time and memory overhead without actually executing the possibly long-running query on the database server. ORMs were mocked as low-level as possible to contain most of the overhead (method calling, memory allocation, etc.).

## Database setup

Dockerfile is provided to initialize Microsoft SQL Server database and fill it with data. Tested using Docker.

Build image:
`docker build -t orm-comparison .`

Run container:
`docker run -d --name orm-comparison -p 1444:1433 orm-comparison`

Test connection:
`sqlcmd -S 127.0.0.1,1444 -U SA -P Testingorms123 -Q "SELECT * FROM [WideWorldImporters].[Purchasing].[PurchaseOrders]"`

## Sources

- [Wide World Importers sample databases for Microsoft SQL](https://learn.microsoft.com/en-us/sql/samples/wide-world-importers-what-is?view=sql-server-ver16)
- [BAK file with WWI database](https://github.com/microsoft/sql-server-samples/releases/download/wide-world-importers-v1.0/WideWorldImporters-Full.bak)
- [Microsoft SQL Server image on DockerHuber](https://hub.docker.com/r/microsoft/mssql-server)
