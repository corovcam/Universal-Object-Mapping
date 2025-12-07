using Model;

namespace AdvisorBenchmarking;

/// <summary>
/// Interface for executing query plan analysis across different ORM frameworks.
/// </summary>
public interface IQueryPlanExecutor
{
    /// <summary>
    /// Extracts SQL from the given ORM sources and analyzes the execution plan.
    /// </summary>
    /// <param name="framework">The ORM framework to analyze.</param>
    /// <param name="sources">The conversion sources containing entity and query definitions.</param>
    /// <param name="connectionString">The database connection string.</param>
    /// <returns>The execution plan analysis result with estimated costs.</returns>
    QueryExecutionPlanResult ExtractAndAnalyzePlan(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString);

    /// <summary>
    /// Analyzes execution plans for multiple frameworks and returns all results.
    /// </summary>
    /// <param name="frameworkSources">Dictionary mapping framework to its conversion sources.</param>
    /// <param name="connectionString">The database connection string.</param>
    /// <returns>List of execution plan results for each framework.</returns>
    IReadOnlyList<QueryExecutionPlanResult> AnalyzeAllFrameworks(
        IReadOnlyDictionary<ORMEnum, IReadOnlyList<ConversionSource>> frameworkSources,
        string connectionString);

    /// <summary>
    /// Ranks execution plan results by estimated cost (lowest first).
    /// </summary>
    /// <param name="results">The execution plan results to rank.</param>
    /// <returns>Results ordered by estimated cost, excluding failed analyses.</returns>
    IReadOnlyList<QueryExecutionPlanResult> RankByEstimatedCost(
        IReadOnlyList<QueryExecutionPlanResult> results);

    /// <summary>
    /// Gets the framework with the lowest estimated execution cost.
    /// </summary>
    /// <param name="results">The execution plan results to evaluate.</param>
    /// <returns>The best framework, or null if no successful results exist.</returns>
    ORMEnum? GetBestFramework(IReadOnlyList<QueryExecutionPlanResult> results);
}
