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

namespace EFCoreSandbox;

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
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DictionaryKeyPolicy = JsonNamingPolicy.CamelCase,
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
            new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) 
        }
    };

    public static string Serialize(object entity)
    {
        return JsonSerializer.Serialize(entity, Options);
    }
}

// --- Schema and Related Settings ---

[Table("Customers", Schema = "Sales")]
public class Customer
{
    [Key]
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
    public int CustomerTransactionID { get; set; }

    [ForeignKey(nameof(Customer))]
    public int CustomerID { get; set; }

    public DateTime TransactionDate { get; set; }

    public decimal TransactionAmount { get; set; }
}

[Table("Orders", Schema = "Sales")]
public class Order
{
    [Key]
    public int OrderID { get; set; }

    public int CustomerID { get; set; }

    public List<OrderLine> OrderLines { get; set; } = [];
}

[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
    [Key]
    public int OrderLineID { get; set; }

    [ForeignKey(nameof(Order))]
    public int OrderID { get; set; }

    public int StockItemID { get; set; }

    public required string Description { get; set; }

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
    public static IQueryable<OrderLine> Query(SandboxDbContext context)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);

        var query = context.OrderLines
            .Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
        
        return query;
    }

    public static void Main(string[] args)
    {   
        // Context/setup code
        using var context = new SandboxDbContext(
            new DbContextOptionsBuilder<SandboxDbContext>()
                .UseSqlServer(
                    args.ElementAtOrDefault(0) ?? Environment.GetEnvironmentVariable("CONNECTION_STRING") 
                        ?? "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True"
                )
                .UseQueryTrackingBehavior(QueryTrackingBehavior.NoTracking).Options
        );

        // Non-materialized query
        var query = Query(context);

        // Deterministic sorting
        var firstSample = query.OrderBy(ol => ol.OrderLineID).FirstOrDefault();
        var lastSample = query.OrderByDescending(ol => ol.OrderLineID).FirstOrDefault();

        // Collect results and serialize
        var result = new SortedDictionary<string, object?>
        {
            { "sqlString", query.ToQueryString() },
            { "estimatedRowCount", query.Count() },
            { "firstSample", firstSample },
            { "lastSample", lastSample }
        };
        Console.WriteLine(CustomJsonSerializer.Serialize(result));
    }
}
