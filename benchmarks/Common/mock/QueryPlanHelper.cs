using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Common;
using System.Globalization;
using System.Linq;
using System.Xml.Linq;

namespace Common.mock;

public static class QueryPlanHelper
{
	private static readonly XNamespace ShowPlanNs = "http://schemas.microsoft.com/sqlserver/2004/07/showplan";

	/// <summary>
	/// Holds the query plan analysis result.
	/// </summary>
	public sealed class QueryPlanInfo
	{
		public string Sql { get; init; } = "";
		public int EstimatedRows { get; init; }
		public List<ColumnInfo> OutputColumns { get; init; } = [];
	}

	public sealed class ColumnInfo
	{
		public string Name { get; init; } = "";
		public Type ClrType { get; init; } = typeof(object);
	}

	public static QueryPlanInfo GetQueryOutputInfo(IQueryable query, string connectionString)
	{
		var sql = query.ToQueryString();
		return AnalyzeSqlQuery(sql, connectionString);
	}

	
	public static QueryPlanInfo AnalyzeSqlQuery(string sql, string? connectionString = null, SqlConnection? sqlConnection = null)
	{
		var connection = sqlConnection ?? new SqlConnection(connectionString);
		if (connection.State != ConnectionState.Open)
			connection.Open();

		string planXml = GetShowPlanXml(sql, connection);
		int estimatedRows = ParsePlan(planXml);
		List<ColumnInfo> outputColumns = GetOutputColumnsInfo(sql, connection);

		return new QueryPlanInfo
		{
			Sql = sql,
			EstimatedRows = estimatedRows,
			OutputColumns = outputColumns
		};
	}

	/// <summary>
	/// Given raw SQL, obtains the SHOWPLAN_XML from SQL Server.
	/// </summary>
	private static string GetShowPlanXml(string sql, DbConnection connection)
	{
		// Enable SHOWPLAN_XML (this returns the plan without executing)
		using (var enableCmd = connection.CreateCommand())
		{
			enableCmd.CommandText = "SET SHOWPLAN_XML ON";
			enableCmd.ExecuteNonQuery();
		}

		string planXml;
		using (var queryCmd = connection.CreateCommand())
		{
			queryCmd.CommandText = sql;
			// SHOWPLAN_XML returns the plan as a single-row, single-column result
			planXml = (string)queryCmd.ExecuteScalar();
		}

		// Disable SHOWPLAN_XML
		using (var disableCmd = connection.CreateCommand())
		{
			disableCmd.CommandText = "SET SHOWPLAN_XML OFF";
			disableCmd.ExecuteNonQuery();
		}

		return planXml;
	}

	private static int ParsePlan(string planXml)
	{
		var doc = XDocument.Parse(planXml);

		// Find the top-level StmtSimple (the actual SELECT statement)
		var statement = doc.Descendants(ShowPlanNs + "StmtSimple")
			.FirstOrDefault(e => e.Attribute("StatementType")?.Value == "SELECT");

		int estimatedRows = 1;
		if (statement != null)
		{
			var estRowsAttr = statement.Attribute("StatementEstRows");
			if (estRowsAttr != null && double.TryParse(estRowsAttr.Value, NumberStyles.Float,
					CultureInfo.InvariantCulture, out var estRows))
			{
				estimatedRows = Math.Max(1, (int)Math.Ceiling(estRows));
			}
		}

		return estimatedRows;
	}

	private static List<ColumnInfo> GetOutputColumnsInfo(string sql, DbConnection connection)
	{
		var columns = new List<ColumnInfo>();
		using (var cmd = connection.CreateCommand())
		{
			cmd.CommandText = sql;
			using var reader = cmd.ExecuteReader(CommandBehavior.SchemaOnly);
			var schemaTable = reader.GetSchemaTable();
			if (schemaTable != null)
			{
				foreach (DataRow row in schemaTable.Rows)
				{
					string columnName = row["ColumnName"] as string ?? "";
					Type clrType = row["DataType"] as Type ?? typeof(object);
					//if (clrType == typeof(DateTime))
					//{
					//	// Map DateTime to DateOnly for better compatibility with EF Core's type mapping
					//	clrType = typeof(DateOnly);
					//}
					columns.Add(new ColumnInfo
					{
						Name = columnName,
						ClrType = clrType
					});
				}
			}
		}
		return columns;
	}

	/// <summary>
	/// Generates a default constant value for the given CLR type.
	/// </summary>
	public static object GetDefaultValue(Type type)
	{
		if (type == typeof(int)) return 1;
		if (type == typeof(long)) return 1L;
		if (type == typeof(short)) return (short)1;
		if (type == typeof(byte)) return (byte)1;
		if (type == typeof(bool)) return false;
		if (type == typeof(decimal)) return 1.00m;
		if (type == typeof(double)) return 1.0d;
		if (type == typeof(float)) return 1.0f;
		if (type == typeof(DateTime)) return new DateTime(2000, 1, 1);
		if (type == typeof(DateOnly)) return new DateOnly(2000, 1, 1);
		if (type == typeof(TimeSpan)) return TimeSpan.Zero;
		if (type == typeof(DateTimeOffset)) return new DateTimeOffset(2000, 1, 1, 0, 0, 0, TimeSpan.Zero);
		if (type == typeof(Guid)) return Guid.Empty;
		if (type == typeof(string)) return "A";
		if (type == typeof(byte[])) return new byte[] { 0 };
		return 1;
	}
}
