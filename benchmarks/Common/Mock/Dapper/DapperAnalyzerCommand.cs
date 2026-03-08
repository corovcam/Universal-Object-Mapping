using System;
using System.Data;
using System.Data.Common;
using System.Threading;
using System.Threading.Tasks;

namespace Common.Mock.Dapper;

public class DapperAnalyzerCommand : DbCommand
{
    private readonly DbCommand _realCommand;
    private readonly BenchmarkCommandExecutor _commandExecutor;

    public DapperAnalyzerCommand(DbCommand realCommand, BenchmarkCommandExecutor? commandExecutor = null)
    {
        _realCommand = realCommand;
        _commandExecutor = commandExecutor ?? BenchmarkCommandExecutor.Instance;
    }

    protected override DbDataReader ExecuteDbDataReader(CommandBehavior behavior)
    {
        if (RecordQueryInfoScope.Current != null)
        {
            var info = QueryOutputInfoHelper.AnalyzeSqlCommand(_realCommand);
            RecordQueryInfoScope.Current.Record(info);
            return BenchmarkCommandExecutor.CreateReader(info, 1);
        }

        return _realCommand.ExecuteReader(behavior);
    }

    public override int ExecuteNonQuery()
    {
        if (RecordQueryInfoScope.Current != null)
        {
            var info = QueryOutputInfoHelper.AnalyzeSqlCommand(_realCommand);
            RecordQueryInfoScope.Current.Record(info);
            return _commandExecutor.ExecuteNonQuery(_realCommand);
        }

        return _realCommand.ExecuteNonQuery();
    }

    public override object? ExecuteScalar()
    {
        if (RecordQueryInfoScope.Current != null)
        {
            var info = QueryOutputInfoHelper.AnalyzeSqlCommand(_realCommand);
            RecordQueryInfoScope.Current.Record(info);
            return _commandExecutor.ExecuteScalar(_realCommand);
        }

        return _realCommand.ExecuteScalar();
    }

    protected override Task<DbDataReader> ExecuteDbDataReaderAsync(CommandBehavior behavior,
        CancellationToken cancellationToken)
    {
        if (RecordQueryInfoScope.Current != null)
        {
            var info = QueryOutputInfoHelper.AnalyzeSqlCommand(_realCommand);
            RecordQueryInfoScope.Current.Record(info);
            return Task.FromResult(BenchmarkCommandExecutor.CreateReader(info, 1));
        }

        return _realCommand.ExecuteReaderAsync(behavior, cancellationToken);
    }

    public override Task<int> ExecuteNonQueryAsync(CancellationToken cancellationToken)
    {
        if (RecordQueryInfoScope.Current != null)
        {
            var info = QueryOutputInfoHelper.AnalyzeSqlCommand(_realCommand);
            RecordQueryInfoScope.Current.Record(info);
            return _commandExecutor.ExecuteNonQueryAsync(_realCommand, cancellationToken);
        }

        return _realCommand.ExecuteNonQueryAsync(cancellationToken);
    }

    public override Task<object?> ExecuteScalarAsync(CancellationToken cancellationToken)
    {
        if (RecordQueryInfoScope.Current != null)
        {
            var info = QueryOutputInfoHelper.AnalyzeSqlCommand(_realCommand);
            RecordQueryInfoScope.Current.Record(info);
            return _commandExecutor.ExecuteScalarAsync(_realCommand, cancellationToken);
        }

        return _realCommand.ExecuteScalarAsync(cancellationToken);
    }

    public override void Prepare() => _realCommand.Prepare();

    public override void Cancel() => _realCommand.Cancel();

    public override string CommandText
    {
        get => _realCommand.CommandText;
        set => _realCommand.CommandText = value;
    }

    public override int CommandTimeout
    {
        get => _realCommand.CommandTimeout;
        set => _realCommand.CommandTimeout = value;
    }

    public override CommandType CommandType
    {
        get => _realCommand.CommandType;
        set => _realCommand.CommandType = value;
    }

    protected override DbParameter CreateDbParameter() => _realCommand.CreateParameter();

    protected override DbParameterCollection DbParameterCollection => _realCommand.Parameters;

    protected override DbConnection DbConnection
    {
        get => _realCommand.Connection;
        set => _realCommand.Connection = value;
    }

    protected override DbTransaction DbTransaction
    {
        get => _realCommand.Transaction;
        set => _realCommand.Transaction = value;
    }

    public override bool DesignTimeVisible
    {
        get => _realCommand.DesignTimeVisible;
        set => _realCommand.DesignTimeVisible = value;
    }

    public override UpdateRowSource UpdatedRowSource
    {
        get => _realCommand.UpdatedRowSource;
        set => _realCommand.UpdatedRowSource = value;
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _realCommand.Dispose();
        }

        base.Dispose(disposing);
    }

    public override ValueTask DisposeAsync()
    {
        return _realCommand.DisposeAsync();
    }
}
