using System;
using System.Linq;
using Microsoft.EntityFrameworkCore;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using System.Text.Json.Serialization;
using System.Text.Json;
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Logging;

namespace efcore_sandbox;

// --- Harness and Utilities ---

public static class CustomJsonSerializer
{
    public class StrictIsoDateTimeConverter : JsonConverter<DateTime>
    {
        public override DateTime Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            return DateTime.Parse(
                reader.GetString()!,
                CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);
        }

        public override void Write(Utf8JsonWriter writer, DateTime value, JsonSerializerOptions options)
        {
            writer.WriteStringValue(value.ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture));
        }
    }

    public class StrictIsoDateTimeOffsetConverter : JsonConverter<DateTimeOffset>
    {
        public override DateTimeOffset Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            return DateTimeOffset.Parse(reader.GetString()!, CultureInfo.InvariantCulture);
        }

        public override void Write(Utf8JsonWriter writer, DateTimeOffset value, JsonSerializerOptions options)
        {
            writer.WriteStringValue(
                value.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss.fff'Z'", CultureInfo.InvariantCulture));
        }
    }

    public class FixedDecimalConverter : JsonConverter<decimal>
    {
        public override decimal Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            return reader.GetDecimal();
        }

        public override void Write(Utf8JsonWriter writer, decimal value, JsonSerializerOptions options)
        {
            writer.WriteRawValue(value.ToString("0.000", CultureInfo.InvariantCulture));
        }
    }

    public class FixedDoubleConverter : JsonConverter<double>
    {
        public override double Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            return reader.GetDouble();
        }

        public override void Write(Utf8JsonWriter writer, double value, JsonSerializerOptions options)
        {
            writer.WriteRawValue(value.ToString("0.000", CultureInfo.InvariantCulture));
        }
    }

    public class CustomCamelCaseNamingPolicy : JsonNamingPolicy
    {
        public override string ConvertName(string name)
        {
            if (string.IsNullOrEmpty(name)) return name;
            string camelCased = CamelCase.ConvertName(name);
            if (camelCased.EndsWith("ID"))
            {
                return camelCased[..^2] + "Id";
            } else if (camelCased.EndsWith("URL"))
            {
                return camelCased[..^3] + "Url";
            }
            return camelCased;
        }
    }

    public static Action<JsonTypeInfo> AlphabetizeProperties()
    {
        return static typeInfo =>
        {
            if (typeInfo.Kind!= JsonTypeInfoKind.Object) return;
            var properties = typeInfo.Properties.OrderBy(p => p.Name, StringComparer.Ordinal).ToList();
            typeInfo.Properties.Clear();
            for (int i = 0; i < properties.Count; i++)
            {
                properties[i].Order = i;
                typeInfo.Properties.Add(properties[i]);
            }
        };
    }

    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = new CustomCamelCaseNamingPolicy(),
        DictionaryKeyPolicy = new CustomCamelCaseNamingPolicy(),
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        ReferenceHandler = ReferenceHandler.IgnoreCycles,
        TypeInfoResolver = new DefaultJsonTypeInfoResolver
        {
            Modifiers = { AlphabetizeProperties() }
        },
        Converters = { 
            new StrictIsoDateTimeConverter(), 
            new StrictIsoDateTimeOffsetConverter(),
            new FixedDecimalConverter(),
            new FixedDoubleConverter(),
            new JsonStringEnumConverter(new CustomCamelCaseNamingPolicy()) 
        }
    };

    public static string Serialize(object? entity)
    {
        return JsonSerializer.Serialize(entity, Options);
    }
}

// --- Schema and Related Settings ---

[Table("Customers", Schema = "Sales")]
public class Customer
{
    [Key]
    [JsonPropertyName("customerId")]
    public required int CustomerID { get; set; }
    [MaxLength(200)]
    public required string CustomerName { get; set; }
    [Column(TypeName="datetime2")]
    [Precision(7)]
    public required DateTime AccountOpenedDate { get; set; }
    [Column(TypeName="decimal")]
    [Precision(18, 2)]
    public decimal? CreditLimit { get; set; }

    public List<CustomerTransaction> CustomerTransactions { get; set; } = [];
}

[Table("CustomerTransactions", Schema = "Sales")]
public class CustomerTransaction
{
    [Key]
    [JsonPropertyName("customerTransactionId")]
    public int CustomerTransactionID { get; set; }
    [ForeignKey(nameof(Customer))]
    [JsonPropertyName("customerId")]
    public int CustomerID { get; set; }
    public DateTime TransactionDate { get; set; }
    public decimal TransactionAmount { get; set; }
}

[Table("Orders", Schema = "Sales")]
public class Order
{
    [Key]
    [JsonPropertyName("orderId")]
    public int OrderID { get; set; }
    [ForeignKey(nameof(Customer))]
    [JsonPropertyName("customerId")]
    public int CustomerID { get; set; }

    public Customer Customer { get; set; } = null!;
    public List<OrderLine> OrderLines { get; set; } = [];
}

[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
    [Key]
    [JsonPropertyName("orderLineId")]
    public int OrderLineID { get; set; }
    [ForeignKey(nameof(Order))]
    [JsonPropertyName("orderId")]
    public int OrderID { get; set; }
    [JsonPropertyName("stockItemId")]
    public int StockItemID { get; set; }
    public required string Description { get; set; }
    [JsonPropertyName("packageTypeId")]
    public int PackageTypeID { get; set; }
    public int Quantity { get; set; }
    public decimal? UnitPrice { get; set; }
    public decimal TaxRate { get; set; }
    public int PickedQuantity { get; set; }
    public DateTime? PickingCompletedWhen { get; set; }
    public int LastEditedBy { get; set; }
    public DateTime LastEditedWhen { get; set; }
}

public class SandboxDbContext(DbContextOptions<SandboxDbContext> options) : DbContext(options)
{
    public DbSet<Customer> Customers => Set<Customer>();
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<CustomerTransaction> CustomerTransactions => Set<CustomerTransaction>();
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
}

// --- Query Entrypoint ---

public static class EFCoreQueryEntrypoint
{   
    public static IQueryable<OrderLine> Query1(SandboxDbContext ctx)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        return ctx.OrderLines.Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
    }

    public static IQueryable<Order> Query2(SandboxDbContext ctx)
    {
        return ctx.Orders
            .Include(o => o.Customer)
                .ThenInclude(c => c.CustomerTransactions)
            .Include(o => o.OrderLines)
            .AsSplitQuery()
            .Where(c => c.CustomerID == 1);
    }

    public static IQueryable<dynamic> Query3(SandboxDbContext ctx)
    {
        return ctx.OrderLines.GroupBy(ol => ol.TaxRate).Select(g => new { TaxRate = g.Key, Count = g.Count() }).OrderByDescending(x => x.Count);
    }

    public static IQueryable<OrderLine> Query4(SandboxDbContext ctx)
    {
        return ctx.OrderLines.OrderByDescending(ol => ol.Quantity).Take(50);
    }

    public static IQueryable<dynamic> Query5(SandboxDbContext ctx)
    {
        return ctx.OrderLines.Select(ol => new { ol.OrderLineID, ol.Quantity });
    }

    private static object RunQuery<T>(Func<IQueryable<T>> q, Func<T, object>? orderBySelector = null)
    {
        var query = q();
        var count = query.Count();
        return new { sqlString = query.ToQueryString(), count, 
            firstSample = count > 0 ? (orderBySelector != null ? q().OrderBy(orderBySelector).FirstOrDefault() : query.FirstOrDefault()) : default, 
            lastSample = count > 1 ? (orderBySelector != null ? q().OrderByDescending(orderBySelector).FirstOrDefault() : query.LastOrDefault()) : default };
    }

    public static void ValidateEntity<T>(SandboxDbContext ctx) where T : class
    {
        Console.WriteLine($"Validating EF Core entity: {typeof(T).Name}");
        Console.WriteLine(CustomJsonSerializer.Serialize(ctx.Set<T>().FirstOrDefault()));
        Console.WriteLine($"Successfully validated EF Core entity: {typeof(T).Name}");
    }

    public static void Main(string[] args)
    {   
        using var context = new SandboxDbContext(
            new DbContextOptionsBuilder<SandboxDbContext>()
                .UseSqlServer(
                    args.ElementAtOrDefault(0) ?? Environment.GetEnvironmentVariable("CONNECTION_STRING") 
                        ?? "Server=localhost,1333;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True"
                )
                .UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking)
                .EnableSensitiveDataLogging()
                .LogTo(Console.WriteLine, [DbLoggerCategory.Database.Command.Name], minimumLevel: LogLevel.Information, options: DbContextLoggerOptions.SingleLine).Options
        );

        // First, validate that our entity mappings are correct and can be used to query the database without errors
        ValidateEntity<Customer>(context);
        ValidateEntity<CustomerTransaction>(context);
        ValidateEntity<Order>(context);
        ValidateEntity<OrderLine>(context);

        // Now create and execute the queries and capture results
        var results = new Dictionary<string, object?>();
        var harnesses = new Func<object>[] {
            () => RunQuery(() => Query1(context), ol => ol.OrderLineID),
            () => RunQuery(() => Query2(context), o => o.OrderID),
            () => RunQuery(() => Query3(context), x => x.TaxRate), // sorting by TaxRate, since it's unique in a groupBy result
            () => RunQuery(() => Query4(context)), // sorting by non-unique column with limiting (.Take) is present; top results may not be consistent accross DBMSs; sorting by unique-column is not possible 
            () => RunQuery(() => Query5(context), ol => ol.OrderLineID)
        };

        for (int i = 0; i < harnesses.Length; i++) {
            var qid = i+1;
            Console.WriteLine($"Running Query {qid}...");
            try {
                results[$"query{qid}"] = harnesses[i]();
            } catch (Exception ex) {
                results[$"query{qid}"] = new { error = ex.Message };
                Console.Error.WriteLine($"Error occurred while running Query{qid}: {ex}");
            }
        }
        File.WriteAllText($"{Environment.GetEnvironmentVariable("EFCORE_RESULTS_PATH")}/efcore_results_{DateTime.Now:yyyyMMdd_HHmmss}.json", CustomJsonSerializer.Serialize(results));
    }
}
