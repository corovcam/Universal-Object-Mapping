using Microsoft.EntityFrameworkCore.SqlServer.Query.Internal;
using Microsoft.EntityFrameworkCore.Storage;
using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Common;
using System.Threading;
using System.Threading.Tasks;

namespace Common.Mock;

/// <summary>
/// A command executor that returns mock DataTableReader instances populated with
/// default values based on query plan metadata (estimated rows and column schema).
/// Designed for benchmarking ORM overhead without actual database round-trips.
/// </summary>
public class BenchmarkCommandExecutor
{
    private int _estimatedRows = 1;
    private List<QueryOutputInfoHelper.ColumnInfo> _outputColumns = [];
    private bool _useUniqueColumnNames = false;

    public static BenchmarkCommandExecutor Instance { get; } = new();

    private BenchmarkCommandExecutor()
    {
    }

    /// <summary>
    /// Configures the executor with query plan metadata for the next benchmark iteration.
    /// </summary>
    public void Configure(QueryOutputInfoHelper.QueryInfo queryInfo, bool useUniqueColumnNames = false)
    {
        _estimatedRows = queryInfo.EstimatedRows;
        _outputColumns = queryInfo.OutputColumns;
        _useUniqueColumnNames = useUniqueColumnNames;
    }

    public void UseUniqueColumnNames(bool useUniqueColumnNames)
    {
        _useUniqueColumnNames = useUniqueColumnNames;
    }

    public virtual int ExecuteNonQuery(DbCommand command)
        => -1;

    public virtual object ExecuteScalar(DbCommand command)
        => 1.00m;

    public virtual DbDataReader ExecuteReader(DbCommand command, CommandBehavior behavior)
        => BuildMockReader();

    public virtual Task<int> ExecuteNonQueryAsync(DbCommand command, CancellationToken cancellationToken)
        => Task.FromResult(-1);

    public virtual Task<object> ExecuteScalarAsync(DbCommand command, CancellationToken cancellationToken)
        => Task.FromResult<object>(1.00m);

    public virtual Task<DbDataReader> ExecuteReaderAsync(DbCommand command, CommandBehavior behavior,
        CancellationToken cancellationToken)
        => Task.FromResult<DbDataReader>(BuildMockReader());

    private DbDataReader BuildMockReader()
    {
        if (_outputColumns.Count > 0)
        {
            return CreateReader(_outputColumns, _estimatedRows, _useUniqueColumnNames);
        }

        // Last resort: single column reader with a scalar value
        return CreateScalarReader(1.00m);
    }

    /// <summary>
    /// Builds a BenchmarkDbDataReader populated with
    /// default values.
    /// </summary>
    public static DbDataReader CreateReader(IReadOnlyList<QueryOutputInfoHelper.ColumnInfo> columns, int rowCount,
        bool useUniqueColumnNames = false)
    {
        return new BenchmarkDbDataReader(columns, rowCount, useUniqueColumnNames);
    }

    /// <summary>
    /// Creates a BenchmarkDbDataReader returning a single scalar result.
    /// </summary>
    public static DbDataReader CreateScalarReader(object value)
    {
        return BenchmarkDbDataReader.CreateScalar(value);
    }
}
