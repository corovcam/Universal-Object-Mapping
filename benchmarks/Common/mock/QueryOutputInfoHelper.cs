using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.Data;
using System.Data.Common;
using System.Globalization;
using System.Linq;
using System.Xml.Linq;

namespace Common.Mock;

public static class QueryOutputInfoHelper
{
	private static readonly XNamespace ShowPlanNs = "http://schemas.microsoft.com/sqlserver/2004/07/showplan";

	/// <summary>
	/// Holds the query plan analysis result.
	/// </summary>
	public sealed class QueryInfo
	{
		public string Sql { get; init; } = "";
		public int EstimatedRows { get; init; }
		public List<ColumnInfo> OutputColumns { get; init; } = [];
	}

	public sealed class ColumnInfo
	{
		public string Name { get; init; } = "";
        public int Ordinal { get; init; }
        public Type ClrType { get; init; } = typeof(object);
	}

	public static QueryInfo AnalyzeSqlCommand(DbCommand command)
	{
		var connection = command.Connection;
        if (connection == null) return new QueryInfo { Sql = command.ToQueryString() };

        bool wasClosed = connection.State == ConnectionState.Closed;
		if (wasClosed) connection.Open();

		string sql = command.ToQueryString();
		string planXml = GetShowPlanXml(command);
		int estimatedRows = ParsePlan(planXml);
		List<ColumnInfo> outputColumns = GetOutputColumnsInfo(command);

        if (wasClosed) connection.Close();

		return new QueryInfo
		{
			Sql = sql,
			EstimatedRows = estimatedRows,
			OutputColumns = outputColumns
		};
	}

	/// <summary>
	/// Given a command, obtains the SHOWPLAN_XML from SQL Server.
	/// </summary>
	private static string GetShowPlanXml(DbCommand command)
	{
		using (var enableCmd = command.Connection!.CreateCommand())
		{
            if (command.Transaction != null) enableCmd.Transaction = command.Transaction;
			enableCmd.CommandText = "SET SHOWPLAN_XML ON";
			enableCmd.ExecuteNonQuery();
		}

		string planXml = (string)(command.ExecuteScalar() ?? "");

		// Disable SHOWPLAN_XML
		using (var disableCmd = command.Connection.CreateCommand())
		{
            if (command.Transaction != null) disableCmd.Transaction = command.Transaction;
			disableCmd.CommandText = "SET SHOWPLAN_XML OFF";
			disableCmd.ExecuteNonQuery();
		}

		return planXml;
	}

	private static int ParsePlan(string planXml)
	{
        if (string.IsNullOrWhiteSpace(planXml)) return 1;

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

	private static List<ColumnInfo> GetOutputColumnsInfo(DbCommand command)
	{
		var columns = new List<ColumnInfo>();
        using var reader = command.ExecuteReader(CommandBehavior.SchemaOnly);
        var schemaTable = reader.GetSchemaTable();
        if (schemaTable != null)
        {
            foreach (DataRow row in schemaTable.Rows)
            {
                string columnName = row["ColumnName"] as string ?? "";
                int columnOrdinal = (int)row["ColumnOrdinal"];
                Type clrType = row["DataType"] as Type ?? typeof(object);
				//if (clrType == typeof(DateTime))
				//{
				//	// Map DateTime to DateOnly for better compatibility with EF Core's type mapping
				//	clrType = typeof(DateOnly);
				//}
                columns.Add(new ColumnInfo
                {
                    Name = columnName,
                    Ordinal = columnOrdinal,
                    ClrType = clrType
                });
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
