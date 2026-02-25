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

	/// <summary>
	/// Configures the executor with query plan metadata for the next benchmark iteration.
	/// </summary>
	public void Configure(QueryOutputInfoHelper.QueryInfo queryInfo)
	{
		_estimatedRows = queryInfo.EstimatedRows;
		_outputColumns = queryInfo.OutputColumns;
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

	public virtual Task<DbDataReader> ExecuteReaderAsync(DbCommand command, CommandBehavior behavior, CancellationToken cancellationToken)
		=> Task.FromResult<DbDataReader>(BuildMockReader());

	private DataTableReader BuildMockReader()
	{
		if (_outputColumns.Count > 0)
		{
			return CreateReader(_outputColumns, _estimatedRows);
		}

		// Last resort: single column reader with a scalar value
		return CreateScalarReader(1.00m);
	}

	public void ConfigureExecutor(DbCommand command)
    {
        var sqlQuery = command.CommandText;
        var queryInfo = QueryOutputInfoHelper.AnalyzeSqlQuery(sqlQuery, command.Connection?.ConnectionString);
		Configure(queryInfo);
	}

	/// <summary>
	/// Builds a DataTable with the specified columns and row count, populated
	/// with default values, then returns its CreateDataReader().
	/// </summary>
	public static DataTableReader CreateReader(IReadOnlyList<QueryOutputInfoHelper.ColumnInfo> columns, int rowCount)
	{
		var table = new DataTable();
		foreach (var col in columns)
		{
			var clrType = col.ClrType == typeof(object) ? typeof(string) : col.ClrType;
			table.Columns.Add(col.Ordinal + "__" + col.Name, clrType);
		}

		for (int i = 0; i < rowCount; i++)
		{
			var row = table.NewRow();
			for (int c = 0; c < columns.Count; c++)
			{
				row[c] = QueryOutputInfoHelper.GetDefaultValue(columns[c].ClrType);
			}
			table.Rows.Add(row);
		}

		return table.CreateDataReader();
	}

	/// <summary>
	/// Creates a DataTableReader returning a single scalar result.
	/// </summary>
	public static DataTableReader CreateScalarReader(object value)
	{
		var table = new DataTable();
		table.Columns.Add("Value", value?.GetType() ?? typeof(object));
		var row = table.NewRow();
		row[0] = value ?? DBNull.Value;
		table.Rows.Add(row);
		return table.CreateDataReader();
	}
}
