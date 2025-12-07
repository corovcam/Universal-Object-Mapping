using Model;

namespace ORMConvertorAPI.Dtos.Advisor;

/// <summary>
/// Advisor response containing the recommended framework selection and
/// collected benchmark measurements for each query/framework pair.
/// </summary>
public record AdvisorRunResult(
    IReadOnlyList<ORMEnum> SelectedFrameworks,
    IReadOnlyDictionary<string, ORMEnum> QueryAssignments,
    IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, BenchmarkMeasurementDto>> Measurements,
    /// <summary>
    /// Optional predictions from execution plan analysis (only populated when UsePrediction is true).
    /// </summary>
    IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, QueryPlanPredictionDto>>? Predictions = null,
    /// <summary>
    /// Indicates whether the result was based on predicted costs (true) or actual execution (false).
    /// </summary>
    bool UsedPrediction = false
);

/// <summary>
/// Lightweight DTO for benchmark results used in the API contract.
/// </summary>
public sealed record BenchmarkMeasurementDto(
    double MeanDurationMilliseconds,
    long AllocatedBytes,
    /// <summary>
    /// Predicted cost from query execution plan analysis (if available).
    /// </summary>
    double? PredictedCost = null,
    /// <summary>
    /// Predicted row count from query execution plan (if available).
    /// </summary>
    double? PredictedRows = null
);
