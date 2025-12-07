using ORMConvertorAPI.Dtos.Advisor;

namespace ORMConvertorAPI.Services;

/// <summary>
/// Minimal contract for running the advisor pipeline end-to-end.
/// </summary>
public interface IAdvisorRunCoordinator
{
    /// <summary>
    /// Runs the advisor with actual query execution and benchmarking.
    /// </summary>
    Task<AdvisorRunResult> RunAsync(
        AdvisorRunRequest request,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Runs the advisor using predicted costs from execution plan analysis
    /// without actually executing the queries.
    /// </summary>
    Task<AdvisorRunResult> RunWithPredictionAsync(
        AdvisorRunRequest request,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Predicts query execution costs for all frameworks without optimization.
    /// Returns raw predictions ranked by estimated cost.
    /// </summary>
    Task<QueryPlanPredictionResult> PredictCostsAsync(
        AdvisorRunRequest request,
        CancellationToken cancellationToken = default);
}
