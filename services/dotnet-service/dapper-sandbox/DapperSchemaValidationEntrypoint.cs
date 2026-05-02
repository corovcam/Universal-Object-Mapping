using System;
using System.Linq;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using System.Collections.Generic;
using Dapper;
using Microsoft.Data.SqlClient;
using System.Text.Json.Serialization.Metadata;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Globalization;
using System.Text.Encodings.Web;

namespace dapper_sandbox;

// --- Schema and Related Settings ---

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

[Table("Customers", Schema = "Sales")]
public class Customer
{
    [Key]
    public int CustomerID { get; set; }
    public string CustomerName { get; set; } = string.Empty;
    public DateTime AccountOpenedDate { get; set; }
    public decimal? CreditLimit { get; set; }
}

[Table("CustomerTransactions", Schema = "Sales")]
public class CustomerTransaction
{
    [Key]
    public int CustomerTransactionID { get; set; }
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
}

[Table("OrderLines", Schema = "Sales")]
public class OrderLine
{
    [Key]
    public int OrderLineID { get; set; }
    public int OrderID { get; set; }
    public int StockItemID { get; set; }
    public string Description { get; set; } = string.Empty;
    public int PackageTypeID { get; set; }
    public int Quantity { get; set; }
    public decimal? UnitPrice { get; set; }
    public decimal TaxRate { get; set; }
    public int PickedQuantity { get; set; }
    public DateTime? PickingCompletedWhen { get; set; }
    public int LastEditedBy { get; set; }
    public DateTime LastEditedWhen { get; set; }
}

// --- Schema Validation Entrypoint ---

public static class DapperSchemaValidationEntrypoint
{
    public static void ValidateEntity<T>(SqlConnection conn, string schema, string table)
    {
        Console.WriteLine($"Validating Dapper entity: {typeof(T).Name}");
        var sql = $"SELECT TOP 1 * FROM {schema}.{table}";
        Console.WriteLine(CustomJsonSerializer.Serialize(conn.QueryFirstOrDefault<T>(sql)));
        Console.WriteLine($"Successfully validated Dapper entity: {typeof(T).Name}");
    }

    public static void Main(string[] args)
    {
        var connectionString = args.ElementAtOrDefault(0) ?? Environment.GetEnvironmentVariable("CONNECTION_STRING") 
            ?? "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

        using var conn = new SqlConnection(connectionString);
        conn.Open();
        
        var queries = new Action[] {
            () => ValidateEntity<Customer>(conn, "Sales", "Customers"),
            () => ValidateEntity<CustomerTransaction>(conn, "Sales", "CustomerTransactions"),
            () => ValidateEntity<Order>(conn, "Sales", "Orders"),
            () => ValidateEntity<OrderLine>(conn, "Sales", "OrderLines")
        };

        foreach (var query in queries) {
            try {
                query();
            } catch (Exception ex) {
                Console.Error.WriteLine($"Error occurred while validating entity: {ex}");
            }
        }
    }
}
