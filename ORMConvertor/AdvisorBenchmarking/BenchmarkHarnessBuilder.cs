using System;
using System.Collections.Generic;
using Model;

namespace AdvisorBenchmarking;

internal static class BenchmarkHarnessBuilder
{
    private static readonly IReadOnlyDictionary<ORMEnum, Func<IReadOnlyList<ConversionSource>, string, BenchmarkSource>> Generators =
        new Dictionary<ORMEnum, Func<IReadOnlyList<ConversionSource>, string, BenchmarkSource>>
        {
            [ORMEnum.Dapper] = DapperBenchmarkHarnessBuilder.Build,
            [ORMEnum.EFCore] = EfCoreBenchmarkHarnessBuilder.Build,
            [ORMEnum.NHibernate] = NHibernateBenchmarkHarnessBuilder.Build
        };

    private static readonly IReadOnlyDictionary<ORMEnum, Func<IReadOnlyList<ConversionSource>, string, BenchmarkSource>> SqlExtractionGenerators =
        new Dictionary<ORMEnum, Func<IReadOnlyList<ConversionSource>, string, BenchmarkSource>>
        {
            [ORMEnum.Dapper] = DapperBenchmarkHarnessBuilder.BuildForSqlExtraction,
            [ORMEnum.EFCore] = EfCoreBenchmarkHarnessBuilder.BuildForSqlExtraction,
            [ORMEnum.NHibernate] = NHibernateBenchmarkHarnessBuilder.BuildForSqlExtraction
        };

    public static BenchmarkSource Build(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        if (!Generators.TryGetValue(framework, out var generator))
        {
            throw new NotSupportedException($"Benchmark harness for framework {framework} is not implemented yet.");
        }

        return generator(sources, connectionString);
    }

    /// <summary>
    /// Builds a harness source specifically for SQL extraction without query execution.
    /// Used for execution plan analysis.
    /// </summary>
    public static BenchmarkSource BuildForSqlExtraction(
        ORMEnum framework,
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        if (!SqlExtractionGenerators.TryGetValue(framework, out var generator))
        {
            throw new NotSupportedException($"SQL extraction harness for framework {framework} is not implemented yet.");
        }

        return generator(sources, connectionString);
    }
}

