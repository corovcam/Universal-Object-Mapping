using NHibernate.Linq;
using System;
using System.Linq;
using System.Text.Json.Serialization;
using System.Text.Json;
using System.Text.Encodings.Web;
using System.Globalization;
using System.Text.Json.Serialization.Metadata;
using System.Collections.Generic;
using NHibernate.Cfg;
using NHibernate.Driver;
using NHibernate.Mapping.ByCode;
using NHibernate.Mapping.ByCode.Conformist;
using NHibernate.Dialect;

namespace nhibernate_sandbox;

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
    public virtual int StockItemID { get; set; }
    public virtual required string StockItemName { get; set; }
}

public class Customer
{
    public virtual int CustomerID { get; set; }
    public virtual required string CustomerName { get; set; }
    public virtual DateTime AccountOpenedDate { get; set; }
    public virtual decimal? CreditLimit { get; set; }
    public virtual IList<CustomerTransaction> Transactions { get; set; } = [];
    public virtual IList<Order> Orders { get; set; } = [];
}

public class CustomerTransaction
{
    public virtual int CustomerTransactionID { get; set; }
    public virtual int CustomerID { get; set; }
    public virtual DateTime TransactionDate { get; set; }
    public virtual decimal TransactionAmount { get; set; }
}

public class Order
{
    public virtual int OrderID { get; set; }
    public virtual int CustomerID { get; set; }
    [JsonIgnore]
    public virtual Customer Customer { get; set; } = null!;
    public virtual IList<OrderLine> OrderLines { get; set; } = [];
}

public class OrderLine
{
    public virtual int OrderLineID { get; set; }
    public virtual int OrderID { get; set; }
    [JsonIgnore]
    public virtual Order Order { get; set; } = null!;
    public virtual int StockItemID { get; set; }
    public virtual StockItem StockItem { get; set; } = null!;
    public virtual required string Description { get; set; }
    public virtual int PackageTypeID { get; set; }
    public virtual int Quantity { get; set; }
    public virtual decimal? UnitPrice { get; set; }
    public virtual decimal TaxRate { get; set; }
    public virtual int PickedQuantity { get; set; }
    public virtual DateTime? PickingCompletedWhen { get; set; }
    public virtual int LastEditedBy { get; set; }
    public virtual DateTime LastEditedWhen { get; set; }
}

public class CustomerMap : ClassMapping<Customer> {
    public CustomerMap() {
        Table("Customers"); Schema("Sales");
        Id(x => x.CustomerID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerName);
        Property(x => x.AccountOpenedDate);
        Property(x => x.CreditLimit);
        Bag(x => x.Transactions, map => { map.Key(k => k.Column("CustomerID")); }, rel => rel.OneToMany());
        Bag(x => x.Orders, map => { map.Key(k => k.Column("CustomerID")); }, rel => rel.OneToMany());
    }
}
public class CustomerTransactionMap : ClassMapping<CustomerTransaction> {
    public CustomerTransactionMap() {
        Table("CustomerTransactions"); Schema("Sales");
        Id(x => x.CustomerTransactionID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID);
        Property(x => x.TransactionDate);
        Property(x => x.TransactionAmount);
    }
}
public class OrderMap : ClassMapping<Order> {
    public OrderMap() {
        Table("Orders"); Schema("Sales");
        Id(x => x.OrderID, m => m.Generator(Generators.Identity));
        Property(x => x.CustomerID, m => { m.Insert(false); m.Update(false); });
        ManyToOne(x => x.Customer, m => m.Column("CustomerID"));
        Bag(x => x.OrderLines, map => { map.Key(k => k.Column("OrderID")); }, rel => rel.OneToMany());
    }
}
public class OrderLineMap : ClassMapping<OrderLine> {
    public OrderLineMap() {
        Table("OrderLines"); Schema("Sales");
        Id(x => x.OrderLineID, m => m.Generator(Generators.Identity));
        Property(x => x.OrderID, m => { m.Insert(false); m.Update(false); });
        ManyToOne(x => x.Order, m => m.Column("OrderID"));
        Property(x => x.StockItemID, m => { m.Insert(false); m.Update(false); });
        ManyToOne(x => x.StockItem, m => m.Column("StockItemID"));
        Property(x => x.Description);
        Property(x => x.PackageTypeID);
        Property(x => x.Quantity);
        Property(x => x.UnitPrice);
        Property(x => x.TaxRate);
        Property(x => x.PickedQuantity);
        Property(x => x.PickingCompletedWhen);
        Property(x => x.LastEditedBy);
        Property(x => x.LastEditedWhen);
    }
}
public class StockItemMap : ClassMapping<StockItem> {
    public StockItemMap() {
        Table("StockItems"); Schema("Warehouse");
        Id(x => x.StockItemID, m => m.Generator(Generators.Identity));
        Property(x => x.StockItemName);
    }
}

// --- Query Entrypoint ---

public static class NHibernateQueryEntrypoint
{
    public static IQueryable<OrderLine> Query1(NHibernate.ISession session)
    {
        var from = new DateTime(2014, 12, 20);
        var to = new DateTime(2014, 12, 31);
        return session.Query<OrderLine>().Where(ol => ol.PickingCompletedWhen >= from && ol.PickingCompletedWhen <= to);
    }

    public static IQueryable<Customer> Query2(NHibernate.ISession session)
    {
        return session.Query<Customer>()
            .FetchMany(c => c.Transactions)
            .FetchMany(c => c.Orders)
            .ThenFetchMany(o => o.OrderLines)
            .ThenFetch(ol => ol.StockItem)
            .Where(c => c.CustomerID == 1);
    }

    public static IQueryable<object> Query3(NHibernate.ISession session)
    {
        return session.Query<OrderLine>().GroupBy(ol => ol.TaxRate).Select(g => new { TaxRate = g.Key, Count = g.Count() }).OrderByDescending(x => x.Count);
    }

    public static IQueryable<OrderLine> Query4(NHibernate.ISession session)
    {
        return session.Query<OrderLine>().OrderByDescending(ol => ol.Quantity).Take(50);
    }

    public static IQueryable<dynamic> Query5(NHibernate.ISession session)
    {
        return session.Query<OrderLine>().Select(ol => new { ol.OrderLineID, ol.Quantity });
    }

    private static object RunQuery<T>(IQueryable<T> q, Func<T, object>? orderBySelector = null)
    {
        var firstSample = orderBySelector != null ? q.OrderBy(orderBySelector).FirstOrDefault() : q.FirstOrDefault();
        var lastSample = orderBySelector != null ? q.OrderByDescending(orderBySelector).FirstOrDefault() : q.LastOrDefault();
        return new { estimatedRowCount = q.Count(), firstSample, lastSample };
    }

    public static void Main(string[] args)
    {
        string connectionString = args.ElementAtOrDefault(0) 
            ?? System.Environment.GetEnvironmentVariable("CONNECTION_STRING") 
            ?? "Server=localhost,1444;Database=WideWorldImporters;User Id=sa;Password=Testingorms123;TrustServerCertificate=True";

        var configuration = new Configuration()
            .DataBaseIntegration(db =>
            {
                db.ConnectionString = connectionString;
                db.Dialect<MsSql2012Dialect>();
                db.Driver<MicrosoftDataSqlClientDriver>();
                db.LogSqlInConsole = true;
            });

        var mapper = new ModelMapper();
        mapper.AddMapping<CustomerMap>();
        mapper.AddMapping<CustomerTransactionMap>();
        mapper.AddMapping<OrderMap>();
        mapper.AddMapping<OrderLineMap>();
        mapper.AddMapping<StockItemMap>();
        configuration.AddMapping(mapper.CompileMappingForAllExplicitlyAddedEntities());

        using var sessionFactory = configuration.BuildSessionFactory();
        using var session = sessionFactory.OpenSession();

        var results = new Dictionary<string, object?>();
        var harnesses = new Func<object>[] {
            () => RunQuery(Query1(session), ol => ol.OrderLineID),
            () => RunQuery(Query2(session), c => c.CustomerID),
            () => RunQuery(Query3(session)), // No order by for Query3, as it already has a deterministic order by clause
            () => RunQuery(Query4(session)), // Same as Query3, Query4 already has an order by clause
            () => RunQuery(Query5(session), ol => ol.OrderLineID)
        };

        for (int i = 0; i < harnesses.Length; i++) {
            try { results[$"query{i+1}"] = harnesses[i](); } catch (Exception ex) { Console.Error.WriteLine($"Error executing query{i+1}: {ex.Message}"); results[$"query{i+1}"] = null; }
        }

        Console.WriteLine(CustomJsonSerializer.Serialize(results));
    }
}
