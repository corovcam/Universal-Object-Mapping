using System;
using System.Collections.Generic;
using System.Linq;
using AdvisorBenchmarking;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Model;
using AdvisorNamespace = Advisor.Advisor;
using OrmConvertor;
using ORMConvertorAPI.Dtos.Advisor;

namespace ORMConvertorAPI.Services;

public class AdvisorRunCoordinator : IAdvisorRunCoordinator
{
    private readonly IBenchmarkExecutor benchmarkExecutor;
    private readonly IQueryPlanExecutor queryPlanExecutor;
    private readonly ILogger<AdvisorRunCoordinator> logger;
    private readonly string connectionString;

    private static readonly ORMEnum[] KnownFrameworks =
    [
        ORMEnum.Dapper,
        ORMEnum.NHibernate,
        ORMEnum.EFCore
    ];

    private static readonly ORMEnum[] SupportedFrameworks =
    [
        ORMEnum.Dapper,
        ORMEnum.EFCore
    ];

    public AdvisorRunCoordinator(
        IBenchmarkExecutor benchmarkExecutor,
        IQueryPlanExecutor queryPlanExecutor,
        IConfiguration configuration,
        ILogger<AdvisorRunCoordinator> logger)
    {
        this.benchmarkExecutor = benchmarkExecutor ?? throw new ArgumentNullException(nameof(benchmarkExecutor));
        this.queryPlanExecutor = queryPlanExecutor ?? throw new ArgumentNullException(nameof(queryPlanExecutor));
        this.logger = logger ?? throw new ArgumentNullException(nameof(logger));
        connectionString = configuration.GetConnectionString("AdvisorDatabase")
            ?? configuration["Advisor:ConnectionString"]
            ?? "Server=mssql_db,1433;Database=WideWorldImporters;User ID=sa;Password=Testingorms123;TrustServerCertificate=true;";
    }

    /// <summary>
    /// Validates the request, resolves target frameworks, and prepares translated artifacts.
    /// Routes to prediction mode if UsePrediction is set.
    /// </summary>
    public Task<AdvisorRunResult> RunAsync(
        AdvisorRunRequest request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(request.Entities);
        ArgumentNullException.ThrowIfNull(request.Queries);

        if (request.Queries.Count == 0)
        {
            throw new ArgumentException("At least one query is required", nameof(request));
        }

        // Route to prediction mode if requested
        if (request.UsePrediction)
        {
            logger.LogInformation("UsePrediction flag set, routing to prediction-based optimization.");
            return RunWithPredictionAsync(request, cancellationToken);
        }

        logger.LogInformation("Advisor run received with {QueryCount} queries from source ORM {SourceOrm}.", request.Queries.Count, request.SourceOrm);

        var targetFrameworks = ResolveTargetFrameworks(request);
        if (targetFrameworks.Count == 0)
        {
            throw new InvalidOperationException("No supported target frameworks resolved for advisor run. Currently supported: Dapper, EFCore.");
        }
        logger.LogInformation("Target frameworks resolved: {Frameworks}.", targetFrameworks);

        var translations = BuildTranslations(
            request,
            targetFrameworks,
            cancellationToken);
        logger.LogInformation("Translations built for all queries.");

        var measurements = RunBenchmarks(
            request,
            targetFrameworks,
            translations,
            cancellationToken);
        logger.LogInformation("Benchmarks completed for {QueryCount} queries.", request.Queries.Count);

        var result = ExecuteAdvisor(
            request,
            targetFrameworks,
            measurements);

        return Task.FromResult(result);
    }

    /// <summary>
    /// Runs the advisor using predicted costs from execution plan analysis.
    /// </summary>
    public Task<AdvisorRunResult> RunWithPredictionAsync(
        AdvisorRunRequest request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(request.Entities);
        ArgumentNullException.ThrowIfNull(request.Queries);

        if (request.Queries.Count == 0)
        {
            throw new ArgumentException("At least one query is required", nameof(request));
        }

        logger.LogInformation("Advisor prediction run received with {QueryCount} queries from source ORM {SourceOrm}.", request.Queries.Count, request.SourceOrm);

        var targetFrameworks = ResolveTargetFrameworks(request);
        if (targetFrameworks.Count == 0)
        {
            throw new InvalidOperationException("No supported target frameworks resolved for advisor run.");
        }

        var translations = BuildTranslations(request, targetFrameworks, cancellationToken);

        // Run predictions instead of benchmarks
        var predictions = RunPredictions(request, targetFrameworks, translations, cancellationToken);

        var result = ExecuteAdvisorWithPredictions(request, targetFrameworks, predictions);

        return Task.FromResult(result);
    }

    /// <summary>
    /// Predicts query execution costs without running the optimizer.
    /// </summary>
    public Task<QueryPlanPredictionResult> PredictCostsAsync(
        AdvisorRunRequest request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(request.Entities);
        ArgumentNullException.ThrowIfNull(request.Queries);

        if (request.Queries.Count == 0)
        {
            throw new ArgumentException("At least one query is required", nameof(request));
        }

        logger.LogInformation("Predicting costs for {QueryCount} queries from source ORM {SourceOrm}.", request.Queries.Count, request.SourceOrm);

        var targetFrameworks = ResolveTargetFrameworks(request);
        if (targetFrameworks.Count == 0)
        {
            throw new InvalidOperationException("No supported target frameworks resolved.");
        }

        var translations = BuildTranslations(request, targetFrameworks, cancellationToken);
        var predictions = RunPredictions(request, targetFrameworks, translations, cancellationToken);

        // Aggregate all predictions and find the best framework
        var allPredictions = new List<QueryPlanPredictionDto>();
        foreach (var (queryId, perFramework) in predictions)
        {
            foreach (var (framework, prediction) in perFramework)
            {
                allPredictions.Add(prediction);
            }
        }

        var rankedPredictions = allPredictions
            .Where(p => p.IsSuccess)
            .OrderBy(p => p.EstimatedCost)
            .ToList();

        var recommendedFramework = rankedPredictions.FirstOrDefault()?.Framework;

        var result = new QueryPlanPredictionResult(
            rankedPredictions,
            recommendedFramework,
            predictions
        );

        return Task.FromResult(result);
    }

    private IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, QueryPlanPredictionDto>> RunPredictions(
        AdvisorRunRequest request,
        IReadOnlyList<ORMEnum> targetFrameworks,
        IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, IReadOnlyList<ConversionSource>>> translations,
        CancellationToken cancellationToken)
    {
        var results = new Dictionary<string, IReadOnlyDictionary<ORMEnum, QueryPlanPredictionDto>>(StringComparer.Ordinal);

        foreach (var query in request.Queries)
        {
            cancellationToken.ThrowIfCancellationRequested();
            logger.LogDebug("Running predictions for query {QueryId}.", query.Id);

            if (!translations.TryGetValue(query.Id, out var frameworkSources))
            {
                throw new InvalidOperationException($"Missing translations for query '{query.Id}'.");
            }

            var perFramework = new Dictionary<ORMEnum, QueryPlanPredictionDto>();
            foreach (var framework in targetFrameworks)
            {
                cancellationToken.ThrowIfCancellationRequested();

                if (!frameworkSources.TryGetValue(framework, out var sources))
                {
                    throw new InvalidOperationException($"Missing translation for query '{query.Id}' and framework '{framework}'.");
                }

                var planResult = queryPlanExecutor.ExtractAndAnalyzePlan(framework, sources, connectionString);
                
                var prediction = new QueryPlanPredictionDto(
                    planResult.Framework,
                    planResult.SqlQuery,
                    planResult.EstimatedCost,
                    planResult.EstimatedRows,
                    planResult.EstimatedCpuCost,
                    planResult.EstimatedIoCost,
                    planResult.IsSuccess,
                    planResult.ErrorMessage
                );

                perFramework[framework] = prediction;
                
                if (planResult.IsSuccess)
                {
                    logger.LogInformation("Prediction {QueryId} on {Framework}: cost {Cost}, rows {Rows}.",
                        query.Id, framework, planResult.EstimatedCost, planResult.EstimatedRows);
                }
                else
                {
                    logger.LogWarning("Prediction failed {QueryId} on {Framework}: {Error}.",
                        query.Id, framework, planResult.ErrorMessage);
                }
            }

            results[query.Id] = perFramework;
        }

        return results;
    }

    private AdvisorRunResult ExecuteAdvisorWithPredictions(
        AdvisorRunRequest request,
        IReadOnlyList<ORMEnum> targetFrameworks,
        IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, QueryPlanPredictionDto>> predictions)
    {
        int queryCount = request.Queries.Count;
        int frameworkCount = targetFrameworks.Count;

        var cost = new double[queryCount * frameworkCount];
        var mem = new long[queryCount * frameworkCount];
        var weights = new int[queryCount];

        // Build measurements from predictions (using estimated cost as the primary metric)
        var dtoMeasurements = new Dictionary<string, IReadOnlyDictionary<ORMEnum, BenchmarkMeasurementDto>>(StringComparer.Ordinal);

        for (int qi = 0; qi < queryCount; qi++)
        {
            var query = request.Queries[qi];
            weights[qi] = Math.Max(1, query.Weight);
            var queryPredictions = predictions[query.Id];

            var measurementMap = new Dictionary<ORMEnum, BenchmarkMeasurementDto>();

            for (int fi = 0; fi < frameworkCount; fi++)
            {
                var framework = targetFrameworks[fi];
                var prediction = queryPredictions[framework];
                int index = (qi * frameworkCount) + fi;

                // Use estimated cost as the "runtime" metric for optimization
                cost[index] = prediction.IsSuccess ? prediction.EstimatedCost : double.MaxValue;
                mem[index] = 0; // Memory not estimated from execution plans

                // Create measurement DTO with prediction data
                measurementMap[framework] = new BenchmarkMeasurementDto(
                    0, // No actual execution time
                    0, // No actual memory
                    prediction.EstimatedCost,
                    prediction.EstimatedRows
                );
            }

            dtoMeasurements[query.Id] = measurementMap;
        }

        int[] selected = new int[frameworkCount];
        int[] assignment = new int[queryCount];

        long maxMemory = request.MaxMemoryBytes > 0 ? request.MaxMemoryBytes : long.MaxValue;

        int status = AdvisorNamespace.Solve(
            mem,
            cost,
            weights,
            maxMemory,
            request.MaxFrameworksToSelect,
            queryCount,
            frameworkCount,
            out int objective,
            selected,
            assignment);

        if (status != 0)
        {
            throw new InvalidOperationException($"Advisor solver failed with status code {status}.");
        }

        var chosenFrameworks = new List<ORMEnum>();
        for (int fi = 0; fi < frameworkCount; fi++)
        {
            if (selected[fi] > 0)
            {
                chosenFrameworks.Add(targetFrameworks[fi]);
            }
        }

        var assignments = new Dictionary<string, ORMEnum>(StringComparer.Ordinal);
        for (int qi = 0; qi < queryCount; qi++)
        {
            int frameworkIndex = assignment[qi];
            if (frameworkIndex < 0 || frameworkIndex >= frameworkCount)
            {
                continue;
            }
            assignments[request.Queries[qi].Id] = targetFrameworks[frameworkIndex];
        }

        return new AdvisorRunResult(
            chosenFrameworks,
            assignments,
            dtoMeasurements,
            predictions,
            UsedPrediction: true
        );
    }

    /// <summary>
    /// Returns explicitly requested frameworks or falls back to the default supported list.
    /// </summary>
    private static IReadOnlyList<ORMEnum> ResolveTargetFrameworks(AdvisorRunRequest request)
    {
        IEnumerable<ORMEnum> candidates = request.TargetFrameworks is { Count: > 0 } explicitTargets
            ? explicitTargets
            : KnownFrameworks;

        var filtered = candidates
            .Where(f => SupportedFrameworks.Contains(f))
            .Distinct()
            .ToArray();

        return filtered;
    }

    /// <summary>
    /// Produces per-query conversion outputs for each target framework using the existing converter.
    /// </summary>
    private static IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, IReadOnlyList<ConversionSource>>> BuildTranslations(
        AdvisorRunRequest request,
        IReadOnlyList<ORMEnum> targetFrameworks,
        CancellationToken cancellationToken)
    {
        var result = new Dictionary<string, IReadOnlyDictionary<ORMEnum, IReadOnlyList<ConversionSource>>>(StringComparer.Ordinal);

        foreach (var query in request.Queries)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var perFramework = new Dictionary<ORMEnum, IReadOnlyList<ConversionSource>>();

            foreach (var framework in targetFrameworks)
            {
                IReadOnlyList<ConversionSource> artifacts;
                // Always run through ConversionHandler to normalize entities into EntityMaps
                // and emit one entity per source for the target framework (even if same as source).
                var sources = ComposeSources(request.Entities, query.Query);
                artifacts = ConversionHandler.Convert(
                    request.SourceOrm,
                    framework,
                    sources);

                // Ensure EFCore harness still receives a query source. EFCore target does not
                // produce a CSharpQuery via QueryBuilder (it's null by design). If missing,
                // append the original query unchanged alongside converted entities.
                if (framework == ORMEnum.EFCore && !artifacts.Any(a => a.ContentType == ConversionContentType.CSharpQuery))
                {
                    var withQuery = new List<ConversionSource>(artifacts.Count + 1);
                    withQuery.AddRange(artifacts);
                    withQuery.Add(Clone(query.Query));
                    artifacts = withQuery;
                }

                perFramework[framework] = artifacts;
            }

            result[query.Id] = perFramework;
        }

        return result;
    }

    /// <summary>
    /// Clones the shared entity inputs and appends the query so each conversion has its own copy.
    /// </summary>
    private static List<ConversionSource> ComposeSources(
        IReadOnlyList<ConversionSource> entities,
        ConversionSource query)
    {
        var combined = new List<ConversionSource>(entities.Count + 1);
        foreach (var entity in entities)
        {
            combined.Add(Clone(entity));
        }

        combined.Add(Clone(query));
        return combined;
    }

    /// <summary>
    /// Creates a defensive copy of the provided conversion source.
    /// </summary>
    private static ConversionSource Clone(ConversionSource source) =>
        new()
        {
            ContentType = source.ContentType,
            Content = source.Content
        };

    private IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, BenchmarkMeasurement>> RunBenchmarks(
        AdvisorRunRequest request,
        IReadOnlyList<ORMEnum> targetFrameworks,
        IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, IReadOnlyList<ConversionSource>>> translations,
        CancellationToken cancellationToken)
    {
        var results = new Dictionary<string, IReadOnlyDictionary<ORMEnum, BenchmarkMeasurement>>(StringComparer.Ordinal);

        foreach (var query in request.Queries)
        {
            cancellationToken.ThrowIfCancellationRequested();
            logger.LogDebug("Running benchmarks for query {QueryId}.", query.Id);

            if (!translations.TryGetValue(query.Id, out var frameworkSources))
            {
                throw new InvalidOperationException($"Missing translations for query '{query.Id}'.");
            }

            var perFramework = new Dictionary<ORMEnum, BenchmarkMeasurement>();
            foreach (var framework in targetFrameworks)
            {
                cancellationToken.ThrowIfCancellationRequested();

                if (!frameworkSources.TryGetValue(framework, out var sources))
                {
                    throw new InvalidOperationException($"Missing translation for query '{query.Id}' and framework '{framework}'.");
                }

                var measurement = benchmarkExecutor.Execute(framework, sources, connectionString);
                perFramework[framework] = measurement;
                logger.LogInformation("Benchmark {QueryId} on {Framework}: mean {Mean} ms, memory {Memory} bytes.", query.Id, framework, measurement.MeanDurationMilliseconds, measurement.AllocatedBytes);
            }

            results[query.Id] = perFramework;
        }

        return results;
    }

    private static AdvisorRunResult ExecuteAdvisor(
        AdvisorRunRequest request,
        IReadOnlyList<ORMEnum> targetFrameworks,
        IReadOnlyDictionary<string, IReadOnlyDictionary<ORMEnum, BenchmarkMeasurement>> measurements)
    {
        int queryCount = request.Queries.Count;
        int frameworkCount = targetFrameworks.Count;

        var cost = new double[queryCount * frameworkCount];
        var mem = new long[queryCount * frameworkCount];
        var weights = new int[queryCount];

        for (int qi = 0; qi < queryCount; qi++)
        {
            var query = request.Queries[qi];
            weights[qi] = Math.Max(1, query.Weight);
            var queryMeasurements = measurements[query.Id];

            for (int fi = 0; fi < frameworkCount; fi++)
            {
                var framework = targetFrameworks[fi];
                var m = queryMeasurements[framework];
                int index = (qi * frameworkCount) + fi;
                cost[index] = m.MeanDurationMilliseconds;
                mem[index] = m.AllocatedBytes;
            }
        }

        int[] selected = new int[frameworkCount];
        int[] assignment = new int[queryCount];

        long maxMemory = request.MaxMemoryBytes > 0
            ? request.MaxMemoryBytes
            : long.MaxValue;

        int status = AdvisorNamespace.Solve(
            mem,
            cost,
            weights,
            maxMemory,
            request.MaxFrameworksToSelect,
            queryCount,
            frameworkCount,
            out int objective,
            selected,
            assignment);

        if (status != 0)
        {
            throw new InvalidOperationException($"Advisor solver failed with status code {status}.");
        }

        var chosenFrameworks = new List<ORMEnum>();
        for (int fi = 0; fi < frameworkCount; fi++)
        {
            if (selected[fi] > 0)
            {
                chosenFrameworks.Add(targetFrameworks[fi]);
            }
        }

        var assignments = new Dictionary<string, ORMEnum>(StringComparer.Ordinal);
        for (int qi = 0; qi < queryCount; qi++)
        {
            int frameworkIndex = assignment[qi];
            if (frameworkIndex < 0 || frameworkIndex >= frameworkCount)
            {
                continue;
            }

            assignments[request.Queries[qi].Id] = targetFrameworks[frameworkIndex];
        }

        // Map measurements to DTO-friendly structure
        var dtoMeasurements = new Dictionary<string, IReadOnlyDictionary<ORMEnum, BenchmarkMeasurementDto>>(StringComparer.Ordinal);
        foreach (var (qid, perFramework) in measurements)
        {
            var map = new Dictionary<ORMEnum, BenchmarkMeasurementDto>();
            foreach (var (framework, m) in perFramework)
            {
                map[framework] = new BenchmarkMeasurementDto(m.MeanDurationMilliseconds, m.AllocatedBytes);
            }
            dtoMeasurements[qid] = map;
        }

        return new AdvisorRunResult(chosenFrameworks, assignments, dtoMeasurements);
    }

}
