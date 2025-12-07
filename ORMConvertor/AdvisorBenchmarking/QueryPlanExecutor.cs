using Microsoft.Extensions.Logging;
using Model;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;

namespace AdvisorBenchmarking;

/// <summary>
/// Executes query plan analysis by compiling and running SQL extraction harnesses.
/// </summary>
public sealed class QueryPlanExecutor : IQueryPlanExecutor
{
    private readonly RoslynBenchmarkCompiler _compiler = new();
    private readonly IReadOnlyList<Microsoft.CodeAnalysis.MetadataReference> _references = BenchmarkReferenceProvider.GetStandardReferences();
    private readonly SqlQueryPlanAnalyzer _planAnalyzer;
    private readonly ILogger<QueryPlanExecutor>? _logger;

    public QueryPlanExecutor(ILogger<QueryPlanExecutor>? logger = null)
    {
        _logger = logger;
        _planAnalyzer = new SqlQueryPlanAnalyzer(logger != null ? 
            Microsoft.Extensions.Logging.LoggerFactoryExtensions.CreateLogger<SqlQueryPlanAnalyzer>(
                new Microsoft.Extensions.Logging.Abstractions.NullLoggerFactory()) : null);
    }

    /// <inheritdoc />
    public QueryExecutionPlanResult ExtractAndAnalyzePlan(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        _logger?.LogInformation("Starting execution plan analysis for framework {Framework}", framework);

        try
        {
            // Build the SQL extraction harness
            var benchmarkSource = BenchmarkHarnessBuilder.BuildForSqlExtraction(framework, sources, connectionString);
            var assemblyName = $"SqlExtraction_{Guid.NewGuid():N}";
            //SaveGeneratedSource(benchmarkSource.Source, framework, logger: _logger);

            _logger?.LogDebug("Compiling SQL extraction harness for {Framework}", framework);

            using var compilation = _compiler.Compile(benchmarkSource.Source, _references, assemblyName);
            
            var extractorType = compilation.Assembly.GetType($"{benchmarkSource.Namespace}.{benchmarkSource.TypeName}")
                ?? throw new InvalidOperationException($"Generated SQL extractor type could not be located for {framework}.");

            var setup = extractorType.GetMethod("Setup");
            var cleanup = extractorType.GetMethod("Cleanup");
            var getSqlQuery = extractorType.GetMethod("GetSqlQuery");

            if (getSqlQuery == null)
            {
                throw new InvalidOperationException($"GetSqlQuery method not found in generated harness for {framework}.");
            }

            var instance = Activator.CreateInstance(extractorType)
                ?? throw new InvalidOperationException($"Failed to instantiate SQL extractor for {framework}.");

            string sqlQuery;
            try
            {
                setup?.Invoke(instance, null);
                sqlQuery = (getSqlQuery.Invoke(instance, null) as string) ?? string.Empty;
            }
            finally
            {
                try
                {
                    cleanup?.Invoke(instance, null);
                }
                catch (Exception ex)
                {
                    _logger?.LogWarning(ex, "Cleanup threw an exception for {Framework}", framework);
                }
            }

            if (string.IsNullOrWhiteSpace(sqlQuery))
            {
                return QueryExecutionPlanResult.Failure(framework, string.Empty, "Failed to extract SQL query from harness.");
            }

            _logger?.LogDebug("Extracted SQL for {Framework}: {Query}", framework, TruncateQuery(sqlQuery));

            // Analyze the execution plan
            return _planAnalyzer.AnalyzeExecutionPlan(framework, sqlQuery, connectionString);
        }
        catch (TargetInvocationException tie) when (tie.InnerException != null)
        {
            _logger?.LogError(tie.InnerException, "SQL extraction failed for {Framework}: {Message}", framework, tie.InnerException.Message);
            return QueryExecutionPlanResult.Failure(framework, string.Empty, $"SQL extraction failed: {tie.InnerException.Message}");
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Execution plan analysis failed for {Framework}: {Message}", framework, ex.Message);
            return QueryExecutionPlanResult.Failure(framework, string.Empty, ex.Message);
        }
    }

    /// <inheritdoc />
    public IReadOnlyList<QueryExecutionPlanResult> AnalyzeAllFrameworks(
        IReadOnlyDictionary<ORMEnum, IReadOnlyList<ConversionSource>> frameworkSources,
        string connectionString)
    {
        var results = new List<QueryExecutionPlanResult>();

        foreach (var (framework, sources) in frameworkSources)
        {
            var result = ExtractAndAnalyzePlan(framework, sources, connectionString);
            results.Add(result);
        }

        return results;
    }

    /// <inheritdoc />
    public IReadOnlyList<QueryExecutionPlanResult> RankByEstimatedCost(
        IReadOnlyList<QueryExecutionPlanResult> results)
    {
        return results
            .Where(r => r.IsSuccess)
            .OrderBy(r => r.EstimatedCost)
            .ToList();
    }

    /// <inheritdoc />
    public ORMEnum? GetBestFramework(IReadOnlyList<QueryExecutionPlanResult> results)
    {
        var ranked = RankByEstimatedCost(results);
        return ranked.FirstOrDefault()?.Framework;
    }

    private static string TruncateQuery(string query, int maxLength = 200)
    {
        if (string.IsNullOrEmpty(query) || query.Length <= maxLength)
        {
            return query;
        }

        return query[..maxLength] + "...";
    }

    private static string SaveGeneratedSource(
        string sourceCode,
        ORMEnum framework,
        string? outputDirectory = null,
        ILogger? logger = null)
    {
        outputDirectory ??= Path.Combine(Directory.GetCurrentDirectory(), "GeneratedCode");

        if (!Directory.Exists(outputDirectory))
        {
            Directory.CreateDirectory(outputDirectory);
        }

        var timestamp = DateTime.UtcNow.ToString("yyyyMMdd_HHmmss");
        var fileName = $"{framework}_SqlExtraction_{timestamp}.cs";
        var filePath = Path.Combine(outputDirectory, fileName);

        File.WriteAllText(filePath, sourceCode, Encoding.UTF8);

        logger?.LogInformation("Saved generated source code to {FilePath}", filePath);

        return filePath;
    }
}
