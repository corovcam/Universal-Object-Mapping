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
        public bool IsGroupingQuery { get; init; }
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

        bool isGroupingQuery = sql.Contains("GROUP BY", StringComparison.OrdinalIgnoreCase) ||
                               sql.Contains("DISTINCT", StringComparison.OrdinalIgnoreCase);

        return new QueryInfo
        {
            Sql = sql,
            EstimatedRows = estimatedRows,
            OutputColumns = outputColumns,
            IsGroupingQuery = isGroupingQuery
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
                columns.Add(new ColumnInfo { Name = columnName, Ordinal = columnOrdinal, ClrType = clrType });
            }
        }

        return columns;
    }

    /// <summary>
    /// Generates a default constant value for the given CLR type.
    /// </summary>
    public static object GetDefaultValue(Type type, int rowIndex = 0, bool isGrouping = false)
    {
        if (type == typeof(int)) return isGrouping ? 1 + rowIndex : 1;
        if (type == typeof(long)) return isGrouping ? 1L + rowIndex : 1L;
        if (type == typeof(short)) return isGrouping ? (short)(1 + rowIndex) : (short)1;
        if (type == typeof(byte)) return isGrouping ? (byte)(1 + (rowIndex % 254)) : (byte)1;
        if (type == typeof(bool)) return isGrouping ? (rowIndex % 2 == 0) : false;
        if (type == typeof(decimal)) return isGrouping ? 1.00m + rowIndex : 1.00m;
        if (type == typeof(double)) return isGrouping ? 1.0d + rowIndex : 1.0d;
        if (type == typeof(float)) return isGrouping ? 1.0f + rowIndex : 1.0f;
        if (type == typeof(DateTime))
            return isGrouping ? new DateTime(2000, 1, 1).AddDays(rowIndex) : new DateTime(2000, 1, 1);
        if (type == typeof(DateOnly))
            return isGrouping ? new DateOnly(2000, 1, 1).AddDays(rowIndex) : new DateOnly(2000, 1, 1);
        if (type == typeof(TimeSpan)) return isGrouping ? TimeSpan.FromMinutes(rowIndex) : TimeSpan.Zero;
        if (type == typeof(DateTimeOffset))
            return isGrouping
                ? new DateTimeOffset(2000, 1, 1, 0, 0, 0, TimeSpan.Zero).AddDays(rowIndex)
                : new DateTimeOffset(2000, 1, 1, 0, 0, 0, TimeSpan.Zero);
        if (type == typeof(Guid)) return isGrouping ? Guid.NewGuid() : Guid.Empty;
        if (type == typeof(string)) return isGrouping ? $"\"{rowIndex}\"" : "null";
        if (type == typeof(byte[])) return isGrouping ? new byte[] { (byte)(rowIndex % 255) } : new byte[] { 0 };
        return isGrouping ? 1 + rowIndex : 1;
    }
}
