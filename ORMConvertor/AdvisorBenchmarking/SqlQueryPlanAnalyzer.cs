using System.Text.RegularExpressions;
using System.Xml.Linq;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Logging;
using Model;

namespace AdvisorBenchmarking;

/// <summary>
/// Analyzes SQL query execution plans using SQL Server's SET SHOWPLAN_XML functionality.
/// </summary>
public sealed class SqlQueryPlanAnalyzer : IQueryPlanAnalyzer
{
    private readonly ILogger<SqlQueryPlanAnalyzer>? _logger;

    public SqlQueryPlanAnalyzer(ILogger<SqlQueryPlanAnalyzer>? logger = null)
    {
        _logger = logger;
    }

    /// <inheritdoc />
    public string ExtractSqlQuery(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        return framework switch
        {
            ORMEnum.EFCore => EfCoreSqlExtractor.ExtractSql(sources, connectionString),
            ORMEnum.Dapper => DapperSqlExtractor.ExtractSql(sources, connectionString),
            ORMEnum.NHibernate => NHibernateSqlExtractor.ExtractSql(sources, connectionString),
            _ => throw new NotSupportedException($"SQL extraction for framework {framework} is not supported.")
        };
    }

    /// <inheritdoc />
    public QueryExecutionPlanResult AnalyzeExecutionPlan(
        ORMEnum framework,
        string sqlQuery,
        string connectionString)
    {
        if (string.IsNullOrWhiteSpace(sqlQuery))
        {
            return QueryExecutionPlanResult.Failure(framework, sqlQuery, "SQL query is empty or null.");
        }

        try
        {
            _logger?.LogDebug("Analyzing execution plan for {Framework}: {Query}", framework, TruncateQuery(sqlQuery));

            using var connection = new SqlConnection(connectionString);
            connection.Open();

            // Get the estimated execution plan without executing the query
            var planXml = GetEstimatedExecutionPlan(connection, sqlQuery);

            if (string.IsNullOrWhiteSpace(planXml))
            {
                return QueryExecutionPlanResult.Failure(framework, sqlQuery, "Failed to retrieve execution plan.");
            }

            // Parse the execution plan XML to extract cost information
            var (estimatedCost, estimatedRows, cpuCost, ioCost) = ParseExecutionPlanCosts(planXml);

            _logger?.LogInformation(
                "Execution plan analysis for {Framework}: EstimatedCost={Cost}, EstimatedRows={Rows}",
                framework, estimatedCost, estimatedRows);

            return QueryExecutionPlanResult.Success(
                framework,
                sqlQuery,
                planXml,
                estimatedCost,
                estimatedRows,
                cpuCost,
                ioCost);
        }
        catch (SqlException ex)
        {
            _logger?.LogError(ex, "SQL error analyzing execution plan for {Framework}", framework);
            return QueryExecutionPlanResult.Failure(framework, sqlQuery, $"SQL error: {ex.Message}");
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Error analyzing execution plan for {Framework}", framework);
            return QueryExecutionPlanResult.Failure(framework, sqlQuery, ex.Message);
        }
    }

    /// <inheritdoc />
    public QueryExecutionPlanResult ExtractAndAnalyze(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        try
        {
            var sqlQuery = ExtractSqlQuery(framework, sources, connectionString);
            return AnalyzeExecutionPlan(framework, sqlQuery, connectionString);
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Failed to extract and analyze SQL for {Framework}", framework);
            return QueryExecutionPlanResult.Failure(framework, string.Empty, ex.Message);
        }
    }

    /// <summary>
    /// Gets the estimated execution plan XML using SET SHOWPLAN_XML ON.
    /// This returns the plan without actually executing the query.
    /// </summary>
    private static string GetEstimatedExecutionPlan(SqlConnection connection, string sqlQuery)
    {
        // Enable SHOWPLAN_XML to get the estimated execution plan
        using (var enableCommand = connection.CreateCommand())
        {
            enableCommand.CommandText = "SET SHOWPLAN_XML ON";
            enableCommand.ExecuteNonQuery();
        }

        string planXml;
        try
        {
            using var queryCommand = connection.CreateCommand();
            queryCommand.CommandText = sqlQuery;

            // ExecuteReader returns the execution plan as XML, not the actual results
            using var reader = queryCommand.ExecuteReader();
            if (reader.Read())
            {
                planXml = reader.GetString(0);
            }
            else
            {
                planXml = string.Empty;
            }
        }
        finally
        {
            // Always disable SHOWPLAN_XML
            using var disableCommand = connection.CreateCommand();
            disableCommand.CommandText = "SET SHOWPLAN_XML OFF";
            disableCommand.ExecuteNonQuery();
        }

        return planXml;
    }

    /// <summary>
    /// Parses the SQL Server execution plan XML to extract cost metrics.
    /// </summary>
    private static (double EstimatedCost, double EstimatedRows, double CpuCost, double IoCost) ParseExecutionPlanCosts(string planXml)
    {
        try
        {
            var doc = XDocument.Parse(planXml);
            var ns = doc.Root?.GetDefaultNamespace() ?? XNamespace.None;

            // Find the top-level statement which contains the total estimated cost
            var stmtSimple = doc.Descendants(ns + "StmtSimple").FirstOrDefault();
            
            double statementSubTreeCost = 0;
            double statementEstRows = 0;

            if (stmtSimple != null)
            {
                var costAttr = stmtSimple.Attribute("StatementSubTreeCost");
                if (costAttr != null && double.TryParse(costAttr.Value, out var cost))
                {
                    statementSubTreeCost = cost;
                }

                var rowsAttr = stmtSimple.Attribute("StatementEstRows");
                if (rowsAttr != null && double.TryParse(rowsAttr.Value, out var rows))
                {
                    statementEstRows = rows;
                }
            }

            // Sum up CPU and I/O costs from all RelOp elements
            double totalCpuCost = 0;
            double totalIoCost = 0;

            foreach (var relOp in doc.Descendants(ns + "RelOp"))
            {
                var cpuAttr = relOp.Attribute("EstimateCPU");
                if (cpuAttr != null && double.TryParse(cpuAttr.Value, out var cpu))
                {
                    totalCpuCost += cpu;
                }

                var ioAttr = relOp.Attribute("EstimateIO");
                if (ioAttr != null && double.TryParse(ioAttr.Value, out var io))
                {
                    totalIoCost += io;
                }
            }

            return (statementSubTreeCost, statementEstRows, totalCpuCost, totalIoCost);
        }
        catch
        {
            // If XML parsing fails, return zeros
            return (0, 0, 0, 0);
        }
    }

    private static string TruncateQuery(string query, int maxLength = 200)
    {
        if (string.IsNullOrEmpty(query) || query.Length <= maxLength)
        {
            return query;
        }

        return query[..maxLength] + "...";
    }
}

/// <summary>
/// Extracts SQL queries from EF Core LINQ expressions.
/// </summary>
internal static class EfCoreSqlExtractor
{
    public static string ExtractSql(IReadOnlyList<ConversionSource> sources, string connectionString)
    {
        var querySource = sources
            .FirstOrDefault(s => s.ContentType == ConversionContentType.CSharpQuery)?.Content
            ?? throw new InvalidOperationException("EF Core requires a query definition to extract SQL.");

        // Look for raw SQL or FromSqlRaw patterns first
        var rawSqlMatch = Regex.Match(querySource, @"FromSqlRaw\s*\(\s*@?""([^""]+)""", RegexOptions.Singleline);
        if (rawSqlMatch.Success)
        {
            return rawSqlMatch.Groups[1].Value;
        }

        // For LINQ queries, we need to analyze the expression
        // This extracts a basic SELECT pattern from the LINQ structure
        return BuildSqlFromLinqPattern(querySource, sources, connectionString);
    }

    private static string BuildSqlFromLinqPattern(
        string querySource,
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        var entityInfos = HarnessGenerationUtilities.ExtractEntityInfos(sources, connectionString);

        // Extract the table name from entity definitions
        var primaryEntity = entityInfos.FirstOrDefault();
        var tableName = primaryEntity?.TableName ?? "UnknownTable";

        // Parse the LINQ query to identify:
        // - Where clauses
        // - Select projections
        // - OrderBy clauses
        // - Take/Skip (TOP/OFFSET)

        var whereConditions = ExtractWhereConditions(querySource);
        var selectColumns = ExtractSelectColumns(querySource);
        var orderBy = ExtractOrderBy(querySource);
        var topN = ExtractTopN(querySource);

        // Build the SQL query
        var sql = new System.Text.StringBuilder();
        sql.Append("SELECT ");

        if (topN.HasValue)
        {
            sql.Append($"TOP ({topN.Value}) ");
        }

        sql.Append(string.IsNullOrEmpty(selectColumns) ? "*" : selectColumns);
        sql.Append($" FROM [{tableName.Replace(".", "].[")}]");

        if (!string.IsNullOrEmpty(whereConditions))
        {
            sql.Append($" WHERE {whereConditions}");
        }

        if (!string.IsNullOrEmpty(orderBy))
        {
            sql.Append($" ORDER BY {orderBy}");
        }

        return sql.ToString();
    }

    private static string ExtractWhereConditions(string querySource)
    {
        // Extract conditions from .Where() calls
        var whereMatch = Regex.Match(querySource, @"\.Where\s*\(\s*\w+\s*=>\s*([^)]+)\)", RegexOptions.Singleline);
        if (!whereMatch.Success) return string.Empty;

        var condition = whereMatch.Groups[1].Value.Trim();
        // Convert C# operators to SQL
        condition = Regex.Replace(condition, @"(\w+)\.(\w+)\s*==\s*""([^""]+)""", "[$2] = '$3'");
        condition = Regex.Replace(condition, @"(\w+)\.(\w+)\s*==\s*(\d+)", "[$2] = $3");
        condition = Regex.Replace(condition, @"&&", "AND");
        condition = Regex.Replace(condition, @"\|\|", "OR");

        return condition;
    }

    private static string ExtractSelectColumns(string querySource)
    {
        // Extract projection from .Select() calls
        var selectMatch = Regex.Match(querySource, @"\.Select\s*\(\s*\w+\s*=>\s*(?:new\s*\{([^}]+)\}|(\w+\.\w+))", RegexOptions.Singleline);
        if (!selectMatch.Success) return string.Empty;

        var projection = selectMatch.Groups[1].Success ? selectMatch.Groups[1].Value : selectMatch.Groups[2].Value;
        // Convert property access to column names
        projection = Regex.Replace(projection, @"\w+\.(\w+)", "[$1]");
        projection = Regex.Replace(projection, @"(\w+)\s*=\s*\[(\w+)\]", "[$2] AS [$1]");

        return projection.Trim();
    }

    private static string ExtractOrderBy(string querySource)
    {
        var orderMatch = Regex.Match(querySource, @"\.OrderBy(?:Descending)?\s*\(\s*\w+\s*=>\s*\w+\.(\w+)\)", RegexOptions.Singleline);
        if (!orderMatch.Success) return string.Empty;

        var direction = querySource.Contains("OrderByDescending") ? " DESC" : " ASC";
        return $"[{orderMatch.Groups[1].Value}]{direction}";
    }

    private static int? ExtractTopN(string querySource)
    {
        var takeMatch = Regex.Match(querySource, @"\.Take\s*\(\s*(\d+)\s*\)");
        if (takeMatch.Success && int.TryParse(takeMatch.Groups[1].Value, out var n))
        {
            return n;
        }
        return null;
    }
}

/// <summary>
/// Extracts SQL queries from Dapper method calls.
/// </summary>
internal static class DapperSqlExtractor
{
    public static string ExtractSql(IReadOnlyList<ConversionSource> sources, string connectionString)
    {
        var querySource = sources
            .FirstOrDefault(s => s.ContentType == ConversionContentType.CSharpQuery)?.Content
            ?? throw new InvalidOperationException("Dapper requires a query definition to extract SQL.");

        // Dapper typically uses raw SQL strings directly
        // Look for triple-quoted strings first (raw string literals)
        var rawStringMatch = Regex.Match(querySource, "\"\"\"(?<sql>.*?)\"\"\"", RegexOptions.Singleline);
        if (rawStringMatch.Success)
        {
            return CleanSqlQuery(rawStringMatch.Groups["sql"].Value);
        }

        // Look for regular string literals
        var stringMatch = Regex.Match(querySource, @"@?""([^""\\]*(\\.[^""\\]*)*)""", RegexOptions.Singleline);
        if (stringMatch.Success)
        {
            var sql = stringMatch.Groups[1].Value;
            // Check if it looks like SQL
            if (LooksLikeSql(sql))
            {
                return CleanSqlQuery(sql);
            }
        }

        // Look for Query<T> or Execute patterns
        var queryMatch = Regex.Match(querySource, @"\.Query(?:<[^>]+>)?\s*\(\s*@?""([^""]+)""", RegexOptions.Singleline);
        if (queryMatch.Success)
        {
            return CleanSqlQuery(queryMatch.Groups[1].Value);
        }

        throw new InvalidOperationException("Could not extract SQL query from Dapper source.");
    }

    private static string CleanSqlQuery(string sql)
    {
        // Remove C# numeric suffixes that might have been left in
        sql = Regex.Replace(sql, @"(?<=\b\d+(?:\.\d+)?)[mMdDfF]\b", string.Empty);
        return sql.Trim();
    }

    private static bool LooksLikeSql(string text)
    {
        var upper = text.ToUpperInvariant();
        return upper.Contains("SELECT") || upper.Contains("INSERT") ||
               upper.Contains("UPDATE") || upper.Contains("DELETE") ||
               upper.Contains("FROM");
    }
}

/// <summary>
/// Extracts SQL queries from NHibernate HQL or Criteria queries.
/// </summary>
internal static class NHibernateSqlExtractor
{
    public static string ExtractSql(IReadOnlyList<ConversionSource> sources, string connectionString)
    {
        var querySource = sources
            .FirstOrDefault(s => s.ContentType == ConversionContentType.CSharpQuery)?.Content
            ?? throw new InvalidOperationException("NHibernate requires a query definition to extract SQL.");

        // Look for CreateSQLQuery (raw SQL)
        var sqlQueryMatch = Regex.Match(querySource, @"CreateSQLQuery\s*\(\s*@?""([^""]+)""", RegexOptions.Singleline);
        if (sqlQueryMatch.Success)
        {
            return sqlQueryMatch.Groups[1].Value.Trim();
        }

        // Look for HQL queries in CreateQuery
        var hqlMatch = Regex.Match(querySource, @"CreateQuery\s*\(\s*@?""([^""]+)""", RegexOptions.Singleline);
        if (hqlMatch.Success)
        {
            return ConvertHqlToSql(hqlMatch.Groups[1].Value, sources, connectionString);
        }

        // Look for QueryOver or Criteria patterns - these are more complex
        // For now, build a basic SELECT based on entity information
        return BuildSqlFromCriteria(querySource, sources, connectionString);
    }

    private static string ConvertHqlToSql(
        string hql,
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        var entityInfos = HarnessGenerationUtilities.ExtractEntityInfos(sources, connectionString);

        // Basic HQL to SQL conversion
        var sql = hql;

        // Replace entity names with table names
        foreach (var entity in entityInfos)
        {
            if (!string.IsNullOrEmpty(entity.TypeName))
            {
                sql = Regex.Replace(sql, $@"\b{entity.TypeName}\b", $"[{entity.TableName}]", RegexOptions.IgnoreCase);
            }
        }

        // Convert HQL keywords to SQL
        sql = Regex.Replace(sql, @"\bfrom\b", "FROM", RegexOptions.IgnoreCase);
        sql = Regex.Replace(sql, @"\bwhere\b", "WHERE", RegexOptions.IgnoreCase);
        sql = Regex.Replace(sql, @"\bselect\b", "SELECT", RegexOptions.IgnoreCase);
        sql = Regex.Replace(sql, @"\border\s+by\b", "ORDER BY", RegexOptions.IgnoreCase);

        // If no SELECT, add SELECT *
        if (!sql.TrimStart().StartsWith("SELECT", StringComparison.OrdinalIgnoreCase))
        {
            sql = "SELECT * " + sql;
        }

        return sql.Trim();
    }

    private static string BuildSqlFromCriteria(
        string querySource,
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        var entityInfos = HarnessGenerationUtilities.ExtractEntityInfos(sources, connectionString);
        var primaryEntity = entityInfos.FirstOrDefault();
        var tableName = primaryEntity?.TableName ?? "UnknownTable";

        // Extract basic patterns from Criteria/QueryOver
        var sql = new System.Text.StringBuilder();
        sql.Append("SELECT * FROM ");
        sql.Append($"[{tableName.Replace(".", "].[")}]");

        // Look for restriction patterns
        var whereConditions = new List<string>();

        // Eq restrictions
        var eqMatches = Regex.Matches(querySource, @"\.Add\s*\(\s*Restrictions\.Eq\s*\(\s*""(\w+)""\s*,\s*(?:""([^""]+)""|(\d+))\s*\)\s*\)");
        foreach (Match match in eqMatches)
        {
            var column = match.Groups[1].Value;
            var strValue = match.Groups[2].Value;
            var numValue = match.Groups[3].Value;

            if (!string.IsNullOrEmpty(strValue))
            {
                whereConditions.Add($"[{column}] = '{strValue}'");
            }
            else if (!string.IsNullOrEmpty(numValue))
            {
                whereConditions.Add($"[{column}] = {numValue}");
            }
        }

        if (whereConditions.Count > 0)
        {
            sql.Append(" WHERE ");
            sql.Append(string.Join(" AND ", whereConditions));
        }

        return sql.ToString();
    }
}
