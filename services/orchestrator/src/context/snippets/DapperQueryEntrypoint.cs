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

namespace dapper_sandbox;

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
    public Customer Customer { get; set; } = null!;
    public List<OrderLine> OrderLines { get; set; } = [];
}

public class OrderLine
{
    public int OrderLineID { get; set; }
    public int OrderID { get; set; }
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

// --- Queries ---

public static class Query1
{
    public static IEnumerable<OrderLine> Query(SqlConnection conn)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        string sql = @"SELECT * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To";
        return conn.Query<OrderLine>(sql, new { From = from, To = to });
    }

    public static object Harness(SqlConnection conn)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        var sql = @"
            SELECT TOP 1 * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To ORDER BY OrderLineID ASC;
            SELECT TOP 1 * FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To ORDER BY OrderLineID DESC;
            SELECT COUNT(*) FROM Sales.OrderLines WHERE PickingCompletedWhen >= @From AND PickingCompletedWhen <= @To;";
        using var multi = conn.QueryMultiple(sql, new { From = from, To = to });
        return new { firstSample = multi.ReadSingle<OrderLine>(), lastSample = multi.ReadSingle<OrderLine>(), estimatedRowCount = multi.ReadSingle<long>() };
    }
}

public static class Query2
{
    static Order Query2mapRow(Order o, Customer c, CustomerTransaction t,  OrderLine ol)
    {
        o.Customer = c;
        o.OrderLines.Add(ol);
        if (c != null) {
            if (t != null)
            {
                c.CustomerTransactions.Add(t);
            }
        }
        return o;
    }

    public static IEnumerable<Order> Query(SqlConnection conn)
    {
        string sql = @"
            SELECT o.*, c.*, t.*, ol.*
            FROM Sales.Orders o
            LEFT JOIN Sales.Customers c ON o.CustomerID = c.CustomerID
            LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            WHERE o.CustomerID = 1";
        var duplicates = conn.Query<Order, Customer, CustomerTransaction, OrderLine, Order>(
            sql, Query2mapRow, splitOn: "CustomerID,CustomerTransactionID,OrderLineID");
        var result = duplicates.GroupBy(o => o.OrderID).Select(g => {
            var order = g.First();
            order.OrderLines = g.SelectMany(o => o.OrderLines).Where(ol => ol != null).GroupBy(ol => ol.OrderLineID).Select(g2 => g2.First()).ToList();
            order.Customer?.CustomerTransactions = g.SelectMany(o => o.Customer.CustomerTransactions).Where(t => t != null).GroupBy(t => t.CustomerTransactionID).Select(g2 => g2.First()).ToList();
            return order;
        });
        return result;
    }

    public static object Harness(SqlConnection conn)
    {
        string sql = @"
            SELECT TOP 1 o.*, c.*, t.*, ol.*
            FROM Sales.Orders o
            LEFT JOIN Sales.Customers c ON o.CustomerID = c.CustomerID
            LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            WHERE o.CustomerID = 1
            ORDER BY o.OrderID ASC;
            SELECT TOP 1 o.*, c.*, t.*, ol.*
            FROM Sales.Orders o
            LEFT JOIN Sales.Customers c ON o.CustomerID = c.CustomerID
            LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            WHERE o.CustomerID = 1
            ORDER BY o.OrderID DESC;
            SELECT COUNT(*)
            FROM Sales.Orders o
            LEFT JOIN Sales.Customers c ON o.CustomerID = c.CustomerID
            LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            WHERE o.OrderID = 1;";
        using var multi = conn.QueryMultiple(sql);
        var firstSample = multi.Read<Order, Customer, CustomerTransaction, OrderLine, Order>(Query2mapRow, splitOn: "CustomerID,CustomerTransactionID,OrderLineID").FirstOrDefault();
        var lastSample = multi.Read<Order, Customer, CustomerTransaction, OrderLine, Order>(Query2mapRow, splitOn: "CustomerID,CustomerTransactionID,OrderLineID").FirstOrDefault();
        var rowCount = multi.ReadSingle<long>();
        return new { firstSample, lastSample, estimatedRowCount = rowCount };
    }
}

public static class Query3
{
    public static IEnumerable<(decimal TaxRate, int Count)> Query(SqlConnection conn)
    {
        string sql = @"SELECT TaxRate, COUNT(*) as Count FROM Sales.OrderLines GROUP BY TaxRate ORDER BY Count DESC";
        return conn.Query<(decimal TaxRate, int Count)>(sql);
    }

    public static object Harness(SqlConnection conn)
    {
        var sql = @"SELECT TOP 1 TaxRate, COUNT(*) as Count FROM Sales.OrderLines GROUP BY TaxRate ORDER BY Count DESC;
                    SELECT TOP 1 TaxRate, COUNT(*) as Count FROM Sales.OrderLines GROUP BY TaxRate ORDER BY Count ASC;
                    SELECT COUNT(*) FROM (SELECT TaxRate, COUNT(*) as Count FROM Sales.OrderLines GROUP BY TaxRate) AS SubQuery;";
        using var multi = conn.QueryMultiple(sql);
        return new { firstSample = multi.ReadSingle<dynamic>(), lastSample = multi.ReadSingle<dynamic>(), estimatedRowCount = multi.ReadSingle<long>() };
    }
}

public static class Query4
{
    public static IEnumerable<OrderLine> Query(SqlConnection conn)
    {
        string sql = @"SELECT TOP 50 * FROM Sales.OrderLines ORDER BY Quantity DESC";
        return conn.Query<OrderLine>(sql);
    }

    public static object Harness(SqlConnection conn)
    {
        var sql = @"SELECT TOP 1 * FROM Sales.OrderLines ORDER BY Quantity DESC;
                    SELECT TOP 1 * FROM Sales.OrderLines ORDER BY Quantity ASC;
                    SELECT COUNT(*) FROM (SELECT TOP 50 * FROM Sales.OrderLines ORDER BY Quantity DESC) AS SubQuery;";
        using var multi = conn.QueryMultiple(sql);
        return new { firstSample = multi.ReadSingle<OrderLine>(), lastSample = multi.ReadSingle<OrderLine>(), estimatedRowCount = multi.ReadSingle<long>() };
    }
}

public static class Query5
{
    public static IEnumerable<(int OrderLineID, int Quantity)> Query(SqlConnection conn)
    {
        string sql = @"SELECT OrderLineID, Quantity FROM Sales.OrderLines";
        return conn.Query<(int OrderLineID, int Quantity)>(sql);
    }
    
    public static object Harness(SqlConnection conn)
    {
        var sql = @"
            SELECT TOP 1 OrderLineID, Quantity FROM Sales.OrderLines ORDER BY OrderLineID ASC;
            SELECT TOP 1 OrderLineID, Quantity FROM Sales.OrderLines ORDER BY OrderLineID DESC;
            SELECT COUNT(*) FROM Sales.OrderLines;";
        using var multi = conn.QueryMultiple(sql);
        return new { firstSample = multi.ReadSingle<dynamic>(), lastSample = multi.ReadSingle<dynamic>(), estimatedRowCount = multi.ReadSingle<long>() };
    }
}

// --- Query Entrypoint ---

public static class DapperQueryEntrypoint
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
        string connectionString = args.ElementAtOrDefault(0) 
            ?? Environment.GetEnvironmentVariable("CONNECTION_STRING") 
            ?? "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

        using var conn = new SqlConnection(connectionString);
        conn.Open();

        // First, validate that our entity mappings are correct and can be used to query the database without errors
        ValidateEntity<Customer>(conn, "Sales", "Customers");
        ValidateEntity<CustomerTransaction>(conn, "Sales", "CustomerTransactions");
        ValidateEntity<Order>(conn, "Sales", "Orders");
        ValidateEntity<OrderLine>(conn, "Sales", "OrderLines");

        // Now create and execute the queries and capture results
        var results = new Dictionary<string, object?>();
        var harnesses = new Func<object>[] {
            () => Query1.Harness(conn),
            () => Query2.Harness(conn),
            () => Query3.Harness(conn),
            () => Query4.Harness(conn),
            () => Query5.Harness(conn)
        };

        for (int i = 0; i < harnesses.Length; i++) {
            var qid = i+1;
            Console.WriteLine($"Running Query {qid}...");
            try {
                results[$"query{qid}"] = harnesses[i]();
                Console.WriteLine($"Successfully ran Query {qid}");
            } catch (Exception ex) {
                Console.WriteLine($"Error occurred while running Query{qid}: {ex}");
            }
        }
        
        var resultsPath = Environment.GetEnvironmentVariable("DAPPER_RESULTS_PATH");
        if (!string.IsNullOrEmpty(resultsPath))
        {
            System.IO.File.WriteAllText($"{resultsPath}/dapper_results_{DateTime.Now:yyyyMMdd_HHmmss}.json", CustomJsonSerializer.Serialize(results));
        }
        else
        {
            Console.WriteLine(CustomJsonSerializer.Serialize(results));
        }
    }
}
