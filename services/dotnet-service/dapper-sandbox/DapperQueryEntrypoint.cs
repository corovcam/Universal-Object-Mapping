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

public class StockItem
{
    public int StockItemID { get; set; }
    public required string StockItemName { get; set; }
}

public class Customer
{
    public required int CustomerID { get; set; }
    public required string CustomerName { get; set; }
    public required DateTime AccountOpenedDate { get; set; }
    public decimal? CreditLimit { get; set; }
    public List<CustomerTransaction> CustomerTransactions { get; set; } = [];
    public List<Order> Orders { get; set; } = [];
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
    [JsonIgnore]
    public Customer Customer { get; set; } = null!;
    public List<OrderLine> OrderLines { get; set; } = [];
}

public class OrderLine
{
    public int OrderLineID { get; set; }
    public int OrderID { get; set; }
    [JsonIgnore]
    public Order Order { get; set; } = null!;
    public int StockItemID { get; set; }
    public StockItem StockItem { get; set; } = null!;
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
    static Customer Query2mapRow(Customer c, CustomerTransaction t, Order o, OrderLine ol, StockItem si)
    {
        var customerDict = new Dictionary<int, Customer>();
        if (!customerDict.TryGetValue(c.CustomerID, out var currentCustomer))
        {
            currentCustomer = c;
            currentCustomer.CustomerTransactions = new List<CustomerTransaction>();
            currentCustomer.Orders = new List<Order>();
            customerDict.Add(currentCustomer.CustomerID, currentCustomer);
        }
        if (t != null && !currentCustomer.CustomerTransactions.Any(x => x.CustomerTransactionID == t.CustomerTransactionID))
            currentCustomer.CustomerTransactions.Add(t);
        
        if (o != null)
        {
            var currentOrder = currentCustomer.Orders.FirstOrDefault(x => x.OrderID == o.OrderID);
            if (currentOrder == null)
            {
                currentOrder = o;
                currentOrder.OrderLines = new List<OrderLine>();
                currentCustomer.Orders.Add(currentOrder);
            }
            if (ol != null && !currentOrder.OrderLines.Any(x => x.OrderLineID == ol.OrderLineID))
            {
                ol.StockItem = si;
                currentOrder.OrderLines.Add(ol);
            }
        }
        return currentCustomer;
    }

    public static IEnumerable<Customer> Query(SqlConnection conn)
    {
        string sql = @"
            SELECT c.*, t.*, o.*, ol.*, si.*
            FROM Sales.Customers c
            LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
            LEFT JOIN Sales.Orders o ON c.CustomerID = o.CustomerID
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            LEFT JOIN Warehouse.StockItems si ON ol.StockItemID = si.StockItemID
            WHERE c.CustomerID = 1";
        return conn.Query<Customer, CustomerTransaction, Order, OrderLine, StockItem, Customer>(
            sql, Query2mapRow, splitOn: "CustomerTransactionID,OrderID,OrderLineID,StockItemID").Distinct();
    }

    public static object Harness(SqlConnection conn)
    {
        string sql = @"
            SELECT TOP 1 c.*, t.*, o.*, ol.*, si.*
            FROM Sales.Customers c
            LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
            LEFT JOIN Sales.Orders o ON c.CustomerID = o.CustomerID
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            LEFT JOIN Warehouse.StockItems si ON ol.StockItemID = si.StockItemID
            WHERE c.CustomerID = 1
            ORDER BY c.CustomerID ASC;
            SELECT TOP 1 c.*, t.*, o.*, ol.*, si.*
            FROM Sales.Customers c
            LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
            LEFT JOIN Sales.Orders o ON c.CustomerID = o.CustomerID
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            LEFT JOIN Warehouse.StockItems si ON ol.StockItemID = si.StockItemID
            WHERE c.CustomerID = 1
            ORDER BY c.CustomerID DESC;
            SELECT COUNT(*)
            FROM Sales.Customers c
            LEFT JOIN Sales.CustomerTransactions t ON c.CustomerID = t.CustomerID
            LEFT JOIN Sales.Orders o ON c.CustomerID = o.CustomerID
            LEFT JOIN Sales.OrderLines ol ON o.OrderID = ol.OrderID
            LEFT JOIN Warehouse.StockItems si ON ol.StockItemID = si.StockItemID
            WHERE c.CustomerID = 1;";
        var customerDict = new Dictionary<int, Customer>();
        using var multi = conn.QueryMultiple(sql);
        var firstSample = multi.Read<Customer, CustomerTransaction, Order, OrderLine, StockItem, Customer>(Query2mapRow, splitOn: "CustomerTransactionID,OrderID,OrderLineID,StockItemID").FirstOrDefault();
        var lastSample = multi.Read<Customer, CustomerTransaction, Order, OrderLine, StockItem, Customer>(Query2mapRow, splitOn: "CustomerTransactionID,OrderID,OrderLineID,StockItemID").FirstOrDefault();
        var rowCount = multi.ReadSingle<long>();
        customerDict.Clear();
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
                    SELECT COUNT(*) FROM (SELECT TaxRate, COUNT(*) as Count FROM Sales.OrderLines GROUP BY TaxRate) AS SubQuery;;";
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
    public static void Main(string[] args)
    {   
        string connectionString = args.ElementAtOrDefault(0) 
            ?? Environment.GetEnvironmentVariable("CONNECTION_STRING") 
            ?? "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

        using var conn = new SqlConnection(connectionString);
        conn.Open();

        var results = new Dictionary<string, object?>();
        var harnesses = new Func<object>[] {
            () => Query1.Harness(conn),
            () => Query2.Harness(conn),
            () => Query3.Harness(conn),
            () => Query4.Harness(conn),
            () => Query5.Harness(conn)
        };

        for (int i = 0; i < harnesses.Length; i++) {
            results[$"query{i+1}"] = harnesses[i]();
        }

        Console.WriteLine(CustomJsonSerializer.Serialize(results));
    }
}
