using System;
using System.Data;
using System.Data.Common;
using System.Threading;
using System.Threading.Tasks;

namespace Common.Mock.Dapper;

public class DapperAnalyzerConnection : DbConnection
{
    private readonly DbConnection _realConnection;

    public DapperAnalyzerConnection(DbConnection realConnection)
    {
        _realConnection = realConnection;
    }

    protected override DbCommand CreateDbCommand()
    {
        var realCommand = _realConnection.CreateCommand();
        return new DapperAnalyzerCommand(realCommand);
    }

    public override ConnectionState State => _realConnection.State;

    public override string ConnectionString
    {
        get => _realConnection.ConnectionString;
        set => _realConnection.ConnectionString = value;
    }

    public override string Database => _realConnection.Database;

    public override string DataSource => _realConnection.DataSource;

    public override string ServerVersion => _realConnection.ServerVersion;

    public override void ChangeDatabase(string databaseName) => _realConnection.ChangeDatabase(databaseName);

    public override void Open() => _realConnection.Open();

    public override Task OpenAsync(CancellationToken cancellationToken) => _realConnection.OpenAsync(cancellationToken);

    public override void Close() => _realConnection.Close();

    protected override DbTransaction BeginDbTransaction(IsolationLevel isolationLevel) => _realConnection.BeginTransaction(isolationLevel);

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _realConnection.Dispose();
        }
        base.Dispose(disposing);
    }

    public override ValueTask DisposeAsync()
    {
        return _realConnection.DisposeAsync();
    }
}
