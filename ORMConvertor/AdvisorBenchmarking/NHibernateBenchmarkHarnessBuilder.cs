using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using Model;
using static AdvisorBenchmarking.HarnessGenerationUtilities;
using EntityInfo = AdvisorBenchmarking.HarnessGenerationUtilities.EntityInfo;

namespace AdvisorBenchmarking;

/// <summary>
/// Builds benchmark harnesses for NHibernate ORM queries.
/// </summary>
internal static class NHibernateBenchmarkHarnessBuilder
{
    /// <summary>
    /// Builds a benchmark harness source for NHibernate queries.
    /// </summary>
    public static BenchmarkSource Build(
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        var entityInfos = ExtractEntityInfos(sources, connectionString);
        if (entityInfos.Count == 0)
        {
            throw new InvalidOperationException("NHibernate harness requires at least one entity definition.");
        }

        var querySource = sources
            .FirstOrDefault(s => s.ContentType == ConversionContentType.CSharpQuery)?.Content
            ?? throw new InvalidOperationException("NHibernate harness requires a query definition.");
        querySource = NormalizeQuerySource(querySource);

        var ns = "DynamicBenchmarks.Generated";
        var typeName = $"NHibernateBenchmark_{Guid.NewGuid():N}";

        var sb = new StringBuilder();
        var usingSet = new HashSet<string>(StringComparer.Ordinal)
        {
            "System",
            "System.Collections.Generic",
            "System.Linq",
            "Microsoft.Data.SqlClient",
            "NHibernate",
            "NHibernate.Cfg",
            "NHibernate.Mapping.ByCode",
            "NHibernate.Mapping.ByCode.Conformist"
        };

        foreach (var entityUsing in entityInfos.SelectMany(e => e.Usings))
        {
            usingSet.Add(entityUsing.Replace(";", string.Empty).Trim());
        }
        foreach (var distinctNs in entityInfos.Select(e => e.Namespace).Where(n => n != null).Distinct())
        {
            usingSet.Add(distinctNs!);
        }

        foreach (var import in usingSet.OrderBy(u => u, StringComparer.Ordinal))
        {
            sb.AppendLine($"using {import};");
        }
        sb.AppendLine();
        sb.AppendLine($"namespace {ns}");
        sb.AppendLine("{");
        sb.AppendLine($"    public class {typeName}");
        sb.AppendLine("    {");
        sb.AppendLine($"        private const string ConnectionString = @\"{EscapeVerbatim(connectionString)}\";");
        sb.AppendLine("        private ISessionFactory sessionFactory = default!;");
        sb.AppendLine("        private ISession session = default!;");
        sb.AppendLine();
        sb.AppendLine("        public void Setup()");
        sb.AppendLine("        {");
        sb.AppendLine("            var cfg = new Configuration();");
        sb.AppendLine("            cfg.DataBaseIntegration(db =>");
        sb.AppendLine("            {");
        sb.AppendLine("                db.ConnectionString = ConnectionString;");
        sb.AppendLine("                db.Dialect<NHibernate.Dialect.MsSql2012Dialect>();");
        sb.AppendLine("                db.Driver<NHibernate.Driver.MicrosoftDataSqlClientDriver>();");
        sb.AppendLine("            });");
        sb.AppendLine();
        sb.AppendLine("            var mapper = new ModelMapper();");
        // Add entity mappings
        foreach (var entity in entityInfos)
        {
            var qualifiedType = GetQualifiedTypeName(entity);
            sb.AppendLine($"            mapper.AddMapping<{entity.TypeName}Map>();");
        }
        sb.AppendLine("            cfg.AddMapping(mapper.CompileMappingForAllExplicitlyAddedEntities());");
        sb.AppendLine();
        sb.AppendLine("            sessionFactory = cfg.BuildSessionFactory();");
        sb.AppendLine("            session = sessionFactory.OpenSession();");
        sb.AppendLine("        }");
        sb.AppendLine();
        sb.AppendLine("        public void Cleanup()");
        sb.AppendLine("        {");
        sb.AppendLine("            session?.Dispose();");
        sb.AppendLine("            sessionFactory?.Dispose();");
        sb.AppendLine("        }");
        sb.AppendLine();
        sb.AppendLine("        public int Execute()");
        sb.AppendLine("        {");
        sb.AppendLine("            return Query().Count;");
        sb.AppendLine("        }");
        sb.AppendLine();
        sb.AppendLine(BuildNHibernateQueryMethod(querySource, entityInfos));
        sb.AppendLine("    }");
        sb.AppendLine();
        // Generate entity mapping classes
        foreach (var entity in entityInfos)
        {
            sb.AppendLine(GenerateEntityMapping(entity));
        }
        sb.AppendLine("}");
        sb.AppendLine();

        foreach (var entity in entityInfos)
        {
            sb.AppendLine(NormalizeEntitySource(entity.Source));
            sb.AppendLine();
        }

        return new BenchmarkSource(ns, typeName, sb.ToString());
    }

    /// <summary>
    /// Builds a harness source that extracts SQL from the NHibernate query without executing it.
    /// </summary>
    public static BenchmarkSource BuildForSqlExtraction(
        IReadOnlyList<ConversionSource> sources,
        string connectionString)
    {
        var entityInfos = ExtractEntityInfos(sources, connectionString);
        if (entityInfos.Count == 0)
        {
            throw new InvalidOperationException("NHibernate harness requires at least one entity definition.");
        }

        var querySource = sources
            .FirstOrDefault(s => s.ContentType == ConversionContentType.CSharpQuery)?.Content
            ?? throw new InvalidOperationException("NHibernate harness requires a query definition.");
        querySource = NormalizeQuerySource(querySource);

        var ns = "DynamicBenchmarks.SqlExtraction";
        var typeName = $"NHibernateSqlExtractor_{Guid.NewGuid():N}";

        // Extract SQL directly from the query source
        var sqlQuery = ExtractSqlFromQuerySource(querySource, entityInfos);

        var sb = new StringBuilder();
        sb.AppendLine("using System;");
        sb.AppendLine();
        sb.AppendLine($"namespace {ns}");
        sb.AppendLine("{");
        sb.AppendLine($"    public class {typeName}");
        sb.AppendLine("    {");
        sb.AppendLine("        public void Setup() { }");
        sb.AppendLine("        public void Cleanup() { }");
        sb.AppendLine();
        sb.AppendLine("        /// <summary>");
        sb.AppendLine("        /// Returns the SQL query string extracted from the NHibernate query.");
        sb.AppendLine("        /// </summary>");
        sb.AppendLine("        public string GetSqlQuery()");
        sb.AppendLine("        {");
        sb.AppendLine($"            return @\"{EscapeVerbatim(sqlQuery)}\";");
        sb.AppendLine("        }");
        sb.AppendLine("    }");
        sb.AppendLine("}");

        return new BenchmarkSource(ns, typeName, sb.ToString());
    }

    /// <summary>
    /// Extracts the SQL query string directly from the NHibernate query source code.
    /// </summary>
    public static string ExtractSqlFromQuerySource(string querySource, IReadOnlyList<EntityInfo> entityInfos)
    {
        string normalized = querySource.ReplaceLineEndings("\n");

        // Look for CreateSQLQuery (raw SQL)
        var sqlQueryMatch = Regex.Match(normalized, @"CreateSQLQuery\s*\(\s*@?""([^""]+)""", RegexOptions.Singleline);
        if (sqlQueryMatch.Success)
        {
            return sqlQueryMatch.Groups[1].Value.Trim();
        }

        // Look for HQL queries in CreateQuery
        var hqlMatch = Regex.Match(normalized, @"CreateQuery\s*\(\s*@?""([^""]+)""", RegexOptions.Singleline);
        if (hqlMatch.Success)
        {
            return ConvertHqlToSql(hqlMatch.Groups[1].Value, entityInfos);
        }

        // Build SQL from entity info for QueryOver/Criteria patterns
        return BuildSqlFromCriteriaPattern(querySource, entityInfos);
    }

    private static string BuildNHibernateQueryMethod(string querySource, IReadOnlyList<EntityInfo> entityInfos)
    {
        var resultType = entityInfos.FirstOrDefault()?.TypeName ?? "object";
        var sql = ExtractSqlFromQuerySource(querySource, entityInfos);

        var builder = new StringBuilder();
        builder.AppendLine($"        public List<{resultType}> Query()");
        builder.AppendLine("        {");
        builder.AppendLine($"            var query = session.CreateSQLQuery(@\"{EscapeVerbatim(sql)}\")");
        builder.AppendLine($"                .AddEntity(typeof({resultType}));");
        builder.AppendLine($"            return query.List<{resultType}>().ToList();");
        builder.AppendLine("        }");
        return builder.ToString();
    }

    private static string ConvertHqlToSql(string hql, IReadOnlyList<EntityInfo> entityInfos)
    {
        var sql = hql;

        // Replace entity names with table names
        foreach (var entity in entityInfos)
        {
            if (!string.IsNullOrEmpty(entity.TypeName))
            {
                sql = Regex.Replace(sql, $@"\b{entity.TypeName}\b", $"[{entity.TableName}]", RegexOptions.IgnoreCase);
            }
        }

        // Convert HQL keywords to SQL
        sql = Regex.Replace(sql, @"\bfrom\b", "FROM", RegexOptions.IgnoreCase);
        sql = Regex.Replace(sql, @"\bwhere\b", "WHERE", RegexOptions.IgnoreCase);
        sql = Regex.Replace(sql, @"\bselect\b", "SELECT", RegexOptions.IgnoreCase);
        sql = Regex.Replace(sql, @"\border\s+by\b", "ORDER BY", RegexOptions.IgnoreCase);
        sql = Regex.Replace(sql, @"\band\b", "AND", RegexOptions.IgnoreCase);
        sql = Regex.Replace(sql, @"\bor\b", "OR", RegexOptions.IgnoreCase);

        // If no SELECT, add SELECT *
        if (!sql.TrimStart().StartsWith("SELECT", StringComparison.OrdinalIgnoreCase))
        {
            sql = "SELECT * " + sql;
        }

        return sql.Trim();
    }

    private static string BuildSqlFromCriteriaPattern(string querySource, IReadOnlyList<EntityInfo> entityInfos)
    {
        var primaryEntity = entityInfos.FirstOrDefault();
        var tableName = primaryEntity?.TableName ?? "UnknownTable";

        var sql = new StringBuilder();
        sql.Append("SELECT * FROM ");
        sql.Append($"[{tableName.Replace(".", "].[")}]");

        // Look for restriction patterns
        var whereConditions = new List<string>();

        // Eq restrictions
        var eqMatches = Regex.Matches(querySource, @"\.Add\s*\(\s*Restrictions\.Eq\s*\(\s*""(\w+)""\s*,\s*(?:""([^""]+)""|(\d+))\s*\)\s*\)");
        foreach (Match match in eqMatches)
        {
            var column = match.Groups[1].Value;
            var strValue = match.Groups[2].Value;
            var numValue = match.Groups[3].Value;

            if (!string.IsNullOrEmpty(strValue))
            {
                whereConditions.Add($"[{column}] = '{strValue}'");
            }
            else if (!string.IsNullOrEmpty(numValue))
            {
                whereConditions.Add($"[{column}] = {numValue}");
            }
        }

        // Like restrictions
        var likeMatches = Regex.Matches(querySource, @"\.Add\s*\(\s*Restrictions\.Like\s*\(\s*""(\w+)""\s*,\s*""([^""]+)""\s*\)\s*\)");
        foreach (Match match in likeMatches)
        {
            var column = match.Groups[1].Value;
            var pattern = match.Groups[2].Value;
            whereConditions.Add($"[{column}] LIKE '{pattern}'");
        }

        // Gt/Lt restrictions
        var gtMatches = Regex.Matches(querySource, @"\.Add\s*\(\s*Restrictions\.Gt\s*\(\s*""(\w+)""\s*,\s*(\d+)\s*\)\s*\)");
        foreach (Match match in gtMatches)
        {
            whereConditions.Add($"[{match.Groups[1].Value}] > {match.Groups[2].Value}");
        }

        var ltMatches = Regex.Matches(querySource, @"\.Add\s*\(\s*Restrictions\.Lt\s*\(\s*""(\w+)""\s*,\s*(\d+)\s*\)\s*\)");
        foreach (Match match in ltMatches)
        {
            whereConditions.Add($"[{match.Groups[1].Value}] < {match.Groups[2].Value}");
        }

        if (whereConditions.Count > 0)
        {
            sql.Append(" WHERE ");
            sql.Append(string.Join(" AND ", whereConditions));
        }

        // Look for ordering
        var orderMatch = Regex.Match(querySource, @"\.AddOrder\s*\(\s*Order\.(?:Asc|Desc)\s*\(\s*""(\w+)""\s*\)\s*\)");
        if (orderMatch.Success)
        {
            var direction = querySource.Contains("Order.Desc") ? "DESC" : "ASC";
            sql.Append($" ORDER BY [{orderMatch.Groups[1].Value}] {direction}");
        }

        return sql.ToString();
    }

    private static string GenerateEntityMapping(EntityInfo entity)
    {
        var tableName = entity.TableName;
        var schema = "dbo";
        var name = tableName;

        if (tableName.Contains('.'))
        {
            var parts = tableName.Split('.', 2);
            schema = parts[0];
            name = parts[1];
        }

        var sb = new StringBuilder();
        sb.AppendLine($"    public class {entity.TypeName}Map : ClassMapping<{entity.TypeName}>");
        sb.AppendLine("    {");
        sb.AppendLine($"        public {entity.TypeName}Map()");
        sb.AppendLine("        {");
        sb.AppendLine($"            Schema(\"{schema}\");");
        sb.AppendLine($"            Table(\"{name}\");");
        sb.AppendLine("            // Note: Property and Id mappings should be added based on entity structure");
        sb.AppendLine("        }");
        sb.AppendLine("    }");

        return sb.ToString();
    }
}
