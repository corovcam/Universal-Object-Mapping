using Model;

namespace ORMConvertorAPI.Dtos.Advisor;

/// <summary>
/// Minimal payload for kicking off an advisor optimisation run.
/// </summary>
public record AdvisorRunRequest(
    ORMEnum SourceOrm,
    IReadOnlyList<ConversionSource> Entities,
    IReadOnlyList<AdvisorRunQuery> Queries,
    long MaxMemoryBytes,
    int MaxFrameworksToSelect,
    IReadOnlyList<ORMEnum>? TargetFrameworks = null,
    /// <summary>
    /// When true, uses query execution plan analysis to predict costs
    /// instead of actually executing the queries. This is faster but less accurate.
    /// </summary>
    bool UsePrediction = false
);
