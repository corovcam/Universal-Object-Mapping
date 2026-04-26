using System;
using System.Linq;
using System.Text.Json.Serialization;
using System.Text.Json;
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using System.Collections.Generic;
using Dapper;
using Microsoft.Data.SqlClient;

namespace DapperSandbox;

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
            if (typeInfo.Kind != JsonTypeInfoKind.Object) return;
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

public class Customer
{
    public required int CustomerID { get; set; }

    public required string CustomerName { get; set; }

    public required DateTime AccountOpenedDate { get; set; }

    public decimal? CreditLimit { get; set; }

    public List<CustomerTransaction> CustomerTransactions { get; set; } = [];
}

public class CustomerTransaction
{
    public int CustomerTransactionID { get; set; }

    public int CustomerID { get; set; }

    public DateTime TransactionDate { get; set; }

    public decimal TransactionAmount { get; set; }
}

public class Order
{
    public int OrderID { get; set; }

    public int CustomerID { get; set; }

    public List<OrderLine> OrderLines { get; set; } = [];
}

public class OrderLine
{
    public int OrderLineID { get; set; }

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

// --- Query Entrypoint ---

public static class DapperQueryEntrypoint
{   
    public static IEnumerable<OrderLine> Query1(SqlConnection conn)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);

        string sql = @"SELECT * FROM Sales.OrderLines 
                       WHERE PickingCompletedWhen >= @From 
                       AND PickingCompletedWhen <= @To";
        
        return conn.Query<OrderLine>(sql, new { From = from, To = to });
    }
    
    public static (OrderLine?, OrderLine?, int) Query1Harness(SqlConnection conn)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        var sql = @"SELECT TOP 1 * FROM Sales.OrderLines 
                    WHERE PickingCompletedWhen >= @From 
                    AND PickingCompletedWhen <= @To
                    ORDER BY OrderLineID ASC;
                    SELECT TOP 1 * FROM Sales.OrderLines 
                    WHERE PickingCompletedWhen >= @From 
                    AND PickingCompletedWhen <= @To
                    ORDER BY OrderLineID DESC;
                    SELECT COUNT(*) FROM Sales.OrderLines 
                    WHERE PickingCompletedWhen >= @From 
                    AND PickingCompletedWhen <= @To;";
        using var multi = conn.QueryMultiple(sql, new { From = from, To = to });
        var firstSample = multi.ReadFirstOrDefault<OrderLine>();
        var lastSample = multi.ReadFirstOrDefault<OrderLine>();
        var rowCount = multi.ReadFirst<int>();
        return (firstSample, lastSample, rowCount);
    }

    public static void Main(string[] args)
    {   
        string connectionString = args.ElementAtOrDefault(0) 
            ?? Environment.GetEnvironmentVariable("CONNECTION_STRING") 
            ?? "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

        using var conn = new SqlConnection(connectionString);
        conn.Open();

        var (firstSample, lastSample, rowCount) = Query1Harness(conn);
        
        var result = new SortedDictionary<string, object?>
        {
            { "estimatedRowCount", rowCount },
            { "firstSample", firstSample },
            { "lastSample", lastSample }
        };
        Console.WriteLine(CustomJsonSerializer.Serialize(result));
    }
}
