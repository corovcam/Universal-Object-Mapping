using Model;

namespace AdvisorBenchmarking;

/// <summary>
/// Interface for analyzing query execution plans from different ORM frameworks.
/// </summary>
public interface IQueryPlanAnalyzer
{
    /// <summary>
    /// Extracts the SQL query from ORM-specific source code without executing it.
    /// </summary>
    /// <param name="framework">The ORM framework being analyzed.</param>
    /// <param name="sources">The conversion sources containing entity and query definitions.</param>
    /// <param name="connectionString">The database connection string.</param>
    /// <returns>The extracted SQL query string.</returns>
    string ExtractSqlQuery(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString);

    /// <summary>
    /// Analyzes the execution plan for a given SQL query and returns the estimated cost.
    /// </summary>
    /// <param name="framework">The ORM framework that generated the query.</param>
    /// <param name="sqlQuery">The SQL query to analyze.</param>
    /// <param name="connectionString">The database connection string.</param>
    /// <returns>The execution plan analysis result with estimated costs.</returns>
    QueryExecutionPlanResult AnalyzeExecutionPlan(
        ORMEnum framework,
        string sqlQuery,
        string connectionString);

    /// <summary>
    /// Extracts SQL and analyzes execution plan in a single operation.
    /// </summary>
    /// <param name="framework">The ORM framework being analyzed.</param>
    /// <param name="sources">The conversion sources containing entity and query definitions.</param>
    /// <param name="connectionString">The database connection string.</param>
    /// <returns>The execution plan analysis result with estimated costs.</returns>
    QueryExecutionPlanResult ExtractAndAnalyze(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString);
}
