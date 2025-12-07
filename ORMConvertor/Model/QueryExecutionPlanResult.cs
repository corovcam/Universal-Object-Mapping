namespace Model;

/// <summary>
/// Represents the result of analyzing a query execution plan without actually executing the query.
/// </summary>
public sealed record QueryExecutionPlanResult
{
    /// <summary>
    /// The ORM framework that generated this query.
    /// </summary>
    public required ORMEnum Framework { get; init; }

    /// <summary>
    /// The SQL query string extracted from the ORM.
    /// </summary>
    public required string SqlQuery { get; init; }

    /// <summary>
    /// The raw execution plan XML or text from the database engine.
    /// </summary>
    public string? ExecutionPlanXml { get; init; }

    /// <summary>
    /// The estimated subtree cost from the query execution plan.
    /// Lower values indicate more efficient queries.
    /// </summary>
    public double EstimatedCost { get; init; }

    /// <summary>
    /// The estimated number of rows that will be processed.
    /// </summary>
    public double EstimatedRows { get; init; }

    /// <summary>
    /// The estimated CPU cost from the execution plan.
    /// </summary>
    public double EstimatedCpuCost { get; init; }

    /// <summary>
    /// The estimated I/O cost from the execution plan.
    /// </summary>
    public double EstimatedIoCost { get; init; }

    /// <summary>
    /// Indicates whether the plan analysis was successful.
    /// </summary>
    public bool IsSuccess { get; init; }

    /// <summary>
    /// Error message if the plan analysis failed.
    /// </summary>
    public string? ErrorMessage { get; init; }

    /// <summary>
    /// Creates a successful result with the given parameters.
    /// </summary>
    public static QueryExecutionPlanResult Success(
        ORMEnum framework,
        string sqlQuery,
        string? executionPlanXml,
        double estimatedCost,
        double estimatedRows = 0,
        double estimatedCpuCost = 0,
        double estimatedIoCost = 0)
    {
        return new QueryExecutionPlanResult
        {
            Framework = framework,
            SqlQuery = sqlQuery,
            ExecutionPlanXml = executionPlanXml,
            EstimatedCost = estimatedCost,
            EstimatedRows = estimatedRows,
            EstimatedCpuCost = estimatedCpuCost,
            EstimatedIoCost = estimatedIoCost,
            IsSuccess = true
        };
    }

    /// <summary>
    /// Creates a failed result with the given error message.
    /// </summary>
    public static QueryExecutionPlanResult Failure(
        ORMEnum framework,
        string sqlQuery,
        string errorMessage)
    {
        return new QueryExecutionPlanResult
        {
            Framework = framework,
            SqlQuery = sqlQuery,
            EstimatedCost = double.MaxValue,
            IsSuccess = false,
            ErrorMessage = errorMessage
        };
    }
}
