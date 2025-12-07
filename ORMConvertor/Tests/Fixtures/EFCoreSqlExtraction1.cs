using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Tests.Fixtures
{
    public class EfCoreSqlExtractor_ca48d48729fb42baaf9f71957a84092e
    {
        private const string ConnectionString = @"Server=localhost,1444;Database=WideWorldImporters;User ID=sa;Password=Testingorms123;TrustServerCertificate=true;";
        private SqlExtractionDbContext context = default!;
        private static readonly QueryBinding CachedQuery = ResolveQueryBinding();

        public void Setup()
        {
            var options = new DbContextOptionsBuilder<SqlExtractionDbContext>()
                .UseSqlServer(ConnectionString)
                .Options;
            context = new SqlExtractionDbContext(options);
        }

        public void Cleanup()
        {
            if (context is null) { return; }
            context.Dispose();
            context = null!;
        }

        /// <summary>
        /// Extracts the SQL query string from the EF Core IQueryable without executing it.
        /// </summary>
        public string GetSqlQuery()
        {
            var result = CachedQuery.Method.Invoke(CachedQuery.Target, new object[] { context });
            return ExtractSqlFromQueryable(result);
        }

        private static string ExtractSqlFromQueryable(object? value)
        {
            if (value is null)
            {
                return string.Empty;
            }

            // Handle async wrappers
            if (value is Task task)
            {
                task.GetAwaiter().GetResult();
                var taskType = task.GetType();
                if (taskType.IsGenericType)
                {
                    var resultProperty = taskType.GetProperty("Result");
                    var taskResult = resultProperty?.GetValue(task);
                    return ExtractSqlFromQueryable(taskResult);
                }
                return string.Empty;
            }

            // Use ToQueryString() for IQueryable to get the SQL
            if (value is IQueryable queryable)
            {
                // Try to call ToQueryString via reflection (EF Core extension method)
                var toQueryStringMethod = typeof(Microsoft.EntityFrameworkCore.EntityFrameworkQueryableExtensions)
                    .GetMethod("ToQueryString", BindingFlags.Public | BindingFlags.Static);
                if (toQueryStringMethod != null)
                {
                    try
                    {
                        var sql = toQueryStringMethod.Invoke(null, new object[] { queryable }) as string;
                        return sql ?? string.Empty;
                    }
                    catch
                    {
                        return queryable.Expression.ToString();
                    }
                }
            }

            return value.ToString() ?? string.Empty;
        }

        private static QueryBinding ResolveQueryBinding()
        {
            var assembly = typeof(SqlExtractionDbContext).Assembly;
            var benchmarkType = typeof(EfCoreSqlExtractor_ca48d48729fb42baaf9f71957a84092e);

            foreach (var type in assembly.GetTypes())
            {
                if (type == benchmarkType || type == typeof(SqlExtractionDbContext))
                {
                    continue;
                }

                foreach (var method in type.GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance))
                {
                    if (!IsSupportedReturnType(method.ReturnType))
                    {
                        continue;
                    }

                    var parameters = method.GetParameters();
                    if (parameters.Length != 1)
                    {
                        continue;
                    }

                    if (!typeof(DbContext).IsAssignableFrom(parameters[0].ParameterType))
                    {
                        continue;
                    }

                    object? target = null;
                    if (!method.IsStatic)
                    {
                        var ctor = type.GetConstructor(Type.EmptyTypes);
                        if (ctor is null)
                        {
                            continue;
                        }

                        target = ctor.Invoke(null);
                    }

                    return new QueryBinding(target, method);
                }
            }

            throw new InvalidOperationException("EF Core query method not found.");
        }

        private static bool IsSupportedReturnType(Type type)
        {
            if (typeof(IQueryable).IsAssignableFrom(type) || typeof(IEnumerable).IsAssignableFrom(type))
            {
                return true;
            }

            if (typeof(Task).IsAssignableFrom(type))
            {
                return true;
            }

            return type.IsValueType && type.FullName is string fullName && fullName.StartsWith("System.Threading.Tasks.ValueTask", StringComparison.Ordinal);
        }

        private sealed class QueryBinding
        {
            public QueryBinding(object? target, MethodInfo method)
            {
                Target = target;
                Method = method;
            }

            public object? Target { get; }
            public MethodInfo Method { get; }
        }

        private sealed class SqlExtractionDbContext : DbContext
        {
            public SqlExtractionDbContext(DbContextOptions<SqlExtractionDbContext> options) : base(options)
            {
            }

            protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
            {
                if (!optionsBuilder.IsConfigured)
                {
                    optionsBuilder.UseSqlServer(ConnectionString);
                }
            }

            protected override void OnModelCreating(ModelBuilder modelBuilder)
            {
                base.OnModelCreating(modelBuilder);
                modelBuilder.Entity<global::Customer>(builder => builder.ToTable("Customers", "Sales"));
                modelBuilder.Entity<global::OrderLine>(builder => builder.ToTable("OrderLines", "Sales"));
            }

            public DbSet<global::Customer> Customers => Set<global::Customer>();
            public DbSet<global::OrderLine> OrderLines => Set<global::OrderLine>();
        }
    }
}

public static class MyQueries
{
    public static IQueryable<Customer> Query1(DbContext ctx)
    {
        return (IQueryable<Customer>)(ctx.Set<Customer>()
            .Where(c => c.CreditLimit > 500)
            .OrderByDescending(c => c.AccountOpenedDate)
            .ThenBy(c => c.CustomerName));
    }
}

[Table("Customers", Schema = "Sales")]
public class Customer
{
    [Key]
    public required int CustomerID { get; set; }

    public required string CustomerName { get; set; }

    public required DateTime AccountOpenedDate { get; set; }

    public decimal? CreditLimit { get; set; }

}

[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
    [Key]
    public required int OrderLineID { get; set; }

    public required int OrderID { get; set; }

    public required string Description { get; set; }

    public required int Quantity { get; set; }

    public decimal? UnitPrice { get; set; }

    public required decimal TaxRate { get; set; }

}

