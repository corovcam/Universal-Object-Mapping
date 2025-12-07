namespace AdvisorBenchmarking;

/// <summary>
/// Represents the results of a benchmark measurement including both actual execution metrics
/// and predicted costs from query execution plan analysis.
/// </summary>
public sealed record BenchmarkMeasurement
{
    /// <summary>
    /// Mean duration in milliseconds from actual execution.
    /// </summary>
    public double MeanDurationMilliseconds { get; init; }

    /// <summary>
    /// Allocated bytes per operation from actual execution.
    /// </summary>
    public long AllocatedBytes { get; init; }

    /// <summary>
    /// Estimated cost from query execution plan analysis.
    /// Lower values indicate more efficient queries.
    /// This is the predicted cost without actually executing the query.
    /// </summary>
    public double? PredictedCost { get; init; }

    /// <summary>
    /// Estimated row count from query execution plan.
    /// </summary>
    public double? PredictedRows { get; init; }

    /// <summary>
    /// Indicates whether predicted cost analysis was successful.
    /// </summary>
    public bool HasPredictedCost => PredictedCost.HasValue;

    /// <summary>
    /// Creates a measurement from actual execution only.
    /// </summary>
    public BenchmarkMeasurement(double meanDurationMilliseconds, long allocatedBytes)
    {
        MeanDurationMilliseconds = meanDurationMilliseconds;
        AllocatedBytes = allocatedBytes;
    }

    /// <summary>
    /// Creates a measurement with both actual execution and predicted costs.
    /// </summary>
    public BenchmarkMeasurement(
        double meanDurationMilliseconds,
        long allocatedBytes,
        double? predictedCost,
        double? predictedRows = null)
    {
        MeanDurationMilliseconds = meanDurationMilliseconds;
        AllocatedBytes = allocatedBytes;
        PredictedCost = predictedCost;
        PredictedRows = predictedRows;
    }

    /// <summary>
    /// Creates a measurement from predicted costs only (no actual execution).
    /// </summary>
    public static BenchmarkMeasurement FromPrediction(double predictedCost, double predictedRows = 0)
    {
        return new BenchmarkMeasurement(0, 0, predictedCost, predictedRows);
    }
}
