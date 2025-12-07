using Model;

namespace AdvisorBenchmarking;

public interface IBenchmarkExecutor
{
    /// <summary>
    /// Executes the benchmark by actually running the query and measuring performance.
    /// </summary>
    BenchmarkMeasurement Execute(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString);

    /// <summary>
    /// Predicts the query cost by analyzing the execution plan without actually executing the query.
    /// This extracts the SQL from the ORM query and uses SET SHOWPLAN_XML to get the estimated cost.
    /// </summary>
    /// <param name="framework">The ORM framework to analyze.</param>
    /// <param name="sources">The conversion sources containing entity and query definitions.</param>
    /// <param name="connectionString">The database connection string.</param>
    /// <returns>The execution plan result with estimated costs.</returns>
    QueryExecutionPlanResult PredictCost(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString);

    /// <summary>
    /// Predicts costs for multiple frameworks and ranks them by estimated cost.
    /// </summary>
    /// <param name="frameworkSources">Dictionary mapping framework to its conversion sources.</param>
    /// <param name="connectionString">The database connection string.</param>
    /// <returns>List of execution plan results ordered by estimated cost (lowest first).</returns>
    IReadOnlyList<QueryExecutionPlanResult> PredictAndRankCosts(
        IReadOnlyDictionary<ORMEnum, IReadOnlyList<ConversionSource>> frameworkSources,
        string connectionString);
}
