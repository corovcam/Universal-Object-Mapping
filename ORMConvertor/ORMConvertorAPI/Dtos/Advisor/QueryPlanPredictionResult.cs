using Model;

namespace ORMConvertorAPI.Dtos.Advisor;

/// <summary>
/// Result of query execution plan prediction for a single framework.
/// </summary>
public sealed record QueryPlanPredictionDto(
    ORMEnum Framework,
    string SqlQuery,
    double EstimatedCost,
    double EstimatedRows,
    double EstimatedCpuCost,
    double EstimatedIoCost,
    bool IsSuccess,
    string? ErrorMessage = null
);

/// <summary>
/// Response containing predicted costs for all frameworks, ranked by estimated cost.
/// </summary>
public sealed record QueryPlanPredictionResult(
    IReadOnlyList<QueryPlanPredictionDto> Predictions,
    ORMEnum? RecommendedFramework,
    IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, QueryPlanPredictionDto>> PredictionsByQuery
);
