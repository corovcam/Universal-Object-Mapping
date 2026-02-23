using Microsoft.EntityFrameworkCore.SqlServer.Query.Internal;
using Microsoft.EntityFrameworkCore.Storage;
using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Common;
using System.Threading;
using System.Threading.Tasks;

namespace Common.mock;

/// <summary>
/// A command executor that returns mock DataTableReader instances populated with
/// default values based on query plan metadata (estimated rows and column schema).
/// Designed for benchmarking ORM overhead without actual database round-trips.
/// </summary>
public class BenchmarkCommandExecutor
{
	private int _estimatedRows = 1;
	private List<QueryPlanHelper.ColumnInfo> _outputColumns = [];
	private ITypeMappingSource _typeMapper;

	/// <summary>
	/// Configures the executor with query plan metadata for the next benchmark iteration.
	/// </summary>
	public void Configure(QueryPlanHelper.QueryPlanInfo planInfo)
	{
		_estimatedRows = planInfo.EstimatedRows;
		_outputColumns = planInfo.OutputColumns;
	}

	public void ConfigureTypeMappingSource(ITypeMappingSource typeMapper)
	{
		_typeMapper = typeMapper;
	}

	public virtual int ExecuteNonQuery(DbCommand command)
		=> -1;

	public virtual object ExecuteScalar(DbCommand command)
		=> 1.00m;

	public virtual DbDataReader ExecuteReader(DbCommand command, CommandBehavior behavior)
		=> BuildMockReader(command);

	public virtual Task<int> ExecuteNonQueryAsync(DbCommand command, CancellationToken cancellationToken)
		=> Task.FromResult(-1);

	public virtual Task<object> ExecuteScalarAsync(DbCommand command, CancellationToken cancellationToken)
		=> Task.FromResult<object>(1.00m);

	public virtual Task<DbDataReader> ExecuteReaderAsync(DbCommand command, CommandBehavior behavior, CancellationToken cancellationToken)
		=> Task.FromResult<DbDataReader>(BuildMockReader(command));

	private DataTableReader BuildMockReader(DbCommand command)
	{
		ConfigureExecutor(command);
		if (_outputColumns.Count > 0)
		{
			return CreateReader(_outputColumns, _estimatedRows);
		}

		// Last resort: single column reader with a scalar value
		return CreateScalarReader(1.00m);
	}

	private void ConfigureExecutor(DbCommand command)
    {
        var sqlQuery = command.CommandText;
        if (sqlQuery == "")
        {
            var queryStringFactory = new SqlServerQueryStringFactory((IRelationalTypeMappingSource)_typeMapper);
            sqlQuery = queryStringFactory.Create(command);
        }
        var queryInfo = QueryPlanHelper.AnalyzeSqlQuery(sqlQuery, command.Connection?.ConnectionString);
		Configure(queryInfo);
	}

	/// <summary>
	/// Builds a DataTable with the specified columns and row count, populated
	/// with default values, then returns its CreateDataReader().
	/// </summary>
	public static DataTableReader CreateReader(IReadOnlyList<QueryPlanHelper.ColumnInfo> columns, int rowCount)
	{
		var table = new DataTable();
		foreach (var col in columns)
		{
			var clrType = col.ClrType == typeof(object) ? typeof(string) : col.ClrType;
			table.Columns.Add(col.Name, clrType);
		}

		for (int i = 0; i < rowCount; i++)
		{
			var row = table.NewRow();
			for (int c = 0; c < columns.Count; c++)
			{
				row[c] = QueryPlanHelper.GetDefaultValue(columns[c].ClrType);
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
